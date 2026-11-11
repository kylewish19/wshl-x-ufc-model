"""Prospective UFC334 Nov14 13-fight Stage A guardrails.

Only the frozen pre-event JSON is inspected here; never substitute sportsbook
price values, actual bout results, model coefficients, or manual flips.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"data/locks/ufc334_2026-11-14"


def read(filename):
    return json.loads((DIR/filename).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def conditional(joint,prefix):
    return {m:joint[f"{prefix}_{m}"]/
            sum(joint[f"{prefix}_{t}"] for t in ("KO","SUB","DEC"))
            for m in ("KO","SUB","DEC")}


def test_13_unique_preprice_event_bouts_with_two_5round_titles():
    a=read("stage_a_final_selection.json")
    raw=read("stage_a_model_raw_three_view.json")
    audit=read("stage_a_final_audit.json")
    assert len(a["fights"])==len(raw["fights"])==audit["fights"]==13
    assert a["stage_a_frozen"] and a["odds_used"] is False
    assert raw["stage_a_frozen"] is False and raw["odds_used"] is False
    assert a["raw_model_sha256"]==sha(DIR/"stage_a_model_raw_three_view.json")
    assert audit["raw_model_sha256"]==a["raw_model_sha256"]
    assert a["event"]==raw["event"]=="UFC 334: Gane vs Hokit"
    assert a["event_date"]=="2026-11-14"
    assert a["research"]["missing_user_screenshot_fight_added_from_UFC_official_event"]=="Stephen Thompson vs Charles Radtke"
    assert a["research"]["original_user_unique_screenshots"]==12
    assert a["research"]["cancelled_bout_excluded"]=="Nazim Sadykhov vs Jefferson Nascimento"
    assert {i["fight_no"] for i in a["fights"]}==set(range(1,14))
    assert len({frozenset((i["a"],i["b"])) for i in a["fights"]})==13
    assert sum(i["scheduled_rounds"]==5 for i in a["fights"])==2
    assert [(x["a"],x["b"]) for x in a["fights"] if x["scheduled_rounds"]==5]==[
        ("Kayla Harrison","Amanda Nunes"),("Ciryl Gane","Josh Hokit")
    ]
    assert len([r for r in a["fights"] if r["stage_a_posture"]=="PASS"])==8
    assert audit["winner_disagreements"]==[1,3,11,13]


def test_model_source_lineage_unmodified_and_numeric_views_valid():
    a=read("stage_a_final_selection.json")
    raw=read("stage_a_model_raw_three_view.json")
    assert a["governance"]["model_reference_weights_fit_through"]=="2026-09-12"
    assert a["governance"]["current_shadows_fit_through"]=="2026-11-07"
    assert a["governance"]["historical_winner_shadow_fit_through"]=="2026-11-07"
    assert a["governance"]["historical_method_timing_fit_through"]=="2026-10-17"
    assert a["governance"]["oof_unified_weights_fit_cutoff"]=="2026-10-17"
    assert a["governance"]["challenger_promoted"] is False
    assert a["governance"]["odds_influenced_stage_a"] is False
    assert a["governance"]["no_method_bets_approved"] is True
    assert a["governance"]["no_timing_bets_approved"] is True
    for f,r in zip(a["fights"],raw["fights"]):
        assert f["a"]==r["a"] and f["b"]==r["b"] and f["fight_no"]==r["fight_no"]
        assert f["official_reference_pick"]==r["winner_reference_pick"]
        for k,raw_p in (
            ("reference",r["winner_reference_p_a"]),
            ("historical_shadow",r["historical_shadow"]["winner_p_a"]),
            ("oof_unified_shadow",r["oof_unified_shadow"]["winner_p_a"]),
        ):
            pred=f["winner_views"][k]
            assert pred["pick"] in (r["a"],r["b"])
            assert 0<=pred["probability"]<=1
            assert pred["probability"]==pytest.approx(raw_p if pred["pick"]==r["a"] else 1-raw_p)
        for model in ("historical_shadow","oof_unified_shadow"):
            assert sum(r[model]["joint_method"].values())==pytest.approx(1,abs=1e-7)
        assert sum(r["joint_calibrated"].values())==pytest.approx(1,abs=1e-7)
        assert f["tape_provenance"]["classification"]!="CONTINUOUS_FULL_FIGHT_REVIEWED"
        assert f["method"]["official_method_if_any"] is None


def test_each_model_own_fighter_method_not_reference_if_side_differs():
    a=read("stage_a_final_selection.json")
    raw=read("stage_a_model_raw_three_view.json")
    disagreement_count=0
    for f,r in zip(a["fights"],raw["fights"]):
        own=f["method"]["primary_method_forecast_for_grade"]
        assert own["all_three_model_methods_use_their_own_selected_fighter"]
        current=f["method"]["current_conditional_if_official_winner"]
        assert own["reference"]==("KO/TKO" if max(current,key=current.get)=="KO"
                                   else max(current,key=current.get))
        for title,view in (("historical_own_fighter","historical_shadow"),
                           ("unified_own_fighter","oof_unified_shadow")):
            pred=f["winner_views"][view]["pick"]
            prefix="A" if pred==f["a"] else "B"
            method=conditional(r[view]["joint_method"],prefix)
            assert own[title]==max(method,key=method.get)
            if pred!=f["official_reference_pick"]:
                disagreement_count+=1
        assert f["method"]["betting_status"].startswith("UNPRICED")
    assert disagreement_count==7  # 3 full shadow disagreements + 1 historical-only


def test_one_primary_timing_frozen_per_fight_with_no_prices():
    a=read("stage_a_final_selection.json")
    audit=read("stage_a_final_audit.json")
    assert audit["primary_timing_per_fight"]==13
    assert audit["method_vs_timing_discrepancy_over_15pp"]==[1,2,3,4,7,11]
    allowed={
        "GTD_YES","GTD_NO","OVER_1.5","UNDER_1.5",
        "OVER_2.5","UNDER_2.5","ROUND_3_STARTS_YES","ROUND_3_STARTS_NO"
    }
    for f in a["fights"]:
        p=f["primary_timing_forecast"]
        assert p["market_key"] in allowed
        assert p["stage_a_primary_timing_for_grade"]
        assert p["selected_pre_fanduel_prop_prices"]
        assert p["not_a_betting_recommendation"]
        candidates={
            key:min(f["timing_current"]["sim_10000"][key],
                    f["timing_oof_unified_shadow"]["sim_10000"][key])
            for key in allowed
        }
        assert p["min_two_model_probability"]==pytest.approx(max(candidates.values()))
        assert p["current_probability"]==f["timing_current"]["sim_10000"][p["market_key"]]
        assert p["unified_shadow_probability"]==f["timing_oof_unified_shadow"]["sim_10000"][p["market_key"]]
        assert 0<=p["min_two_model_probability"]<=1
