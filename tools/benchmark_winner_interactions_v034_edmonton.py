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


v034 = load_module("v034_existing", ROOT / "tools/benchmark_winner_interactions_v034.py")
rb = v034.rb
from wshlx_ufc.models import WinnerModel

RAW_DIR = ROOT / "data/raw/ufcedmonton_2026-10-17"
CLEAN = ROOT / "data/results/clean_ufc_125_2026-10-17.csv"
OUT = ROOT / "reports/post_edmonton_challengers/winner_v034"


def main() -> None:
    old_cutoff = rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF = pd.Timestamp("2026-10-18", tz="UTC")
    try:
        fights, stats, static = rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF = old_cutoff

    fight_stats = rb.aggregate_fight_stats(fights, stats)
    winner_df, _, _ = rb.enrich_and_snapshot(fights, fight_stats, static)
    winner_df = v034.add_interactions(winner_df)
    clean = pd.read_csv(CLEAN)
    sample = v034.add_interactions(v034.match_clean(clean, winner_df))
    y = sample["winner_is_a"].to_numpy(int)
    base_features = list(rb.WINNER_FEATURES)

    probabilities = {name: np.full(len(sample), np.nan) for name in v034.VARIANTS}
    for cutoff in sorted(sample["event_date"].unique()):
        train = winner_df.loc[winner_df["event_date"] < cutoff].copy()
        mask = sample["event_date"] == cutoff
        for name, extra in v034.VARIANTS.items():
            features = base_features + extra
            model = WinnerModel(c=0.25).fit(train[features], train["winner_is_a"])
            probabilities[name][mask] = model.predict_proba(sample.loc[mask, features])[:, 0]

    metrics = {name: v034.metrics(y, p) for name, p in probabilities.items()}
    edmonton_mask = sample["event_date"].str.startswith("2026-10-17").to_numpy()
    edmonton_metrics = {
        name: v034.metrics(y[edmonton_mask], p[edmonton_mask])
        for name, p in probabilities.items()
    }
    base = metrics["base"]
    variants = []
    for name, m in metrics.items():
        if name == "base":
            continue
        variants.append({
            "name": name,
            "features": v034.VARIANTS[name],
            "metrics_clean125": m,
            "edmonton_fold": edmonton_metrics[name],
            "delta_accuracy": m["accuracy"] - base["accuracy"],
            "delta_brier": m["brier"] - base["brier"],
            "delta_log_loss": m["log_loss"] - base["log_loss"],
            "passes_retrospective_metric_gate": bool(
                m["accuracy"] >= base["accuracy"]
                and m["brier"] < base["brier"]
                and m["log_loss"] < base["log_loss"]
            ),
        })

    payload = {
        "status": "POST_EDMONTON_V034_RETROSPECTIVE_DIAGNOSTIC_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "clean_sample": "clean_ufc_125_2026-10-17.csv",
        "base_clean125": base,
        "base_edmonton_fold": edmonton_metrics["base"],
        "variants": variants,
        "governance": {
            "production_change": False,
            "promotion_allowed_from_this_report": False,
            "reason": "These features were designed after prior outcomes were known. Edmonton is included only to diagnose stability, not to create retrospective promotion proof.",
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "benchmark_clean125.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    comp = sample[["event_date", "clean_fight", "fighter_a", "fighter_b", "winner", "winner_is_a"]].copy()
    for name, p in probabilities.items():
        comp[f"p_a_{name}"] = p
        comp[f"correct_{name}"] = ((p >= .5).astype(int) == y).astype(int)
    comp.to_csv(OUT / "oof_comparison_clean125.csv", index=False)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
