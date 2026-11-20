from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import OffsetLogisticRidge

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/v033_ufcedmonton_full_stats/clean125_oof_method_inputs_fullstats.csv"
OUT = ROOT / "reports/post_edmonton_challengers/method_submission_access"

# Fixed before this diagnostic is run. These are explicit access-before-weapon signals
# already frozen in the causal method feature rows; no result-derived feature is used.
ACCESS_FEATURES = [
    "submission_attempt_interaction",
    "td_access_interaction",
    "control_interaction",
    "offensive_wrestling_exposure_interaction",
]
RIDGE = 10.0
CALIBRATION_RIDGE = 0.5


def grade(y: np.ndarray, p: np.ndarray) -> dict[str, object]:
    classes = np.asarray(["KO", "SUB", "DEC"])
    pred = classes[np.argmax(p, axis=1)]
    # multiclass Brier and log loss implemented directly to keep the report standalone.
    idx = {"KO": 0, "SUB": 1, "DEC": 2}
    onehot = np.zeros_like(p)
    for i, label in enumerate(y):
        onehot[i, idx[str(label)]] = 1.0
    pp = np.clip(p, 1e-12, 1.0)
    pp = pp / pp.sum(axis=1, keepdims=True)
    ll = -float(np.mean([np.log(pp[i, idx[str(label)]]) for i, label in enumerate(y)]))
    return {
        "n": int(len(y)),
        "accuracy": float(np.mean(pred == y)),
        "brier": float(np.mean(np.sum((pp - onehot) ** 2, axis=1))),
        "log_loss": ll,
        "calls": {c: int(np.sum(pred == c)) for c in classes},
        "actual": {c: int(np.sum(y == c)) for c in classes},
        "recall": {
            c: (float(np.mean(pred[y == c] == c)) if np.any(y == c) else None)
            for c in classes
        },
    }


def calibrated_probs(cal: MethodInterceptCalibrator, frame: pd.DataFrame) -> np.ndarray:
    out = cal.predict_proba(
        baseline_ko=frame["base_KO"],
        baseline_sub=frame["base_SUB"],
        baseline_dec=frame["base_DEC"],
    )
    return out[["KO", "SUB", "DEC"]].to_numpy(float)


def fit_access_head(train: pd.DataFrame, train_cal: np.ndarray):
    method = train["clean_actual_method"].astype(str).to_numpy()
    finish_mask = method != "DEC"
    y_sub = (method[finish_mask] == "SUB").astype(float)
    if finish_mask.sum() < 8 or len(np.unique(y_sub)) < 2:
        raise ValueError("insufficient KO/SUB finish examples for access head")

    finish_prob = train_cal[finish_mask, 0] + train_cal[finish_mask, 1]
    baseline_sub_given_finish = np.divide(
        train_cal[finish_mask, 1],
        finish_prob,
        out=np.full(int(finish_mask.sum()), 0.5, dtype=float),
        where=finish_prob > 0,
    )
    imputer = SimpleImputer(strategy="median", add_indicator=True)
    scaler = StandardScaler()
    x = imputer.fit_transform(train.loc[finish_mask, ACCESS_FEATURES].astype(float))
    z = np.clip(scaler.fit_transform(x), -5.0, 5.0)
    head = OffsetLogisticRidge(ridge=RIDGE).fit(z, y_sub, baseline_sub_given_finish)
    return imputer, scaler, head, int(finish_mask.sum()), int(y_sub.sum())


def apply_access_head(test: pd.DataFrame, test_cal: np.ndarray, imputer, scaler, head) -> np.ndarray:
    x = imputer.transform(test[ACCESS_FEATURES].astype(float))
    z = np.clip(scaler.transform(x), -5.0, 5.0)
    p_finish = test_cal[:, 0] + test_cal[:, 1]
    base_sub_cond = np.divide(
        test_cal[:, 1],
        p_finish,
        out=np.full(len(test_cal), 0.5, dtype=float),
        where=p_finish > 0,
    )
    p_sub_cond = head.predict_proba(z, base_sub_cond)
    p_sub = p_finish * p_sub_cond
    p_ko = p_finish * (1.0 - p_sub_cond)
    p_dec = test_cal[:, 2]
    out = np.column_stack([p_ko, p_sub, p_dec])
    return out / out.sum(axis=1, keepdims=True)


