"""UFC334 13-fight 334-price Stage B reproducibility and honest research-only gates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from collections import Counter
from math import isfinite

import pytest

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"data/locks/ufc334_2026-11-14"
QUOTES=ROOT/"data/quotes/ufc334_2026-11-14_fanduel_user_screenshots.json"


def read(p):return json.loads(p.read_text())


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def test_all_original_334_quotes_and_missing_props_only_from_source():
    a=read(QUOTES)
    assert a["event_date"]=="2026-11-14"
    assert a["sportsbook"]=="FanDuel"
    assert a["total_markets"]==334
    assert a["modeled_quote_count"]==310 and a["draw_quote_count"]==24
    assert a["complete_displayed_fights"]==12 and a["moneyline_only_fights"]==1
    assert len(a["quoted_markets"])==13
    assert [x["observed_market_count"] for x in a["quoted_markets"]]==[27,2]+[27]*9+[31,31]
    for i,quote in enumerate(a["quoted_markets"],1):
        assert quote["fight_no"]==i
        assert quote["odds_used_in_stage_a"] is False
        assert quote["sportsbook"]=="FanDuel"
        assert quote["observed_market_count"]==a["source_receipts"][str(i)]["posted_market_count"]
        assert sha(ROOT/a["source_receipts"][str(i)]["file"])==a["source_receipts"][str(i)]["sha256"]
    second=a["quoted_markets"][1]
    assert second["a"]=="Alatengheili" and second["b"]=="Juan Diaz"
    assert second["moneyline"]=={"a":265,"b":-370}
    assert all(second[k] is None for k in ("method_of_victory","double_chance","goes_distance",
                                           "total_rounds","how_fight_ends","round_to_start"))
    assert a["quoted_markets"][5]["total_rounds"]=={"threshold":0.5,"OVER":-230,"UNDER":186}
    assert a["quoted_markets"][11]["total_rounds"]=={"threshold":3.5,"OVER":104,"UNDER":-126}
    assert a["quoted_markets"][12]["moneyline"]=={"a":-188,"b":144}
    assert a["quoted_markets"][12]["round_to_start"]["5"]=={"YES":150,"NO":-192}


def test_full_market_audit_all_334_model_refs_still_original_and_no_approved_bets():
    a=read(DIR/"stage_b_all_334_fanduel_prices_audit.json")
    frozen=read(DIR/"stage_a_final_selection.json")
    assert a["stage_a_original_sha256"]==sha(DIR/"stage_a_final_selection.json")
    assert a["all_quotes_sha256"]==sha(QUOTES)
    assert a["raw_model_sha256"]==sha(DIR/"stage_a_model_raw_three_view.json")
    assert frozen["stage_a_frozen"] is True and frozen["odds_used"] is False
    assert len(a["all_334_markets"])==334
    assert a["completeness"]["unique_fights"]==13
    assert sum(x["raw_current_probability"] is None for x in a["all_334_markets"])==24
    assert sum(x["raw_current_probability"] is not None for x in a["all_334_markets"])==310
    assert a["completeness"]["quotes"]==334
    for item in a["all_334_markets"]:
        assert not item["approved_official"]
        assert item["american_odds"]>=100 or item["american_odds"]<=-100
        assert item["break_even_probability"]==pytest.approx(
            100/(100+item["american_odds"]) if item["american_odds"]>0
            else -item["american_odds"]/(100-item["american_odds"]))
        if item["raw_current_probability"] is not None:
            assert 0<=item["raw_current_probability"]<=1
            assert 0<=item["raw_unified_probability"]<=1
            assert "independent_calibrated_conservative_probability_not_established" in item["block_reasons"]
            assert item["two_view_floor_not_independently_calibrated"] is True
    interesting=[(x["fight_no"],x["market"],x["american_odds"])
                 for x in a["raw_mechanical_gate_pass_candidates"]]
    assert interesting==[(6,"Fight goes distance YES",900),
                         (6,"Round 3 starts YES",640),
                         (8,"Charles Radtke ML",126)]
    assert a["official_approved_card"]["number_official_wagers"]==0
    assert a["official_approved_card"]["official_roi"] is None


def test_frozen_top5_both_real_prices_and_3_compatible_same_fight_pairs():
    from wshlx_ufc.two_tier_card import BEST_BETS,LONGSHOTS,tier_for_odds,fight_key
    from wshlx_ufc.market_compatibility import can_both_win
    watch=read(DIR/"stage_b_top5_ranked_research_review_compatible_cross_tier.json")
    summary=read(DIR/"stage_b_two_tier_outcome.json")
    audit=read(DIR/"stage_b_all_334_fanduel_prices_audit.json")
    assert watch["stage_a_original_sha256"]==sha(DIR/"stage_a_final_selection.json")
    assert watch["full_price_audit_sha256"]==sha(DIR/"stage_b_all_334_fanduel_prices_audit.json")
    assert watch["fanduel_screenshot_sha256"]==sha(QUOTES)
    assert watch["qualified_bets_in_either_category"]==0
    assert watch["stage_a_or_original_stage_b_mutated"] is False
    assert set(watch["categories"])=={BEST_BETS,LONGSHOTS}
    assert all(len(watch["categories"][tier])==5 for tier in (BEST_BETS,LONGSHOTS))
    quoted={(x["fight_no"],x["market"]):x for x in audit["all_334_markets"]}
    seen={}
    for tier in (BEST_BETS,LONGSHOTS):
        category=watch["categories"][tier]
        assert len({item["fight_no"] for item in category})==5
        for i,sel in enumerate(category,1):
            assert sel["rank"]==i
            assert sel["status"]=="PASS_RESEARCH_ONLY_NOT_APPROVED_OR_BETTABLE"
            assert sel["not_in_official_betting_grade"]
            assert sel["sportsbook"]=="FanDuel"
            assert sel["reasons_not_approved"]
            assert sel["raw_unadjusted_ev_per_unit"]>0
            assert sel["raw_min_model_ev_per_unit_unvalidated"]>0
            q=quoted[(sel["fight_no"],sel["market"])]
            assert sel["screenshot_american_odds"]==q["american_odds"]
            assert tier_for_odds(sel["screenshot_american_odds"])==tier
            assert sel["market_spec"]==q["market_spec"]
            k=sel["fight_key"]
            for v in seen.get(k,[]):
                assert v["tier"]!=tier
                assert sel["market_spec"]!=v["market_spec"]
                assert can_both_win(sel["market_spec"],v["market_spec"],
                                    scheduled_rounds=sel["scheduled_rounds"])
            seen.setdefault(k,[]).append({"tier":tier,"market_spec":sel["market_spec"]})
    assert len(seen)==7
    assert len(watch["compatible_same_fight_pairs"])==3
    assert summary["official_betting_stakes_units"]==0
    assert summary["official_betting_roi"] is None
    assert summary["top_5_best_bets"]["research_presented"]==5
    assert summary["top_5_longshots"]["research_presented"]==5
    # Discourage misreporting the +640 Round3 as a preselected Stage A pick.
    r3=next(x for x in watch["categories"][LONGSHOTS] if x["fight_no"]==6)
    assert r3["market"]=="Round 3 starts YES"
    assert r3["stage_a_primary_timing_prediction"]=="Fight goes distance NO"
    assert r3["is_original_primary_timing_market"] is False


def test_both_top5_pending_one_virtual_unit_not_real_money():
    from wshlx_ufc.research_top5_ledger import grade_research_watchlist
    from wshlx_ufc.two_tier_card import BEST_BETS,LONGSHOTS
    card=read(DIR/"stage_b_top5_ranked_research_review_compatible_cross_tier.json")
    ledger=read(DIR/"stage_b_top5_research_units_pending.json")
    regrade=grade_research_watchlist(card)
    assert ledger["frozen_research_watchlist_sha256"]==sha(DIR/"stage_b_top5_ranked_research_review_compatible_cross_tier.json")
    assert ledger["status"]=="PRE_EVENT_PENDING_ONLY_NO_RESULTS"
    assert ledger["combined"]==regrade["combined"]
    assert ledger["combined"]["record"]=={"W":0,"L":0,"PUSH":0,"VOID":0,"PENDING":10}
    assert ledger["combined"]["hypothetical_settled_risk_units"]==0
    assert ledger["combined"]["hypothetical_net_units"]==0
    assert ledger["combined"]["hypothetical_roi"] is None
    for tier in (LONGSHOTS,BEST_BETS):
        assert ledger["categories"][tier]["displayed_candidates"]==5
        assert all(sel["result"]=="PENDING" and sel["hypothetical_profit_units"]==0
                   and sel["is_actual_bet"] is False
                   for sel in ledger["categories"][tier]["selections"])
