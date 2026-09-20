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

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

rb = load_module("rebuild_v027", ROOT / "tools/rebuild_v027.py")
stage = load_module("ufc331_stage_a", ROOT / "tools/run_ufc331_stage_a.py")

from wshlx_ufc.grading import binary_brier, multiclass_brier
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger, V027_FEATURES
from wshlx_ufc.models import ConditionalMethodModel, WinnerModel
from wshlx_ufc.timing import DiscreteTimeHazardModel

EVENT_DATE = pd.Timestamp("2026-09-19", tz="UTC")
CLEAN_LEDGER = ROOT / "data/results/clean_ufc_76_2026-09-19.csv"
RAW_LOCK = ROOT / "data/locks/ufc331_2026-09-19/stage_a_model_raw_v3.json"

RESULTS = {
    ("Giga Chikadze", "Joanderson Brito"): dict(winner="Joanderson Brito", method="KO", duration_seconds=117.0),
    ("Casey O'Neill", "Eduarda Moura"): dict(winner="Casey O'Neill", method="SUB", duration_seconds=202.0),
    ("Edmen Shahbazyan", "Brunno Ferreira"): dict(winner="Edmen Shahbazyan", method="DEC", duration_seconds=900.0),
    ("Ryan Gandra", "Ozzy Diaz"): dict(winner="Ryan Gandra", method="KO", duration_seconds=124.0),
    ("Michael Aswell Jr.", "Joosang Yoo"): dict(winner="Michael Aswell Jr.", method="DEC", duration_seconds=900.0),
    ("Tai Tuivasa", "Robelis Despaigne"): dict(winner="Robelis Despaigne", method="DEC", duration_seconds=900.0),
    ("Marlon Vera", "Charles Jourdain"): dict(winner="Marlon Vera", method="KO", duration_seconds=722.0),
    ("Alonzo Menifield", "Iwo Baraniewski"): dict(winner="Alonzo Menifield", method="DEC", duration_seconds=900.0),
    ("Gable Steveson", "Sean Sharaf"): dict(winner="Sean Sharaf", method="KO", duration_seconds=12.0),
    ("Patricio Pitbull", "Dooho Choi"): dict(winner="Patricio Pitbull", method="KO", duration_seconds=208.0),
    ("Arman Tsarukyan", "Mauricio Ruffy"): dict(winner="Arman Tsarukyan", method="KO", duration_seconds=296.0),
    ("Joshua Van", "Alexandre Pantoja"): dict(winner="Joshua Van", method="DEC", duration_seconds=1500.0),
}


def prepare_history(fights, fight_stats, static):
    history = stage.completed_history(fights, fight_stats)
    for target, source in stage.HISTORY_ALIASES.items():
        merged = list(history.get(target, [])) + list(history.get(source, []))
        merged.sort(key=lambda x: pd.Timestamp(x["event_date"]))
        history[target] = merged
        if target not in static and source in static:
            static[target] = dict(static[source])
    return history


def build_feedback_rows(history, static):
    winner_rows, method_rows, timing_rows = [], [], []
    for f in stage.CARD:
        key = (f["a"], f["b"])
        actual = RESULTS[key]
        a = rb.summarize_history(f["a"], history, static, EVENT_DATE)
        b = rb.summarize_history(f["b"], history, static, EVENT_DATE)
        for name, side in [(f["a"], a), (f["b"], b)]:
            for field, value in stage.CURRENT_PROFILE_OVERRIDES.get(name, {}).items():
                side[field] = float(value)

        wf = rb.winner_features(a, b, f["weight_class"], f["scheduled_seconds"])
        winner_is_a = int(rb.norm_name(actual["winner"]) == rb.norm_name(f["a"]))
        w_side, o_side = (a, b) if winner_is_a else (b, a)
        mf = rb.method_features(w_side, o_side, f["weight_class"], f["scheduled_seconds"])
        rf = rb.residual_features(w_side, o_side)

        meta = {
            "fight_key": f"2026-09-19|{f['a']} vs. {f['b']}",
            "event": "UFC 331: Van vs. Pantoja 2",
            "event_date": EVENT_DATE.isoformat(),
            "bout": f"{f['a']} vs. {f['b']}",
            "fighter_a": f["a"],
            "fighter_b": f["b"],
            "winner": actual["winner"],
            "method": actual["method"],
            "winner_is_a": winner_is_a,
            "weight_class": f["weight_class"],
            "scheduled_seconds": int(f["scheduled_seconds"]),
            "duration_seconds": float(actual["duration_seconds"]),
        }
        winner_rows.append({**meta, **wf})
        method_rows.append({**meta, **mf, **rf})
        timing_rows.append({**meta, **wf})

    return pd.DataFrame(winner_rows), pd.DataFrame(method_rows), pd.DataFrame(timing_rows)


