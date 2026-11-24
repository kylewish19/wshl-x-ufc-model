"""Opponent-adjusted historical method/access measurements, research only.

For each completed fight compare the observed attack with the opponent's
PRE-day defensive exposure rate (and vice versa). Store residuals with
shrinkage, reliability counts and bounded PRE-day UFC Elo weighting.
Not a causal estimate or a direct get-up/submission escape measurement.
"""
from collections import defaultdict
from itertools import groupby
import numpy as np

CHANNELS=("KO_win","SUB_win","knockdown","submission_attempt","grappling_access")
PRIOR=np.array([.18,.09,.22,.25,.45])
ALPHA=6.
N=20
MATCH_N=45

def fresh():
    return {"n":np.zeros((2,5)), "hits":np.zeros((2,5)),
            "weighted_n":np.zeros((2,5)), "residual":np.zeros((2,5)),
            "elo":1500.}

def rates(s):
    return (s["hits"]+ALPHA*PRIOR)/(s["n"]+ALPHA)

def vec(s):
    return np.r_[(s["residual"]/(s["weighted_n"]+ALPHA)).ravel(),
                 np.log1p(s["n"]).ravel()]

def observed(result,method,stats):
    v=np.full(5,np.nan)
    if result in ("W","L","D"):
        v[:2]=[result=="W" and method=="KO_TKO",result=="W" and method=="SUB"]
    if stats is not None:
        def valid(k):
            x=stats.get(k)
            return x is not None and np.isfinite(x) and x>=0
        for i,k in ((2,"kd"),(3,"sub_att")):
            if valid(k):v[i]=float(stats[k]>0)
        if valid("td_landed") and valid("ctrl_sec"):
            v[4]=float(stats["td_landed"]>0 or stats["ctrl_sec"]>=60)
    return v

def update(s,own,other,rival_pre,rival_elo):
    # Larger weight against stronger UFC opposition; fixed conservative bound.
    # No claim that UFC-only Elo measures complete regional ability.
    weight=float(np.clip(1+(rival_elo-1500)/800,.5,1.5))
    for role,(v,e) in enumerate(((own,rival_pre[1]),(other,rival_pre[0]))):
        ok=np.isfinite(v)
        s["n"][role,ok]+=1
        s["hits"][role,ok]+=v[ok]
        s["weighted_n"][role,ok]+=weight
        s["residual"][role,ok]+=weight*(v[ok]-e[ok])

def matchup(a,b):
    va,ra=a;vb,rb=b
    # Log-odds additive exposure proxy: not calibrated forecast of access.
    def logit(x):
        x=np.clip(x,.001,.999)
        return np.log(x/(1-x))
    combined=1/(1+np.exp(-(logit(ra[0])+logit(rb[1])-logit(PRIOR))))
    out=np.r_[va,vb,combined]
    if out.shape!=(MATCH_N,) or not np.isfinite(out).all():raise ValueError("bad matchup features")
    return out

def build(records):
    states=defaultdict(fresh);out={};counts=0;covered=0
    for day,batch in groupby(sorted(records,key=lambda r:(r["date"],r["event"],r["a"],r["b"])),key=lambda r:r["date"]):
        rows=list(batch)
        names={r[z] for r in rows for z in ("a","b")}
        pre={n:(vec(states[n]),rates(states[n]),states[n]["elo"]) for n in names}
        for r in rows:
            a,b=r["a"],r["b"]
            key=(day.isoformat(),r["event"],*sorted((a,b)))
            if a==b or key in out:raise ValueError("duplicate historical identity")
            out[key]=(a,b,matchup(pre[a][:2],pre[b][:2]),matchup(pre[b][:2],pre[a][:2]))
        for r in rows:
            a,b=r["a"],r["b"];pa,pb=pre[a],pre[b]
            va=observed(r["result"][0],r["method"],r.get("stats_a"))
            vb=observed(r["result"][1],r["method"],r.get("stats_b"))
            update(states[a],va,vb,pb[1],pb[2]);update(states[b],vb,va,pa[1],pa[2])
            score={"W":1.,"L":0.,"D":.5}[r["result"][0]]
            delta=24*(score-1/(1+10**((pb[2]-pa[2])/400)))
            states[a]["elo"]+=delta;states[b]["elo"]-=delta
            counts+=1;covered+=int(np.isfinite(va[2:]).all() and np.isfinite(vb[2:]).all())
    return out,{"historical_bouts":counts,"both_fighters_all_access_fields_present":covered,
        "fighter_count":len(states),"same_date_frozen":True,
        "opponent_quality":"UFC-only Elo at time of historical meeting",
        "n_features":MATCH_N}

def features(f,side,lookup):
    if f["event_date"]!=f["feature_as_of_exclusive"]:raise ValueError("not as-of")
    key=(f["event_date"],f["event"],*sorted((f["fighter_a"],f["fighter_b"])))
    a,b,va,vb=lookup[key]
    name=f["fighter_"+side]
    if name==a:return va
    if name==b:return vb
    raise ValueError("fighter identity mismatch")
