"""Eligibility guards for the WSHL-X unified UFC ensemble.

The unified stack is trained only on ordinary decided win/loss fights whose method is
KO/TKO, submission, or decision. Draws, no contests, DQs, overturned/other outcomes,
and any other non-binary result must not be silently coerced into winner, method, or
timing targets.
"""
from __future__ import annotations

from collections import defaultdict
import re
import unicodedata
from typing import Mapping

import pandas as pd

SUPPORTED_METHODS = {"KO_TKO", "SUB", "DEC"}

NAME_ALIASES = {
    "alatengheili": "heilialateng",
    "tinablack": "valescamachado",
    "mahammadaliosmanli": "mehemmedeliosmanli",
    "kinggreen": "bobbygreen",
    "stanleydorsainvil": "standorsainvil",
}


def norm_name(value: object) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    s = raw.lower().replace("’", "'")
    s = re.sub(r"[^a-z0-9]+", "", s)
    return NAME_ALIASES.get(s, s)


def pair_key(a: object, b: object) -> tuple[str, str]:
    return tuple(sorted((norm_name(a), norm_name(b))))


def _column(df: pd.DataFrame, name: str) -> str:
    wanted = re.sub(r"[^A-Z0-9]+", "", str(name).upper())
    for col in df.columns:
        if re.sub(r"[^A-Z0-9]+", "", str(col).upper()) == wanted:
            return str(col)
    raise KeyError(f"missing column {name!r}")


def _bout_names(value: object) -> tuple[str, str] | None:
    text = str(value or "").strip()
    for token in (" vs. ", " vs ", " v. ", " v "):
        if token in text:
            a, b = text.split(token, 1)
            if a.strip() and b.strip():
                return a.strip(), b.strip()
    return None


def _binary_win_loss(value: object) -> bool:
    """True only when the recorded result is one W and one L."""
    parts = [p for p in re.split(r"[/|,-]", str(value or "").upper().replace(" ", "")) if p]
    if len(parts) < 2:
        return False

    def norm(part: str) -> str:
        if part.startswith("W"):
            return "W"
        if part.startswith("L"):
            return "L"
        if part.startswith("D"):
            return "D"
        if "NC" in part:
            return "NC"
        return part

    a, b = norm(parts[0]), norm(parts[1])
    return {a, b} == {"W", "L"}


def unsupported_pairs_by_date(frame: pd.DataFrame) -> dict[str, set[tuple[str, str]]]:
    """Return perspective-table pairs whose method is outside KO/SUB/DEC."""
    required = {"date", "fighter", "opponent", "fight_method"}
    missing = required - set(frame.columns)
    if missing:
        raise KeyError(f"missing eligibility columns: {sorted(missing)}")

    out: defaultdict[str, set[tuple[str, str]]] = defaultdict(set)
    dates = pd.to_datetime(frame["date"], errors="coerce")
    for i, row in frame.iterrows():
        method = str(row["fight_method"] or "").upper()
        if method in SUPPORTED_METHODS:
            continue
        date = dates.loc[i]
        if pd.isna(date):
            continue
        out[pd.Timestamp(date).strftime("%Y-%m-%d")].add(pair_key(row["fighter"], row["opponent"]))
    return dict(out)


def unsupported_result_pairs_by_date(
    results: pd.DataFrame,
    events: pd.DataFrame,
) -> dict[str, set[tuple[str, str]]]:
    """Return raw-result pairs that are not ordinary binary W/L decisions.

    This catches draws and no contests that are absent from the decided-fight pre-fight
    perspective table, plus any DQ/other result that must not enter unified meta fitting.
    """
    event_col = _column(events, "EVENT")
    date_col = _column(events, "DATE")
    result_event_col = _column(results, "EVENT")
    bout_col = _column(results, "BOUT")
    outcome_col = _column(results, "OUTCOME")

    event_dates = {
        str(row[event_col]).strip(): pd.to_datetime(row[date_col], errors="coerce")
        for _, row in events.iterrows()
    }
    out: defaultdict[str, set[tuple[str, str]]] = defaultdict(set)
    for _, row in results.iterrows():
        if _binary_win_loss(row[outcome_col]):
            continue
        names = _bout_names(row[bout_col])
        if names is None:
            continue
        date = event_dates.get(str(row[result_event_col]).strip())
        if date is None or pd.isna(date):
            continue
        out[pd.Timestamp(date).strftime("%Y-%m-%d")].add(pair_key(*names))
    return dict(out)


def merge_unsupported_pairs(
    *sources: Mapping[str, set[tuple[str, str]]],
) -> dict[str, set[tuple[str, str]]]:
    out: defaultdict[str, set[tuple[str, str]]] = defaultdict(set)
    for source in sources:
        for date, pairs in source.items():
            out[str(date)].update(pairs)
    return dict(out)


def filter_lock_payload(
    payload: Mapping[str, object],
    *,
    card_date: str,
    unsupported: Mapping[str, set[tuple[str, str]]],
) -> tuple[dict, list[str]]:
    """Return a copy of a frozen payload with unsupported-result fights excluded.

    The original frozen JSON is never modified. The returned list is an audit trail of
    excluded matchups.
    """
    blocked = unsupported.get(str(card_date), set())
    out = dict(payload)
    fights = list(payload.get("fights", []))
    kept, excluded = [], []
    for fight in fights:
        key = pair_key(fight.get("a"), fight.get("b"))
        if key in blocked:
            excluded.append(f"{fight.get('a')} vs {fight.get('b')}")
        else:
            kept.append(fight)
    out["fights"] = kept
    return out, excluded