def grade_method_probs(actual, probs):
    classes = ["KO", "SUB", "DEC"]
    arr = probs[classes].to_numpy(float)
    y = np.asarray(actual, dtype=str)
    pred = np.asarray(classes)[np.argmax(arr, axis=1)]
    return {
        "n": int(len(y)),
        "accuracy": float(np.mean(pred == y)),
        "brier": float(multiclass_brier(y, arr, classes)),
        "log_loss": float(log_loss(y, arr[:, [2, 0, 1]], labels=["DEC", "KO", "SUB"])),
        "calls": {c: int(np.sum(pred == c)) for c in classes},
        "actual": {c: int(np.sum(y == c)) for c in classes},
    }


def prospective_ufc331_locked_metrics():
    raw = json.loads(RAW_LOCK.read_text())["payload"]["fights"]
    winner_y, winner_p = [], []
    baseline_rows, shadow_rows, methods = [], [], []
    for row, f in zip(raw, stage.CARD):
        actual = RESULTS[(f["a"], f["b"])]
        a_won = rb.norm_name(actual["winner"]) == rb.norm_name(f["a"])
        winner_y.append(int(a_won))
        winner_p.append(float(row["p_a_win"]))
        baseline_rows.append(
            row["method_if_a_wins_baseline"] if a_won else row["method_if_b_wins_baseline"]
        )
        shadow_rows.append(
            row["method_if_a_wins_v027_shadow"] if a_won else row["method_if_b_wins_v027_shadow"]
        )
        methods.append(actual["method"])

    wp = np.asarray(winner_p, dtype=float)
    wy = np.asarray(winner_y, dtype=int)
    pred = (wp >= 0.5).astype(int)

    baseline = pd.DataFrame(baseline_rows)
    shadow = pd.DataFrame(shadow_rows)
    return {
        "winner_raw": {
            "n": 12,
            "accuracy": float(np.mean(pred == wy)),
            "brier": float(binary_brier(wy, wp)),
            "log_loss": float(log_loss(wy, np.column_stack([1.0 - wp, wp]), labels=[0, 1])),
        },
        "method_baseline_on_actual_winner": grade_method_probs(methods, baseline),
        "method_v027_shadow_on_actual_winner": grade_method_probs(methods, shadow),
    }


def save_models(winner_df, method_df, timing_df, clean_oof, artifact_dir):
    artifact_dir.mkdir(parents=True, exist_ok=True)

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
    # v0.28 timing candidate uses 30-second bins. This exactly represents
    # sportsbook half-round thresholds (150, 450, 750, ... seconds).
    timing = DiscreteTimeHazardModel(bin_seconds=30, c=0.10).fit(
        timing_df[rb.TIMING_FEATURES],
        timing_df["duration_seconds"].to_numpy(float),
        timing_df["scheduled_seconds"].to_numpy(int),
        ((timing_df["method"] != "DEC") | (timing_df["duration_seconds"] < timing_df["scheduled_seconds"])).astype(int).to_numpy(),
    )

    paths = {
        "winner": artifact_dir / "winner_v028_feedback.joblib",
        "method_baseline": artifact_dir / "method_baseline_v028_feedback.joblib",
        "method_residual": artifact_dir / "method_residual_v028_feedback.joblib",
        "timing": artifact_dir / "timing_v028_feedback_30s.joblib",
    }
    joblib.dump(winner, paths["winner"])
    joblib.dump(method, paths["method_baseline"])
    joblib.dump(residual, paths["method_residual"])
    joblib.dump(timing, paths["timing"])
    return {k: rb.sha256_file(v) for k, v in paths.items()}


