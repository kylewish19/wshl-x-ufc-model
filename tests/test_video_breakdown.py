"""Guardrails for evidence-grounded, non-retroactive UFC video explanations."""
import hashlib
import json
from pathlib import Path

import pytest

from wshlx_ufc.video_breakdown import (
    as_markdown, explain_card, explain_fight, own_method, pct
)

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/locks/ufc334_2026-11-14"


def fixture():
    r = {
        "a": "Alpha", "b": "Beta", "fight_no": 1,
        "joint_calibrated": {"A_KO": .35, "A_SUB": .21, "A_DEC": .14,
                             "B_KO": .05, "B_SUB": .10, "B_DEC": .15},
        "historical_shadow": {"joint_method": {
            "A_KO": .10, "A_SUB": .10, "A_DEC": .20,
            "B_KO": .35, "B_SUB": .15, "B_DEC": .10}},
        "oof_unified_shadow": {"joint_method": {
            "A_KO": .22, "A_SUB": .11, "A_DEC": .22,
            "B_KO": .20, "B_SUB": .15, "B_DEC": .10}},
    }
    f = {
        "a": "Alpha", "b": "Beta", "fight_no": 1,
        "official_reference_pick": "Alpha", "stage_a_posture": "PASS",
        "winner_views": {
            "reference": {"pick": "Alpha", "probability": .7},
            "historical_shadow": {"pick": "Beta", "probability": .6},
            "oof_unified_shadow": {"pick": "Alpha", "probability": .55}},
        "primary_timing_forecast": {
            "market": "Over 1.5 rounds", "current_probability": .6,
            "unified_shadow_probability": .58},
        "evidence_density": {
            "a_age": 29.2, "b_age": 32.5, "a_reach": 72, "b_reach": 74,
            "a_prior_ufc_bouts": 5, "b_prior_ufc_bouts": 12},
        "method_timing_coherence": {
            "method_vs_current_timing_finish_discrepancy_pp": 18.2},
        "tape_provenance": {"classification": "UNAVAILABLE"},
    }
    raw = {"event": "Test UFC", "event_date": "2026-11-14",
           "odds_used": False, "fights": [r]}
    raw_bytes = json.dumps(raw).encode()
    lock = {"event": "Test UFC", "event_date": "2026-11-14",
            "odds_used": False, "stage_a_frozen": True,
            "fights": [f],
            "raw_model_sha256": hashlib.sha256(raw_bytes).hexdigest()}
    return lock, raw, raw_bytes


def test_different_model_fighter_and_conditional_denominator():
    lock, raw, _ = fixture()
    f = explain_fight(lock["fights"][0], raw["fights"][0])
    assert f["reference_frozen_pick"] == "Alpha"
    assert f["model_views"]["historical_shadow"]["pick"] == "Beta"
    hist_method = f["model_views"]["historical_shadow"]["method"]
    assert hist_method["top"] == "KO"
    assert hist_method["top_conditional_p"] == pytest.approx(.35 / .6)
    assert hist_method["top_exact_p"] == pytest.approx(.35)
    assert f["model_views"]["reference"]["method"]["top_exact_p"] == pytest.approx(.35)
    assert f["all_three_agree"] is False
    assert f["stage_a_posture"] == "PASS"
    assert f["method_timing_flag"] is True
    assert "not an approved wager" in f["video_script_roughly_one_minute"].lower()
    assert f["per_fight_feature_attribution_available"] is False


def test_source_hash_odds_and_matchup_guards():
    lock, raw, raw_bytes = fixture()
    x = explain_card(lock, raw, raw_bytes)
    assert x["fight_count"] == 1
    assert x["no_model_promotion_or_changed_picks"] is True
    assert "Short-form model forecast script" in as_markdown(x)
    with pytest.raises(ValueError, match="SHA-256"):
        explain_card(lock, raw, raw_bytes + b"tampered")
    lock["odds_used"] = True
    with pytest.raises(ValueError, match="odds-blind"):
        explain_card(lock, raw, raw_bytes)


def test_unsourced_claims_excluded_and_wrong_identity_rejected():
    lock, raw, _ = fixture()
    with pytest.raises(ValueError, match="mismatch"):
        explain_fight(lock["fights"][0], {**raw["fights"][0], "b": "Wrong"})
    notes = {"1": [{"category": "striking", "claim": "unverified claim",
                    "source_url": "", "reviewed_by_human": False}]}
    f = explain_fight(lock["fights"][0], raw["fights"][0], notes)
    assert f["reviewed_scouting_notes"] == []
    assert f["rejected_scouting_notes"] == 1
    assert "unverified claim" not in f["video_script_roughly_one_minute"]
    assert pct(.37455) == "37.5%"
    with pytest.raises(ValueError, match="not in"):
        own_method(raw["fights"][0], "reference", "Missing")


def test_real_ufc334_archived_inputs_are_unchanged_and_explain_all_fights():
    if not (DIR / "stage_a_final_selection.json").exists():
        pytest.skip("UFC334 artifacts aren't available in this checkout")
    lock = json.loads((DIR / "stage_a_final_selection.json").read_text())
    raw_bytes = (DIR / "stage_a_model_raw_three_view.json").read_bytes()
    raw = json.loads(raw_bytes)
    x = explain_card(lock, raw, raw_bytes)
    assert x["fight_count"] == 13
    assert {f["fight_no"] for f in x["fights"]} == set(range(1, 14))
    assert sum(f["stage_a_posture"] == "PASS" for f in x["fights"]) == 8
    assert [f["fight_no"] for f in x["fights"] if f["method_timing_flag"]] == [1, 2, 3, 4, 7, 11]
    assert all(f["original_frozen_pick_unchanged"] for f in x["fights"])
    assert all(not f["tactical_research_complete"] for f in x["fights"])
    assert all("not an approved wager" in f["video_script_roughly_one_minute"]
               for f in x["fights"])
