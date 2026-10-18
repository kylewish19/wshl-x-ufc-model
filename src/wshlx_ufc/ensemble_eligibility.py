"""Eligibility guards for the WSHL-X unified UFC ensemble.

The unified method and timing stack is defined only for ordinary KO/TKO, submission,
and decision outcomes. Nonstandard results (DQ, overturned/no contest, other) must not
be silently coerced into those targets or used to learn ensemble weights.
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


def unsupported_pairs_by_date(frame: pd.DataFrame) -> dict[str, set[tuple[str, str]]]:
    """Return fight pairs whose recorded outcome is outside KO/SUB/DEC.

    Perspective data contains two mirrored rows per fight, so sets de-duplicate them.
    Dates are normalized to YYYY-MM-DD for direct comparison with frozen card dates.
    """
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


def filter_lock_payload(
    payload: Mapping[str, object],
    *,
    card_date: str,
    unsupported: Mapping[str, set[tuple[str, str]]],
) -> tuple[dict, list[str]]:
    """Return a copy of a frozen payload with nonstandard-result fights excluded.

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