def main():
    raw_dir = ROOT / "build/v028_ufc331_feedback/raw"
    rb.download_sources(raw_dir)
    fights, stats, static = rb.load_fights(raw_dir)
    fight_stats = rb.aggregate_fight_stats(fights, stats)

    # Historical causal snapshots through Sep. 12 from the pinned feed.
    winner_hist, method_hist, timing_hist = rb.enrich_and_snapshot(fights, fight_stats, static)

    # UFC 331 rows are reconstructed strictly from the same prefight history
    # available on Sep. 19; only labels (winner/method/duration) come from the event.
    history = prepare_history(fights, fight_stats, static)
    winner_fb, method_fb, timing_fb = build_feedback_rows(history, static)

    winner_all = pd.concat([winner_hist, winner_fb], ignore_index=True, sort=False)
    method_all = pd.concat([method_hist, method_fb], ignore_index=True, sort=False)
    timing_all = pd.concat([timing_hist, timing_fb], ignore_index=True, sort=False)

    clean = pd.read_csv(CLEAN_LEDGER)
    clean_oof = rb.add_clean_oof_baselines(rb.find_clean_rows(clean, method_all), method_all)
    winner_benchmark = rb.winner_clean_benchmark(clean, winner_all)
    method_benchmark = rb.chronology_residual_benchmark(clean_oof)
    prospective = prospective_ufc331_locked_metrics()

    artifact_dir = ROOT / "artifacts/v028_ufc331_feedback"
    report_dir = ROOT / "reports/v028_ufc331_feedback"
    report_dir.mkdir(parents=True, exist_ok=True)
    hashes = save_models(winner_all, method_all, timing_all, clean_oof, artifact_dir)

    clean_export_cols = [
        "fight_key", "event", "event_date", "bout", "winner", "clean_actual_method",
        "base_KO", "base_SUB", "base_DEC", *V027_FEATURES
    ]
    clean_oof.to_csv(
        report_dir / "clean76_oof_method_inputs.csv",
        index=False,
        columns=clean_export_cols,
    )
    winner_fb.to_csv(report_dir / "ufc331_frozen_prefight_winner_feedback.csv", index=False)
    method_fb.to_csv(report_dir / "ufc331_frozen_prefight_method_feedback.csv", index=False)
    timing_fb.to_csv(report_dir / "ufc331_frozen_prefight_timing_feedback.csv", index=False)

    manifest = {
        "status": "V0.28_UFC331_FEEDBACK_SHADOW",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_data": {
            "historical_upstream_repo": rb.UPSTREAM_REPO,
            "historical_upstream_commit": rb.UPSTREAM_COMMIT,
            "historical_feed_last_event": fights["event_date"].max().isoformat(),
            "ufc331_feedback_rows": 12,
            "clean_feedback_rows": int(len(clean_oof)),
            "winner_training_rows": int(len(winner_all)),
            "method_training_rows": int(len(method_all)),
            "timing_training_rows": int(len(timing_all)),
        },
        "causal_integrity": {
            "ufc331_prefight_features": "reconstructed from data available before 2026-09-19",
            "ufc331_postfight_inputs_used": ["winner", "method_class", "duration_seconds"],
            "ufc331_round_stats_used": False,
            "same_day_leakage": False,
            "note": "Full UFC 331 round stats will update fighter histories after the upstream feed refreshes; they are not needed to label the already-frozen UFC 331 prefight rows.",
        },
        "architecture_changes": {
            "winner": "same reconstruction architecture; refit with 12 new causal feedback rows",
            "method_baseline": "same architecture; refit with 12 new causal feedback rows",
            "method_residual": "same residual architecture; final fit now uses clean-76 feedback",
            "timing": "candidate changed from 60-second to 30-second hazard bins so half-round sportsbook thresholds are represented exactly",
            "selection_policy": "new research-override, sparse-sample, method-promotion and timing-promotion gates live in src/wshlx_ufc/selection_policy.py",
        },
        "prospective_ufc331_locked_evaluation": prospective,
        "clean76_winner_reconstruction_benchmark": winner_benchmark,
        "clean76_method_reconstruction_benchmark": method_benchmark,
        "artifact_sha256": hashes,
        "promotion": {
            "authorized": False,
            "role": "shadow_candidate",
            "reason": "Core coefficients now include UFC 331 labels, so the next unseen UFC card is required for prospective validation before promotion.",
        },
    }
    (artifact_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (report_dir / "benchmark.json").write_text(
        json.dumps(
            {
                "prospective_ufc331_locked_evaluation": prospective,
                "winner_clean76": winner_benchmark,
                "method_clean76": method_benchmark,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    summary = [
        "# v0.28 UFC 331 feedback build",
        "",
        f"- Status: **{manifest['status']}**",
        "- UFC 331 labeled feedback rows appended: **12**",
        f"- Clean WSHL_X feedback ledger: **{len(clean_oof)} fights**",
        "- UFC 331 round stats used in this build: **No**",
        "- Timing candidate resolution: **30 seconds**",
        "",
        "## Prospective UFC 331 check of the pre-event models",
        "",
        f"- Raw winner accuracy: **{prospective['winner_raw']['accuracy']:.3f}**",
        f"- Raw winner Brier: **{prospective['winner_raw']['brier']:.4f}**",
        f"- Baseline method accuracy on actual winner: **{prospective['method_baseline_on_actual_winner']['accuracy']:.3f}**",
        f"- v0.27 shadow method accuracy on actual winner: **{prospective['method_v027_shadow_on_actual_winner']['accuracy']:.3f}**",
        "",
        "## Clean-76 chronology benchmark",
        "",
        f"- Winner reconstruction accuracy: **{winner_benchmark['accuracy']:.3f}**",
    ]
    c = method_benchmark.get("chronology_candidate")
    b = method_benchmark.get("chronology_baseline")
    if c and b:
        summary += [
            f"- Method baseline accuracy: **{b['accuracy']:.3f}**",
            f"- Method residual accuracy: **{c['accuracy']:.3f}**",
            f"- Method baseline Brier: **{b['multiclass_brier']:.4f}**",
            f"- Method residual Brier: **{c['multiclass_brier']:.4f}**",
        ]
    summary += [
        "",
        "## Promotion decision",
        "",
        "**Do not promote yet.** v0.28 is a real retrained shadow candidate. The next unseen card is its first prospective test.",
    ]
    (report_dir / "BUILD_REPORT.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
