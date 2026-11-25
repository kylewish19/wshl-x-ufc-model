"""Determine whether two FanDuel UFC straight-bet markets can BOTH settle WIN.

A same-bout pairing may be selected once in EACH of the two Top-5 tiers
only when their structured markets admit a common match result. This is
logical compatibility, NOT probabilistic independence or model calibration.

Never infer market meaning from the plain-English market label. Exact
typed market_spec fields are required. Unknown/custom markets fail closed.

Scope: normal 3- or 5-round MMA bouts with KO/TKO, submission and decisions,
no unusual DQ, no draw payout, no technical decisions/partial finishes.
These other market types MUST stay excluded until explicitly modeled.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping

METHODS = frozenset(("KO_TKO", "SUB", "DEC"))
SIDES = frozenset(("a", "b"))
KINDS = frozenset((
    "moneyline", "method", "double_chance", "goes_distance",
    "total_rounds", "round_to_start", "fight_end_method",
))
MARKET_FAMILY_FOR_KIND = {
    "moneyline": "moneyline",
    "method": "method",
    "double_chance": "double_chance",
    "goes_distance": "timing",
    "total_rounds": "timing",
    "round_to_start": "timing",
    "fight_end_method": "method",
}


def validate_market_spec(spec: Any, *, market_family: str, scheduled_rounds: int) -> dict:
    """Validate the exact declared sportsbook outcome, not a parsed label."""
    if not isinstance(spec, dict):
        raise ValueError("market_spec must be a structured dictionary; do not infer from market text")
    if scheduled_rounds not in (3, 5) or isinstance(scheduled_rounds, bool):
        raise ValueError("scheduled_rounds must be 3 or 5")
    kind = spec.get("kind")
    if kind not in KINDS or MARKET_FAMILY_FOR_KIND[kind] != market_family:
        raise ValueError("market_spec kind is unsupported or incompatible with market_family")
    required = {
        "moneyline": {"kind", "side"},
        "method": {"kind", "side", "method"},
        "double_chance": {"kind", "side", "methods"},
        "goes_distance": {"kind", "outcome"},
        "total_rounds": {"kind", "direction", "threshold"},
        "round_to_start": {"kind", "round", "outcome"},
        "fight_end_method": {"kind", "method"},
    }[kind]
    if set(spec) != required:
        raise ValueError(f"market_spec {kind} must use exactly {sorted(required)}")
    if "side" in spec and spec["side"] not in SIDES:
        raise ValueError("market_spec.side must be a or b")
    if kind in ("method", "fight_end_method") and spec["method"] not in METHODS:
        raise ValueError("market_spec.method invalid")
    if kind == "double_chance":
        methods = spec["methods"]
        if not isinstance(methods, list) or len(methods) != 2 or set(methods) - METHODS or len(set(methods)) != 2:
            raise ValueError("Double chance must have two distinct methods from KO_TKO, SUB, DEC")
    if kind in ("goes_distance", "round_to_start") and spec["outcome"] not in ("YES", "NO"):
        raise ValueError("Outcome must be YES or NO")
    if kind == "total_rounds":
        threshold = spec["threshold"]
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not any(
            threshold == x + .5 for x in range(scheduled_rounds)
        ):
            raise ValueError("Over/Under threshold must be a valid X.5 round line")
        if spec["direction"] not in ("OVER", "UNDER"):
            raise ValueError("direction must be OVER or UNDER")
    if kind == "round_to_start":
        rnd = spec["round"]
        if type(rnd) is not int or not 2 <= rnd <= scheduled_rounds:
            raise ValueError("round_to_start round must be 2..scheduled_rounds")
    # Copy to avoid callers mutating an already-selected item's logical meaning.
    out = dict(spec)
    if kind == "double_chance":
        out["methods"] = sorted(spec["methods"])
    return out


def _wins(spec: dict, winner: str, method: str, elapsed_seconds: int, max_seconds: int) -> bool:
    kind = spec["kind"]
    if kind == "moneyline":
        return winner == spec["side"]
    if kind == "method":
        return winner == spec["side"] and method == spec["method"]
    if kind == "double_chance":
        return winner == spec["side"] and method in spec["methods"]
    if kind == "fight_end_method":
        return method == spec["method"]
    if kind == "goes_distance":
        return (method == "DEC") == (spec["outcome"] == "YES")
    if kind == "total_rounds":
        threshold_s = round(spec["threshold"] * 300)
        if spec["direction"] == "OVER":
            return elapsed_seconds > threshold_s
        return elapsed_seconds < threshold_s
    if kind == "round_to_start":
        started = elapsed_seconds > (spec["round"] - 1) * 300
        return started == (spec["outcome"] == "YES")
    raise ValueError(f"Unimplemented market kind {kind}")


@lru_cache(maxsize=2048)
def _compatible_immutable(a: tuple, b: tuple, scheduled_rounds: int) -> bool:
    def decode(value: tuple) -> dict:
        return {k: list(v) if k == "methods" else v for k, v in value}
    sa, sb = decode(a), decode(b)
    max_seconds = scheduled_rounds * 300
    # Every in-round second represents a possible stopping time. Decision
    # occurs at the end of the final scheduled round. This is exhaustive
    # with respect to the supported sides / finish methods / half-round
    # settlement boundaries; nonstandard void/DQ markets are unsupported.
    for winner in ("a", "b"):
        for method in ("KO_TKO", "SUB"):
            for elapsed in range(1, max_seconds):
                if _wins(sa, winner, method, elapsed, max_seconds) and _wins(sb, winner, method, elapsed, max_seconds):
                    return True
        if _wins(sa, winner, "DEC", max_seconds, max_seconds) and _wins(
            sb, winner, "DEC", max_seconds, max_seconds
        ):
            return True
    return False


def can_both_win(a: Mapping[str, Any], b: Mapping[str, Any], *, scheduled_rounds: int) -> bool:
    """Return True exactly when two SUPPORTED markets can both be winners."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        raise ValueError("Both markets need exact typed spec dictionaries")
    fa = MARKET_FAMILY_FOR_KIND.get(a.get("kind"))
    fb = MARKET_FAMILY_FOR_KIND.get(b.get("kind"))
    if fa is None or fb is None:
        raise ValueError("Unknown market cannot receive an assumed compatibility pass")
    ca = validate_market_spec(a, market_family=fa, scheduled_rounds=scheduled_rounds)
    cb = validate_market_spec(b, market_family=fb, scheduled_rounds=scheduled_rounds)
    key_a = tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in ca.items()))
    key_b = tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in cb.items()))
    return _compatible_immutable(key_a, key_b, scheduled_rounds)
