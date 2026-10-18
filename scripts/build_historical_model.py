#!/usr/bin/env python3
"""Build UFC historical pre-fight features, split tables, and winner model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wshlx_ufc.historical_data import build_from_directory, download_source_files
from wshlx_ufc.historical_model import fit_historical_winner_model
from wshlx_ufc.historical_rates import comprehensive_conditional_rate_tables


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-dir", default="data/raw/ufcstats_mirror")
    p.add_argument("--output-dir", default="data/historical")
    p.add_argument("--download", action="store_true", help="refresh public UFCStats mirror first")
    p.add_argument("--min-bin-n", type=int, default=30)
    args = p.parse_args()

    src = ROOT / args.source_dir
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    if args.download:
        download_source_files(src)

    frame = build_from_directory(src)
    if frame.empty:
        raise SystemExit("No decided fights were reconstructed from source files")
    frame.to_csv(out / "prefight_perspective_rows.csv", index=False)

    rates = comprehensive_conditional_rate_tables(frame, min_n=args.min_bin_n)
    rates.to_csv(out / "conditional_win_rates.csv", index=False)

    bundle, metrics = fit_historical_winner_model(frame)
    joblib.dump(bundle, out / "historical_winner_model.joblib")
    (out / "historical_winner_metrics.json").write_text(json.dumps(metrics, indent=2, default=str) + "\n")

    manifest = {
        "perspective_rows": int(len(frame)),
        "unique_fights": int(frame["fight_id"].nunique()),
        "first_date": str(pd.to_datetime(frame["date"]).min().date()),
        "last_date": str(pd.to_datetime(frame["date"]).max().date()),
        "conditional_rate_rows": int(len(rates)),
        "metrics": metrics,
    }
    (out / "historical_build_manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    print(json.dumps(manifest, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
