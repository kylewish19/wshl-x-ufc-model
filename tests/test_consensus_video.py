"""Consensus reports never alter the champion or conflates method/timing votes."""
import hashlib
import json
from pathlib import Path

import pytest

from wshlx_ufc.consensus_video import (
    majority, consensus_card, timing_top, to_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/locks/ufc334_2026-11-14"


def files():
    frozen = json.loads((DIR / "stage_a_final_selection.json").read_text())
    raw_bytes = (DIR / "stage_a_model_raw_three_view.json").read_bytes()
    return frozen, json.loads(raw_bytes), raw_bytes


def test_majority_only_exact_matching_votes():
    assert majority(["A", "A", "A"])["consensus"] == "UNANIMOUS"
    assert majority(["A", "A", "B"])["selection"] == "A"
    assert majority(["A", "B", "C"])["selection"] is None
    assert majority([("A", "KO"), ("B", "KO"), ("B", "KO")])["selection"] == ("B", "KO")
    assert majority([("A", "KO"), ("A", "SUB"), ("B", "KO")])["selection"] is None
    with pytest.raises(ValueError):
        majority(["A", "A"])


def test_original_ufc334_model_consensus_is_never_champion_replacement():
    lock, raw, raw_bytes = files()
    before = json.dumps(lock, sort_keys=True)
    card = consensus_card(lock, raw, raw_bytes)
    assert card["fighters"] == 13
    assert card["bets_approved_by_this_overlay"] == 0
    assert card["model_views_are_not_independent"]
    assert card["source"] == "ORIGINAL_FROZEN_STAGE_A_NO_STAGE_B_ODDS"
    assert json.dumps(lock, sort_keys=True) == before
    assert sum(f["winner"]["votes"] == 3 for f in card["fights"]) == 9
    assert sum(f["winner"]["votes"] == 2 for f in card["fights"]) == 4
    assert card["fights"][0]["original_stage_a_reference_winner"] == "Evan Elder"
    assert card["fights"][0]["winner"]["selection"] == "Samuel Sanches"
    assert card["fights"][0]["winner_plus_method"]["selection"] == ("Samuel Sanches", "KO/TKO")
    assert card["fights"][2]["winner_plus_method"]["selection"] == ("Bia Mesquita", "SUB")
    assert card["fights"][10]["winner_plus_method"]["selection"] == ("Yousri Belgaroui", "KO/TKO")
    assert card["fights"][4]["original_stage_a_primary_timing"] == "GTD_NO"
    assert card["fights"][4]["timing"]["selection"] == "OVER_1.5"
    assert not card["fights"][4]["timing"]["same_as_original_frozen_timing"]
    assert all(not f["winner_plus_method"]["approved_bet"] for f in card["fights"])
    assert all(not f["timing"]["approved_bet"] for f in card["fights"])
    assert [f["fight_no"] for f in card["fights"] if f["winner_plus_method"]["coherence_blocked"]] == [1,2,3,4,7,11]
    assert "DIFFERS FROM ORIGINAL TIMING LOCK" in to_markdown(card)
    assert "ORIGINAL PASS" in to_markdown(card)


def test_frozen_hash_and_odds_integrity():
    lock, raw, raw_bytes = files()
    assert hashlib.sha256(raw_bytes).hexdigest() == lock["raw_model_sha256"]
    with pytest.raises(ValueError, match="SHA-256"):
        consensus_card(lock, raw, raw_bytes + b"tamper")
    lock["odds_used"] = True
    with pytest.raises(ValueError, match="odds-blind"):
        consensus_card(lock, raw, raw_bytes)
    lock, raw, raw_bytes = files()
    raw["fights"][0]["b"] = "Wrong"
    with pytest.raises(ValueError, match="identities"):
        consensus_card(lock, raw, raw_bytes)


def test_timing_market_comparison_always_same_market_set():
    lock, raw, _ = files()
    f = lock["fights"][0]
    assert timing_top(f["timing_current"]["sim_10000"]) == "OVER_1.5"
    p = dict(f["timing_current"]["sim_10000"])
    p.pop("GTD_NO")
    with pytest.raises(ValueError, match="Missing timing"):
        timing_top(p)
