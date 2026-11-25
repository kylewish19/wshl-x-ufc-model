from __future__ import annotations

import hashlib
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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rb = load_module("rebuild_v027_edmonton", ROOT / "tools/rebuild_v027.py")
v034 = load_module("benchmark_v034_edmonton_refresh", ROOT / "tools/benchmark_winner_interactions_v034.py")

from wshlx_ufc.grading import multiclass_brier
from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger, V027_FEATURES
from wshlx_ufc.models import ConditionalMethodModel, WinnerModel
from wshlx_ufc.nonperformance import activity_dates_from_raw
from wshlx_ufc.timing import DiscreteTimeHazardModel

RAW_DIR = ROOT / "data/raw/ufcedmonton_2026-10-17"
CLEAN_OLD = ROOT / "data/results/clean_ufc_112_2026-10-10.csv"
CLEAN_DELTA = ROOT / "data/results/clean_ufcedmonton_13_2026-10-17.csv"
CLEAN_OUT = ROOT / "data/results/clean_ufc_125_2026-10-17.csv"
GRADE = ROOT / "reports/ufcedmonton_2026-10-17/post_event_grade.json"
OUT = ROOT / "reports/v033_ufcedmonton_full_stats"
ART = ROOT / "artifacts/v033_ufcedmonton_full_stats"
V034_ART = ROOT / "artifacts/v034_winner_interactions"
SOURCE_COMMIT = "3e2f3db5751c14b5d4ea52e41921982ca23b9b23"
EVENT = "UFC Fight Night: Buckley vs. Malott"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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


def merge_kai_kamaka_identity(fights: pd.DataFrame, stats: pd.DataFrame, static: dict):
    old_key = rb.norm_name("Kai Kamaka")
    new_key = rb.norm_name("Kai Kamaka III")
    relabelled_fight_fields = 0
    for col in ("fighter_a", "fighter_b", "winner"):
        mask = fights[col].map(rb.norm_name).eq(old_key)
        relabelled_fight_fields += int(mask.sum())
        fights.loc[mask, col] = "Kai Kamaka III"
    stat_mask = stats["FIGHTER_KEY"].eq(old_key)
    relabelled_stat_rows = int(stat_mask.sum())
    stats.loc[stat_mask, "FIGHTER"] = "Kai Kamaka III"
    stats.loc[stat_mask, "FIGHTER_KEY"] = new_key
    if old_key in static and new_key not in static:
        static[new_key] = dict(static[old_key])
        static[new_key]["name"] = "Kai Kamaka III"
    return fights, stats, static, {
        "canonical_name": "Kai Kamaka III",
        "older_display_name": "Kai Kamaka",
        "relabelled_fight_fields": relabelled_fight_fields,
        "relabelled_stat_rows": relabelled_stat_rows,
        "policy": "Verified identity reconciliation carried forward from the pre-Vegas-122 audit.",
    }


def build_clean125() -> pd.DataFrame:
    old = pd.read_csv(CLEAN_OLD)
    delta = pd.read_csv(CLEAN_DELTA)
    clean = pd.concat([old, delta], ignore_index=True)
    if len(clean) != 125:
        raise RuntimeError(f"Expected 125 clean decisive fights, got {len(clean)}")
    if clean.duplicated(["event_date", "fight"]).any():
        dupes = clean.loc[clean.duplicated(["event_date", "fight"], keep=False), ["event_date", "fight"]]
        raise RuntimeError(f"Duplicate clean rows found: {dupes.to_dict('records')}")
    clean.to_csv(CLEAN_OUT, index=False)
    return clean


