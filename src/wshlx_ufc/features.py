from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


NON_FEATURE_COLUMNS = {
    "fight_id",
    "event_id",
    "event_date",
    "fighter_a",
    "fighter_b",
    "winner",
    "method",
    "finish_round",
    "finish_time_seconds",
    "result",
}


@dataclass(frozen=True)
class FeatureSnapshot:
    fight_id: str
    event_date: datetime
    source_cutoff: datetime
    columns: tuple[str, ...]


def assert_prefight_cutoff(
    frame: pd.DataFrame,
    *,
    event_date_col: str = "event_date",
    source_time_col: str = "source_timestamp",
) -> None:
    """Reject rows containing source information timestamped after the fight."""
    if event_date_col not in frame or source_time_col not in frame:
        raise ValueError(
            f"Required columns missing: {event_date_col!r}, {source_time_col!r}"
        )

    event_time = pd.to_datetime(frame[event_date_col], utc=True)
    source_time = pd.to_datetime(frame[source_time_col], utc=True)

    leaking = source_time >= event_time
    if leaking.any():
        bad = frame.loc[leaking].index.tolist()[:10]
        raise ValueError(f"Post-fight or same-time source leakage in rows: {bad}")


def feature_columns(frame: pd.DataFrame, extra_exclude: Iterable[str] = ()) -> list[str]:
    excluded = NON_FEATURE_COLUMNS | set(extra_exclude)
    cols = [
        c
        for c in frame.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(frame[c])
    ]
    if not cols:
        raise ValueError("No numeric prefight feature columns were found.")
    return cols


def make_differential_features(
    frame: pd.DataFrame,
    paired_feature_names: Sequence[str],
    *,
    suffix_a: str = "_a",
    suffix_b: str = "_b",
) -> pd.DataFrame:
    """Create matchup A-minus-B differentials without mutating the input."""
    out = frame.copy()
    for base in paired_feature_names:
        a, b = f"{base}{suffix_a}", f"{base}{suffix_b}"
        if a not in out or b not in out:
            raise KeyError(f"Missing paired columns for {base}: {a}, {b}")
        out[f"{base}_diff"] = pd.to_numeric(out[a], errors="coerce") - pd.to_numeric(
            out[b], errors="coerce"
        )
    return out


def stable_log_bouts(values: pd.Series) -> pd.Series:
    values = pd.to_numeric(values, errors="coerce")
    return np.log1p(values.clip(lower=0))
