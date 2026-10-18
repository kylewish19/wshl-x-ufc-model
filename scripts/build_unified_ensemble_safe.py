#!/usr/bin/env python3
"""Run the unified ensemble while excluding nonstandard-result fights from meta fitting.

This wrapper preserves the frozen card JSON files exactly as recorded. It derives an
eligibility mask from the leakage-safe historical perspective table, then filters only
the in-memory payloads passed to the unified builder. DQ/OTHER outcomes therefore do
not get mislabeled as KO/SUB/DEC or ordinary timing finishes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import build_unified_ensemble as base
from wshlx_ufc.ensemble_eligibility import (
    filter_lock_payload,
    norm_name,
    unsupported_pairs_by_date,
)


def main() -> int:
    frame_path = ROOT / "data/historical/prefight_perspective_rows.csv"
    if not frame_path.exists():
        raise SystemExit("Run build_historical_model.py before the unified ensemble build")
    frame = pd.read_csv(frame_path, low_memory=False)
    unsupported = unsupported_pairs_by_date(frame)

    # Keep the builder's pair matching on the same Unicode-safe normalization used by
    # eligibility filtering. This avoids false misses when one source contains accented
    # fighter names and another stores the ASCII transliteration.
    base.norm_name = norm_name

    original_read_lock = base.read_lock
    date_by_path = {Path(path).resolve(): date for date, path in base.LOCKS.items()}
    exclusions: list[str] = []

    def safe_read_lock(path: Path) -> dict:
        payload = original_read_lock(path)
        date = date_by_path.get(Path(path).resolve())
        if date is None:
            return payload
        filtered, dropped = filter_lock_payload(payload, card_date=date, unsupported=unsupported)
        exclusions.extend(f"{date}: {fight}" for fight in dropped)
        return filtered

    base.read_lock = safe_read_lock
    rc = base.main()
    if exclusions:
        print("Unified ensemble eligibility exclusions:")
        for item in sorted(set(exclusions)):
            print(f"- {item}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
