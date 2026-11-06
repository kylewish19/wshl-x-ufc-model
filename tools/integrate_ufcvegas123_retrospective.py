"""Causal UFC Oct 31 retrospective full-stat learning, without fabricated Stage A.

- Preserves 139 real frozen/graded events untouched.
- Writes a SEPARATE 'retrospective/unpicked' October 31 result and stat ledger.
- Checks out-of-event-date method predictions conditioned on the *known* winner:
  this is a CLASSIFIER DIAGNOSTIC, never a fight-side or official bet prediction.
- Retrains future-only shadow artifacts using Oct 31 data after grading.
"""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rb = load_module("rb_oct31_2026", ROOT / "tools/rebuild_v027.py")
access = load_module("access_oct31_2026", ROOT / "tools/diagnose_method_submission_access_edmonton.py")
from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger, V027_FEATURES
from wshlx_ufc.models import ConditionalMethodModel, WinnerModel
from wshlx_ufc.nonperformance import activity_dates_from_raw
from wshlx_ufc.timing import DiscreteTimeHazardModel

RAW = ROOT / "data/raw/ufcvegas123_2026-10-31"
CLEAN = ROOT / "data/results/clean_ufc_139_2026-10-24.csv"
PRIOR_OOF = ROOT / "reports/ufc333_2026-10-24/full_stats/clean139_causal_method_inputs.csv"
OUT_DIR = ROOT / "reports/ufcvegas123_2026-10-31/retrospective"
ART = ROOT / "artifacts/ufcvegas123_post_event_shadow"
RESULTS = ROOT / "data/results/ufcvegas123_2026-10-31_retrospective_only.csv"
FIGHTER_STATS = ROOT / "data/results/ufcvegas123_2026-10-31_fighter_stats.csv"
CUTOFF = "2026-10-31"
CLASSES = ["KO", "SUB", "DEC"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fix_known_identities(fights: pd.DataFrame, stats: pd.DataFrame, static: dict):
    """Preserve same-name split and verified aliases from previous integration."""
    notes = {}
    # As before, retain older Anthony Romero distinct from the 2026-10-03 debutant.
    old_key = rb.norm_name("Anthony Romero")
    old_label = "Anthony Romero (The Genius)"
    non332 = fights["event"].map(rb.norm_text).ne("UFC 332: Silva vs. Wang")
    relabeled = 0
    for col in ("fighter_a", "fighter_b", "winner"):
        mask = fights[col].map(rb.norm_name).eq(old_key) & non332
        relabeled += int(mask.sum())
        fights.loc[mask, col] = old_label
    stat_mask = stats["FIGHTER_KEY"].eq(old_key) & stats["EVENT_KEY"].map(rb.norm_text).ne("UFC 332: Silva vs. Wang")
    stats.loc[stat_mask, "FIGHTER"] = old_label
    stats.loc[stat_mask, "FIGHTER_KEY"] = rb.norm_name(old_label)
    notes["anthony_romero"] = {
        "relabelled_fight_fields": relabeled,
        "relabelled_stat_rows": int(stat_mask.sum()),
        "older_identity_kept_separate": True
    }

    old_key, new_key = rb.norm_name("Kai Kamaka"), rb.norm_name("Kai Kamaka III")
    alias_count = 0
    for col in ("fighter_a", "fighter_b", "winner"):
        mask = fights[col].map(rb.norm_name).eq(old_key)
        alias_count += int(mask.sum())
        fights.loc[mask, col] = "Kai Kamaka III"
    stat_mask = stats["FIGHTER_KEY"].eq(old_key)
    stats.loc[stat_mask, "FIGHTER"] = "Kai Kamaka III"
    stats.loc[stat_mask, "FIGHTER_KEY"] = new_key
    if old_key in static and new_key not in static:
        static[new_key] = dict(static[old_key])
        static[new_key]["name"] = "Kai Kamaka III"
    notes["kai_kamaka"] = {"relabelled_fight_fields": alias_count, "round_rows": int(stat_mask.sum())}

    # Current UFCResults lists Zachary Reese; UFCStats exports Zach Reese.
    # Keep observed history together under one canonical name in this rebuild.
    z_old, z_new = rb.norm_name("Zach Reese"), rb.norm_name("Zachary Reese")
    z_count = 0
    for col in ("fighter_a", "fighter_b", "winner"):
        mask = fights[col].map(rb.norm_name).eq(z_old)
        z_count += int(mask.sum())
        fights.loc[mask, col] = "Zachary Reese"
    stat_mask = stats["FIGHTER_KEY"].eq(z_old)
    stats.loc[stat_mask, "FIGHTER"] = "Zachary Reese"
    stats.loc[stat_mask, "FIGHTER_KEY"] = z_new
    if z_old in static and z_new not in static:
        static[z_new] = dict(static[z_old])
        static[z_new]["name"] = "Zachary Reese"
    notes["zach_reese"] = {"relabelled_fight_fields": z_count, "round_rows": int(stat_mask.sum())}
    return fights, stats, static, notes


def pure_grade(y: np.ndarray, p: np.ndarray) -> dict:
    return access.grade(np.asarray(y, dtype=str), np.asarray(p, dtype=float))


def make_event_stats(fights: pd.DataFrame, totals: dict) -> pd.DataFrame:
    rows = []
    target = fights[fights["event_date"].astype(str).str.startswith(CUTOFF)]
    for bout in target.itertuples(index=False):
        for name, opponent in ((bout.fighter_a, bout.fighter_b), (bout.fighter_b, bout.fighter_a)):
            vals = totals.get((rb.norm_text(bout.event), rb.norm_text(bout.bout), rb.norm_name(name)))
            if vals is None:
                raise RuntimeError(f"Missing fighter aggregate stats {bout.bout}: {name}")
            row = {
                "event_date": CUTOFF,
                "fight": bout.bout,
                "fighter": name, "opponent": opponent,
                "actual_winner": bout.winner,
                "actual_method": bout.method,
                "finish_round": bout.finish_round,
                "duration_seconds": bout.duration_seconds,
                "official_stats_fight_url": bout.fight_url,
            }
            for col in ("sig_landed", "sig_attempted", "kd_for", "ground_landed",
                        "ground_attempted", "td_landed", "td_attempted", "sub_att", "ctrl_seconds"):
                row[col] = vals[col]
            rows.append(row)
    result = pd.DataFrame(rows)
    if len(result) != 24:
        raise RuntimeError(f"Expected 24 fighter-fight rows; got {len(result)}")
    result.to_csv(FIGHTER_STATS, index=False)
    return result


def make_retrospective_results(fights: pd.DataFrame, audit: dict):
    target = fights[fights["event_date"].astype(str).str.startswith(CUTOFF)]
    rows = []
    for r in target.itertuples(index=False):
        parts = {rb.norm_name(r.fighter_a), rb.norm_name(r.fighter_b)}
        raw = next((x for x in audit["official_results"]
                    if {rb.norm_name(s) for s in __import__("re").split(r"\s+vs\.?\s+", x["bout"], maxsplit=1, flags=__import__("re").I)} == parts), None)
        # Allow source display name Zach Reese vs verified Zachary Reese.
        if raw is None:
            def short_name(s):
                return rb.norm_name(s).replace("zacharyreese", "zachreese")
            raw = next((x for x in audit["official_results"]
                        if {short_name(s) for s in __import__("re").split(r"\s+vs\.?\s+", x["bout"], maxsplit=1, flags=__import__("re").I)} ==
                        {short_name(r.fighter_a), short_name(r.fighter_b)}), None)
        if raw is None:
            raise RuntimeError(f"Result cannot be mapped to official source {r.bout}")
        rows.append({
            "event_date": CUTOFF, "event": r.event, "fight": r.bout,
            "winner": r.winner, "method": r.method,
            "round": r.finish_round, "duration_seconds": r.duration_seconds,
            "doctor_stoppage": raw["special_stoppage"],
            "source_fight_url": r.fight_url,
            "has_frozen_stage_a": False, "has_frozen_stage_b": False,
            "official_winner_prediction_count": 0,
            "official_method_prediction_count": 0,
            "evaluation_role": "RETROSPECTIVE_TRAINING_AND_RESEARCH_ONLY",
        })
    result = pd.DataFrame(rows)
    if len(result) != 12:
        raise RuntimeError("Expected 12 separate Oct31 result rows")
    result.to_csv(RESULTS, index=False)
    return result


def heldout_actual_winner_method(method_df: pd.DataFrame, prior_oof: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Only calculate conditional method *given actual winning fighter*.

    That conditioning uses the known winner; do NOT treat this as pre-fight
    executable fighter+method or a scored Stage A wager.
    """
    earlier = method_df[method_df["event_date"].astype(str) < CUTOFF]
    target = method_df[method_df["event_date"].astype(str).str.startswith(CUTOFF)].copy()
    if len(target) != 12 or len(earlier) < 8000:
        raise RuntimeError(f"Method split incorrect: train {len(earlier)} / test {len(target)}")
    pre_model = ConditionalMethodModel(finish_c=0.1, sub_c=0.1).fit(
        earlier[rb.METHOD_BASE_FEATURES], earlier["method"]
    )
    bp = pre_model.predict_proba(target[rb.METHOD_BASE_FEATURES])[CLASSES].to_numpy(float)
    if not (prior_oof["event_date"].astype(str).str[:10] < CUTOFF).all():
        raise RuntimeError("Calibration history includes current/postevent outcomes")
    if len(prior_oof) != 139:
        raise RuntimeError("Expected clean139 calibration evidence")
    calibrator = MethodInterceptCalibrator(ridge=0.5).fit(
        actual_method=prior_oof["clean_actual_method"],
        baseline_ko=prior_oof["base_KO"],
        baseline_sub=prior_oof["base_SUB"],
        baseline_dec=prior_oof["base_DEC"],
    )
    cp = calibrator.predict_proba(
        baseline_ko=bp[:, 0], baseline_sub=bp[:, 1], baseline_dec=bp[:, 2]
    )[CLASSES].to_numpy(float)
    trainp = calibrator.predict_proba(
        baseline_ko=prior_oof["base_KO"],
        baseline_sub=prior_oof["base_SUB"],
        baseline_dec=prior_oof["base_DEC"],
    )[CLASSES].to_numpy(float)
    imputer, scaler, head, nf, ns = access.fit_access_head(prior_oof, trainp)
    ap = access.apply_access_head(target, cp, imputer, scaler, head)
    y = target["method"].to_numpy(str)
    report = {
        "status": "OFFLINE_RETROSPECTIVE_METHOD_CONDITIONAL_ON_OBSERVED_WINNER",
        "interpretation": "Not a fight-side or fighter+method pre-fight prediction. A known winner is used only to evaluate the conditional method learner on prefight snapshots. Pre-Oct31 labels only used to fit baseline/calibration/access.",
        "training_max_date_before_test": str(earlier["event_date"].max()),
        "training_baseline_rows": len(earlier), "training_feedback_rows": len(prior_oof),
        "access_training_finish_rows": nf, "access_training_submission_rows": ns,
        "baseline": pure_grade(y, bp),
        "calibrated": pure_grade(y, cp),
        "submission_access": pure_grade(y, ap),
    }
    rows = []
    for i, r in enumerate(target.itertuples(index=False)):
        item = {
            "event_date": CUTOFF, "fight": r.bout, "actual_winner": r.winner,
            "actual_method": r.method, "evaluation_role": report["status"],
        }
        for model, mat in (("base", bp), ("cal", cp), ("access", ap)):
            for j, c in enumerate(CLASSES):
                item[f"{model}_{c}"] = float(mat[i, j])
        rows.append(item)
    return report, pd.DataFrame(rows)


def main():
    audit = json.loads((RAW / "availability.json").read_text())
    if audit["upstream_commit"] != "3d4886d222e72be2c5336b49b98b721f5103d949":
        raise RuntimeError("Oct31 source commit changed")
    if not audit["full_card_stats_available"] or audit["fighter_round_stat_rows"] != 64:
        raise RuntimeError("12 fights / 64 UFCStats fighter-round rows must be present")
    clean = pd.read_csv(CLEAN)
    if len(clean) != 139 or clean["event_date"].astype(str).ge(CUTOFF).any():
        raise RuntimeError("Official clean139 ledger contains Oct31 or is incomplete; do not modify it")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    rb.TRAINING_CUTOFF = pd.Timestamp("2026-11-01", tz="UTC")
    fights, stats, static = rb.load_fights(RAW)
    fights, stats, static, identities = fix_known_identities(fights, stats, static)
    target = fights[fights["event_date"].astype(str).str.startswith(CUTOFF)]
    if len(target) != 12 or not target["event"].str.contains("Moicano").all():
        raise RuntimeError(f"Expected exactly 12 UFC Vegas123 bouts, found {len(target)}")
    totals = rb.aggregate_fight_stats(fights, stats)
    event_stats = make_event_stats(fights, totals)
    result_ledger = make_retrospective_results(fights, audit)
    winner_df, method_df, timing_df = rb.enrich_and_snapshot(fights, totals, static)
    prior_oof = pd.read_csv(PRIOR_OOF)
    method_report, rows = heldout_actual_winner_method(method_df, prior_oof)
    rows.to_csv(OUT_DIR / "heldout_conditional_actual_winner_method.csv", index=False)

    # Train POSTEVENT models for future fights only; keep main/champion untouched.
    winner = WinnerModel(c=0.25).fit(winner_df[rb.WINNER_FEATURES], winner_df["winner_is_a"])
    baseline = ConditionalMethodModel(finish_c=0.1, sub_c=0.1).fit(
        method_df[rb.METHOD_BASE_FEATURES], method_df["method"]
    )
    calibrator = MethodInterceptCalibrator(ridge=0.5).fit(
        actual_method=prior_oof["clean_actual_method"],
        baseline_ko=prior_oof["base_KO"],
        baseline_sub=prior_oof["base_SUB"],
        baseline_dec=prior_oof["base_DEC"],
    )
    residual = V027MethodResidualChallenger(ridge=10.0, clip_z=5.0).fit(
        prior_oof[list(V027_FEATURES)],
        actual_method=prior_oof["clean_actual_method"],
        baseline_ko=prior_oof["base_KO"],
        baseline_sub=prior_oof["base_SUB"],
        baseline_dec=prior_oof["base_DEC"],
    )
    timing = DiscreteTimeHazardModel(bin_seconds=30, c=0.10).fit(
        timing_df[rb.TIMING_FEATURES],
        timing_df["duration_seconds"].to_numpy(float),
        timing_df["scheduled_seconds"].to_numpy(int),
        ((timing_df["method"] != "DEC") | (timing_df["duration_seconds"] < timing_df["scheduled_seconds"])).astype(int).to_numpy(),
    )
    hashes = {}
    for key, model in (
        ("winner", winner), ("method_baseline", baseline),
        ("method_calibrator", calibrator), ("method_residual", residual),
        ("timing_30s", timing)
    ):
        p = ART / f"{key}_shadow_through_2026-10-31.joblib"
        joblib.dump(model, p)
        hashes[key] = {"path": str(p.relative_to(ROOT)), "sha256": sha256(p)}
    activity = activity_dates_from_raw(RAW)
    (ART / "activity_last_dates.json").write_text(
        json.dumps({k: v.isoformat() for k, v in sorted(activity.items())}, indent=2, sort_keys=True) + "\n"
    )

    # Measure event outcomes only, not betting or prediction returns.
    method_counts = result_ledger["method"].value_counts()
    prior_m = clean["actual_method"].value_counts()
    verified = {
        "source_bouts": 12, "fighter_round_rows": 64,
        "fighter_bout_aggregates": len(event_stats),
        "doctor_stoppages": int(result_ledger["doctor_stoppage"].sum()),
        "class_counts": {k: int(method_counts.get(k, 0)) for k in CLASSES},
        "prior139_counts": {k: int(prior_m.get(k, 0)) for k in CLASSES},
        "total_combined_observed_method_counts_diagnostic_only": {
            k: int(method_counts.get(k, 0)) + int(prior_m.get(k, 0)) for k in CLASSES
        },
        "aggregate_notice": "139 previous frozen-graded bouts plus 12 unpicked results = 151 observed fights, NOT 151 officially predicted or graded fights.",
    }
    manifest = {
        "status": "OCT31_FULL_STATS_INTEGRATED_UNPICKED_RETROSPECTIVE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "event": audit["event"], "event_date": CUTOFF,
        "provenance": {
            "upstream_commit": audit["upstream_commit"],
            "availability": str((RAW / "availability.json").relative_to(ROOT)),
            "source_urls": audit["official_crosscheck_sources"],
        },
        "integrity": verified,
        "training": {
            "historical_performance_fights": len(winner_df),
            "latest_performance_date": str(fights["event_date"].max()),
            "locked_feedback_unchanged": 139,
            "data_cutoff_exclusive": "2026-11-01",
            "future_only_artifact": True,
            "identity_reconciliation": identities,
        },
        "offline_conditional_method_reconstruction": method_report,
        "shadow_artifacts": hashes,
        "governance": {
            "official_prediction_record": False, "official_stage_a": False,
            "official_stage_b": False, "official_profit_loss": None,
            "retrospective_model_predictions_are_not_official": True,
            "clean139_ledger_untouched": True,
            "model_promoted": False, "champion_changed": False,
            "historical_shadow_only": True,
            "warning": "Oct31 lacked any pre-event freeze. Future-data refresh is allowed, but never score retro-predicted winner/method/timing as official selections."
        },
    }
    (ART / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (OUT_DIR / "integration_report.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": manifest["status"], "training_fights": len(winner_df),
        "outcome_class_counts": verified["class_counts"],
        "offline_actual_winner_method": {
            k: {"n": v["n"], "accuracy": v["accuracy"], "brier": v["brier"], "log_loss": v["log_loss"]}
            for k, v in method_report.items() if k in ("baseline", "calibrated", "submission_access")
        },
        "official_pick_record_unchanged": True
    }, indent=2))


if __name__ == "__main__":
    main()
