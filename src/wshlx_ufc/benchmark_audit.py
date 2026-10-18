"""Audit reproduced UFC conditional-rate tables against published benchmarks.

Published rates are validation targets only.  They are never injected into model
predictions and never replace rates reconstructed from the project's own prefight
history.  The audit exists to catch sign, bucket, chronology, and subject-orientation
bugs in the historical-rate engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BenchmarkAuditConfig:
    absolute_tolerance: float = 0.03
    minimum_n: int = 30


def load_published_benchmarks(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"family", "bucket", "target", "subject", "rate", "n", "source_url", "as_of"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"benchmark file missing columns: {sorted(missing)}")
    frame = frame.copy()
    frame["rate"] = pd.to_numeric(frame["rate"], errors="coerce")
    frame["n"] = pd.to_numeric(frame["n"], errors="coerce")
    return frame


def compare_rate_tables(
    reproduced: pd.DataFrame,
    benchmarks: pd.DataFrame,
    *,
    family_map: dict[str, str] | None = None,
    bucket_map: dict[tuple[str, str], str] | None = None,
    config: BenchmarkAuditConfig = BenchmarkAuditConfig(),
) -> pd.DataFrame:
    """Compare compatible winner/finish rate rows and flag material disagreement.

    `reproduced` is expected to contain split, bucket, n and win_rate columns from
    historical_rates.py.  Explicit maps are required when local bucket labels differ
    from the published registry; the function intentionally does not guess semantics.
    """
    required = {"split", "bucket", "n", "win_rate"}
    missing = required - set(reproduced.columns)
    if missing:
        raise ValueError(f"reproduced table missing columns: {sorted(missing)}")

    local = reproduced.copy()
    local["family"] = local["split"].astype(str).map(family_map or {}).fillna(local["split"].astype(str))
    if bucket_map:
        local["benchmark_bucket"] = [
            bucket_map.get((str(f), str(b)), str(b))
            for f, b in zip(local["family"], local["bucket"])
        ]
    else:
        local["benchmark_bucket"] = local["bucket"].astype(str)

    pub = benchmarks.copy()
    merged = local.merge(
        pub,
        left_on=["family", "benchmark_bucket"],
        right_on=["family", "bucket"],
        suffixes=("_local", "_published"),
        how="inner",
    )
    if merged.empty:
        return merged

    merged["rate_error"] = pd.to_numeric(merged["win_rate"], errors="coerce") - pd.to_numeric(merged["rate"], errors="coerce")
    merged["abs_rate_error"] = merged["rate_error"].abs()
    merged["enough_local_n"] = pd.to_numeric(merged["n_local"], errors="coerce") >= config.minimum_n
    merged["within_tolerance"] = merged["abs_rate_error"] <= config.absolute_tolerance
    merged["audit_pass"] = merged["enough_local_n"] & merged["within_tolerance"]
    return merged.sort_values(["audit_pass", "abs_rate_error"], ascending=[True, False]).reset_index(drop=True)


def audit_summary(audit: pd.DataFrame) -> dict[str, float]:
    if audit.empty:
        return {"matched_rows": 0.0, "pass_rows": 0.0, "pass_rate": np.nan, "max_abs_error": np.nan}
    passed = pd.to_numeric(audit["audit_pass"], errors="coerce").fillna(False).astype(bool)
    return {
        "matched_rows": float(len(audit)),
        "pass_rows": float(passed.sum()),
        "pass_rate": float(passed.mean()),
        "max_abs_error": float(pd.to_numeric(audit["abs_rate_error"], errors="coerce").max()),
    }
