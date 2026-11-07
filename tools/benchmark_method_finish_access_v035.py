"""v0.35 SHADOW ONLY: conditional finish-vs-decision access correction.

Motivated by repeat high-variance KO/DEC method errors across multiple UFC cards.
The feature set and ridge are fixed in this script. Walk-forward folds have no
random split or post-event input. Historical results are development evidence
only; UFC333 was known before this new design, so it is NOT a prospective test.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import OffsetLogisticRidge

SOURCE = ROOT / "reports/ufc333_2026-10-24/full_stats/clean139_causal_method_inputs.csv"
OUT = ROOT / "reports/post_ufc333_method_finish_access"
CLASSES = ["KO", "SUB", "DEC"]
FEATURES = [
    "winner_recent5_finish_rate",
    "opponent_recent5_finish_rate",
    "winner_kd_for_per15",
    "opponent_kd_against_per15",
    "winner_sub_att_per15",
    "opponent_sub_att_against_per15",
    "scheduled_five_round",
]
RIDGE = 20.0
CALIBRATION_RIDGE = 0.5
EPS = 1e-7


def fit_scaler(train: pd.DataFrame):
    imp = SimpleImputer(strategy="median", add_indicator=True)
    scl = StandardScaler()
    mat = imp.fit_transform(train[FEATURES].astype(float))
    return imp, scl, np.clip(scl.fit_transform(mat), -5, 5)


def candidate_finish(train: pd.DataFrame, test: pd.DataFrame, train_cal: np.ndarray, test_cal: np.ndarray):
    imp, scl, ztrain = fit_scaler(train)
    ztest = np.clip(scl.transform(imp.transform(test[FEATURES].astype(float))), -5, 5)
    base_finish_train = np.clip(train_cal[:, 0] + train_cal[:, 1], EPS, 1 - EPS)
    base_finish_test = np.clip(test_cal[:, 0] + test_cal[:, 1], EPS, 1 - EPS)
    y = train["clean_actual_method"].astype(str).ne("DEC").astype(int).to_numpy()
    if len(np.unique(y)) != 2:
        raise ValueError("Finish training label must contain both DEC and non-DEC")
    clf = OffsetLogisticRidge(ridge=RIDGE).fit(ztrain, y, base_finish_train)
    finish = np.clip(clf.predict_proba(ztest, base_finish_test), EPS, 1 - EPS)
    pko_cond = test_cal[:, 0] / base_finish_test
    psub_cond = test_cal[:, 1] / base_finish_test
    pred = np.column_stack([finish * pko_cond, finish * psub_cond, 1 - finish])
    pred = pred / pred.sum(axis=1, keepdims=True)
    return pred, {"ridge": RIDGE, "coefficients_scaled": [float(x) for x in clf.coef_],
                   "train_fights": int(len(train)), "train_finishes": int(y.sum())}


def grade(y: np.ndarray, p: np.ndarray):
    classes = np.asarray(CLASSES)
    predicted = classes[p.argmax(axis=1)]
    actual = np.asarray(y, dtype=str)
    eye = (classes.reshape(1, -1) == actual.reshape(-1, 1)).astype(float)
    return {
        "n": int(len(y)),
        "accuracy": float(np.mean(predicted == actual)),
        "correct": int(np.sum(predicted == actual)),
        "brier": float(np.mean(np.sum((p - eye) ** 2, axis=1))),
        "log_loss": float(-np.mean(np.log(np.clip(p[eye.astype(bool)], 1e-10, 1)))),
        "actual": {k: int(np.sum(actual == k)) for k in CLASSES},
        "calls": {k: int(np.sum(predicted == k)) for k in CLASSES},
        "recall": {k: float(np.mean(predicted[actual == k] == k)) if np.any(actual == k) else None for k in CLASSES},
        "mean_predicted_decision": float(p[:, 2].mean()),
        "actual_decision_rate": float(np.mean(actual == "DEC")),
    }


def main():
    df = pd.read_csv(SOURCE)
    if len(df) != 139:
        raise RuntimeError(f"Expected 139 causal clean method rows, got {len(df)}")
    for key in FEATURES:
        if key not in df:
            raise RuntimeError(f"Required pre-fight feature missing: {key}")
    if any(x in ("method", "winner", "duration_seconds", "actual_method", "event_date") for x in FEATURES):
        raise RuntimeError("Target/identification field accidentally used as feature")
    df["event_date"] = df["event_date"].astype(str).str[:10]
    predictions, folds = [], []
    for date in sorted(df.event_date.unique())[1:]:
        train = df[df.event_date < date].copy()
        test = df[df.event_date == date].copy()
        if len(train) < 24:
            continue
        cal = MethodInterceptCalibrator(ridge=CALIBRATION_RIDGE).fit(
            actual_method=train["clean_actual_method"],
            baseline_ko=train["base_KO"], baseline_sub=train["base_SUB"], baseline_dec=train["base_DEC"]
        )
        tc = cal.predict_proba(
            baseline_ko=train["base_KO"], baseline_sub=train["base_SUB"], baseline_dec=train["base_DEC"]
        )[CLASSES].to_numpy(float)
        pc = cal.predict_proba(
            baseline_ko=test["base_KO"], baseline_sub=test["base_SUB"], baseline_dec=test["base_DEC"]
        )[CLASSES].to_numpy(float)
        pp, receipt = candidate_finish(train, test, tc, pc)
        y = test["clean_actual_method"].astype(str).to_numpy()
        folds.append({"date": date, **receipt, "test_fights": len(test),
                      "calibrated": grade(y, pc), "finish_access": grade(y, pp)})
        for i, (_, r) in enumerate(test.iterrows()):
            pred = {"event_date": date, "bout": r["bout"], "actual_method": y[i]}
            for j, c in enumerate(CLASSES):
                pred[f"cal_{c}"] = float(pc[i, j])
                pred[f"finish_{c}"] = float(pp[i, j])
            predictions.append(pred)
    p = pd.DataFrame(predictions)
    if len(p[p.event_date == "2026-10-24"]) != 14:
        raise RuntimeError("Missing UFC333 fold in finish-access evaluation")
    output = {}
    for name, g in {
        "all_historical_dev": p,
        "prior_125_feedback_dev": p[p.event_date < "2026-10-24"],
        "ufc333_retrospective": p[p.event_date == "2026-10-24"],
    }.items():
        y = g.actual_method.to_numpy(str)
        output[name] = {}
        for model in ("cal", "finish"):
            output[name][model] = grade(y, g[[f"{model}_{c}" for c in CLASSES]].to_numpy(float))
        output[name]["delta_finish_minus_cal"] = {
            "accuracy": output[name]["finish"]["accuracy"] - output[name]["cal"]["accuracy"],
            "brier": output[name]["finish"]["brier"] - output[name]["cal"]["brier"],
            "log_loss": output[name]["finish"]["log_loss"] - output[name]["cal"]["log_loss"],
        }
    result = {
        "status": "V0.35_METHOD_FINISH_ACCESS_RETROSPECTIVE_RESEARCH_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "feature_source": str(SOURCE.relative_to(ROOT)),
        "feature_names": FEATURES,
        "ridge": RIDGE, "calibration_ridge": CALIBRATION_RIDGE,
        "training_scope": "Causal pre-bout snapshots; train and calibrate before each event.",
        "evaluation": output, "folds": folds,
        "governance": {
            "development_post_ufc333": True,
            "ufc333_is_not_clean_prospective_proof": True,
            "model_role": "RESEARCH_SHADOW",
            "promoted": False,
            "reason": "This variant was proposed after UFC333. Chronology checks are necessary but not sufficient; future unseen frozen cards required.",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diagnostic.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    p.to_csv(OUT / "chronological_predictions.csv", index=False)
    print(json.dumps({"status": result["status"], "scores": output}, indent=2))


if __name__ == "__main__":
    main()
