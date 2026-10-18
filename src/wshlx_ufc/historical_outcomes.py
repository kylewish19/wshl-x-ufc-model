"""Leakage-safe outcome targets derived from completed UFC results.

Targets are kept outside the prefight feature builder so result/method/timing fields can
never accidentally enter the predictor matrix. Method labels are derived from the
existing decided-fight perspective rows. Timing labels are attached from the raw result
record only after prefight state reconstruction is complete.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .historical_data import bout, col, method, num, rounds, secs, txt

METHOD_STATES = (
    "WIN_KO_TKO",
    "WIN_SUB",
    "WIN_DEC",
    "LOSS_KO_TKO",
    "LOSS_SUB",
    "LOSS_DEC",
)


def add_method_targets(frame: pd.DataFrame) -> pd.DataFrame:
    """Add six-state fighter-specific method target plus binary component targets."""
    out = frame.copy()
    m = out["fight_method"].astype("string")
    valid = m.isin(["KO_TKO", "SUB", "DEC"]) & out["win"].isin([0, 1])
    side = np.where(out["win"].eq(1), "WIN_", "LOSS_")
    out["method_target"] = pd.Series(np.where(valid, side + m.fillna(""), pd.NA), index=out.index, dtype="string")
    for state in METHOD_STATES:
        out[f"target_{state.lower()}"] = np.where(out["method_target"].notna(), out["method_target"].eq(state).astype(float), np.nan)
    return out


def _result_timing_map(results: pd.DataFrame) -> dict[tuple[str, tuple[str, str]], dict[str, float]]:
    ec, bc = col(results, "EVENT"), col(results, "BOUT")
    if ec is None or bc is None:
        raise ValueError("results CSV needs EVENT and BOUT")
    wc = col(results, "WEIGHTCLASS")
    mc = col(results, "METHOD")
    rc = col(results, "ROUND")
    tc = col(results, "TIME")
    tfc = col(results, "TIME_FORMAT", "TIME FORMAT")
    out: dict[tuple[str, tuple[str, str]], dict[str, float]] = {}
    for _, row in results.iterrows():
        pair = bout(row[bc])
        if pair is None:
            continue
        ev = txt(row[ec])
        key = (ev, tuple(sorted(pair)))
        wc_text = txt(row[wc]) if wc else ""
        scheduled_rounds = rounds(txt(row[tfc]) if tfc else "", wc_text)
        if scheduled_rounds not in (3, 5):
            continue
        meth = method(row[mc]) if mc else "OTHER"
        scheduled_seconds = scheduled_rounds * 300
        if meth == "DEC":
            duration_seconds = float(scheduled_seconds)
            observed = 0.0
        elif meth in {"KO_TKO", "SUB"} and rc is not None and tc is not None:
            rnd = int(max(1, num(row[rc])))
            duration_seconds = float((rnd - 1) * 300 + secs(row[tc]))
            if not (0 < duration_seconds <= scheduled_seconds):
                continue
            observed = 1.0
        else:
            continue
        out[key] = {
            "finish_seconds": duration_seconds,
            "scheduled_seconds": float(scheduled_seconds),
            "finish_observed": observed,
        }
    return out


def add_timing_targets(frame: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    """Attach duration/censoring targets to already-built prefight perspective rows."""
    out = frame.copy()
    timing = _result_timing_map(results)
    finish_seconds: list[float] = []
    scheduled_seconds: list[float] = []
    observed: list[float] = []
    for _, row in out.iterrows():
        key = (str(row["event"]), tuple(sorted((str(row["fighter"]), str(row["opponent"])))))
        rec = timing.get(key)
        if rec is None:
            finish_seconds.append(np.nan)
            scheduled_seconds.append(np.nan)
            observed.append(np.nan)
        else:
            finish_seconds.append(rec["finish_seconds"])
            scheduled_seconds.append(rec["scheduled_seconds"])
            observed.append(rec["finish_observed"])
    out["finish_seconds"] = finish_seconds
    out["scheduled_seconds"] = scheduled_seconds
    out["finish_observed"] = observed
    out["finish_r1"] = np.where(out["finish_observed"].notna(), ((out["finish_observed"] == 1) & (out["finish_seconds"] <= 300)).astype(float), np.nan)
    out["survive_450"] = np.where(out["finish_observed"].notna(), (out["finish_seconds"] > 450).astype(float), np.nan)
    out["survive_750"] = np.where(out["finish_observed"].notna(), (out["finish_seconds"] > 750).astype(float), np.nan)
    out["goes_distance"] = np.where(out["finish_observed"].notna(), (out["finish_observed"] == 0).astype(float), np.nan)
    return out
