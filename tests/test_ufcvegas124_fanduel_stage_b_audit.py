"""Nov 7 2026: 14 fights / 378 actual user FanDuel quoted markets.

Bets must never be invented from apparent raw EV. The frozen odds-blind
Stage A and failure reasons are independent, verifiable artifact contracts.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

from wshlx_ufc.two_tier_card import LONGSHOTS, BEST_BETS, break_even, tier_for_odds

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"data/locks/ufcvegas124_2026-11-07"
QUOTES=ROOT/"data/quotes/ufcvegas124_2026-11-07_fanduel_user_screenshots.json"


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_snapshot_matches_all_frozen_fights_and_book():
    q=load(QUOTES)
    freeze=load(DIR/"stage_a_final_selection.json")
    assert q["sportsbook"]=="FanDuel" and q["event_date"]=="2026-11-07"
    assert q["fight_count"]==14
    assert len(q["quoted_markets"])==len(freeze["fights"])==14
    assert freeze["stage_a_frozen"] and not freeze["odds_used"]
    for row,locked in zip(q["quoted_markets"],freeze["fights"]):
        assert row["fight_no"]==locked["fight_no"]
        assert (row["a"],row["b"])==(locked["a"],locked["b"])
        assert row["method_of_victory"]["DRAW"]==5000
        assert row["double_chance"]["DRAW"]==5000
    assert q["quoted_markets"][1]["moneyline"]["a"]==-720
    assert q["quoted_markets"][12]["moneyline"]["a"]==-200
    assert q["quoted_markets"][13]["moneyline"]["b"]==190
    assert q["quoted_markets"][2]["total_rounds"] is None
    assert q["quoted_markets"][7]["total_rounds"] is None
    assert set(q["quoted_markets"][13]["round_to_start"])=={"2","3","4","5"}
    assert q["exact_quote_timestamp_utc"] is None


def test_full_market_audit_378_prices_no_fabricated_draw_probabilities():
    audit=load(DIR/"stage_b_fanduel_full_price_audit.json")
    assert audit["source_quotes_sha256"]==sha(QUOTES)
    assert audit["stage_a_sha256"]==sha(DIR/"stage_a_final_selection.json")
    assert audit["raw_model_sha256"]==sha(DIR/"stage_a_model_raw_three_view.json")
    assert audit["odds_source"].startswith("User-supplied")
    assert audit["sportsbook"]=="FanDuel"
    assert audit["exact_quote_timestamp_utc"] is None
    c=audit["completeness"]
    assert c["fight_count"]==14
    assert c["quoted_market_prices"]==378
    assert c["modeled_market_prices"]==350
    assert c["unmodeled_draw_quote_prices"]==28
    assert len(audit["all_market_comparisons"])==378
    assert len(c["missing_markets_not_inferred"])==3
    rows=audit["all_market_comparisons"]
    draw=[x for x in rows if x["market"].startswith("Draw:")]
    assert len(draw)==28
    assert all(x["raw_model_probability"] is None and "no_draw_model_probability" in x["block_reasons"] for x in draw)
    for row in rows:
        assert row["tier"]==tier_for_odds(row["american_odds"])
        assert row["break_even"]==break_even(row["american_odds"])
        if row["raw_model_probability"] is not None:
            assert 0<=row["raw_model_probability"]<=1
            assert math.isfinite(row["raw_ev_per_unit"])


def test_no_fight_overlap_no_forced_plus200_or_best_bets():
    summary=load(DIR/"stage_b_two_tier_outcome.json")
    audit=load(DIR/"stage_b_fanduel_full_price_audit.json")
    assert summary["quotes_count"]==378
    assert summary["quotes_sha256"]==sha(QUOTES)
    assert summary["stage_a_sha256"]==sha(DIR/"stage_a_final_selection.json")
    assert summary["top_5_longshots"]["selected"]==[]
    assert summary["top_5_best_bets"]["selected"]==[]
    assert summary["no_overlap"] and summary["no_forced_bets"]
    assert summary["optional_favorite_2leg"] is None
    assert summary["optional_favorite_3leg"] is None
    assert summary["official_straight_bets_within_top5_tiers"]==[]
    assert not any(x["eligible"] for x in audit["all_market_comparisons"])
    assert summary["model_or_fight_side_flips"]==0


def test_odds_favorites_and_screenshot_value_traps_are_flagged():
    audit=load(DIR/"stage_b_fanduel_full_price_audit.json")
    rows=audit["all_market_comparisons"]
    def market(n,name):
        m=[x for x in rows if x["fight_no"]==n and x["market"]==name]
        assert len(m)==1
        return m[0]

    ko=market(2,"Seokhyeon Ko ML")
    assert ko["american_odds"]==-720
    assert ko["raw_probability_edge_pp"]<-16
    assert not ko["eligible"]

    suarez=market(13,"Tatiana Suarez ML")
    assert suarez["american_odds"]==-200
    assert suarez["raw_probability_edge_pp"]>9
    assert suarez["block_reasons"]==["outside_requested_price_bands"]

    parsons=market(1,"Jonny Parsons ML")
    assert parsons["american_odds"]==188
    assert parsons["raw_probability_edge_pp"]>30
    assert parsons["block_reasons"]==["stage_a_research_pass"]

    mago=market(5,"Murtazali Magomedov by SUB")
    assert "official_method_doublechance_family_blocked_by_stage_a_coherence" in mago["block_reasons"]

    smith=market(12,"Fight goes distance YES")
    assert smith["american_odds"]==132
    assert smith["raw_probability_edge_pp"]>19
    assert "timing_and_method_finish_models_disagree_gt_15pp" in smith["block_reasons"]

    nina=market(10,"Fight goes distance YES")
    assert nina["raw_probability_edge_pp"]>34
    assert "sparse_ufc_history_blocks_timing" in nina["block_reasons"]

    grant=market(12,"Davey Grant ML")
    assert "oppose_frozen_reference_side_price_cannot_flip" in grant["block_reasons"]

    assert len(audit["raw_positive_ev_but_rejected_watchlist"][LONGSHOTS])==5
    assert len(audit["raw_positive_ev_but_rejected_watchlist"][BEST_BETS])==5
