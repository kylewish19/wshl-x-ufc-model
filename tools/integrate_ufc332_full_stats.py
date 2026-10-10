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

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rb = load_module("rebuild_v027_v033", ROOT / "tools/rebuild_v027.py")

from wshlx_ufc.grading import multiclass_brier
from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger, V027_FEATURES
from wshlx_ufc.models import ConditionalMethodModel, WinnerModel
from wshlx_ufc.nonperformance import activity_dates_from_raw
from wshlx_ufc.timing import DiscreteTimeHazardModel

RAW_DIR = ROOT / "data/raw/ufc332_2026-10-03"
CLEAN = ROOT / "data/results/clean_ufc_101_2026-10-03.csv"
GRADE = ROOT / "reports/ufc332_2026-10-03/post_event_grade.json"
OUT = ROOT / "reports/v033_ufc332_full_stats"
ART = ROOT / "artifacts/v033_ufc332_full_stats"
SOURCE_COMMIT = "1ccacc5cd4f642bd2deb8b278405a0205791bfa3"
UFC332_EVENT = "UFC 332: Silva vs. Wang"


def grade_methods(y, pdf):
    classes = ["KO", "SUB", "DEC"]
    arr = pdf[classes].to_numpy(float)
    y = np.asarray(y, dtype=str)
    pred = np.asarray(classes)[np.argmax(arr, axis=1)]
    return {
        "n": int(len(y)),
        "accuracy": float(np.mean(pred == y)),
        "brier": float(multiclass_brier(y, arr, classes)),
        "log_loss": float(log_loss(y, arr[:, [2, 0, 1]], labels=["DEC", "KO", "SUB"])),
        "calls": {c: int(np.sum(pred == c)) for c in classes},
        "actual": {c: int(np.sum(y == c)) for c in classes},
        "recall": {
            c: (float(np.mean(pred[y == c] == c)) if np.any(y == c) else None)
            for c in classes
        },
    }


def chronology_calibration(clean_oof, ridge=0.5):
    ys, bases, cals, folds = [], [], [], []
    for test_date in sorted(clean_oof["event_date"].unique())[1:]:
        train = clean_oof.loc[clean_oof["event_date"] < test_date]
        test = clean_oof.loc[clean_oof["event_date"] == test_date]
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
        bases.append(
            test[["base_KO", "base_SUB", "base_DEC"]]
            .rename(columns={"base_KO": "KO", "base_SUB": "SUB", "base_DEC": "DEC"})
            .reset_index(drop=True)
        )
        cals.append(pred.reset_index(drop=True))
        folds.append(
            {
                "test_date": str(test_date),
                "train_n": int(len(train)),
                "test_n": int(len(test)),
                "finish_offset": cal.finish_offset_,
                "sub_offset": cal.sub_offset_,
            }
        )
    y = np.asarray(ys, dtype=str)
    return {
        "ridge": ridge,
        "baseline": grade_methods(y, pd.concat(bases, ignore_index=True)),
        "candidate": grade_methods(y, pd.concat(cals, ignore_index=True)),
        "folds": folds,
    }


def separate_anthony_romero_identities(fights: pd.DataFrame, stats: pd.DataFrame):
    """Prevent the older lightweight Anthony Romero from leaking into the
    UFC 332 featherweight debutant's history.

    UFCStats exposes both athletes under the same display name. The Oct. 3,
    2026 McGhee bout belongs to fighter id 4419acb81e6f0ea4 (The Bully).
    Older same-name UFCStats/DWCS rows belong to a different athlete and are
    relabeled internally before chronological feature construction.
    """
    old_label = "Anthony Romero (The Genius)"
    bully_key = rb.norm_name("Anthony Romero")
    genius_key = rb.norm_name(old_label)

    old_fight_rows = 0
    for col in ("fighter_a", "fighter_b", "winner"):
        mask = (
            fights[col].map(rb.norm_name).eq(bully_key)
            & fights["event"].map(rb.norm_text).ne(UFC332_EVENT)
        )
        old_fight_rows += int(mask.sum())
        fights.loc[mask, col] = old_label

    stat_mask = (
        stats["FIGHTER_KEY"].eq(bully_key)
        & stats["EVENT_KEY"].map(rb.norm_text).ne(UFC332_EVENT)
    )
    old_stat_rows = int(stat_mask.sum())
    stats.loc[stat_mask, "FIGHTER"] = old_label
    stats.loc[stat_mask, "FIGHTER_KEY"] = genius_key

    return fights, stats, {
        "same_name": "Anthony Romero",
        "ufc332_identity": "Anthony Romero 'The Bully' / UFCStats id 4419acb81e6f0ea4",
        "older_identity_label": old_label,
        "old_fight_fields_relabelled": old_fight_rows,
        "old_stat_rows_relabelled": old_stat_rows,
        "policy": "Never merge histories solely because normalized display names match when a verified same-name collision exists.",
    }


