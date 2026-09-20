from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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

v028 = load_module("v028_feedback", ROOT / "tools/train_v028_ufc331_feedback.py")
rb = v028.rb

from wshlx_ufc.models import WinnerModel

CLEAN = ROOT / "data/results/clean_ufc_76_2026-09-19.csv"
OUT = ROOT / "reports/v030_winner_reliability"


def match_clean(clean, winner_df):
    rows = []
    used = set()
    for c in clean.itertuples(index=False):
        date = str(c.event_date)
        f1, f2 = [x.strip() for x in str(c.fight).split(" vs ", 1)]
        nset = {rb.norm_name(f1), rb.norm_name(f2)}
        cand = winner_df.loc[winner_df["event_date"].str.startswith(date)]
        best_i, best_score = None, -1
        for i, r in cand.iterrows():
            rset = {rb.norm_name(r["fighter_a"]), rb.norm_name(r["fighter_b"])}
            score = len(nset & rset)
            if score > best_score and int(i) not in used:
                best_i, best_score = i, score
        if best_i is None or best_score < 2:
            raise RuntimeError(f"Could not match {date} {c.fight}")
        used.add(int(best_i))
        row = winner_df.loc[best_i].to_dict()
        row["clean_fight"] = c.fight
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    raw_dir = ROOT / "build/v030_winner_reliability/raw"
    rb.download_sources(raw_dir)
    fights, stats, static = rb.load_fights(raw_dir)
    fight_stats = rb.aggregate_fight_stats(fights, stats)
    winner_hist, _, _ = rb.enrich_and_snapshot(fights, fight_stats, static)
    history = v028.prepare_history(fights, fight_stats, static)
    winner_fb, _, _ = v028.build_feedback_rows(history, static)
    winner_all = pd.concat([winner_hist, winner_fb], ignore_index=True, sort=False)

    clean = pd.read_csv(CLEAN)
    sample = match_clean(clean, winner_all)
    p_a = np.full(len(sample), np.nan)
    for cutoff in sorted(sample["event_date"].unique()):
        train = winner_all.loc[winner_all["event_date"] < cutoff]
        mask = sample["event_date"] == cutoff
        model = WinnerModel(c=0.25).fit(train[rb.WINNER_FEATURES], train["winner_is_a"])
        p_a[mask] = model.predict_proba(sample.loc[mask, rb.WINNER_FEATURES])[:, 0]

    y = sample["winner_is_a"].to_numpy(int)
    pred_a = p_a >= 0.5
    confidence = np.maximum(p_a, 1.0 - p_a)
    correct = (pred_a.astype(int) == y)

    out_rows = sample[["event_date","clean_fight","fighter_a","fighter_b","winner"]].copy()
    out_rows["p_a_win_oof"] = p_a
    out_rows["model_confidence"] = confidence
    out_rows["predicted_winner"] = np.where(pred_a, out_rows["fighter_a"], out_rows["fighter_b"])
    out_rows["correct"] = correct.astype(int)

    thresholds = []
    for t in (0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90):
        mask = confidence >= t
        thresholds.append({
            "threshold": t,
            "n": int(mask.sum()),
            "coverage": float(mask.mean()),
            "accuracy": float(correct[mask].mean()) if mask.any() else None,
            "wins": int(correct[mask].sum()),
            "losses": int(mask.sum() - correct[mask].sum()),
        })

    bins = []
    edges = [0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.90,1.000001]
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (confidence >= lo) & (confidence < hi)
        bins.append({
            "lo": lo, "hi": hi,
            "n": int(mask.sum()),
            "mean_confidence": float(confidence[mask].mean()) if mask.any() else None,
            "accuracy": float(correct[mask].mean()) if mask.any() else None,
            "wins": int(correct[mask].sum()),
            "losses": int(mask.sum() - correct[mask].sum()),
        })

    overall = {
        "n": int(len(y)),
        "accuracy": float(correct.mean()),
        "brier": float(np.mean((p_a-y)**2)),
        "log_loss": float(log_loss(y, np.column_stack([1-p_a,p_a]), labels=[0,1])),
    }

    payload = {
        "status":"V0.30_WINNER_RELIABILITY_AUDIT",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "overall":overall,
        "thresholds":thresholds,
        "bins":bins,
        "note":"All probabilities are chronology/out-of-fold for their event date. Thresholds are descriptive development evidence, not guaranteed future hit rates.",
    }
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"benchmark.json").write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
    out_rows.to_csv(OUT/"oof_winner_predictions_76.csv",index=False)

    best_70 = next((x for x in thresholds if x["n"] >= 15 and x["accuracy"] is not None and x["accuracy"] >= .70), None)
    report=[
        "# v0.30 winner reliability audit","",
        f"- Overall: **{overall['accuracy']:.1%} ({int(correct.sum())}-{int(len(y)-correct.sum())})**",
        f"- Brier: **{overall['brier']:.4f}**",
        "",
        "## Confidence thresholds","",
    ]
    for x in thresholds:
        acc="n/a" if x["accuracy"] is None else f"{x['accuracy']:.1%}"
        report.append(f"- >= {x['threshold']:.0%}: {x['wins']}-{x['losses']} ({acc}), n={x['n']}")
    report += ["", "## Interpretation", ""]
    if best_70:
        report.append(f"First threshold with >=15 fights and >=70% observed accuracy: **{best_70['threshold']:.0%}**.")
    else:
        report.append("No threshold with >=15 fights reached 70% observed accuracy; do not manufacture a lock threshold.")
    (OUT/"BUILD_REPORT.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
