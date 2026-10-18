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

from wshlx_ufc.historical_data import (
    build_prefight_perspective_rows,
    download_source_files,
    load_source_files,
    normalize_events,
)
from wshlx_ufc.historical_model import fit_historical_winner_model
from wshlx_ufc.historical_rates import comprehensive_conditional_rate_tables


def apply_results_supplements(tables: dict[str, pd.DataFrame], supplement_dir: Path) -> tuple[dict[str, pd.DataFrame], int]:
    """Append completed-event results that are newer than the public stats mirror.

    Supplements are automatically ignored once the mirror contains an event on the same
    date, preventing duplicate fights when the upstream scraper catches up. Detailed
    fight statistics are intentionally left missing unless a verified stats source is
    available; the feature builder tracks that missing coverage explicitly.
    """
    if not supplement_dir.exists():
        return tables, 0

    out = {k: v.copy() for k, v in tables.items()}
    known_dates = set(pd.to_datetime(normalize_events(out["events"])["date"]).dt.normalize().dropna())
    added = 0

    for path in sorted(supplement_dir.glob("*.csv")):
        sup = pd.read_csv(path)
        required = {"EVENT", "DATE", "BOUT", "OUTCOME"}
        if not required.issubset(sup.columns):
            raise ValueError(f"Supplement {path} missing required columns: {sorted(required - set(sup.columns))}")
        sup_dates = pd.to_datetime(sup["DATE"], errors="raise").dt.normalize()
        for date in pd.unique(sup_dates):
            if date in known_dates:
                continue
            rows = sup.loc[sup_dates == date].copy()
            event_rows = rows[[c for c in ("EVENT", "DATE", "LOCATION") if c in rows.columns]].drop_duplicates("EVENT")
            out["events"] = pd.concat([out["events"], event_rows], ignore_index=True, sort=False)
            result_cols = [c for c in rows.columns if c not in {"DATE", "LOCATION", "SOURCE_URL"}]
            out["results"] = pd.concat([out["results"], rows[result_cols]], ignore_index=True, sort=False)
            known_dates.add(date)
            added += len(rows)
    return out, added


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-dir", default="data/raw/ufcstats_mirror")
    p.add_argument("--supplement-dir", default="data/supplemental/results")
    p.add_argument("--output-dir", default="data/historical")
    p.add_argument("--download", action="store_true", help="refresh public UFCStats mirror first")
    p.add_argument("--min-bin-n", type=int, default=30)
    args = p.parse_args()

    src = ROOT / args.source_dir
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    if args.download:
        download_source_files(src)

    tables = load_source_files(src)
    mirror_last_date = pd.to_datetime(normalize_events(tables["events"])["date"]).max()
    tables, supplemental_rows = apply_results_supplements(tables, ROOT / args.supplement_dir)
    frame = build_prefight_perspective_rows(tables["events"], tables["results"], tables["stats"], tables["fighters"])
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
        "mirror_last_date": str(mirror_last_date.date()),
        "supplemental_result_rows": int(supplemental_rows),
        "conditional_rate_rows": int(len(rates)),
        "conditional_rate_families": int(rates["split"].nunique()) if len(rates) else 0,
        "metrics": metrics,
    }
    (out / "historical_build_manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    print(json.dumps(manifest, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
