"""WSHL_X two separate UFC Top-5 research cards: 1-unit hypothetical P&L.

This NEVER represents wagers actually placed or official approved Stage-B
plays. Those are graded by two_tier_card.grade_two_tier on their own ledger.
No bet can enter this research ledger absent its pre-event frozen candidate
and FanDuel screenshot price. Values are settled 1u straight bet *simulations*
only; account for correlation separately. All updates must be versioned.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from wshlx_ufc.two_tier_card import BEST_BETS, LONGSHOTS, TIERS, tier_for_odds, net_profit_per_unit
from wshlx_ufc.market_compatibility import validate_market_spec, can_both_win

OUTCOMES = ("W", "L", "PUSH", "VOID", "PENDING")
HYPOTHETICAL_STAKE_UNITS = 1.0


def candidate_id(tier: str, rank: int, fight_no: int) -> str:
    """Stable identifier tied to immutable top-five card position and fight."""
    if tier not in TIERS or type(rank) is not int or not 1 <= rank <= 5 or type(fight_no) is not int or not 1 <= fight_no <= 25:
        raise ValueError("Invalid tier/rank/fight identity")
    return f"{tier}:{rank}:{fight_no}"


def _validated_pre_event_rows(card: Mapping[str, Any]) -> dict[str, list[dict]]:
    if card.get("report_type") != "POST_PRICE_RANKED_FANDUEL_TWO_TIER_RESEARCH_WATCHLIST":
        raise ValueError("Expected WSHL_X frozen two-tier research watchlist")
    if card.get("stage_a_or_original_stage_b_mutated") is not False:
        raise ValueError("Historical Stage A and Stage B immutability must be preserved")
    if card.get("qualified_bets_in_either_category") != 0:
        raise ValueError("This ledger may not substitute for official bet grading")
    if not isinstance(card.get("event_date"), str) or not card.get("event"):
        raise ValueError("Event identity required")
    src = card.get("categories")
    if not isinstance(src, dict) or set(src) != set(TIERS):
        raise ValueError("Both research categories must be present")
    output = {}
    bouts: dict[str, list[dict]] = {}
    for tier in TIERS:
        rows = src[tier]
        if not isinstance(rows, list) or len(rows) > 5:
            raise ValueError("Each category contains at most five pre-fight research picks")
        output[tier] = []
        ids_in_fight = set()
        for i, row in enumerate(rows, 1):
            if row.get("rank") != i:
                raise ValueError("Ranking must not be shuffled after pre-event freeze")
            no = row.get("fight_no")
            cid = candidate_id(tier, i, no)
            if row.get("sportsbook") != "FanDuel":
                raise ValueError("Only original FanDuel prices may enter this research ledger")
            odds = row.get("screenshot_american_odds")
            if tier_for_odds(odds) != tier:
                raise ValueError("Historical odds fall outside category")
            if row.get("status") != "PASS_RESEARCH_ONLY_NOT_APPROVED_OR_BETTABLE":
                raise ValueError("Watchlist may only contain clearly marked research-only picks")
            if row.get("not_in_official_betting_grade") is not True:
                raise ValueError("Cannot count research as official graded exposure")
            key = row.get("fight_key")
            if not isinstance(key, str) or not key or key in ids_in_fight:
                raise ValueError("Duplicate fight inside one research tier")
            ids_in_fight.add(key)
            spec = row.get("market_spec")
            if not isinstance(spec, dict):
                raise ValueError("Explicit market specification required")
            families = {"moneyline": "moneyline", "method": "method", "double_chance": "double_chance",
                        "goes_distance": "timing", "total_rounds": "timing",
                        "round_to_start": "timing", "fight_end_method": "method"}
            family = families.get(spec.get("kind"))
            if family is None:
                raise ValueError("Unsupported research market")
            # We validate event 3/5 rounds from this card's market type;
            # a valid posted R4/R5 prop must have an explicit rounds field.
            rounds = row.get("scheduled_rounds", 3)
            if type(rounds) is not int or rounds not in (3, 5):
                raise ValueError("Unsupported scheduled round count")
            norm = validate_market_spec(spec, market_family=family, scheduled_rounds=rounds)
            for other in bouts.get(key, []):
                if other["tier"] == tier or norm == other["spec"] or not can_both_win(
                    norm, other["spec"], scheduled_rounds=max(rounds, other["rounds"])
                ):
                    raise ValueError("Research entries in different tiers conflict or duplicate")
            bouts.setdefault(key, []).append({"tier": tier, "spec": norm, "rounds": rounds})
            output[tier].append({
                "candidate_id": cid, "rank": i, "fight_no": no,
                "fight": row["fight"], "fight_key": key,
                "market": row["market"], "market_spec": norm,
                "american_odds": odds,
                "status": "RESEARCH_ONLY_NOT_AN_APPROVED_BET",
            })
    return output


def grade_research_watchlist(
    card: Mapping[str, Any],
    results: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Compute settled *hypothetical* units, never actual recorded wagers.

    Unsettled candidates default to PENDING; pending, push and void add zero
    realized research P/L and are not included in settled risk/ROI denominator.
    Grades are applied only after verified external outcome data is supplied
    to the CLI and matched by immutable watchlist + quote-file SHA.
    """
    results = results or {}
    rows = _validated_pre_event_rows(card)
    valid_ids = {r["candidate_id"] for tier in TIERS for r in rows[tier]}
    if set(results) - valid_ids:
        raise ValueError("Untracked candidate in result input")
    if any(outcome not in OUTCOMES for outcome in results.values()):
        raise ValueError("Only W/L/PUSH/VOID/PENDING settlements allowed")
    summaries = {}
    for tier in TIERS:
        record = {k: 0 for k in OUTCOMES}
        total_pnl = risk = 0.0
        entries = []
        for row in rows[tier]:
            outcome = results.get(row["candidate_id"], "PENDING")
            record[outcome] += 1
            risk += HYPOTHETICAL_STAKE_UNITS if outcome in ("W", "L") else 0
            pnl = (HYPOTHETICAL_STAKE_UNITS * net_profit_per_unit(row["american_odds"])
                   if outcome == "W" else
                   -HYPOTHETICAL_STAKE_UNITS if outcome == "L" else 0.0)
            total_pnl += pnl
            entries.append({
                **row, "result": outcome, "hypothetical_stake_units": HYPOTHETICAL_STAKE_UNITS,
                "hypothetical_profit_units": round(pnl, 6),
                "is_actual_bet": False,
            })
        summaries[tier] = {
            "displayed_candidates": len(rows[tier]),
            "record": record,
            "hypothetical_settled_risk_units": risk,
            "hypothetical_net_units": round(total_pnl, 6),
            "hypothetical_roi": total_pnl / risk if risk else None,
            "selections": entries,
        }
    total_risk = sum(v["hypothetical_settled_risk_units"] for v in summaries.values())
    total_pnl = sum(v["hypothetical_net_units"] for v in summaries.values())
    return {
        "schema_version": "1.0",
        "ledger_type": "TWO_TIER_RESEARCH_ONLY_HYPOTHETICAL_ONE_UNIT_PER_PICK",
        "event": card["event"],
        "event_date": card["event_date"],
        "basis": "Original screenshot FanDuel prices; separate from approved bets and real money",
        "default_hypothetical_stake_units": HYPOTHETICAL_STAKE_UNITS,
        "quoted_market_prices_may_change": True,
        "categories": summaries,
        "combined": {
            "displayed_candidates": sum(len(rows[tier]) for tier in TIERS),
            "record": {x: sum(s["record"][x] for s in summaries.values()) for x in OUTCOMES},
            "hypothetical_settled_risk_units": total_risk,
            "hypothetical_net_units": round(total_pnl, 6),
            "hypothetical_roi": total_pnl / total_risk if total_risk else None,
        },
        "approved_betting_stakes_not_conflated": True,
        "same_fight_selections_can_be_correlated": True,
    }
