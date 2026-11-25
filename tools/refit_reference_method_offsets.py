"""Rebuild Reference method offsets on corrected chronological baselines.
Retrospective development only: actual-winner conditional method diagnostics
are not joint winner/method accuracy or genuine frozen forecasts.
"""
from pathlib import Path
import hashlib,json,tempfile
import numpy as np
import pandas as pd
import joblib
import rebuild_v027 as rb
from refit_reference_identity_corrected import source,rebuild,FILES,selfcheck
from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger,V027_FEATURES
from wshlx_ufc.models import ConditionalMethodModel

OUT=Path("research_outputs/reference_method_offsets_2026-11-25")
LEDGER=Path("reports/ufcvegas124_2026-11-07/full_stats/clean153_causal_method_inputs.csv")
CLASSES=["KO","SUB","DEC"]
def key(r):
    return (str(r["event_date"])[:10],*sorted(rb.norm_name(r[z]) for z in ("fighter_a","fighter_b")))
def args(f):
    return {"baseline_"+z.lower():f["base_"+z].to_numpy() for z in CLASSES}
def fit(f):
    y=f["method"].to_numpy()
    assert set(y)==set(CLASSES)
    return (MethodInterceptCalibrator(ridge=.5).fit(actual_method=y,**args(f)),
            V027MethodResidualChallenger(ridge=10.,clip_z=5.).fit(f[list(V027_FEATURES)],actual_method=y,**args(f)))
def scores(f,p):
    p=np.asarray(p,float)
    assert np.isfinite(p).all() and np.allclose(p.sum(axis=1),1)
    y=np.array([CLASSES.index(z) for z in f["method"]])
    return {"n":len(y),"hits":int((p.argmax(axis=1)==y).sum()),"logloss":float(-np.log(np.clip(p[np.arange(len(y)),y],1e-12,1)).mean()),"brier":float(((p-np.eye(3)[y])**2).sum(axis=1).mean())}
def main():
    selfcheck()
    if OUT.exists():raise FileExistsError("Do not overwrite offsets")
    t=source()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)
        for k,v in FILES.items():t[k].to_csv(path/v,index=False)
        rb.TRAINING_CUTOFF=pd.Timestamp("2026-11-22",tz="UTC")
        fights,stats,static=rb.load_fights(path)
    (_,m,_),_,_=rebuild(fights,rb.aggregate_fight_stats(fights,stats),static)
    idx={key(r):r for r in m.to_dict("records")}
    assert len(idx)==len(m)
    old=pd.read_csv(LEDGER)
    assert len(old)==153
    chosen=[]
    for r in old.to_dict("records"):
        k=key(r)
        if k not in idx:
            candidates=[z for z in idx if z[0]==k[0] and set(z[1:])&set(k[1:])]
            raise ValueError("Historical feedback identity mismatch: "+str((k,candidates)))
        x=idx[k]
        if x["method"]!=r["clean_actual_method"] or rb.norm_name(x["winner"])!=rb.norm_name(r["winner"]):
            raise ValueError("Historical feedback label disagreement: "+str(k))
        chosen.append(x)
    chosen.extend(r for r in idx.values() if str(r["event_date"])[:10] in ("2026-11-14","2026-11-21"))
    assert len(chosen)==177 and len({key(r) for r in chosen})==177
    data=pd.DataFrame(chosen).sort_values(["event_date","fight_key"]).reset_index(drop=True)
    for day in sorted(data.event_date.unique()):
        before=m[m.event_date<day]
        assert len(before)>1000
        model=ConditionalMethodModel(finish_c=.1,sub_c=.1).fit(before[list(rb.METHOD_BASE_FEATURES)],before["method"])
        mask=data.event_date==day
        p=model.predict_proba(data.loc[mask,list(rb.METHOD_BASE_FEATURES)])
        for z in CLASSES:data.loc[mask,"base_"+z]=p[z].to_numpy()
    assert np.allclose(data[["base_"+z for z in CLASSES]].sum(axis=1),1)
    # Expanding evaluation of offsets; every evaluation event is excluded from offset fitting.
    predictions={k:[] for k in ("baseline","calibrated","residual")};evaluated=[]
    for day in sorted(data.event_date.unique()):
        tr=data[data.event_date<day];te=data[data.event_date==day]
        if len(tr)<64 or set(tr.method)!=set(CLASSES):continue
        ca,re=fit(tr)
        predictions["baseline"].append(te[["base_"+z for z in CLASSES]].to_numpy())
        predictions["calibrated"].append(ca.predict_proba(**args(te))[CLASSES].to_numpy())
        predictions["residual"].append(re.predict_proba(te[list(V027_FEATURES)],**args(te))[CLASSES].to_numpy())
        evaluated.append(te)
    ev=pd.concat(evaluated,ignore_index=True)
    report={"feedback_rows":len(data),"prior_feedback_rows":153,"added_decisive_rows":24,"conditional_on_actual_winner":True,"retrospective_only":True,"new_prospective_observations":0,"production_migrated":False,"scores":{k:scores(ev,np.concatenate(v)) for k,v in predictions.items()},"artifacts":{}}
    ca,re=fit(data)
    OUT.mkdir(parents=True)
    for name,obj in (("method_calibrator",ca),("method_residual",re)):
        p=OUT/(name+".joblib");joblib.dump(obj,p,compress=3)
        report["artifacts"][name]=hashlib.sha256(p.read_bytes()).hexdigest()
    data.to_csv(OUT/"corrected_retrospective_oof.csv",index=False)
    (OUT/"manifest.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
if __name__=="__main__":main()
