"""Reproduce UFC334 pre-Nov14-only simple method-offset shadow holdout.

Only 153 PRIOR causal method rows (through Nov7) may fit the offset.
UFC334 original frozen probabilities form a completely held-out evaluation.
This is neither a new Stage A pick nor permission to change model weights.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from wshlx_ufc.method_calibration import MethodInterceptCalibrator

ROOT = Path(__file__).resolve().parents[1]
OLDER = ROOT / "reports/ufcvegas124_2026-11-07/full_stats/clean153_causal_method_inputs.csv"
STAGE_A = ROOT / "data/locks/ufc334_2026-11-14/stage_a_final_selection.json"
RAW = ROOT / "data/locks/ufc334_2026-11-14/stage_a_model_raw_three_view.json"
RESULTS = ROOT / "data/results/ufc334_2026-11-14_verified_outcomes.json"
SHADOW = ROOT / "reports/ufc334_2026-11-14/PRE_NOV14_METHOD_OFFSET_SHADOW_HOLDOUT.json"
CLASSES = ["KO", "SUB", "DEC"]


def evaluate(probabilities: np.ndarray, actual_methods: list[str]) -> dict:
    p = np.asarray(probabilities, dtype=float)
    truth = np.asarray(actual_methods, dtype=str)
    if p.shape != (len(truth),3) or not np.allclose(p.sum(axis=1), 1, atol=1e-6):
        raise ValueError("Invalid conditional-method probability matrix")
    if set(truth)-set(CLASSES):
        raise ValueError("Unknown actual method")
    target = (truth[:,None] == np.asarray(CLASSES)[None,:]).astype(float)
    hit = np.asarray(CLASSES)[p.argmax(axis=1)] == truth
    return {
        "n": len(truth),
        "top_accuracy": float(hit.mean()),
        "mean_brier": float(np.mean(np.sum((p-target)**2,axis=1))),
        "mean_logloss": float(-np.mean(np.log(
            np.clip(p[np.arange(len(truth)), target.argmax(axis=1)],1e-12,1)))),
    }


def compute() -> dict:
    old = pd.read_csv(OLDER)
    if len(old) != 153:
        raise ValueError("Need all 153 prior training method outcomes")
    dates = pd.to_datetime(old["event_date"]).dt.date
    if max(dates).isoformat() > "2026-11-07":
        raise ValueError("Future leakage into Nov14 shadow training")
    if not np.allclose(old[["base_KO","base_SUB","base_DEC"]].sum(axis=1),1,atol=1e-5):
        raise ValueError("Improper prior probability data")
    cal = MethodInterceptCalibrator(ridge=2.0).fit(
        actual_method=old["clean_actual_method"],
        baseline_ko=old["base_KO"],
        baseline_sub=old["base_SUB"],
        baseline_dec=old["base_DEC"])
    lock, raw, actual = [json.loads(p.read_text()) for p in (STAGE_A,RAW,RESULTS)]
    if not lock["stage_a_frozen"] or lock["odds_used"] or raw["odds_used"]:
        raise ValueError("Original predictions must remain frozen and odds blind")
    raw_by_id={r["fight_no"]:r for r in raw["fights"]}
    actual_by_id={r["fight_no"]:r for r in actual["fights"]}
    reference_baseline=[]
    reference_actual=[]
    oracle_baseline=[]
    oracle_actual=[]
    reference_exact=0
    shadow_exact=0
    rows=[]
    for f in lock["fights"]:
        n=f["fight_no"]
        y=actual_by_id[n]
        if y["method"]=="DRAW":
            continue
        if y["method"] not in CLASSES:
            raise ValueError("Method not gradeable")
        src=f["method"]["current_conditional_if_official_winner"]
        base=np.asarray([[float(src[x]) for x in CLASSES]],dtype=float)
        shadow=cal.predict_proba(
            baseline_ko=base[:,0],baseline_sub=base[:,1],
            baseline_dec=base[:,2])[CLASSES].to_numpy(float)
        predicted=CLASSES[int(base.argmax(axis=1)[0])]
        proposed=CLASSES[int(shadow.argmax(axis=1)[0])]
        correct=f["official_reference_pick"]==y["winner"]
        if correct:
            reference_baseline.append(base[0])
            reference_actual.append(y["method"])
            reference_exact+=int(predicted==y["method"])
            shadow_exact+=int(proposed==y["method"])
        pair=raw_by_id[n]["joint_calibrated"]
        prefix="A" if f["a"]==y["winner"] else "B"
        joint=np.asarray([[float(pair[prefix+"_"+x]) for x in CLASSES]],dtype=float)
        joint/=joint.sum(axis=1,keepdims=True)
        oracle_baseline.append(joint[0])
        oracle_actual.append(y["method"])
        rows.append({"fight_no":n,"reference_winner_correct":correct,
                     "original_top_method":predicted,"shadow_top_method":proposed})
    if len(rows)!=12 or len(reference_actual)!=8:
        raise ValueError("Unexpected UFC334 holdout count")
    return {
        "prior_fit_rows":len(old),
        "fit_max_date":max(dates).isoformat(),
        "finish_offset":float(cal.finish_offset_),
        "sub_offset":float(cal.sub_offset_),
        "original_exact_correct":reference_exact,
        "shadow_exact_correct":shadow_exact,
        "correct_reference_winner_method": {
            "baseline":evaluate(np.asarray(reference_baseline),reference_actual),
            "shadow":evaluate(
                cal.predict_proba(
                    baseline_ko=np.asarray(reference_baseline)[:,0],
                    baseline_sub=np.asarray(reference_baseline)[:,1],
                    baseline_dec=np.asarray(reference_baseline)[:,2],
                )[CLASSES].to_numpy(float),
                reference_actual),
        },
        "known_winner_conditional_method_oracle": {
            "baseline":evaluate(np.asarray(oracle_baseline),oracle_actual),
            "shadow":evaluate(
                cal.predict_proba(
                    baseline_ko=np.asarray(oracle_baseline)[:,0],
                    baseline_sub=np.asarray(oracle_baseline)[:,1],
                    baseline_dec=np.asarray(oracle_baseline)[:,2],
                )[CLASSES].to_numpy(float),
                oracle_actual),
        },
        "rows":rows,
        "no_model_promotion":True,
    }


def main():
    out=compute()
    stored=json.loads(SHADOW.read_text())
    if abs(out["finish_offset"]-stored["finish_vs_decision_logit_offset"])>1e-8:
        raise RuntimeError("Shadow offset report drift")
    if abs(out["sub_offset"]-stored["submission_given_finish_logit_offset"])>1e-8:
        raise RuntimeError("Shadow submission report drift")
    for key, previous in (
        ("correct_reference_winner_method", "own_reference_selected_fighter_when_correct"),
        ("known_winner_conditional_method_oracle", "oracle_actual_winner_method_non_betting")
    ):
        for label in ("base","shadow"):
            report_label="baseline" if label=="base" else label
            for metric in ("n","top_accuracy","mean_brier","mean_logloss"):
                a=out[key][report_label][metric]
                b=stored["metrics"][previous][label][metric]
                if abs(a-b)>1e-8:
                    raise RuntimeError(f"Stored holdout mismatch: {key}/{label}/{metric} {a}!={b}")
    print(json.dumps(out,indent=2))


if __name__=="__main__":
    main()
