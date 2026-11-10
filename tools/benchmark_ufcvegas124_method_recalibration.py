"""Chronological KO/SUB/DEC calibration tests after verified Nov7 UFCStats.

All 153 rows hold *causal pre-event* baseline conditional-method forecasts.
Each time-split fits ONLY dates before its evaluation date. Never include
post-fight result, current fight stats, market price or opponent result
in the feature matrix.

These are method classifications GIVEN THE KNOWN WINNER for retrospective
diagnostics, not standalone fighter+method betting predictions or proof of
prospective shadow validation. Nov7 fighter+method prospective grades are
the already-frozen 14-bout three-model grading file (8/14 unified, etc).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tools"))

from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger, V027_FEATURES
from benchmark_method_finish_access_v035 import candidate_finish, FEATURES as FINISH_FEATURES

INPUT=ROOT/"reports/ufcvegas124_2026-11-07/full_stats/clean153_causal_method_inputs.csv"
OUTPUT=ROOT/"reports/ufcvegas124_2026-11-07/full_stats/chronological_method_calibration_benchmark.json"
PRED=ROOT/"reports/ufcvegas124_2026-11-07/full_stats/chronological_method_calibration_predictions.csv"
CLASSES=["KO","SUB","DEC"]
MIN_TRAIN=36
GATE_PROSPECTIVE=300


def evaluate(y,p):
    labels=np.asarray(CLASSES)
    actual=np.asarray(y,dtype=str)
    vals=np.asarray(p,dtype=float)
    if vals.shape!=(len(actual),3) or not np.isfinite(vals).all() or not np.allclose(vals.sum(axis=1),1):
        raise RuntimeError("Invalid three-method probability vector")
    hit=labels[vals.argmax(axis=1)]==actual
    one_hot=(actual[:,None]==labels[None,:]).astype(float)
    return {
        "n":len(y),"correct":int(hit.sum()),"accuracy":float(hit.mean()),
        "brier":float(np.mean(np.sum((vals-one_hot)**2,axis=1))),
        "log_loss":float(-np.mean(np.log(np.clip(vals[np.arange(len(y)),one_hot.argmax(axis=1)],1e-12,1)))),
        "predicted_calls":{k:int(sum(labels[vals.argmax(axis=1)]==k)) for k in CLASSES},
        "actual_counts":{k:int(sum(actual==k)) for k in CLASSES},
        "class_recall":{k:float(np.mean(hit[actual==k])) if any(actual==k) else None
                        for k in CLASSES},
    }


def make_prob_cal(cal,frame):
    return cal.predict_proba(baseline_ko=frame["base_KO"],
                             baseline_sub=frame["base_SUB"],
                             baseline_dec=frame["base_DEC"])[CLASSES].to_numpy(float)


def make_prob_residual(model,frame):
    return model.predict_proba(frame[list(V027_FEATURES)],
                               baseline_ko=frame["base_KO"],
                               baseline_sub=frame["base_SUB"],
                               baseline_dec=frame["base_DEC"])[CLASSES].to_numpy(float)


def main():
    if OUTPUT.exists() or PRED.exists():
        raise RuntimeError("Refusing to overwrite a previous benchmark; version re-runs")
    df=pd.read_csv(INPUT)
    if len(df)!=153:
        raise RuntimeError("Require all 153 causal clean UFC method OOF observations")
    df["event_date"]=df["event_date"].astype(str).str[:10]
    if sum(df["event_date"]=="2026-11-07")!=14:
        raise RuntimeError("Nov7 14 observations absent")
    if any(x in V027_FEATURES or x in FINISH_FEATURES for x in (
        "winner","actual_method","method","duration_seconds","fight_method",
        "sig_landed","td_landed","ctrl_seconds"
    )):
        raise RuntimeError("Feature leakage into candidate method models")
    needed=list(V027_FEATURES)+list(FINISH_FEATURES)+["base_KO","base_SUB","base_DEC","clean_actual_method"]
    if set(needed)-set(df):
        raise RuntimeError("Missing pre-fight causal model feature(s)")
    if not np.allclose(df[["base_KO","base_SUB","base_DEC"]].sum(axis=1),1,atol=1e-6):
        raise RuntimeError("Stored pre-event method distributions not normalized")

    rows=[]
    folds=[]
    for date in sorted(df["event_date"].unique()):
        train=df.loc[df.event_date<date].copy()
        test=df.loc[df.event_date==date].copy()
        if len(train)<MIN_TRAIN:
            continue
        if train.event_date.max()>=date:
            raise RuntimeError("Same-event or later outcomes leaked into calibration")
        train_method=train["clean_actual_method"].astype(str)
        classes=set(train_method)
        if classes!={"KO","SUB","DEC"}:
            raise RuntimeError(f"At date {date}, training class missing: {classes}")
        y=test["clean_actual_method"].to_numpy(str)
        cal=MethodInterceptCalibrator(ridge=0.5).fit(
            actual_method=train_method,
            baseline_ko=train["base_KO"],
            baseline_sub=train["base_SUB"],
            baseline_dec=train["base_DEC"],
        )
        residual=V027MethodResidualChallenger(ridge=10.0,clip_z=5.0).fit(
            train[list(V027_FEATURES)],actual_method=train_method,
            baseline_ko=train["base_KO"],baseline_sub=train["base_SUB"],
            baseline_dec=train["base_DEC"],
        )
        base=test[["base_KO","base_SUB","base_DEC"]].to_numpy(float)
        cal_p=make_prob_cal(cal,test)
        residual_p=make_prob_residual(residual,test)
        train_cal=make_prob_cal(cal,train)
        finish_p,_=candidate_finish(train,test,train_cal,cal_p)
        all_p={"base":base,"cal":cal_p,"v027_residual":residual_p,"v035_finish_access":finish_p}
        folds.append({"date":date,"train_rows":len(train),"test_rows":len(test),
                      "train_max_date":train.event_date.max(),
                      "metrics":{k:evaluate(y,v) for k,v in all_p.items()}})
        for n,(_,item) in enumerate(test.iterrows()):
            row={"event_date":date,"bout":item["bout"],
                 "actual_method":str(y[n]),"pre_fight_baseline_provenance":
                 "FROZEN_NOV7_RAW_METHOD_PROBABILITY" if date=="2026-11-07" else "PRIOR_139_CAUSAL_OUT_OF_FOLD_BASELINE"}
            for model,p in all_p.items():
                for j,k in enumerate(CLASSES):
                    row[f"{model}_{k}"]=float(p[n,j])
            rows.append(row)
    pred=pd.DataFrame(rows)
    if len(pred)<100 or sum(pred["event_date"]=="2026-11-07")!=14:
        raise RuntimeError("Chronological method folds did not reach Nov7 cohort")
    summary={}
    for key,subset in (
        ("historical_development_pre_nov7",pred[pred.event_date<"2026-11-07"]),
        ("nov7_chronological_reconstruction_not_official_frozen_picks",
         pred[pred.event_date=="2026-11-07"]),
        ("all_chronological_crossfit",pred),
    ):
        y=subset["actual_method"].to_numpy(str)
        summary[key]={m:evaluate(y,subset[[f"{m}_{c}" for c in CLASSES]].to_numpy(float))
                      for m in ("base","cal","v027_residual","v035_finish_access")}
    early=summary["historical_development_pre_nov7"]
    selection={}
    for candidate in ("v027_residual","v035_finish_access"):
        # An algorithm cannot be promoted merely because it has slightly more
        # classification wins; probability calibration (two proper scores),
        # rare-SUB recall, and independent prospective validation all matter.
        x=early[candidate];comp=early["cal"]
        selection[candidate]={
            "historical_n":x["n"],
            "brier_better":x["brier"]<comp["brier"],
            "logloss_better":x["log_loss"]<comp["log_loss"],
            "class_accuracy_better":x["accuracy"]>comp["accuracy"],
            "sub_recall_not_worse":(
                x["class_recall"]["SUB"] is not None and
                x["class_recall"]["SUB"]>=comp["class_recall"]["SUB"]
            ),
            "minimum_300_prospective_fight_validation_met":False,
            "promoted":False,
        }
    report={
        "status":"NOV7_FUTURE_ONLY_METHOD_CALIBRATION_CHRONOLOGICAL_BENCHMARK_NOT_PROMOTED",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "data_scope":"139 older causal method feedback rows plus 14 pre-event baseline probabilities for Nov7, evaluated with known winning fighter",
        "method_feedback_rows":len(df),
        "total_chronologically_scored_bouts":len(pred),
        "minimum_train_rows":MIN_TRAIN,
        "tested_methods":["raw_base","intercept_cal","v027_residual","v035_finish_access"],
        "metrics":summary,
        "folds":folds,
        "candidate_gates":selection,
        "source_method_feedback":"reports/ufcvegas124_2026-11-07/full_stats/clean153_causal_method_inputs.csv",
        "governance":{
            "no_current_event_training_in_its_own_fold":True,
            "nov7_is_not_an_official_new_method_bet_projection":True,
            "original_frozen_nov7_unified_8of14_unchanged":True,
            "future_refit_calibrator_from_153_exists_separately":True,
            "no_model_promotion":True,
            "original_champion_method_coefficients_unchanged":True,
            "betting_method_coherence_gate_preserved":True,
            "requires_genuinely_prospective_external_validation":True,
        }
    }
    OUTPUT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    pred.to_csv(PRED,index=False)
    print(json.dumps({
        "status":report["status"],
        "historical_dev":summary["historical_development_pre_nov7"],
        "nov7_reconstructed_conditional_method":summary["nov7_chronological_reconstruction_not_official_frozen_picks"],
        "method_candidate_gates":selection,
        "total":len(pred),
        "promoted":False
    },indent=2))


if __name__=="__main__":
    main()
