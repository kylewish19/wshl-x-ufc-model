"""One timing forecast per UFC Vegas 124 fight, chosen before outcomes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.select_ufcvegas124_single_timing_picks import get_candidates

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"data/locks/ufcvegas124_2026-11-07"
QUOTES=ROOT/"data/quotes/ufcvegas124_2026-11-07_fanduel_user_screenshots.json"


def _read(p):
    return json.loads(p.read_text())


def _digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_single_timing_pre_fight_research_forecast_per_bout():
    saved=_read(DIR/"stage_b_one_timing_forecast_per_fight.json")
    locked=_read(DIR/"stage_a_final_selection.json")
    quote=_read(QUOTES)
    full=_read(DIR/"stage_b_fanduel_full_price_audit.json")
    assert locked["stage_a_frozen"] and locked["odds_used"] is False
    assert saved["post_price_research_selection"] is True
    assert saved["stage_a_historically_locked_timing_pick"] is False
    assert saved["research_fight_count"]==14
    assert saved["official_timing_bets_approved"]==0
    assert saved["not_included_in_top5_two_tier_bets"] is True
    assert saved["grade_these_predictions_separately_not_as_placed_bets"] is True
    assert saved["original_stage_a_sha256"]==_digest(DIR/"stage_a_final_selection.json")
    assert saved["snapshot_fanduel_quote_sha256"]==_digest(QUOTES)
    assert saved["full_stage_b_price_audit_sha256"]==_digest(DIR/"stage_b_fanduel_full_price_audit.json")
    assert len(saved["fights"])==len(locked["fights"])==len(quote["quoted_markets"])==14
    assert [x["fight_no"] for x in saved["fights"]]==list(range(1,15))
    for forecast, lock, screenshot in zip(saved["fights"],locked["fights"],quote["quoted_markets"]):
        assert forecast["fight"]==f'{lock["a"]} vs {lock["b"]}'
        assert forecast["original_stage_a_posture"]==lock["stage_a_posture"]
        assert not forecast["stage_b_timing_market_approved"]
        options=get_candidates(lock,screenshot)
        expected=sorted(options,key=lambda v:(
            -v["two_model_min_probability"],-v["current_simulated_probability"],v["market"]
        ))[0]
        for field in ("market","group","metric","two_model_min_probability",
                      "current_simulated_probability","unified_shadow_simulated_probability"):
            assert forecast[field]==expected[field]
        assert not forecast["metric"].startswith("ROUND_2_")
        audited=[x for x in full["all_market_comparisons"] if
                 x["fight_no"]==forecast["fight_no"] and x["market"]==forecast["market"]]
        assert len(audited)==1
        assert forecast["fanduel_screenshot_odds"]==audited[0]["american_odds"]
        assert forecast["timing_market_block_reasons"]==audited[0]["block_reasons"]


def test_preflight_one_market_per_fight_snapshot_does_not_depend_on_odds():
    locked=_read(DIR/"stage_a_final_selection.json")
    quote=_read(QUOTES)
    for f,shown in zip(locked["fights"],quote["quoted_markets"]):
        original=get_candidates(f,shown)
        changed=json.loads(json.dumps(shown))
        for key in ("moneyline","double_chance","method_of_victory","goes_distance","round_to_start","how_fight_ends"):
            if key in changed: changed[key]={}  # price fields discarded
        if changed["total_rounds"]:
            changed["total_rounds"]["OVER"]=-9000
            changed["total_rounds"]["UNDER"]=9000
        updated=get_candidates(f,changed)
        assert original==updated, "Selection features must never use price"