def main():
    availability = json.loads((RAW_DIR / "availability.json").read_text())
    if not availability.get("full_card_stats_available"):
        raise RuntimeError("Full UFC 332 stats are unavailable or incomplete")
    if int(availability.get("unique_stat_bouts", 0)) != 14:
        raise RuntimeError("Expected 14 UFC 332 stat bouts")
    if int(availability.get("fight_stat_rows", 0)) != 50:
        raise RuntimeError("Expected 50 UFC 332 fighter-round stat rows")

    old_cutoff = rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF = pd.Timestamp("2026-10-04", tz="UTC")
    try:
        fights, stats, static = rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF = old_cutoff

    fights, stats, identity_audit = separate_anthony_romero_identities(fights, stats)
    fight_stats = rb.aggregate_fight_stats(fights, stats)
    winner_df, method_df, timing_df = rb.enrich_and_snapshot(fights, fight_stats, static)

    clean = pd.read_csv(CLEAN)
    clean_rows = rb.find_clean_rows(clean, method_df)
    clean_oof = rb.add_clean_oof_baselines(clean_rows, method_df)
    winner_bench = rb.winner_clean_benchmark(clean, winner_df)
    residual_bench = rb.chronology_residual_benchmark(clean_oof)
    calibration_bench = chronology_calibration(clean_oof, 0.5)

    ART.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    winner = WinnerModel(c=0.25).fit(winner_df[rb.WINNER_FEATURES], winner_df["winner_is_a"])
    method = ConditionalMethodModel(finish_c=0.10, sub_c=0.10).fit(
        method_df[rb.METHOD_BASE_FEATURES], method_df["method"]
    )
    residual = V027MethodResidualChallenger(ridge=10.0, clip_z=5.0).fit(
        clean_oof[list(V027_FEATURES)],
        actual_method=clean_oof["clean_actual_method"],
        baseline_ko=clean_oof["base_KO"],
        baseline_sub=clean_oof["base_SUB"],
        baseline_dec=clean_oof["base_DEC"],
    )
    calibrator = MethodInterceptCalibrator(ridge=0.5).fit(
        actual_method=clean_oof["clean_actual_method"],
        baseline_ko=clean_oof["base_KO"],
        baseline_sub=clean_oof["base_SUB"],
        baseline_dec=clean_oof["base_DEC"],
    )
    timing = DiscreteTimeHazardModel(bin_seconds=30, c=0.10).fit(
        timing_df[rb.TIMING_FEATURES],
        timing_df["duration_seconds"].to_numpy(float),
        timing_df["scheduled_seconds"].to_numpy(int),
        (
            (timing_df["method"] != "DEC")
            | (timing_df["duration_seconds"] < timing_df["scheduled_seconds"])
        ).astype(int).to_numpy(),
    )

    paths = {
        "winner": ART / "winner_v033.joblib",
        "method_baseline": ART / "method_baseline_v033.joblib",
        "method_residual": ART / "method_residual_v033.joblib",
        "timing_30s": ART / "timing_v033_30s.joblib",
    }
    for key, obj in [
        ("winner", winner),
        ("method_baseline", method),
        ("method_residual", residual),
        ("timing_30s", timing),
    ]:
        joblib.dump(obj, paths[key])

    activity = activity_dates_from_raw(RAW_DIR)
    activity_payload = {k: v.isoformat() for k, v in sorted(activity.items())}
    (ART / "activity_last_dates.json").write_text(
        json.dumps(activity_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    clean_oof.to_csv(OUT / "clean101_oof_method_inputs_fullstats.csv", index=False)

    grade = json.loads(GRADE.read_text())
    prospective = grade["prospective_model_metrics"]

    import hashlib

    def sha(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()

    manifest = {
        "status": "V0.33_UFC332_FULL_STATS_SHADOW",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "upstream_commit": SOURCE_COMMIT,
            "full_card_stats_available": True,
            "unique_result_bouts": availability["unique_result_bouts"],
            "unique_stat_bouts": availability["unique_stat_bouts"],
            "fighter_round_stat_rows": availability["fight_stat_rows"],
        },
        "population": {
            "training_rows": int(len(winner_df)),
            "clean_feedback_rows": int(len(clean_oof)),
            "latest_performance_event_date": str(fights["event_date"].max()),
        },
        "identity_handling": identity_audit,
        "prospective_ufc332_pre_retrain": prospective,
        "benchmarks": {
            "winner_clean101": winner_bench,
            "method_residual_clean101": residual_bench,
            "method_intercept_calibration_clean101": calibration_bench,
        },
        "final_method_calibration": {
            "ridge": 0.5,
            "finish_offset": calibrator.finish_offset_,
            "sub_given_finish_offset": calibrator.sub_offset_,
        },
        "artifact_sha256": {k: sha(v) for k, v in paths.items()},
        "promotion": {
            "winner_v032": "NOT_PROMOTED: reference and v0.32 both went 13-1 on UFC 332, while reference retained slightly better prospective Brier/log loss.",
            "method_calibration": "LEADING_SHADOW_NOT_PROMOTED: calibrated method again beat baseline and residual prospectively, but governance still requires 300 newly locked prospective fights before champion promotion.",
            "timing": "SHADOW_PROBATION: UFC 332 timing leans were 8-6, while official timing wagers are 0-4 through UFC 332. Retain model, sparse block and 0.25u probation cap.",
            "v033_role": "current full-stat data backbone + shadow retrain for future cards",
        },
    }
    (ART / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (OUT / "benchmark.json").write_text(json.dumps(manifest["benchmarks"], indent=2, sort_keys=True), encoding="utf-8")
    (OUT / "identity_audit.json").write_text(json.dumps(identity_audit, indent=2, sort_keys=True), encoding="utf-8")

    report = [
        "# v0.33 UFC 332 full-stat integration",
        "",
        f"- UFC 332 full stats: **{availability['unique_stat_bouts']}/14 bouts, {availability['fight_stat_rows']} fighter-round rows**",
        f"- Clean feedback ledger: **{len(clean_oof)} fights**",
        f"- Causal training rows: **{len(winner_df):,}**",
        f"- Latest included performance date: **{fights['event_date'].max()}**",
        "- Same-name Anthony Romero histories are separated before feature construction.",
        "",
        "## Frozen UFC 332 prospective evidence",
        "",
        "- Winner reference: **13-1 (92.9%)**, Brier **0.1539**, log loss **0.4830**",
        "- Winner v0.32 shadow: **13-1 (92.9%)**, Brier **0.1542**, log loss **0.4842**",
        "- Method baseline: **42.9%**, Brier **0.5496**",
        "- Method calibrated: **71.4%**, Brier **0.4086**",
        "- Method residual: **42.9%**, Brier **0.5964**",
        "- Timing leans: **8-6 (57.1%)**",
        "",
        "## Promotion decision",
        "",
        "**Winner v0.32 is not promoted.** The reference still had slightly better probability quality on the frozen UFC 332 test.",
        "**Method calibration remains the leading shadow, not champion.** It won another unseen card, but the 300-fight prospective promotion rule remains in force.",
        "**Timing remains shadow/probationary.** Keep the 12-point edge gate, sparse-sample block and 0.25u official timing stake cap.",
        "**v0.33 is the new full-stat data backbone for future cards.**",
    ]
    (OUT / "BUILD_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
