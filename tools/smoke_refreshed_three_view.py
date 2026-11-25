"""Artifact-bound, non-card integration smoke test. No published picks."""
from pathlib import Path
import argparse,hashlib,json,tempfile
import joblib
import numpy as np
import pandas as pd
import rebuild_v027 as rb
from refit_reference_identity_corrected import source,rebuild,FILES,summarize
from wshlx_ufc.models import joint_outcome_probabilities,fighter_double_chance
from wshlx_ufc.method_residual_v027 import V027_FEATURES
from wshlx_ufc.simulation import simulate_joint_outcomes
from wshlx_ufc.refreshed_unified import validate,package,compose
from wshlx_ufc.historical_data import build_prefight_perspective_rows,col
from wshlx_ufc.historical_timing_model import symmetric_timing_frame,_encode_transform

REFERENCE={"winner":"72848612430383684f5da11cdbe493a7ae22e3dd11044865506536dd73589b0a","method_baseline":"fff7ec007b7df31871c8343d5b905464a82180027db22e47c0fda4c4d2e5db74","timing_30s":"89764a4ae32c7ee7ef5b44aa2832d937db0563edd494e59095d283ff1dbf27e6"}
OFFSETS={"method_calibrator":"64f54078e6640349ac863a2c903fee5f4774505296bcd2de13cd6f487c03f503","method_residual":"e439278464ae1f9d56f268f6bf19f0570656118cdfa09106bba079a91167702c"}
def checked_load(root,name,digest):
    p=root/(name+".joblib")
    if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError("Artifact SHA mismatch: "+name)
    return joblib.load(p)
def reference_view(a,b,wc,seconds,models):
    wf=rb.winner_features(a,b,wc,seconds)
    p=float(models["winner"].predict_proba(pd.DataFrame([wf],columns=rb.WINNER_FEATURES))[0,0])
    methods=[];residual=[]
    for own,opp in ((a,b),(b,a)):
        x=pd.DataFrame([rb.method_features(own,opp,wc,seconds)],columns=rb.METHOD_BASE_FEATURES)
        base=models["method_baseline"].predict_proba(x).iloc[0]
        kw={"baseline_"+k.lower():[float(base[k])] for k in ("KO","SUB","DEC")}
        methods.append(models["method_calibrator"].predict_proba(**kw).iloc[0].to_dict())
        rx=pd.DataFrame([rb.residual_features(own,opp)],columns=list(V027_FEATURES))
        residual.append(models["method_residual"].predict_proba(rx,**kw).iloc[0].to_dict())
    timing=models["timing_30s"]
    h=timing._hazards_for_one(pd.Series(wf).reindex(timing.base_feature_names_),seconds)
    joint=joint_outcome_probabilities(p,*methods)
    res=joint_outcome_probabilities(p,*residual)
    assert np.isclose(sum(res.values()),1)
    return {"winner_p_a":p,"joint_method":joint,"hazards_30s":h}
def historical_view(t,names,wc,seconds,day,models):
    event="__HYPOTHETICAL_INTEGRATION_TEST__"
    ev=t["events"].copy()
    rr=t["results"].copy()
    ev=pd.concat([ev,pd.DataFrame([{"EVENT":event,"DATE":str(day.date())}])],ignore_index=True)
    row={"EVENT":event,"BOUT":" vs. ".join(names),"OUTCOME":"W/L","METHOD":"DEC","ROUND":seconds//300,"TIME":"5:00","WEIGHTCLASS":wc}
    row[col(rr,"TIME FORMAT","TIME_FORMAT")]=str(seconds//300)+" Rnd"
    rr=pd.concat([rr,pd.DataFrame([row])],ignore_index=True)
    f=build_prefight_perspective_rows(ev,rr,t["stats"],t["fighters"])
    f=f[f.event==event].copy()
    assert len(f)==2 and f.fight_id.nunique()==1
    # Reversing the synthetic outcome cannot change any model predictor.
    rr.loc[rr.EVENT==event,"OUTCOME"]="L/W"
    g=build_prefight_perspective_rows(ev,rr,t["stats"],t["fighters"])
    g=g[g.event==event].copy()
    fields=set(models["winner"].feature_columns)|set(models["method"].feature_columns)
    raw=[z for z in f if z in fields]
    pd.testing.assert_frame_equal(f.set_index("fighter")[raw].sort_index(),g.set_index("fighter")[raw].sort_index())
    idx=f[f.fighter==names[0]].index[0]
    pa=float(pd.Series(models["winner"].predict_proba(f),index=f.index).loc[idx])
    p=models["method"].predict_joint_probabilities(f).loc[idx]
    j={side+"_"+m:float(p[prefix+"_"+("KO_TKO" if m=="KO" else m)]) for side,prefix in (("A","WIN"),("B","LOSS")) for m in ("KO","SUB","DEC")}
    tm=models["timing"]
    tf=symmetric_timing_frame(f);tf["scheduled_seconds"]=seconds
    x=_encode_transform(tf,tm.rate_encoders).iloc[0]
    assert tm.hazard_model.bin_seconds==30
    return {"winner_p_a":pa,"joint_method":j,"hazards_30s":tm._hazards(x,seconds)}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--reference",type=Path,required=True);ap.add_argument("--offsets",type=Path,required=True);ap.add_argument("--historical",type=Path)
    args=ap.parse_args()
    models={**{n:checked_load(args.reference,n,s) for n,s in REFERENCE.items()},**{n:checked_load(args.offsets,n,s) for n,s in OFFSETS.items()}}
    hist=None
    if args.historical:
        mf=json.loads((args.historical/"manifest.json").read_text())
        assert mf["history_through"]=="2026-11-21" and mf["research_only"] is True
        hist={n:checked_load(args.historical,"historical_"+n,mf["models"][n]["sha256"]) for n in ("winner","method","timing")}
        assert all(str(pd.Timestamp(x.history_end).date())=="2026-11-21" for x in hist.values())
    t=source()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)
        for k,v in FILES.items():t[k].to_csv(path/v,index=False)
        rb.TRAINING_CUTOFF=pd.Timestamp("2026-11-22",tz="UTC")
        fights,stats,static=rb.load_fights(path)
    _,history,coverage=rebuild(fights,rb.aggregate_fight_stats(fights,stats),static)
    day=pd.Timestamp("2026-12-05",tz="UTC")
    checked=0
    for names,wc,seconds in [(("Bruno Silva [Bulldog]","Amir Albazi"),"Flyweight Bout",900),(("Dan Hooker","Mateusz Gamrot"),"Lightweight Bout",1500)]:
        assert all(rb.norm_name(n) in history and rb.norm_name(n) in static for n in names)
        a,b=(summarize(n,history,static,day) for n in names)
        r=reference_view(a,b,wc,seconds,models)
        if hist:
            h=historical_view(t,names,wc,seconds,day,hist)
            views=compose(r,h,scheduled_seconds=seconds)
            selected=[views[z] for z in ("reference","historical","unified")]
        else:
            p,j,h=validate(r,seconds)
            selected=[package(p,j,h,seconds)]
        for v in selected:
            for joint in v["coherence"].values():
                assert np.isclose(sum(simulate_joint_outcomes(joint,trials=10000,seed=1125).values()),1)
                assert all(0<=x<=1 for x in fighter_double_chance(joint).values())
            checked+=1
    print(json.dumps({"reference_artifacts_sha_verified":5,"historical_artifacts_verified":3 if hist else 0,"hypothetical_matchups":2,"model_views_checked":checked,"joint_simulation_trials":10000,"coverage":coverage,"real_card_predictions":0,"production_migrated":False}))
if __name__=="__main__":main()
