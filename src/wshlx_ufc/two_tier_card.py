"""Two independent WSHL_X UFC Top-5 straight-bet tiers; FanDuel Stage B ONLY.

This module does not generate model probabilities, bypass existing selection
policy gates, infer sportsbook prices, or treat a fight PASS as bettable.
It uses explicit, reviewed FanDuel quotes and a conservative probability
estimate to rank *already eligible* candidate straights.

A fight may appear once in EACH category only if the two *typed* market outcomes
can both win. Conflicting fight outcomes cannot be paired across tiers.
No betting-pick minimum is imposed. Up to five research-only display candidates
can be shown per tier, clearly marked PASS, without faking official bets.
An unsuccessful 3-leg parlay cannot be disguised as three straight results.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from wshlx_ufc.market_compatibility import can_both_win, validate_market_spec

LONGSHOTS = "top_5_longshots"
BEST_BETS = "top_5_best_bets"
TIERS = (LONGSHOTS, BEST_BETS)
GATES = ("stage_a_supported", "research", "price", "calibration", "market_family")
MARKET_FAMILIES = ("moneyline", "method", "timing", "double_chance")


def _normalize_name(s: str) -> str:
    t = unicodedata.normalize("NFKD", str(s))
    t = "".join(x for x in t if not unicodedata.combining(x))
    return re.sub(r"[^a-z0-9]", "", t.casefold())


def fight_key(a: str, b: str) -> str:
    """Order independent; identical names must not produce a valid matchup."""
    x, y = _normalize_name(a), _normalize_name(b)
    if not x or not y or x == y:
        raise ValueError("Two distinct fighter names required")
    return "|".join(sorted((x, y)))


def tier_for_odds(american: int) -> str | None:
    """+200+, or -150 through -100 and +100 through +190 inclusive.

    US odds convention doesn't use integers from -99 to +99. Positive
    +191...+199 is intentionally excluded by the user's requested gap.
    """
    if not isinstance(american, int) or isinstance(american, bool) or -99 <= american <= 99:
        raise ValueError("Valid integer American odds required (e.g. -150, +190, +200)")
    if american >= 200:
        return LONGSHOTS
    if -150 <= american <= -100 or 100 <= american <= 190:
        return BEST_BETS
    return None


def break_even(american: int) -> float:
    tier_for_odds(american)  # Validate even when price falls into neither tier.
    return 100 / (american + 100) if american > 0 else -american / (100 - american)


def net_profit_per_unit(american: int) -> float:
    tier_for_odds(american)
    return american / 100 if american > 0 else 100 / (-american)


def expected_value(american: int, probability: float) -> float:
    p = float(probability)
    if not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("Probability must lie in [0, 1]")
    return p * net_profit_per_unit(american) - (1 - p)


def _prob(x: Any, name: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (float, int)):
        raise ValueError(f"{name} must be numeric")
    p = float(x)
    if not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError(f"{name} must be within [0, 1]")
    return p


def _stake(x: Any) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError("stake_units must be numeric")
    v = float(x)
    if not math.isfinite(v) or not 0 < v <= 10:
        raise ValueError("stake_units must be greater than zero and <=10")
    return v


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: explicit offset-aware timestamp required")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as ex:
        raise ValueError(f"{label}: malformed timestamp") from ex
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError(f"{label}: timestamp must have timezone")
    return d.astimezone(timezone.utc)


def _score_key(c: Mapping[str, Any]):
    """Prioritize conservative estimated EV, then edge, certainty, quality.

    Compatible bets can share a fight across tiers; any competing selection
    within the SAME tier or conflicting outcome is excluded, regardless of EV.
    Qualification gates always take precedence over rankings.
    """
    return (
        -float(c["conservative_ev_per_unit"]),
        -float(c["conservative_probability_edge"]),
        -float(c["conservative_probability"]),
        -float(c["evidence_quality"]),
        str(c["candidate_id"]),
    )


def select_two_tier(
    *,
    event: str,
    event_date: str,
    stage_a_sha256: str,
    candidates: Sequence[Mapping[str, Any]],
    verified_stage_a_fights: Sequence[Mapping[str, str]],
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build an executable card from explicitly reviewed FanDuel Stage B prices.

    Candidate fields:
       candidate_id, fighter_a, fighter_b, market, market_family,
       market_spec (mandatory structured typed contract),
       american_odds, model_probability, conservative_probability,
       evidence_quality, stake_units, sportsbook, quoted_at_utc,
       gates (five explicit booleans), and researched_before_start.

    conservative_probability is a separately justified lower-bound estimate;
    there is intentionally NO fallback to uncalibrated raw model probability.
    """
    if not event or not event_date or len(stage_a_sha256) != 64 or any(
        ch not in "0123456789abcdef" for ch in stage_a_sha256.lower()
    ):
        raise ValueError("Event/date and 64-character frozen Stage A SHA required")
    date = datetime.fromisoformat(event_date).date()
    now = _timestamp(generated_at_utc or datetime.now(timezone.utc).isoformat(), "generated_at_utc")
    event_start_boundary = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    # Do not assert a midnight UTC cutoff: U.S. events can start hours later.
    # Quotes are independently timestamped and validated in the event audit.
    if len(verified_stage_a_fights) == 0:
        raise ValueError("Cannot validate selections without frozen Stage A fight identities")
    allowed = {
        fight_key(f["a"], f["b"]): f.get("scheduled_rounds")
        for f in verified_stage_a_fights
    }
    if any(v not in (3, 5) or type(v) is not int for v in allowed.values()):
        raise ValueError("Frozen fights must carry scheduled_rounds 3 or 5 to validate market compatibility")
    if len(allowed) != len(verified_stage_a_fights):
        raise ValueError("Frozen card contains duplicated matchups")

    qualifying: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reviewed: list[dict[str, Any]] = []
    ids = set()
    for source in candidates:
        c = dict(source)
        cid = c.get("candidate_id")
        if not isinstance(cid, str) or not cid.strip() or cid in ids:
            raise ValueError("Each candidate must have a nonempty unique candidate_id")
        ids.add(cid)
        key = fight_key(c["fighter_a"], c["fighter_b"])
        if key not in allowed:
            raise ValueError(f"{cid}: fight is not in verified frozen Stage A card")
        odds = c.get("american_odds")
        tier = tier_for_odds(odds)
        model_p = _prob(c.get("model_probability"), "model_probability")
        conservative_p = _prob(c.get("conservative_probability"), "conservative_probability")
        if conservative_p > model_p + 1e-12:
            raise ValueError(f"{cid}: conservative_probability cannot exceed raw model probability")
        quality = _prob(c.get("evidence_quality"), "evidence_quality")
        stake = _stake(c.get("stake_units"))
        if c.get("market_family") not in MARKET_FAMILIES:
            raise ValueError(f"{cid}: unsupported market family")
        market_spec = validate_market_spec(
            c.get("market_spec"), market_family=c["market_family"],
            scheduled_rounds=allowed[key],
        )
        if not isinstance(c.get("market"), str) or not c["market"].strip():
            raise ValueError(f"{cid}: market name required")
        if c.get("sportsbook") != "FanDuel":
            raise ValueError(f"{cid}: only verified FanDuel quotes allowed")
        quote_time = _timestamp(c.get("quoted_at_utc"), f"{cid} quoted_at_utc")
        if quote_time > now:
            raise ValueError(f"{cid}: quote cannot be from the future")
        if quote_time.date() > date:
            raise ValueError(f"{cid}: quote after event date")
        if c.get("researched_before_start") is not True:
            raise ValueError(f"{cid}: fight-start verification required")
        gates = c.get("gates")
        if not isinstance(gates, dict) or set(gates) != set(GATES) or any(
            not isinstance(v, bool) for v in gates.values()
        ):
            raise ValueError(f"{cid}: all five explicit existing-policy gates required")
        ev = expected_value(odds, conservative_p)
        edge = conservative_p - break_even(odds)
        reasons = []
        if tier is None:
            reasons.append("outside_requested_odds_tiers")
        for gate_name in GATES:
            if gates[gate_name] is False:
                reasons.append(f"failed_{gate_name}_gate")
        if edge <= 0 or ev <= 0:
            reasons.append("no_positive_conservative_value")
        row = {
            "candidate_id": cid, "fighter_a": c["fighter_a"], "fighter_b": c["fighter_b"],
            "fight_key": key, "scheduled_rounds": allowed[key],
            "market": c["market"], "market_family": c["market_family"],
            "market_spec": market_spec,
            "sportsbook": "FanDuel", "quoted_at_utc": quote_time.isoformat(),
            "american_odds": odds, "model_probability": model_p,
            "conservative_probability": conservative_p,
            "break_even_probability": break_even(odds),
            "conservative_probability_edge": edge,
            "conservative_ev_per_unit": ev,
            "evidence_quality": quality, "stake_units": stake,
            "gates": gates, "tier": tier, "status": "STAGE_B_CANDIDATE",
        }
        row["preselection_gate_reasons"] = list(reasons)
        reviewed.append(row)
        if reasons:
            rejected.append({"candidate_id": cid, "fight_key": key, "tier": tier, "reasons": reasons})
        else:
            qualifying.append(row)
    selected = {LONGSHOTS: [], BEST_BETS: []}
    selected_by_fight: dict[str, list[dict[str, Any]]] = {}
    for c in sorted(qualifying, key=_score_key):
        tier = c["tier"]
        prior = selected_by_fight.get(c["fight_key"], [])
        if any(other["tier"] == tier for other in prior):
            rejected.append({"candidate_id": c["candidate_id"], "fight_key": c["fight_key"],
                             "tier": tier, "reasons": ["fight_already_selected_within_tier"]})
            continue
        if any(
            other["market_spec"] == c["market_spec"] or not can_both_win(
                other["market_spec"], c["market_spec"],
                scheduled_rounds=c["scheduled_rounds"],
            ) for other in prior
        ):
            rejected.append({"candidate_id": c["candidate_id"], "fight_key": c["fight_key"],
                             "tier": tier, "reasons": ["duplicate_or_mutually_exclusive_same_fight_market"]})
            continue
        if len(selected[tier]) == 5:
            rejected.append({"candidate_id": c["candidate_id"], "fight_key": c["fight_key"],
                             "tier": tier, "reasons": ["five_selection_limit_reached"]})
            continue
        c["status"] = "OFFICIAL_TWO_TIER_STRAIGHT"
        selected[tier].append(c)
        selected_by_fight.setdefault(c["fight_key"], []).append(c)

    # User-facing top-five research review: the approved picks come first.
    # Fill remaining display slots ONLY from markets actually quoted/reviewed
    # in the specified odds band. Every non-approved entry is visibly PASS,
    # with its reasons. We never invent markets or promote PASS to wagers.
    ranked_display = {tier: [dict(row) for row in selected[tier]] for tier in TIERS}
    visible: dict[str, list[dict[str, Any]]] = {}
    for tier in TIERS:
        for row in ranked_display[tier]:
            visible.setdefault(row["fight_key"], []).append(row)
    rejected_reasons = {x["candidate_id"]: x["reasons"] for x in rejected}
    for c in sorted(reviewed, key=_score_key):
        tier = c["tier"]
        if tier is None or len(ranked_display[tier]) >= 5:
            continue
        if any(x["candidate_id"] == c["candidate_id"] for x in ranked_display[tier]):
            continue
        already = visible.get(c["fight_key"], [])
        if any(x["tier"] == tier for x in already):
            continue
        if any(
            x["market_spec"] == c["market_spec"] or not can_both_win(
                x["market_spec"], c["market_spec"], scheduled_rounds=c["scheduled_rounds"]
            )
            for x in already
        ):
            continue
        view = dict(c)
        view["status"] = "PASS_RESEARCH_ONLY_NOT_APPROVED_OR_BETTABLE"
        view["nonapproval_reasons"] = rejected_reasons.get(c["candidate_id"], [
            "not_selected_under_five_selection_limit",
        ])
        ranked_display[tier].append(view)
        visible.setdefault(c["fight_key"], []).append(view)

    same_fight_pairs = [
        (key, picks) for key, picks in selected_by_fight.items() if len(picks) == 2
    ]
    if any(len(picks) > 2 or picks[0]["tier"] == picks[1]["tier"] or not can_both_win(
        picks[0]["market_spec"], picks[1]["market_spec"],
        scheduled_rounds=picks[0]["scheduled_rounds"]
    ) for _, picks in same_fight_pairs):
        raise RuntimeError("Unsafe same-fight allocation in official categories")
    payload = {
        "schema_version": "2.0",
        "policy_version": "WSHL_X_UFC_TOP5_COMPATIBLE_SAME_FIGHT_EFFECTIVE_2026-11-07",
        "event": event, "event_date": event_date,
        "stage": "B_FANDUEL_ONLY_TWO_INDEPENDENT_TOP5_STRAIGHT_CARDS",
        "stage_a_sha256": stage_a_sha256,
        "stage_a_frozen_odds_blind": True,
        "generated_at_utc": now.isoformat(),
        "category_definition": {
            LONGSHOTS: "FanDuel +200 and longer, max 5; no forced picks",
            BEST_BETS: "FanDuel -150 through +190 inclusive, max 5; no forced picks",
        },
        "allocation_policy": "Globally sort gate-approved candidates by conservative EV, edge, reliability; max one pick per fight within each tier. Cross-tier same-fight picks permitted ONLY when independently typed market outcomes can both settle WIN; conflicting or identical outcomes blocked.",
        "gates_required": list(GATES),
        "selected": selected,
        "ranked_display": ranked_display,
        "rejected": rejected,
        "counts": {k: len(selected[k]) for k in TIERS},
        "display_counts": {k: len(ranked_display[k]) for k in TIERS},
        "selected_total": sum(len(selected[tier]) for tier in TIERS),
        "distinct_fights_selected": len(selected_by_fight),
        "same_fight_compatible_pairs": len(same_fight_pairs),
        "no_duplicate_or_conflicting_selections": True,
        "same_fight_correlation_warning": True,
        "bets_placed_not_asserted": True,
        "note": "Display can contain PASS research candidates up to five per tier even when there are ZERO approved bets. Same-fight compatible wagers remain correlated. No proof of actual wager placement or profitability.",
    }
    return payload


