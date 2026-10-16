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


rb = load_module("rebuild_v027_vegas122", ROOT / "tools/rebuild_v027.py")
v034 = load_module("benchmark_v034_vegas122_refresh", ROOT / "tools/benchmark_winner_interactions_v034.py")

from wshlx_ufc.grading import multiclass_brier
from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger, V027_FEATURES
from wshlx_ufc.models import ConditionalMethodModel, WinnerModel
from wshlx_ufc.nonperformance import activity_dates_from_raw
from wshlx_ufc.timing import DiscreteTimeHazardModel

RAW_DIR = ROOT / "data/raw/ufcvegas122_2026-10-10"
CLEAN_OLD = ROOT / "data/results/clean_ufc_101_2026-10-03.csv"
CLEAN_DELTA = ROOT / "data/results/clean_ufcvegas122_11_2026-10-10.csv"
CLEAN_OUT = ROOT / "data/results/clean_ufc_112_2026-10-10.csv"
GRADE = ROOT / "reports/ufcvegas122_2026-10-10/post_event_grade.json"
OUT = ROOT / "reports/v033_ufcvegas122_full_stats"
ART = ROOT / "artifacts/v033_ufcvegas122_full_stats"
V034_ART = ROOT / "artifacts/v034_winner_interactions"
SOURCE_COMMIT = "5e38ebeb9bb854c9ab4359f8f6f5b444328c555c"
EVENT = "UFC Fight Night: Allen vs. Duncan"


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
    """Merge verified older 'Kai Kamaka' UFCStats rows into Kai Kamaka III.

    The pre-Vegas-122 identity audit established that these records belong to
    the same fighter. This correction is applied before chronological feature
    construction, so older UFC bouts contribute to the current fighter state.
    """
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
        "policy": "Verified identity reconciliation; not a model-tuning change.",
    }


def build_clean112() -> pd.DataFrame:
    old = pd.read_csv(CLEAN_OLD)
    delta = pd.read_csv(CLEAN_DELTA)
    clean = pd.concat([old, delta], ignore_index=True)
    if len(clean) != 112:
        raise RuntimeError(f"Expected 112 clean decisive fights, got {len(clean)}")
    if clean.duplicated(["event_date", "fight"]).any():
        dupes = clean.loc[clean.duplicated(["event_date", "fight"], keep=False), ["event_date", "fight"]]
        raise RuntimeError(f"Duplicate clean rows found: {dupes.to_dict('records')}")
    clean.to_csv(CLEAN_OUT, index=False)
    return clean