def main() -> None:
    df = pd.read_csv(SOURCE)
    missing = [c for c in ACCESS_FEATURES if c not in df]
    if missing:
        raise RuntimeError(f"missing access features: {missing}")

    dates = sorted(df["event_date"].astype(str).unique())
    all_y: list[str] = []
    all_cal: list[np.ndarray] = []
    all_access: list[np.ndarray] = []
    rows: list[dict] = []
    folds = []

    for test_date in dates[1:]:
        train = df[df["event_date"].astype(str) < test_date].copy()
        test = df[df["event_date"].astype(str) == test_date].copy()
        if len(train) < 12 or test.empty:
            continue

        cal = MethodInterceptCalibrator(ridge=CALIBRATION_RIDGE).fit(
            actual_method=train["clean_actual_method"],
            baseline_ko=train["base_KO"], baseline_sub=train["base_SUB"], baseline_dec=train["base_DEC"],
        )
        train_cal = calibrated_probs(cal, train)
        test_cal = calibrated_probs(cal, test)
        try:
            imputer, scaler, head, finish_n, sub_n = fit_access_head(train, train_cal)
        except ValueError:
            continue
        access = apply_access_head(test, test_cal, imputer, scaler, head)
        y = test["clean_actual_method"].astype(str).to_numpy()

        all_y.extend(y.tolist())
        all_cal.append(test_cal)
        all_access.append(access)
        folds.append({
            "test_date": test_date,
            "train_fights": int(len(train)),
            "train_finishes": finish_n,
            "train_submissions": sub_n,
            "test_fights": int(len(test)),
            "finish_offset": float(cal.finish_offset_),
            "sub_offset": float(cal.sub_offset_),
            "access_coefficients_scaled": {
                name: float(coef) for name, coef in zip(ACCESS_FEATURES, head.coef_[: len(ACCESS_FEATURES)])
            },
        })
        for i, (_, r) in enumerate(test.iterrows()):
            rows.append({
                "event_date": test_date,
                "fight": r["bout"],
                "actual_method": y[i],
                "cal_KO": test_cal[i, 0], "cal_SUB": test_cal[i, 1], "cal_DEC": test_cal[i, 2],
                "access_KO": access[i, 0], "access_SUB": access[i, 1], "access_DEC": access[i, 2],
            })

    if not all_y:
        raise RuntimeError("no chronological folds available")
    y = np.asarray(all_y, dtype=str)
    cal_p = np.vstack(all_cal)
    access_p = np.vstack(all_access)
    cal_grade = grade(y, cal_p)
    access_grade = grade(y, access_p)

    comp = pd.DataFrame(rows)
    edm = comp[comp["event_date"].astype(str).str.startswith("2026-10-17")].copy()
    edm_y = edm["actual_method"].astype(str).to_numpy()
    edm_cal = edm[["cal_KO", "cal_SUB", "cal_DEC"]].to_numpy(float)
    edm_access = edm[["access_KO", "access_SUB", "access_DEC"]].to_numpy(float)

    payload = {
        "status": "POST_EDMONTON_SUBMISSION_ACCESS_SHADOW_DIAGNOSTIC",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(SOURCE.relative_to(ROOT)),
        "design": {
            "finish_head": "chronological MethodInterceptCalibrator; unchanged between comparison arms",
            "sub_vs_ko_head": "strong-ridge offset logistic correction around calibrated SUB-vs-KO probability",
            "access_features": ACCESS_FEATURES,
            "ridge": RIDGE,
            "calibration_ridge": CALIBRATION_RIDGE,
            "odds_used": False,
        },
        "chronological_evaluation": {
            "calibrated_reference": cal_grade,
            "submission_access_candidate": access_grade,
            "delta_accuracy": access_grade["accuracy"] - cal_grade["accuracy"],
            "delta_brier": access_grade["brier"] - cal_grade["brier"],
            "delta_log_loss": access_grade["log_loss"] - cal_grade["log_loss"],
            "delta_sub_recall": (
                access_grade["recall"]["SUB"] - cal_grade["recall"]["SUB"]
                if access_grade["recall"]["SUB"] is not None and cal_grade["recall"]["SUB"] is not None else None
            ),
        },
        "edmonton_fold": {
            "calibrated_reference": grade(edm_y, edm_cal) if len(edm) else None,
            "submission_access_candidate": grade(edm_y, edm_access) if len(edm) else None,
        },
        "folds": folds,
        "governance": {
            "production_change": False,
            "promotion_allowed_from_this_report": False,
            "reason": "Access architecture was specified after Edmonton exposed a submission-recall weakness. This is retrospective development evidence only and must remain shadow until future frozen cards test it.",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diagnostic.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    comp.to_csv(OUT / "chronological_predictions.csv", index=False)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
