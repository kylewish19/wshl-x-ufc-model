from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wshlx_ufc.grading import multiclass_brier
from wshlx_ufc.method_calibration import MethodInterceptCalibrator

INPUT = ROOT / "reports/v028_ufc331_feedback/clean76_oof_method_inputs.csv"
OUT = ROOT / "reports/v029_method_calibration"
ART = ROOT / "artifacts/v029_method_calibration"


def grade(y, p):
    classes = ["KO", "SUB", "DEC"]
    arr = p[classes].to_numpy(float)
    pred = np.asarray(classes)[np.argmax(arr, axis=1)]
    y = np.asarray(y, dtype=str)
    return {
        "n": int(len(y)),
        "accuracy": float(np.mean(pred == y)),
        "brier": float(multiclass_brier(y, arr, classes)),
        "log_loss": float(log_loss(y, arr[:, [2, 0, 1]], labels=["DEC", "KO", "SUB"])),
        "calls": {c: int(np.sum(pred == c)) for c in classes},
        "actual": {c: int(np.sum(y == c)) for c in classes},
        "recall": {c: float(np.mean(pred[y == c] == c)) if np.any(y == c) else None for c in classes},
    }


def chronology(frame, ridge):
    ys, bases, cals = [], [], []
    folds = []
    dates = sorted(frame["event_date"].unique())
    for test_date in dates[1:]:
        train = frame.loc[frame["event_date"] < test_date].copy()
        test = frame.loc[frame["event_date"] == test_date].copy()
        if len(train) < 12:
            continue
        cal = MethodInterceptCalibrator(ridge=ridge).fit(
            actual_method=train["clean_actual_method"],
            baseline_ko=train["base_KO"],
            baseline_sub=train["base_SUB"],
            baseline_dec=train["base_DEC"],
        )
        pred = cal.predict_proba(
            baseline_ko=test["base_KO"],
            baseline_sub=test["base_SUB"],
            baseline_dec=test["base_DEC"],
        )
        ys.extend(test["clean_actual_method"].tolist())
        bases.append(test[["base_KO", "base_SUB", "base_DEC"]].rename(columns={
            "base_KO":"KO","base_SUB":"SUB","base_DEC":"DEC"
        }).reset_index(drop=True))
        cals.append(pred.reset_index(drop=True))
        folds.append({
            "test_date": test_date,
            "train_n": int(len(train)),
            "test_n": int(len(test)),
            "finish_offset": cal.finish_offset_,
            "sub_offset": cal.sub_offset_,
        })
    y = np.asarray(ys, dtype=str)
    base = pd.concat(bases, ignore_index=True)
    cand = pd.concat(cals, ignore_index=True)
    return {
        "ridge": ridge,
        "baseline": grade(y, base),
        "candidate": grade(y, cand),
        "folds": folds,
    }


def main():
    frame = pd.read_csv(INPUT)
    candidates = [chronology(frame, r) for r in (0.5, 1.0, 2.0, 5.0, 10.0)]

    # Development selection: prioritize Brier, then log loss. This remains a
    # shadow choice and requires future prospective validation.
    best = min(
        candidates,
        key=lambda x: (x["candidate"]["brier"], x["candidate"]["log_loss"]),
    )
    final = MethodInterceptCalibrator(ridge=best["ridge"]).fit(
        actual_method=frame["clean_actual_method"],
        baseline_ko=frame["base_KO"],
        baseline_sub=frame["base_SUB"],
        baseline_dec=frame["base_DEC"],
    )

    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "V0.29_METHOD_INTERCEPT_CALIBRATION_SHADOW",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_rows": int(len(frame)),
        "candidate_grid": candidates,
        "selected_ridge": best["ridge"],
        "selected_chronology_grade": best,
        "final_offsets": {
            "finish_logit_offset": final.finish_offset_,
            "sub_given_finish_logit_offset": final.sub_offset_,
        },
        "promotion": {
            "authorized": False,
            "role": "shadow_candidate",
            "rule": "Must beat the baseline on future prospective method Brier/log loss before promotion.",
        },
    }
    (OUT / "benchmark.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (ART / "calibration.json").write_text(json.dumps({
        "ridge": best["ridge"],
        "finish_offset": final.finish_offset_,
        "sub_offset": final.sub_offset_,
    }, indent=2, sort_keys=True), encoding="utf-8")

    b = best["baseline"]
    c = best["candidate"]
    report = [
        "# v0.29 method intercept calibration",
        "",
        f"- Selected ridge: **{best['ridge']}**",
        f"- Chronology fights: **{c['n']}**",
        f"- Baseline accuracy: **{b['accuracy']:.4f}**",
        f"- Calibrated accuracy: **{c['accuracy']:.4f}**",
        f"- Baseline Brier: **{b['brier']:.6f}**",
        f"- Calibrated Brier: **{c['brier']:.6f}**",
        f"- Baseline log loss: **{b['log_loss']:.6f}**",
        f"- Calibrated log loss: **{c['log_loss']:.6f}**",
        f"- Baseline calls: **{b['calls']}**",
        f"- Calibrated calls: **{c['calls']}**",
        "",
        "This remains a shadow candidate. The grid search is retrospective development, not prospective proof.",
    ]
    (OUT / "BUILD_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
