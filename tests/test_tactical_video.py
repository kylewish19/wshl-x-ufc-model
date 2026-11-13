"""Sourced tactical scripts must have real matchup detail but NO stated picks."""
import hashlib
import json
from pathlib import Path

import pytest

from wshlx_ufc.tactical_video import validate_and_build, to_markdown

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "data/locks/ufc334_2026-11-14/stage_a_final_selection.json"
RAW = ROOT / "data/locks/ufc334_2026-11-14/stage_a_model_raw_three_view.json"
RESEARCH = ROOT / "research/ufc334_2026-11-14_tactical_video_research.json"


def load():
    return json.loads(LOCK.read_text()), json.loads(RESEARCH.read_text())


def test_actual_card_all_13_tactical_scripts_sources_and_silent_picks():
    lock, research = load()
    raw_digest = hashlib.sha256(RAW.read_bytes()).hexdigest()
    out = validate_and_build(lock, research, raw_digest)
    assert out["fight_count"] == 13
    assert [f["fight_no"] for f in out["fights"]] == list(range(1, 14))
    assert out["original_model_picks_changed"] is False
    assert out["model_retrained"] is False
    assert out["official_bets_authorized"] is False
    for fight in out["fights"]:
        assert len(fight["spoken_matchup_breakdown"].split()) >= 65
        assert fight["no_model_names_or_probabilities_in_script"]
        assert fight["no_pick_revealed"]
        assert len(fight["research_sources"]) >= 1
        assert all(s.startswith("https://") for s in fight["research_sources"])
        assert "model" not in fight["spoken_matchup_breakdown"].lower()
        assert "[HOST REVEALS WINNER]" == fight["host_selection_fields"]["winner"]
        assert fight["review_status"] == "EDITORIAL_DRAFT_NEEDS_FINAL_FACT_AND_TAPE_CHECK"
    md = to_markdown(out)
    assert md.count("**Spoken fight breakdown:**") == 13
    assert md.count("Winner: [YOU REVEAL]") == 13
    assert md.count("Method: [YOU REVEAL]") == 13
    assert md.count("Timing prop: [YOU REVEAL]") == 13


def test_no_fake_research_and_no_partial_card_or_identity_change():
    lock, research = load()
    research["bouts"][0]["script"] = "Our pick is Fighter A at 75%."
    with pytest.raises(ValueError, match="reveals model numbers"):
        validate_and_build(lock, research)
    lock, research = load()
    research["bouts"][0]["source_urls"] = []
    with pytest.raises(ValueError, match="source URLs"):
        validate_and_build(lock, research)
    lock, research = load()
    research["bouts"].pop()
    with pytest.raises(ValueError, match="Every frozen fight"):
        validate_and_build(lock, research)
    lock, research = load()
    research["bouts"][0]["fighters"] = ["Wrong", "Person"]
    with pytest.raises(ValueError, match="Wrong fighters"):
        validate_and_build(lock, research)


def test_frozen_sha_and_odds_guard():
    lock, research = load()
    with pytest.raises(ValueError, match="SHA-256"):
        validate_and_build(lock, research, raw_sha="bad-digest")
    lock["odds_used"] = True
    with pytest.raises(ValueError, match="odds-blind"):
        validate_and_build(lock, research)
