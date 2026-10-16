from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

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


rb = load_module("rebuild_v027_v034_clean112", ROOT / "tools/rebuild_v027.py")
v034 = load_module("v034_original_clean112", ROOT / "tools/benchmark_winner_interactions_v034.py")
from wshlx_ufc.models import WinnerModel

RAW_DIR = ROOT / "data/raw/ufcvegas122_2026-10-10"
CLEAN = ROOT / "data/results/clean_ufc_112_2026-10-10.csv"
OUT = ROOT / "reports/v034_winner_interactions_clean112"


def reconcile_kai(fights: pd.DataFrame, stats: pd.DataFrame, static: dict):
    old_key = rb.norm_name("Kai Kamaka")
    new_key = rb.norm_name("Kai Kamaka III")
    for col in ("fighter_a", "fighter_b", "winner"):
        mask = fights[col].map(rb.norm_name).eq(old_key)
        fights.loc[mask, col] = "Kai Kamaka III"
    mask = stats["FIGHTER_KEY"].eq(old_key)
    stats.loc[mask, "FIGHTER"] = "Kai Kamaka III"
    stats.loc[mask, "FIGHTER_KEY"] = new_key
    if old_key in static and new_key not in static:
        static[new_key] = dict(static[old_key])
        static[new_key]["name"] = "Kai Kamaka III"
    return fights, stats, static


def main() -> None:
    old_cutoff = rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF = pd.Timestamp("2026-10-11", tz="UTC")
    try:
        fights, stats, static = rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF = old_cutoff

    fights, stats, static = reconcile_kai(fights, stats, static)
    fight_stats = rb.aggregate_fight_stats(fights, stats)
    winner_df, _, _ = rb.enrich_and_snapshot(fights, fight_stats, static)
    winner_df = v034.add_interactions(winner_df)

    clean = pd.read_csv(CLEAN)
    sample = v034.add_interactions(v034.match_clean(clean, winner_df))
    if len(sample) != 112:
        raise RuntimeError(f"Expected 112 clean fights, got {len(sample)}")

    y = sample["winner_is_a"].to_numpy(int)
    base_features = list(rb.WINNER_FEATURES)
    probabilities: dict[str, np.ndarray] = {
        name: np.full(len(sample), np.nan) for name in v034.VARIANTS
    }

    for cutoff in sorted(sample["event_date"].unique()):
        train = winner_df.loc[winner_df["event_date"] < cutoff].copy()
        mask = sample["event_date"] == cutoff
        for name, extra in v034.VARIANTS.items():
            features = base_features + list(extra)
            model = WinnerModel(c=0.25).fit(train[features], train["winner_is_a"])
            probabilities[name][mask] = model.predict_proba(sample.loc[mask, features])[:, 0]

    metrics = {name: v034.metrics(y, p) for name, p in probabilities.items()}
    base = metrics["base"]
    variants = []
    for name, m in metrics.items():
        if name == "base":
            continue
        variants.append({
            "name": name,
            "features": list(v034.VARIANTS[name]),
            "metrics": m,
            "delta_accuracy": m["accuracy"] - base["accuracy"],
            "delta_brier": m["brier"] - base["brier"],
            "delta_log_loss": m["log_loss"] - base["log_loss"],
            "passes_retrospective_metric_gate": bool(
                m["accuracy"] >= base["accuracy"]
                and m["brier"] < base["brier"]
                and m["log_loss"] < base["log_loss"]
            ),
        })

    best = min(variants, key=lambda x: (x["metrics"]["brier"], x["metrics"]["log_loss"]))
    payload = {
        "status": "V0.34_CLEAN112_POST_VEGAS122_DIAGNOSTIC_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "clean_sample": "clean_ufc_112_2026-10-10.csv",
        "n": 112,
        "base": base,
        "variants": variants,
        "best_retrospective_brier_variant": best["name"],
        "best_variant_passes_metric_gate": best["passes_retrospective_metric_gate"],
        "governance": {
            "promotion_allowed": False,
            "reason": "All v0.34 features were designed after UFC Vegas 122, partly in response to that card's misses. Adding Vegas 122 to this retrospective benchmark is contaminated development evidence and cannot be counted as prospective validation or used to promote/reselect the official winner model.",
            "selected_shadow_before_this_test": "experience_only",
            "selected_shadow_change_from_this_test": "NONE",
        },
    }

    comparison = sample[["event_date", "clean_fight", "fighter_a", "fighter_b", "winner", "winner_is_a"]].copy()
    for name, p in probabilities.items():
        comparison[f"p_a_{name}"] = p
        comparison[f"correct_{name}"] = ((p >= 0.5).astype(int) == y).astype(int)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "benchmark.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    comparison.to_csv(OUT / "oof_comparison_112.csv", index=False)

    lines = [
        "# v0.34 winner interactions — clean112 diagnostic",
        "",
        "This reruns every v0.34 ablation after integrating UFC Vegas 122 full stats.",
        "",
        "**Governance warning:** v0.34 was designed after UFC Vegas 122 and partly from its misses. Therefore Vegas 122 is contaminated development data for these features. This report is diagnostic only and cannot promote or reselect a model.",
        "",
        f"Base: **{base['wins']}-{base['losses']} ({base['accuracy']:.1%})**, Brier {base['brier']:.6f}, log loss {base['log_loss']:.6f}",
        "",
        "## Variants",
        "",
    ]
    for row in sorted(variants, key=lambda x: x["metrics"]["brier"]):
        m = row["metrics"]
        lines.append(
            f"- **{row['name']}**: {m['wins']}-{m['losses']} ({m['accuracy']:.1%}), "
            f"Brier {m['brier']:.6f} ({row['delta_brier']:+.6f}), "
            f"log loss {m['log_loss']:.6f} ({row['delta_log_loss']:+.6f}); "
            f"retrospective gate={'PASS' if row['passes_retrospective_metric_gate'] else 'FAIL'}"
        )
    lines += [
        "",
        f"Best retrospective Brier on clean112: **{best['name']}**.",
        "",
        "No production or shadow-selection change is authorized from this rerun. The previously selected experience-only shadow remains the tracked v0.34 candidate until genuinely future frozen-card evidence accumulates.",
    ]
    (OUT / "BUILD_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
