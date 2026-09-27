from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m

rb=load_module("rebuild_v027_v032",ROOT/"tools/rebuild_v027.py")

from wshlx_ufc.grading import multiclass_brier
from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger, V027_FEATURES
from wshlx_ufc.models import ConditionalMethodModel, WinnerModel
from wshlx_ufc.timing import DiscreteTimeHazardModel
from wshlx_ufc.nonperformance import activity_dates_from_raw

RAW_DIR=ROOT/"data/raw/ufcvegas121_2026-09-26"
CLEAN=ROOT/"data/results/clean_ufc_87_2026-09-26.csv"
GRADE=ROOT/"reports/ufcvegas121_2026-09-26/post_event_grade.json"
OUT=ROOT/"reports/v032_ufcvegas121_full_stats"
ART=ROOT/"artifacts/v032_ufcvegas121_full_stats"
SOURCE_COMMIT="b93901a2ab58d7c9880797451c7ef0ef5e03ce1a"

def grade_methods(y,pdf):
    classes=["KO","SUB","DEC"]
    arr=pdf[classes].to_numpy(float); y=np.asarray(y,dtype=str)
    pred=np.asarray(classes)[np.argmax(arr,axis=1)]
    return {
      "n":int(len(y)),
      "accuracy":float(np.mean(pred==y)),
      "brier":float(multiclass_brier(y,arr,classes)),
      "log_loss":float(log_loss(y,arr[:,[2,0,1]],labels=["DEC","KO","SUB"])),
      "calls":{c:int(np.sum(pred==c)) for c in classes},
      "actual":{c:int(np.sum(y==c)) for c in classes},
      "recall":{c:(float(np.mean(pred[y==c]==c)) if np.any(y==c) else None) for c in classes},
    }

def chronology_calibration(clean_oof,ridge=0.5):
    ys=[]; bases=[]; cals=[]; folds=[]
    for test_date in sorted(clean_oof["event_date"].unique())[1:]:
        train=clean_oof.loc[clean_oof["event_date"]<test_date]
        test=clean_oof.loc[clean_oof["event_date"]==test_date]
        if len(train)<12: continue
        cal=MethodInterceptCalibrator(ridge=ridge).fit(
          actual_method=train["clean_actual_method"],
          baseline_ko=train["base_KO"],baseline_sub=train["base_SUB"],baseline_dec=train["base_DEC"])
        pred=cal.predict_proba(
          baseline_ko=test["base_KO"],baseline_sub=test["base_SUB"],baseline_dec=test["base_DEC"])
        ys.extend(test["clean_actual_method"].tolist())
        bases.append(test[["base_KO","base_SUB","base_DEC"]].rename(columns={"base_KO":"KO","base_SUB":"SUB","base_DEC":"DEC"}).reset_index(drop=True))
        cals.append(pred.reset_index(drop=True))
        folds.append({"test_date":test_date,"train_n":int(len(train)),"test_n":int(len(test)),
                      "finish_offset":cal.finish_offset_,"sub_offset":cal.sub_offset_})
    y=np.asarray(ys,dtype=str)
    return {"ridge":ridge,"baseline":grade_methods(y,pd.concat(bases,ignore_index=True)),
            "candidate":grade_methods(y,pd.concat(cals,ignore_index=True)),"folds":folds}