def grade_two_tier(
    card: Mapping[str, Any],
    results_by_candidate_id: Mapping[str, str],
) -> dict[str, Any]:
    """Grade frozen cards separately; WIN/LOSS/PUSH/VOID or pending.

    Profit and exposure count only settled W/L wagers. A push/void returns
    the stake and contributes 0 units; pending stakes are not prematurely
    included in ROI. This is an official-model-card grade, not evidence
    that a person placed a real wager.
    """
    allowed = {"W", "L", "PUSH", "VOID"}
    selected = card["selected"]
    all_rows = [r for tier in TIERS for r in selected[tier]]
    ids = [r["candidate_id"] for r in all_rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate candidate across frozen categories")
    per_fight: dict[str, list[dict[str, Any]]] = {}
    for tier in TIERS:
        for r in selected[tier]:
            if tier_for_odds(r["american_odds"]) != tier:
                raise ValueError("Selected market in wrong odds category")
            spec = validate_market_spec(r.get("market_spec"),
                                        market_family=r["market_family"],
                                        scheduled_rounds=r.get("scheduled_rounds"))
            if spec != r["market_spec"]:
                raise ValueError("Tampered market_spec")
            prior = per_fight.get(r["fight_key"], [])
            if any(x["tier"] == tier for x in prior):
                raise ValueError("Two bets in same tier from same fight")
            if any(x["market_spec"] == spec or not can_both_win(
                x["market_spec"], spec, scheduled_rounds=r["scheduled_rounds"]
            ) for x in prior):
                raise ValueError("Same-fight Top5 picks are duplicated or conflicting")
            per_fight.setdefault(r["fight_key"], []).append({"tier": tier, "market_spec": spec})
    if len(selected[LONGSHOTS]) > 5 or len(selected[BEST_BETS]) > 5:
        raise ValueError("Category exceeded 5 selections")
    unknown = set(results_by_candidate_id) - set(ids)
    if unknown:
        raise ValueError(f"Results contain unselected candidate IDs: {sorted(unknown)}")

    groups, all_graded = {}, []
    for tier in TIERS:
        graded = []
        counts = {"W": 0, "L": 0, "PUSH": 0, "VOID": 0, "PENDING": 0}
        risk = pnl = 0.0
        for r in selected[tier]:
            result = results_by_candidate_id.get(r["candidate_id"], "PENDING")
            if result != "PENDING" and result not in allowed:
                raise ValueError(f"Unsupported outcome {result!r}")
            units = float(r["stake_units"])
            p = units * net_profit_per_unit(int(r["american_odds"])) if result == "W" else (
                -units if result == "L" else 0.0
            )
            if result in {"W", "L"}:
                risk += units
            pnl += p
            counts[result] += 1
            graded.append({
                "candidate_id": r["candidate_id"], "fight_key": r["fight_key"],
                "market": r["market"], "american_odds": r["american_odds"],
                "stake_units": units, "result": result, "profit_units": p,
            })
        groups[tier] = {
            "selected": len(selected[tier]), "record": counts,
            "settled_risk_units": risk, "pnl_units": pnl,
            "roi": pnl / risk if risk else None,
            "grades": graded,
        }
        all_graded.extend(graded)
    risk = sum(groups[k]["settled_risk_units"] for k in TIERS)
    pnl = sum(groups[k]["pnl_units"] for k in TIERS)
    return {
        "schema_version": "2.0", "event": card["event"],
        "event_date": card["event_date"], "stage_a_sha256": card["stage_a_sha256"],
        "categories": groups,
        "combined": {
            "graded_selections": len(all_graded),
            "distinct_fights": len(per_fight),
            "compatible_same_fight_pairs": sum(len(x) == 2 for x in per_fight.values()),
            "W": sum(groups[k]["record"]["W"] for k in TIERS),
            "L": sum(groups[k]["record"]["L"] for k in TIERS),
            "PUSH": sum(groups[k]["record"]["PUSH"] for k in TIERS),
            "VOID": sum(groups[k]["record"]["VOID"] for k in TIERS),
            "PENDING": sum(groups[k]["record"]["PENDING"] for k in TIERS),
            "settled_risk_units": risk, "pnl_units": pnl, "roi": pnl / risk if risk else None,
        },
        "not_claiming_real_wager_placement": True,
    }
