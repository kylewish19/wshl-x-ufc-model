#!/usr/bin/env python3
"""Build UFC historical prefight features, conditional rates, and shadow models."""
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
from wshlx_ufc.historical_method_model import fit_historical_method_model, method_conditional_rate_tables
from wshlx_ufc.historical_model import fit_historical_winner_model
from wshlx_ufc.historical_rates import comprehensive_conditional_rate_tables
from wshlx_ufc.historical_timing_model import fit_historical_timing_model, timing_conditional_rate_tables


def apply_results_supplements(tables: dict[str, pd.DataFrame], supplement_dir: Path) -> tuple[dict[str, pd.DataFrame], int]:
    """Append completed-event results that are newer than the public stats mirror."""
    if not supplement_dir.exists():
        return tables, 0

    out = {k: v.copy() for k, v in tables.items()}
    known_dates = {pd.Timestamp(d).normalize() for d in pd.to_datetime(normalize_events(out["events"])["date"]).dropna()}
    added = 0

    for path in sorted(supplement_dir.glob("*.csv")):
        sup = pd.read_csv(path)
        required = {"EVENT", "DATE", "BOUT", "OUTCOME"}
        if not required.issubset(sup.columns):
            raise ValueError(f"Supplement {path} missing required columns: {sorted(required - set(sup.columns))}")
        sup_dates = pd.to_datetime(sup["DATE"], errors="raise").dt.normalize()
        for raw_date in pd.unique(sup_dates):
            date = pd.Timestamp(raw_date).normalize()
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


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n")


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

    winner_rates = comprehensive_conditional_rate_tables(frame, min_n=args.min_bin_n)
    winner_rates.to_csv(out / "conditional_win_rates.csv", index=False)
    winner_bundle, winner_metrics = fit_historical_winner_model(frame)
    joblib.dump(winner_bundle, out / "historical_winner_model.joblib")
    _write_json(out / "historical_winner_metrics.json", winner_metrics)

    method_rates = method_conditional_rate_tables(frame, min_n=args.min_bin_n)
    method_rates.to_csv(out / "conditional_method_rates.csv", index=False)
    method_bundle, method_metrics = fit_historical_method_model(frame)
    joblib.dump(method_bundle, out / "historical_method_model.joblib")
    _write_json(out / "historical_method_metrics.json", method_metrics)

    timing_rates = timing_conditional_rate_tables(frame, tables["results"], min_n=args.min_bin_n)
    timing_rates.to_csv(out / "conditional_timing_rates.csv", index=False)
    timing_bundle, timing_metrics = fit_historical_timing_model(frame, tables["results"])
    joblib.dump(timing_bundle, out / "historical_timing_model.joblib")
    _write_json(out / "historical_timing_metrics.json", timing_metrics)

    manifest = {
        "perspective_rows": int(len(frame)),
        "unique_fights": int(frame["fight_id"].nunique()),
        "first_date": str(pd.to_datetime(frame["date"]).min().date()),
        "last_date": str(pd.to_datetime(frame["date"]).max().date()),
        "mirror_last_date": str(mirror_last_date.date()),
        "supplemental_result_rows": int(supplemental_rows),
        "winner_conditional_rate_rows": int(len(winner_rates)),
        "winner_conditional_rate_families": int(winner_rates["split"].nunique()) if len(winner_rates) else 0,
        "method_conditional_rate_rows": int(len(method_rates)),
        "method_conditional_rate_families": int(method_rates[["outcome", "split"]].drop_duplicates().shape[0]) if len(method_rates) else 0,
        "timing_conditional_rate_rows": int(len(timing_rates)),
        "timing_conditional_rate_families": int(timing_rates[["outcome", "split"]].drop_duplicates().shape[0]) if len(timing_rates) else 0,
        "winner_metrics": winner_metrics,
        "method_metrics": method_metrics,
        "timing_metrics": timing_metrics,
    }
    _write_json(out / "historical_build_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