def main():
    availability = json.loads((RAW_DIR / "availability.json").read_text())
    if not availability.get("full_card_stats_available"):
        raise RuntimeError("Full UFC Edmonton stats are unavailable or incomplete")
    expected = {
        "unique_result_bouts": 13,
        "unique_stat_bouts": 13,
        "fight_stat_rows": 50,
        "decisive_result_rows": 13,
        "draw_result_rows": 0,
    }
    for key, value in expected.items():
        if int(availability.get(key, -1)) != value:
            raise RuntimeError(f"Edmonton availability mismatch for {key}: expected {value}, got {availability.get(key)}")

    clean = build_clean125()

    old_cutoff = rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF = pd.Timestamp("2026-10-18", tz="UTC")
    try:
        fights, stats, static = rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF = old_cutoff

    fights, stats, static, identity_audit = merge_kai_kamaka_identity(fights, stats, static)
    event_decisive = fights.loc[fights["event"].map(rb.norm_text).eq(EVENT)]
    if len(event_decisive) != 13:
        raise RuntimeError(f"Expected 13 decisive Edmonton fights in training state, got {len(event_decisive)}")

    fight_stats = rb.aggregate_fight_stats(fights, stats)
    winner_df, method_df, timing_df = rb.enrich_and_snapshot(fights, fight_stats, static)

    clean_rows = rb.find_clean_rows(clean, method_df)
    if len(clean_rows) != 125:
        raise RuntimeError(f"Expected 125 matched clean rows, got {len(clean_rows)}")
    clean_oof = rb.add_clean_oof_baselines(clean_rows, method_df)
    winner_bench = rb.winner_clean_benchmark(clean, winner_df)
    residual_bench = rb.chronology_residual_benchmark(clean_oof)
    calibration_bench = chronology_calibration(clean_oof, 0.5)

    ART.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    V034_ART.mkdir(parents=True, exist_ok=True)

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
        "winner": ART / "winner_v033_through_2026-10-17.joblib",
        "method_baseline": ART / "method_baseline_v033_through_2026-10-17.joblib",
        "method_residual": ART / "method_residual_v033_through_2026-10-17.joblib",
        "method_calibrator": ART / "method_calibrator_v033_through_2026-10-17.joblib",
        "timing_30s": ART / "timing_v033_30s_through_2026-10-17.joblib",
    }
    for key, obj in [
        ("winner", winner),
        ("method_baseline", method),
        ("method_residual", residual),
        ("method_calibrator", calibrator),
        ("timing_30s", timing),
    ]:
        joblib.dump(obj, paths[key])

    v034_df = v034.add_interactions(winner_df)
    v034_features = list(rb.WINNER_FEATURES) + list(v034.EXPERIENCE_FEATURES)
    v034_model = WinnerModel(c=0.25).fit(v034_df[v034_features], v034_df["winner_is_a"])
    v034_path = V034_ART / "winner_v034_experience_shadow_through_2026-10-17.joblib"
    joblib.dump(v034_model, v034_path)
    v034_refresh = {
        "status": "SHADOW_ONLY_NOT_PROMOTED",
        "trained_through": "2026-10-17",
        "selected_variant": "experience_only",
        "selected_features": list(v034.EXPERIENCE_FEATURES),
        "evaluation_note": "Edmonton is admitted to training only after its frozen prospective grade. This refresh is not retroactive Edmonton validation and does not promote v0.34.",
        "artifact_sha256": sha256(v034_path),
    }
    (V034_ART / "refresh_2026-10-17.json").write_text(json.dumps(v034_refresh, indent=2, sort_keys=True), encoding="utf-8")

    activity = activity_dates_from_raw(RAW_DIR)
    (ART / "activity_last_dates.json").write_text(
        json.dumps({k: v.isoformat() for k, v in sorted(activity.items())}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    clean_oof.to_csv(OUT / "clean125_oof_method_inputs_fullstats.csv", index=False)

    grade = json.loads(GRADE.read_text())
    manifest = {
        "status": "V0.33_UFCEDMONTON_FULL_STATS_BACKBONE_REFRESH",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "upstream_commit": SOURCE_COMMIT,
            "event": EVENT,
            "full_card_stats_available": True,
            "unique_result_bouts": availability["unique_result_bouts"],
            "unique_stat_bouts": availability["unique_stat_bouts"],
            "fighter_round_stat_rows": availability["fight_stat_rows"],
            "decisive_result_rows": availability["decisive_result_rows"],
            "draw_result_rows": availability["draw_result_rows"],
        },
        "population": {
            "training_rows": int(len(winner_df)),
            "clean_feedback_rows": int(len(clean_oof)),
            "latest_performance_event_date": str(fights["event_date"].max()),
        },
        "identity_handling": identity_audit,
        "prospective_edmonton_frozen_grade": {
            "winner_record": grade["stage_a_grade"]["winner_record"],
            "winner_accuracy": grade["stage_a_grade"]["winner_accuracy"],
            "winner_brier": grade["stage_a_grade"]["winner_brier"],
            "winner_log_loss": grade["stage_a_grade"]["winner_log_loss"],
            "displayed_method_class_record": grade["stage_a_grade"]["displayed_method_class_record"],
            "stage_b_record": grade["stage_b_grade"]["record"],
            "stage_b_pnl_units": grade["stage_b_grade"]["profit_loss_units"],
            "timing_official_record_after_event": grade["timing_directional_grade"]["official_timing_record_after_event"],
        },
        "edmonton_diagnostics": {
            "actual_method_classes": grade["method_distribution"]["actual_method_classes"],
            "stage_a_top_method_classes": grade["method_distribution"]["stage_a_top_method_classes"],
            "submission_recall_by_class": grade["method_distribution"]["submission_recall_by_class"],
            "timing_directional_grade": grade["timing_directional_grade"],
            "governance_note": "Edmonton diagnostics motivate challenger testing only; no production architecture/promotion is inferred from hindsight.",
        },
        "benchmarks": {
            "winner_clean125": winner_bench,
            "method_residual_chronology": residual_bench,
            "method_intercept_calibration_chronology": calibration_bench,
        },
        "artifacts": {k: {"path": str(v.relative_to(ROOT)), "sha256": sha256(v)} for k, v in paths.items()},
        "v034_shadow": v034_refresh,
        "governance": {
            "reference_champion_changed": False,
            "v034_promoted": False,
            "method_global_promotion": False,
            "timing_global_promotion": False,
            "note": "This is a causal data/backbone refresh through 2026-10-17, not a hindsight promotion decision.",
        },
    }
    (ART / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (OUT / "integration_report.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