def main():
    availability = json.loads((RAW_DIR / "availability.json").read_text())
    if not availability.get("full_card_stats_available"):
        raise RuntimeError("Full UFC Vegas 122 stats are unavailable or incomplete")
    if int(availability.get("unique_result_bouts", 0)) != 12:
        raise RuntimeError("Expected 12 UFC Vegas 122 result bouts")
    if int(availability.get("unique_stat_bouts", 0)) != 12:
        raise RuntimeError("Expected 12 UFC Vegas 122 stat bouts")
    if int(availability.get("fight_stat_rows", 0)) != 50:
        raise RuntimeError("Expected 50 UFC Vegas 122 fighter-round stat rows")
    if int(availability.get("decisive_result_rows", 0)) != 11 or int(availability.get("draw_result_rows", 0)) != 1:
        raise RuntimeError("Expected 11 decisive fights plus one draw")

    clean = build_clean112()

    old_cutoff = rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF = pd.Timestamp("2026-10-11", tz="UTC")
    try:
        fights, stats, static = rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF = old_cutoff

    fights, stats, static, identity_audit = merge_kai_kamaka_identity(fights, stats, static)
    event_decisive = fights.loc[fights["event"].map(rb.norm_text).eq(EVENT)]
    if len(event_decisive) != 11:
        raise RuntimeError(f"Expected 11 decisive Vegas 122 fights in training state, got {len(event_decisive)}")

    fight_stats = rb.aggregate_fight_stats(fights, stats)
    winner_df, method_df, timing_df = rb.enrich_and_snapshot(fights, fight_stats, static)

    clean_rows = rb.find_clean_rows(clean, method_df)
    if len(clean_rows) != 112:
        raise RuntimeError(f"Expected 112 matched clean rows, got {len(clean_rows)}")
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
        "winner": ART / "winner_v033_through_2026-10-10.joblib",
        "method_baseline": ART / "method_baseline_v033_through_2026-10-10.joblib",
        "method_residual": ART / "method_residual_v033_through_2026-10-10.joblib",
        "timing_30s": ART / "timing_v033_30s_through_2026-10-10.joblib",
    }
    for key, obj in [
        ("winner", winner),
        ("method_baseline", method),
        ("method_residual", residual),
        ("timing_30s", timing),
    ]:
        joblib.dump(obj, paths[key])

    # Refresh the already-selected v0.34 shadow on the newest causal history.
    # This does not re-grade Vegas 122 as prospective evidence for v0.34;
    # v0.34 was designed after this event and remains shadow-only.
    v034_df = v034.add_interactions(winner_df)
    v034_features = list(rb.WINNER_FEATURES) + list(v034.EXPERIENCE_FEATURES)
    v034_model = WinnerModel(c=0.25).fit(v034_df[v034_features], v034_df["winner_is_a"])
    v034_path = V034_ART / "winner_v034_experience_shadow_through_2026-10-10.joblib"
    joblib.dump(v034_model, v034_path)
    v034_refresh = {
        "status": "SHADOW_ONLY_NOT_PROMOTED",
        "trained_through": "2026-10-10",
        "selected_variant": "experience_only",
        "selected_features": list(v034.EXPERIENCE_FEATURES),
        "evaluation_note": "Vegas 122 is not counted as prospective validation for v0.34 because these features were designed after that event.",
        "artifact_sha256": sha256(v034_path),
    }
    (V034_ART / "refresh_2026-10-10.json").write_text(json.dumps(v034_refresh, indent=2, sort_keys=True), encoding="utf-8")

    activity = activity_dates_from_raw(RAW_DIR)
    (ART / "activity_last_dates.json").write_text(
        json.dumps({k: v.isoformat() for k, v in sorted(activity.items())}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    clean_oof.to_csv(OUT / "clean112_oof_method_inputs_fullstats.csv", index=False)

    grade = json.loads(GRADE.read_text())
    stage_a = grade["stage_a"]
    stage_b = grade["stage_b"]

    manifest = {
        "status": "V0.33_UFCVEGAS122_FULL_STATS_BACKBONE_REFRESH",
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
            "draw_bouts": availability["draw_bouts"],
        },
        "population": {
            "training_rows": int(len(winner_df)),
            "clean_feedback_rows": int(len(clean_oof)),
            "latest_performance_event_date": str(fights["event_date"].max()),
        },
        "identity_handling": identity_audit,
        "draw_handling": {
            "binary_winner_target": "EXCLUDED",
            "method_target": "EXCLUDED",
            "timing_training": "EXCLUDED under current decisive-fight loader",
            "raw_round_stats": "PRESERVED",
            "neutral_history": "NOT ACTIVATED pending separate tested pipeline change",
        },
        "prospective_ufcvegas122": {
            "winner_record_including_draw": stage_a["winner_record_including_draw"],
            "winner_accuracy_decisive_only": stage_a["winner_accuracy_decisive_only"],
            "displayed_method_record": stage_a["displayed_method_class_record_decisive_only"],
            "timing_lean_record": stage_a["timing_lean_record"],
            "stage_b_record": stage_b["record"],
            "stage_b_pnl_units": stage_b["pnl_units"],
        },
        "benchmarks": {
            "winner_clean112": winner_bench,
            "method_residual_clean112": residual_bench,
            "method_intercept_calibration_clean112": calibration_bench,
        },
        "final_method_calibration": {
            "ridge": 0.5,
            "finish_offset": calibrator.finish_offset_,
            "sub_given_finish_offset": calibrator.sub_offset_,
        },
        "artifact_sha256": {k: sha256(v) for k, v in paths.items()},
        "promotion": {
            "winner_reference": "UNCHANGED. Vegas 122 is one new frozen card and does not justify replacing the official reference.",
            "v033_role": "current full-stat data backbone refreshed through 2026-10-10",
            "v034": "SHADOW_ONLY. Refreshed on newest causal history; Vegas 122 is not prospective evidence for a challenger designed after that event.",
            "method_calibration": "LEADING_SHADOW_NOT_PROMOTED. Keep existing prospective promotion governance.",
            "timing": "SHADOW_PROBATION. Official timing is 0-5, -3.00u through Vegas 122; retain 12-point edge gate, sparse block and 0.25u cap.",
            "sparse_market_rule": "NO CHANGE. Continue prospective disagreement watchlist; do not remove sparse protections from two retrospective wins.",
        },
    }
    (ART / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (OUT / "benchmark.json").write_text(json.dumps(manifest["benchmarks"], indent=2, sort_keys=True), encoding="utf-8")
    (OUT / "identity_audit.json").write_text(json.dumps(identity_audit, indent=2, sort_keys=True), encoding="utf-8")

    report = [
        "# UFC Vegas 122 full-stat integration — v0.33 backbone refresh",
        "",
        f"- Canonical mirror source: `{SOURCE_COMMIT}`",
        "- Full card verified: **12/12 bouts, 50 fighter-round stat rows**",
        "- Decisive fights added to clean feedback: **11**",
        "- Majority draw: **Ernesta Kareckaite vs. Melissa Gatto** — preserved raw, excluded from binary/method targets.",
        f"- Clean feedback ledger: **{len(clean_oof)} decisive fights**",
        f"- Causal training rows: **{len(winner_df):,}**",
        f"- Latest included decisive performance date: **{fights['event_date'].max()}**",
        "- Verified Kai Kamaka / Kai Kamaka III histories are reconciled before feature construction.",
        "",
        "## Prospective Vegas 122 evidence",
        "",
        f"- Winner: **{stage_a['winner_record_including_draw']}**, decisive accuracy {stage_a['winner_accuracy_decisive_only']:.1%}",
        f"- Displayed method class: **{stage_a['displayed_method_class_record_decisive_only']}**",
        f"- Timing leans: **{stage_a['timing_lean_record']}**",
        f"- Stage B: **{stage_b['record']}**, {stage_b['pnl_units']:+.3f}u",
        "",
        "## Governance decisions",
        "",
        "- **No winner champion change.** One poor card is not enough to replace the reference model.",
        "- **v0.33 remains the full-stat backbone**, now refreshed through Oct. 10.",
        "- **v0.34 remains shadow-only.** Its selected experience-only shadow was refreshed on the new causal history, but Vegas 122 is not counted as validation because v0.34 was designed after the event.",
        "- **Method calibration remains a leading shadow**, subject to the existing promotion sample rule.",
        "- **Timing remains on probation at 0.25u max** with the 12-point edge and sparse-sample gates unchanged.",
        "- **Sparse underdog protections remain unchanged.** Frye/Tanzilovi stay in the prospective disagreement-study track, not a new staking rule.",
        "",
        "## Draw handling",
        "",
        "The Kareckaite-Gatto draw is excluded from the binary winner and method targets. Its 6 fighter-round rows are preserved in the raw package. A neutral-history representation is intentionally not activated until it can be benchmarked separately, avoiding the previous failure mode of silently treating draws as losses.",
    ]
    (OUT / "BUILD_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