def main():
    availability=json.loads((RAW_DIR/"availability.json").read_text())
    if not availability.get("full_card_stats_available"):
        raise RuntimeError("full UFC Vegas 121 stats unavailable")

    old=rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF=pd.Timestamp("2026-09-27",tz="UTC")
    try:
        fights,stats,static=rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF=old

    fight_stats=rb.aggregate_fight_stats(fights,stats)
    winner_df,method_df,timing_df=rb.enrich_and_snapshot(fights,fight_stats,static)

    clean=pd.read_csv(CLEAN)
    clean_rows=rb.find_clean_rows(clean,method_df)
    clean_oof=rb.add_clean_oof_baselines(clean_rows,method_df)
    winner_bench=rb.winner_clean_benchmark(clean,winner_df)
    residual_bench=rb.chronology_residual_benchmark(clean_oof)
    calibration_bench=chronology_calibration(clean_oof,0.5)

    ART.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    winner=WinnerModel(c=0.25).fit(winner_df[rb.WINNER_FEATURES],winner_df["winner_is_a"])
    method=ConditionalMethodModel(finish_c=0.10,sub_c=0.10).fit(method_df[rb.METHOD_BASE_FEATURES],method_df["method"])
    residual=V027MethodResidualChallenger(ridge=10.0,clip_z=5.0).fit(
      clean_oof[list(V027_FEATURES)],
      actual_method=clean_oof["clean_actual_method"],
      baseline_ko=clean_oof["base_KO"],baseline_sub=clean_oof["base_SUB"],baseline_dec=clean_oof["base_DEC"])
    calibrator=MethodInterceptCalibrator(ridge=0.5).fit(
      actual_method=clean_oof["clean_actual_method"],
      baseline_ko=clean_oof["base_KO"],baseline_sub=clean_oof["base_SUB"],baseline_dec=clean_oof["base_DEC"])
    timing=DiscreteTimeHazardModel(bin_seconds=30,c=0.10).fit(
      timing_df[rb.TIMING_FEATURES],
      timing_df["duration_seconds"].to_numpy(float),
      timing_df["scheduled_seconds"].to_numpy(int),
      ((timing_df["method"]!="DEC") | (timing_df["duration_seconds"]<timing_df["scheduled_seconds"])).astype(int).to_numpy())

    paths={
      "winner":ART/"winner_v032.joblib",
      "method_baseline":ART/"method_baseline_v032.joblib",
      "method_residual":ART/"method_residual_v032.joblib",
      "timing_30s":ART/"timing_v032_30s.joblib",
    }
    for key,obj in [("winner",winner),("method_baseline",method),("method_residual",residual),("timing_30s",timing)]:
        joblib.dump(obj,paths[key])

    activity=activity_dates_from_raw(RAW_DIR)
    activity_payload={k:v.isoformat() for k,v in sorted(activity.items())}
    (ART/"activity_last_dates.json").write_text(json.dumps(activity_payload,indent=2,sort_keys=True))
    clean_oof.to_csv(OUT/"clean87_oof_method_inputs_fullstats.csv",index=False)

    grade=json.loads(GRADE.read_text())
    prospective=grade["prospective_model_metrics"]
    prospective["winner_v031_clean"]={
      "n":11,"accuracy":9/11,"brier":0.13120574762789083,"log_loss":0.4370952034219332}
    prospective["winner_reference_clean"]={
      "n":11,"accuracy":9/11,"brier":0.13088957191378825,"log_loss":0.43633940764431234}

    import hashlib
    def sha(path):
        h=hashlib.sha256()
        with open(path,"rb") as f:
            for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
        return h.hexdigest()

    manifest={
      "status":"V0.32_UFCVEGAS121_FULL_STATS_SHADOW",
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "source":{"upstream_commit":SOURCE_COMMIT,"full_card_stats_available":True,
                "unique_result_bouts":availability["unique_result_bouts"],
                "unique_stat_bouts":availability["unique_stat_bouts"],
                "fighter_round_stat_rows":availability["fight_stat_rows"]},
      "population":{"training_rows":int(len(winner_df)),"clean_feedback_rows":int(len(clean_oof)),
                    "latest_performance_event_date":str(fights["event_date"].max())},
      "nonperformance_handling":{
        "known_injury_stoppages_excluded_from_performance_training":True,
        "dq_nc_excluded_from_performance_training":True,
        "official_activity_dates_saved_separately":True,
        "ufcvegas121_dq":"Mahammadali Osmanli vs Ilimbek Akylbek preserved as activity/official result, excluded from clean performance labels"
      },
      "identity_handling":{
        "alatengheili_to_heili_alateng":True,
        "tina_black_to_valesca_machado":True,
        "mahammadali_to_mehemmedeli_osmanli":True
      },
      "prospective_ufcvegas121":prospective,
      "benchmarks":{"winner_clean87":winner_bench,"method_residual_clean87":residual_bench,
                    "method_intercept_calibration_clean87":calibration_bench},
      "final_method_calibration":{"ridge":0.5,"finish_offset":calibrator.finish_offset_,
                                  "sub_given_finish_offset":calibrator.sub_offset_},
      "artifact_sha256":{k:sha(v) for k,v in paths.items()},
      "promotion":{
        "winner_v031":"NOT_PROMOTED: same 9-2 accuracy as reference and slightly worse prospective Brier/log loss on first unseen card",
        "method_calibration":"LEADING_SHADOW: clearly best method layer prospectively, but one unseen card is not enough for champion promotion",
        "timing":"SHADOW: 7-4 clean timing leans; retain 30-second bins and current gate",
        "v032_role":"current data backbone + shadow retrain"
      }
    }
    (ART/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True))
    (OUT/"benchmark.json").write_text(json.dumps(manifest["benchmarks"],indent=2,sort_keys=True))
    report=[
      "# v0.32 UFC Vegas 121 full-stat integration","",
      f"- Full event stats: **{availability['unique_stat_bouts']}/12 bouts, {availability['fight_stat_rows']} fighter-round rows**",
      f"- Clean feedback ledger: **{len(clean_oof)} fights**",
      f"- Causal training rows: **{len(winner_df):,}**",
      "- DQ/NC and known injury-stoppage anomalies are excluded from clean performance training while activity dates are retained separately.",
      "",
      "## First unseen v0.31 test","",
      "- Winner v0.31: **9-2 clean (81.8%)**, Brier **0.1312**, log loss **0.4371**",
      "- Winner reference: **9-2 clean (81.8%)**, Brier **0.1309**, log loss **0.4363**",
      "- Method baseline: **36.4%**, Brier **0.6758**",
      "- Method calibrated: **54.5%**, Brier **0.5831**",
      "- Method residual: **45.5%**, Brier **0.7064**",
      "- Timing leans: **7-4 clean (63.6%)**",
      "",
      "## Promotion decision","",
      "**Winner v0.31 is not promoted** because the reference was marginally better on probability quality despite identical accuracy.",
      "**Method calibration is the leading shadow** after a clear prospective win, but needs more unseen fights before champion promotion.",
      "**v0.32 is the current full-stat data backbone** for the next card."
    ]
    (OUT/"BUILD_REPORT.md").write_text("\n".join(report)+"\n")
    print(json.dumps(manifest,indent=2,sort_keys=True))

if __name__=="__main__": main()
