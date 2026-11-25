"""Method-only stacking of previously out-of-year conditional distributions.
No target outcomes enter weights. Winner mass never changes. Research only.
"""
import numpy as np
from scipy.optimize import minimize, minimize_scalar

def validate(x):
    p=np.asarray(x,float)
    if p.ndim!=3 or p.shape[1]!=2 or p.shape[2]!=3:
        raise ValueError("expected model x potential winner x method")
    if not np.isfinite(p).all() or np.any(p<0) or not np.allclose(p.sum(2),1,atol=1e-8,rtol=0):
        raise ValueError("invalid conditional simplex")
    return p

def group(f):
    # Fixed pre-fight rules. No result, odds, weight class inference or
    # invented style labels. "Higher grappling activity" is a proxy only.
    n=min(f["a_prior_ufc_bouts"],f["b_prior_ufc_bouts"])
    if n<3:return "limited_UFC_history"
    fields=[f.get(s+"_"+k) for s in ("a","b") for k in
            ("own_sub_attempts_per15","own_takedowns_landed_per15")]
    if any(x is None or not np.isfinite(x) for x in fields):
        return "unknown_activity"
    if min(f["a_stats_coverage"],f["b_stats_coverage"])<.8:
        return "unknown_activity"
    if max(fields[0],fields[2])>=1 or max(fields[1],fields[3])>=3:
        return "higher_grappling_activity"
    return "other_established"

def fit_weights(obs,anchor=None,penalty=12.):
    # obs contains probability each model assigned to actual method GIVEN
    # actual winner, solely on previous out-of-year predictions.
    x=np.asarray(obs,float)
    if x.ndim!=2 or not len(x) or not np.isfinite(x).all() or np.any(x<0) or np.any(x>1):
        raise ValueError("invalid earlier validation probabilities")
    m=x.shape[1]
    a=np.ones(m)/m if anchor is None else np.asarray(anchor,float)
    if a.shape!=(m,) or np.any(a<0) or abs(a.sum()-1)>1e-8:
        raise ValueError("invalid anchor")
    def loss(w):
        return -np.log(np.maximum(x@w,1e-12)).sum()+penalty*np.sum((w-a)**2)
    r=minimize(loss,a,method="SLSQP",bounds=[(0,1)]*m,
        constraints=[{"type":"eq","fun":lambda w:w.sum()-1}],
        options={"maxiter":300,"ftol":1e-9})
    if not r.success or np.any(r.x< -1e-8) or abs(r.x.sum()-1)>1e-7:
        raise ValueError("weight optimization failed: "+r.message)
    w=np.maximum(r.x,0);return w/w.sum()

def blend(p,w):
    p=validate(p);w=np.asarray(w,float)
    if w.shape!=(p.shape[0],) or np.any(w<0) or not np.isfinite(w).all() or abs(w.sum()-1)>1e-8:
        raise ValueError("invalid weight simplex")
    return np.einsum("m,msk->sk",w,p)

def temper(p,t):
    if not .5<=t<=3:raise ValueError("invalid temperature")
    v=np.maximum(np.asarray(p,float),1e-12)**(1/t)
    return v/v.sum(axis=-1,keepdims=True)

def fit_temperature(p,y):
    p=np.asarray(p,float);y=np.asarray(y,int)
    if p.shape!=(len(y),3) or not len(y):raise ValueError("invalid calibration set")
    def loss(t):
        q=temper(p,t)
        return -np.log(q[np.arange(len(y)),y]).sum()+12*(np.log(t)**2)
    r=minimize_scalar(loss,bounds=(.5,3),method="bounded")
    if not r.success:raise ValueError("temperature optimization failed")
    return float(r.x)

def fit(rows):
    if not rows:raise ValueError("empty meta training")
    observed=np.array([validate(r["p"])[:,r["side"],r["method"]] for r in rows])
    w=fit_weights(observed)
    groups={}
    for g in sorted({r["group"] for r in rows}):
        ids=[i for i,r in enumerate(rows) if r["group"]==g]
        # Shrink group weights strongly to the global solution.
        if len(ids)>=80:groups[g]=fit_weights(observed[ids],w,penalty=80.)
    cal=np.array([blend(r["p"],w)[r["side"]] for r in rows])
    temp=fit_temperature(cal,[r["method"] for r in rows])
    return w,groups,temp

def predict(p,g,fitted):
    w,groups,t=fitted
    eq=blend(p,np.ones(len(w))/len(w))
    glob=blend(p,w)
    return {"equal_blend":eq,"learned_global":glob,
            "learned_group":blend(p,groups.get(g,w)),
            "learned_global_temperature":temper(glob,t)}
