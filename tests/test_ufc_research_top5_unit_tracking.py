"""Non-fabricated odds, 1u hypothetical P&L and separate two-tier tracking."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from wshlx_ufc.research_top5_ledger import candidate_id, grade_research_watchlist
from wshlx_ufc.two_tier_card import LONGSHOTS, BEST_BETS

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"data/locks/ufcvegas124_2026-11-07/stage_b_top5_ranked_research_review_compatible_cross_tier.json"


def snapshot():
    return json.loads(PATH.read_text())


def test_pending_baseline_tracks_both_5_odds_without_fake_stakes():
    card=snapshot()
    tracked=grade_research_watchlist(card)
    assert card["qualified_bets_in_either_category"]==0
    assert tracked["ledger_type"]=="TWO_TIER_RESEARCH_ONLY_HYPOTHETICAL_ONE_UNIT_PER_PICK"
    assert tracked["approved_betting_stakes_not_conflated"] is True
    assert tracked["same_fight_selections_can_be_correlated"] is True
    assert tracked["combined"]["displayed_candidates"]==10
    assert tracked["combined"]["record"]["PENDING"]==10
    assert tracked["combined"]["hypothetical_settled_risk_units"]==0
    assert tracked["combined"]["hypothetical_net_units"]==0
    assert tracked["combined"]["hypothetical_roi"] is None

    assert [r["american_odds"] for r in tracked["categories"][LONGSHOTS]["selections"]] == [240,230,400,360,460]
    assert [r["american_odds"] for r in tracked["categories"][BEST_BETS]["selections"]] == [100,188,188,-110,132]
    for tier in (LONGSHOTS,BEST_BETS):
        group=tracked["categories"][tier]
        assert group["displayed_candidates"]==5
        assert group["record"]=={"W":0,"L":0,"PUSH":0,"VOID":0,"PENDING":5}
        for original, graded in zip(card["categories"][tier], group["selections"]):
            assert graded["candidate_id"]==candidate_id(tier,original["rank"],original["fight_no"])
            assert graded["american_odds"]==original["screenshot_american_odds"]
            assert graded["hypothetical_stake_units"]==1
            assert graded["hypothetical_profit_units"]==0
            assert graded["is_actual_bet"] is False


def test_proper_pnl_for_plus_and_minus_american_odds_with_push_void_pending():
    card=snapshot()
    results={
        candidate_id(LONGSHOTS,1,13):"W",  # +240 -> +2.40u
        candidate_id(LONGSHOTS,2,4):"L",  # +230 -> -1u
        candidate_id(LONGSHOTS,3,3):"PUSH",
        candidate_id(BEST_BETS,4,4):"W",  # -110 -> +0.909091u
        candidate_id(BEST_BETS,1,5):"L",  # +100 -> -1u
        candidate_id(BEST_BETS,2,1):"VOID",
    }
    grade=grade_research_watchlist(card,results)
    long=grade["categories"][LONGSHOTS]
    best=grade["categories"][BEST_BETS]
    assert long["record"]=={"W":1,"L":1,"PUSH":1,"VOID":0,"PENDING":2}
    assert long["hypothetical_settled_risk_units"]==2
    assert long["hypothetical_net_units"]==pytest.approx(1.4)
    assert long["hypothetical_roi"]==pytest.approx(0.7)
    assert best["record"]=={"W":1,"L":1,"PUSH":0,"VOID":1,"PENDING":2}
    assert best["hypothetical_settled_risk_units"]==2
    assert best["hypothetical_net_units"]==pytest.approx(-1+100/110,abs=1e-6)
    assert best["hypothetical_roi"]==pytest.approx((-1+100/110)/2,abs=1e-6)
    assert grade["combined"]["hypothetical_settled_risk_units"]==4
    assert grade["combined"]["hypothetical_net_units"]==pytest.approx(1.4-1+100/110,abs=1e-6)


@pytest.mark.parametrize("alter",[
    lambda c: c["categories"][LONGSHOTS][0].update(sportsbook="BetMGM"),
    lambda c: c["categories"][LONGSHOTS][0].update(screenshot_american_odds=155),
    lambda c: c["categories"][LONGSHOTS][0].update(rank=2),
    lambda c: c["categories"][LONGSHOTS][0].update(status="OFFICIAL_TWO_TIER_STRAIGHT"),
    lambda c: c["categories"][LONGSHOTS][0].update(not_in_official_betting_grade=False),
    lambda c: c.update(qualified_bets_in_either_category=1),
])
def test_corrupted_frozen_research_cards_fail_closed(alter):
    card=snapshot()
    alter(card)
    with pytest.raises(ValueError):
        grade_research_watchlist(card)


def test_unknown_candidate_id_and_unverified_result_rejected():
    card=snapshot()
    with pytest.raises(ValueError):
        grade_research_watchlist(card,{"unknown-id":"W"})
    with pytest.raises(ValueError):
        grade_research_watchlist(card,{candidate_id(LONGSHOTS,1,13):"UNVERIFIED"})
    assert len(hashlib.sha256(PATH.read_bytes()).hexdigest())==64


def test_same_fight_cross_tier_matches_can_both_win_before_tracking():
    card=snapshot()
    all_rows=[x for tier in (LONGSHOTS,BEST_BETS) for x in card["categories"][tier]]
    assert len({x["fight_key"] for x in all_rows})==7
    assert len(card["compatible_same_fight_pairs"])==3
    g=grade_research_watchlist(card)
    assert g["categories"][LONGSHOTS]["selections"][3]["fight_no"]==5
    assert g["categories"][BEST_BETS]["selections"][0]["fight_no"]==5
    hacked=deepcopy(card)
    hacked["categories"][LONGSHOTS][3]["market_spec"]={"kind":"method","side":"a","method":"SUB"}
    with pytest.raises(ValueError):
        grade_research_watchlist(hacked)
