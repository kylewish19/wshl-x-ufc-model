"""Causally integrate UFC 333 round stats and test prior method challengers.

The UFC333 Stage A lock and its prior model grade are immutable. Every OOF fold
trains only on dates STRICTLY before the evaluated date. All new fitted models
are SHADOW artifacts for future cards, not retroactive October 24 forecasts.
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
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rb = load_module("rb_ufc333_integration", ROOT / "tools/rebuild_v027.py")
prior = load_module("method_access_prior_ufc333", ROOT / "tools/diagnose_method_submission_access_edmonton.py")

from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger, V027_FEATURES
from wshlx_ufc.models import ConditionalMethodModel, WinnerModel
from wshlx_ufc.timing import DiscreteTimeHazardModel
from wshlx_ufc.nonperformance import activity_dates_from_raw

RAW = ROOT / "data/raw/ufc333_2026-10-24"
OLD = ROOT / "data/results/clean_ufc_125_2026-10-17.csv"
OUT_CLEAN = ROOT / "data/results/clean_ufc_139_2026-10-24.csv"
OUT_STATS = ROOT / "data/results/ufc333_2026-10-24_fighter_fight_stats.csv"
GRADED = ROOT / "data/grades/ufc333_2026-10-24_stage_a_grade.json"
FROZEN = ROOT / "data/locks/ufc333_2026-10-24/stage_a_final_selection.json"
REPORT = ROOT / "reports/ufc333_2026-10-24/full_stats"
ART = ROOT / "artifacts/ufc333_post_event_shadow"
CLASSES = ["KO", "SUB", "DEC"]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def method3(name: str) -> str:
    s = str(name).strip().upper()
    if s in {"KO", "KO/TKO", "TKO"}:
        return "KO"
    if s in {"SUB", "DEC"}:
        return s
    raise ValueError(f"Unknown method {name!r}")


def clean_139(grade: dict, frozen: dict) -> pd.DataFrame:
    old = pd.read_csv(OLD)
    assert len(old) == 125, "Previous 125-row clean ledger cannot be silently replaced"
    if len(grade["bouts"]) != 14 or len(frozen["fights"]) != 14:
        raise RuntimeError("Missing UFC 333 grade or frozen side")
    out = []
    for g, f in zip(grade["bouts"], frozen["fights"]):
        if g["fight_no"] != f["fight_no"] or g["fight"] != f'{f["a"]} vs {f["b"]}':
            raise RuntimeError("UFC333 frozen card/grade ordering mismatch")
        actual = g["actual"]
        top = method3(f["method"]["top_method_current"])
        correct = int(actual["winner"] == f["official_reference_pick"])
        out.append({
            "event_date": "2026-10-24",
            "fight": g["fight"],
            "locked_pick": f["official_reference_pick"],
            "actual_winner": actual["winner"],
            "displayed_method": top,
            "actual_method": actual["method_class"],
            "winner_correct": correct,
            "method_correct": int(top == actual["method_class"]),
            "joint_correct": int(correct and top == actual["method_class"]),
        })
    combined = pd.concat([old, pd.DataFrame(out)], ignore_index=True)
    if len(combined) != 139 or combined.duplicated(["event_date", "fight"]).any():
        raise RuntimeError("New clean139 ledger has missing or duplicate fights")
    if (combined.loc[:124, old.columns].reset_index(drop=True) != old.reset_index(drop=True)).any().any():
        raise RuntimeError("Previous 125 rows mutated")
    OUT_CLEAN.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUT_CLEAN, index=False)
    return combined


def reconcile_identities(fights: pd.DataFrame, stats: pd.DataFrame, static: dict):
    """Carry forward two previously audited SAME-NAME / alias protections."""
    notes = {}
    old_label = "Anthony Romero (The Genius)"
    key = rb.norm_name("Anthony Romero")
    former = fights["event"].map(rb.norm_text).ne("UFC 332: Silva vs. Wang")
    n = 0
    for col in ("fighter_a", "fighter_b", "winner"):
        mask = fights[col].map(rb.norm_name).eq(key) & former
        n += int(mask.sum())
        fights.loc[mask, col] = old_label
    old_stat = (
        stats["FIGHTER_KEY"].eq(key)
        & stats["EVENT_KEY"].map(rb.norm_text).ne("UFC 332: Silva vs. Wang")
    )
    stats.loc[old_stat, "FIGHTER"] = old_label
    stats.loc[old_stat, "FIGHTER_KEY"] = rb.norm_name(old_label)
    notes["anthony_romero"] = {
        "older_identity_relabel_fields": n,
        "older_identity_round_rows": int(old_stat.sum()),
        "policy": "Never conflate UFC332 debutant (The Bully) with older same-name fighter (The Genius).",
    }
    old_key, new_key = rb.norm_name("Kai Kamaka"), rb.norm_name("Kai Kamaka III")
    n = 0
    for col in ("fighter_a", "fighter_b", "winner"):
        mask = fights[col].map(rb.norm_name).eq(old_key)
        n += int(mask.sum())
        fights.loc[mask, col] = "Kai Kamaka III"
    old_stat = stats["FIGHTER_KEY"].eq(old_key)
    stats.loc[old_stat, "FIGHTER"] = "Kai Kamaka III"
    stats.loc[old_stat, "FIGHTER_KEY"] = new_key
    if old_key in static and new_key not in static:
        static[new_key] = dict(static[old_key])
        static[new_key]["name"] = "Kai Kamaka III"
    notes["kai_kamaka"] = {
        "relabel_fields": n,
        "relabel_round_rows": int(old_stat.sum()),
    }
    return fights, stats, static, notes


def score(y: np.ndarray, p: np.ndarray) -> dict:
    return prior.grade(np.asarray(y, dtype=str), np.asarray(p, dtype=float))


def chronological_method_test(oof: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    folds, predictions = [], []
    for date in sorted(oof["event_date"].astype(str).unique())[1:]:
        train = oof[oof["event_date"].astype(str) < date].copy()
        test = oof[oof["event_date"].astype(str) == date].copy()
        if len(train) < 24 or test.empty:
            continue
        cal = MethodInterceptCalibrator(ridge=0.5).fit(
            actual_method=train["clean_actual_method"],
            baseline_ko=train["base_KO"],
            baseline_sub=train["base_SUB"],
            baseline_dec=train["base_DEC"],
        )
        pred_cal = prior.calibrated_probs(cal, test)
        pred_base = test[["base_KO", "base_SUB", "base_DEC"]].to_numpy(float)
        try:
            train_cal = prior.calibrated_probs(cal, train)
            imputer, scaler, head, nf, ns = prior.fit_access_head(train, train_cal)
            pred_access = prior.apply_access_head(test, pred_cal, imputer, scaler, head)
        except ValueError as ex:
            raise RuntimeError(f"Submission challenger cannot evaluate date {date}: {ex}") from ex
        y = test["clean_actual_method"].astype(str).to_numpy()
        folds.append({
            "test_date": date[:10], "train_n": len(train), "test_n": len(test),
            "training_finish_n": nf, "training_sub_n": ns,
            "baseline": score(y, pred_base),
            "calibrated": score(y, pred_cal),
            "submission_access": score(y, pred_access),
        })
        for i, (_, row) in enumerate(test.iterrows()):
            one = {
                "event_date": date[:10], "bout": row["bout"], "actual_method": y[i],
                "used_training_before_date_only": True,
            }
            for view, mat in (("base", pred_base), ("cal", pred_cal), ("access", pred_access)):
                for j, m in enumerate(CLASSES):
                    one[f"{view}_{m}"] = float(mat[i, j])
            predictions.append(one)
    preds = pd.DataFrame(predictions)
    if preds.empty or len(preds[preds["event_date"] == "2026-10-24"]) != 14:
        raise RuntimeError("Missing 14 chronological held-out UFC333 method rows")
    result = {
        "protocol": "Walk-forward event-date training. Baseline feature snapshots use only prior fighter fights. Calibration and submission-access weights fit STRICTLY prior dates.",
        "candidate_specified_pre_ufc333": True,
        "candidate_source": "tools/diagnose_method_submission_access_edmonton.py",
        "submission_access_features": list(prior.ACCESS_FEATURES),
        "full_chronological": {},
        "prior_through_2026_10_17": {},
        "held_out_ufc333": {},
        "folds": folds,
    }
    for group_name, group in (
        ("full_chronological", preds),
        ("prior_through_2026_10_17", preds[preds["event_date"] < "2026-10-24"]),
        ("held_out_ufc333", preds[preds["event_date"] == "2026-10-24"]),
    ):
        group_y = group["actual_method"].astype(str).to_numpy()
        for view in ("base", "cal", "access"):
            pp = group[[f"{view}_{c}" for c in CLASSES]].to_numpy(float)
            result[group_name][view] = score(group_y, pp)
    return result, preds


def event_fighter_stats(fights: pd.DataFrame, fight_stats: dict) -> pd.DataFrame:
    rows = []
    for fight in fights.itertuples(index=False):
        if not str(fight.event_date).startswith("2026-10-24"):
            continue
        k = (rb.norm_text(fight.event), rb.norm_text(fight.bout))
        for fighter, opp in ((fight.fighter_a, fight.fighter_b), (fight.fighter_b, fight.fighter_a)):
            one = fight_stats.get((*k, rb.norm_name(fighter)))
            if not one:
                raise RuntimeError(f"Missing source round stats for fighter {fighter}")
            row = {
                "event_date": "2026-10-24", "bout": fight.bout,
                "fighter": fighter, "opponent": opp, "winner": fight.winner,
                "method": fight.method, "finish_round": fight.finish_round,
                "duration_seconds": fight.duration_seconds,
                "source_url": fight.fight_url,
            }
            for field in (
                "kd_for", "sig_landed", "sig_attempted",
                "td_landed", "td_attempted", "sub_att", "ctrl_seconds",
                "ground_landed", "ground_attempted",
                "r1_sig_landed", "r3_sig_landed",
            ):
                row[field] = one[field]
            rows.append(row)
    result = pd.DataFrame(rows)
    if len(result) != 28:
        raise RuntimeError(f"Expected 28 UFC333 fighter-stat records, got {len(result)}")
    result.to_csv(OUT_STATS, index=False)
    return result


def main() -> None:
    a = json.loads((RAW / "availability.json").read_text())
    if a["upstream_commit"] != "5d6622ffc349a1d0c6dd25158d737a96b889a3e0":
        raise RuntimeError("Pinned UFC333 stats source was changed")
    if not a["full_card_stats_available"] or a["fighter_round_stat_rows"] != 62:
        raise RuntimeError("UFC333 complete raw source not available")
    grade, frozen = (
        json.loads(GRADED.read_text()), json.loads(FROZEN.read_text())
    )
    clean = clean_139(grade, frozen)
    rb.TRAINING_CUTOFF = pd.Timestamp("2026-10-25", tz="UTC")
    fights, stats, static = rb.load_fights(RAW)
    fights, stats, static, identities = reconcile_identities(fights, stats, static)
    new_fights = fights[fights["event_date"].astype(str).str.startswith("2026-10-24")]
    if len(new_fights) != 14 or not new_fights["event"].str.contains("UFC 333").all():
        raise RuntimeError(f"Expected 14 UFC333 decisive bouts, got {len(new_fights)}")
    fight_stats = rb.aggregate_fight_stats(fights, stats)
    event_rows = event_fighter_stats(fights, fight_stats)
    winner_df, method_df, timing_df = rb.enrich_and_snapshot(fights, fight_stats, static)
    clean_rows = rb.find_clean_rows(clean, method_df)
    if len(clean_rows) != 139:
        raise RuntimeError(f"Only {len(clean_rows)} of 139 clean performance rows matched")
    oof = rb.add_clean_oof_baselines(clean_rows, method_df)
    REPORT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    oof.to_csv(REPORT / "clean139_causal_method_inputs.csv", index=False)
    comparison, predictions = chronological_method_test(oof)
    predictions.to_csv(REPORT / "method_walk_forward_predictions.csv", index=False)
    (REPORT / "method_walk_forward_comparison.json").write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n"
    )

    # Fit updated state for FUTURE events only, without touching the pre-UFC333 freeze.
    champion_side = WinnerModel(c=0.25).fit(winner_df[rb.WINNER_FEATURES], winner_df["winner_is_a"])
    method = ConditionalMethodModel(finish_c=0.1, sub_c=0.1).fit(
        method_df[rb.METHOD_BASE_FEATURES], method_df["method"]
    )
    cal = MethodInterceptCalibrator(ridge=0.5).fit(
        actual_method=oof["clean_actual_method"],
        baseline_ko=oof["base_KO"], baseline_sub=oof["base_SUB"],
        baseline_dec=oof["base_DEC"]
    )
    resid = V027MethodResidualChallenger(ridge=10, clip_z=5).fit(
        oof[list(V027_FEATURES)],
        actual_method=oof["clean_actual_method"],
        baseline_ko=oof["base_KO"], baseline_sub=oof["base_SUB"],
        baseline_dec=oof["base_DEC"],
    )
    timing = DiscreteTimeHazardModel(bin_seconds=30, c=0.1).fit(
        timing_df[rb.TIMING_FEATURES],
        timing_df["duration_seconds"].to_numpy(float),
        timing_df["scheduled_seconds"].to_numpy(int),
        (
            (timing_df["method"] != "DEC") |
            (timing_df["duration_seconds"] < timing_df["scheduled_seconds"])
        ).astype(int).to_numpy(),
    )
    model_objects = {
        "winner": champion_side, "method_baseline": method,
        "method_calibrator": cal, "method_residual": resid, "timing_30s": timing,
    }
    hashes = {}
    for key, model in model_objects.items():
        p = ART / f"{key}_shadow_through_2026-10-24.joblib"
        joblib.dump(model, p)
        hashes[key] = {"path": str(p.relative_to(ROOT)), "sha256": digest(p)}
    activity = activity_dates_from_raw(RAW)
    (ART / "activity_last_dates.json").write_text(
        json.dumps({k: v.isoformat() for k, v in sorted(activity.items())}, indent=2, sort_keys=True) + "\n"
    )
    old, new = clean.iloc[:125], clean.iloc[125:]
    def dist(x: pd.Series) -> dict:
        return {m: int((x == m).sum()) for m in CLASSES}
    summary = {
        "status": "UFC333_FULLSTAT_INTEGRATED_SHADOW_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"commit": a["upstream_commit"], "raw_validation": str((RAW / "availability.json").relative_to(ROOT)),
                   "fighter_round_rows": a["fighter_round_stat_rows"], "event_fighter_rows": int(len(event_rows))},
        "population": {
            "fights_in_causal_training": int(len(winner_df)), "feedback_clean_before": 125,
            "feedback_clean_after": len(clean), "new_feedback": len(new),
            "most_recent_performance_date": str(fights["event_date"].max()),
        },
        "method_displayed_across_versions": {
            "warning": "These displayed classifications come from different frozen Stage A model versions. They must not be treated as one identical estimator.",
            "prior125": {
                "correct": int(old["method_correct"].sum()), "n": len(old),
                "actual": dist(old["actual_method"]), "called": dist(old["displayed_method"]),
                "submission_recall": {
                    "correct": int(((old["actual_method"] == "SUB") & (old["displayed_method"] == "SUB")).sum()),
                    "actual_submissions": int((old["actual_method"] == "SUB").sum()),
                },
            },
            "ufc333": {
                "correct": int(new["method_correct"].sum()), "n": len(new),
                "actual": dist(new["actual_method"]), "called": dist(new["displayed_method"]),
            },
            "combined139": {
                "correct": int(clean["method_correct"].sum()), "n": len(clean),
                "actual": dist(clean["actual_method"]), "called": dist(clean["displayed_method"]),
            },
        },
        "walk_forward": comparison,
        "identities": identities,
        "model_artifacts": hashes,
        "governance": {
            "reference_changed": False, "historical_pr_merged": False,
            "challenger_promoted": False, "future_shadow_trained": True,
            "ufc333_stage_a_recomputed": False,
            "note": "UFC333 outcome is newly admitted to training only for future bouts. Do not relabel any reprocessed prediction as the original frozen Stage A.",
        },
    }
    (ART / "manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (REPORT / "integration_report.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": summary["status"], "causal_training": summary["population"]["fights_in_causal_training"],
        "clean_feedback": 139, "ufc333_fighter_stats": len(event_rows),
        "method_scores": {k: {name: {"n": v["n"], "accuracy": v["accuracy"], "brier": v["brier"], "log_loss": v["log_loss"]}
                              for name, v in group.items()}
                          for k, group in comparison.items() if k in {"full_chronological", "held_out_ufc333"}},
    }, indent=2))


if __name__ == "__main__":
    main()
