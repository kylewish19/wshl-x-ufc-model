"""UFC334 Unified exact-method 13-fight prospectively frozen / 12 priced research track."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"data/locks/ufc334_2026-11-14"
QUOTE=ROOT/"data/quotes/ufc334_2026-11-14_fanduel_user_screenshots.json"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_unified_fighter_method_stored_before_fanduel_and_not_posthoc_filtered():
    report=read(DIR/"unified_exact_method_13_picks_12_fanduel_quotes_pending.json")
    frozen=read(DIR/"stage_a_final_selection.json")
    raw=read(DIR/"stage_a_model_raw_three_view.json")
    prices=read(QUOTE)
    assert report["status"]=="PRE_EVENT_UNIFIED_13_FIGHTER_METHOD_FORECASTS_12_PRICEABLE_SHADOWS_PENDING"
    assert report["frozen_stage_a_sha256"]==digest(DIR/"stage_a_final_selection.json")
    assert report["frozen_model_sha256"]==digest(DIR/"stage_a_model_raw_three_view.json")
    assert report["original_fanduel_snapshot_sha256"]==digest(QUOTE)
    assert report["total_prediction_rows"]==13 and report["original_exact_method_price_count"]==12
    assert report["missing_quote_fights"]==[2]
    assert len(report["rows"])==13
    assert report["no_bets_implied"] and report["separate_from_both_top5_tiers"]
    assert report["actual_staked_units"]==report["official_approved_units"]==0
    assert report["hypothetical_current_settled_risk_units"]==0
    assert report["hypothetical_current_net_units"]==0
    assert report["hypothetical_current_roi"] is None
    for i,entry in enumerate(report["rows"],1):
        a=frozen["fights"][i-1]
        r=raw["fights"][i-1]
        q=prices["quoted_markets"][i-1]
        assert entry["fight_no"]==i
        assert entry["model_result"]=="PENDING"
        assert entry["selected_fighter"]==a["winner_views"]["oof_unified_shadow"]["pick"]
        side="a" if entry["selected_fighter"]==a["a"] else "b"
        prefix="A_" if side=="a" else "B_"
        joint=r["oof_unified_shadow"]["joint_method"]
        method=max(["KO","SUB","DEC"],key=lambda x:joint[prefix+x])
        expected="KO_TKO" if method=="KO" else method
        assert entry["selected_method"]==expected
        assert a["method"]["primary_method_forecast_for_grade"]["unified_own_fighter"]==method
        assert entry["original_unified_six_class_joint_probability"]==pytest.approx(joint[prefix+method])
        assert entry["original_unified_conditional_method_probability"]==pytest.approx(
            joint[prefix+method]/sum(joint[prefix+x] for x in ("KO","SUB","DEC")))
        original=None if q["method_of_victory"] is None else q["method_of_victory"][side][expected]
        assert entry["original_fanduel_exact_method_american_odds"]==original
        assert entry["hypothetical_staked_units_if_price_available"]==(0 if original is None else 1)
        assert entry["hypothetical_net_units_to_date"]==0
    assert report["rows"][1]["hypothetical_price_grade_status"]=="NO_METHOD_QUOTE_DONT_INFER_PRICE"
    assert [x["original_fanduel_exact_method_american_odds"] for x in report["rows"]]==[
        180,None,-110,160,155,145,310,480,-310,115,470,200,145
    ]
