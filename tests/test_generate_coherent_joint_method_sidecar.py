"""A candidate sidecar is separate from Stage A/B and never a bet/official pick."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/generate_coherent_joint_method_sidecar.py"
RAW = ROOT / "data/locks/ufc334_2026-11-14/stage_a_model_raw_three_view.json"
FROZEN = ROOT / "data/locks/ufc334_2026-11-14/stage_a_final_selection.json"


def module():
    spec = importlib.util.spec_from_file_location("coherent_sidecar", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_sidecar_13_bouts_with_original_frozen_sha_and_zero_bets():
    raw_bytes = RAW.read_bytes()
    original_raw_before = raw_bytes
    original_locked_before = FROZEN.read_bytes()
    frozen = json.loads(original_locked_before)
    raw = json.loads(original_raw_before)
    m = module()
    payload = m.build_sidecar(frozen,raw,raw_bytes,generated_date="2026-11-10")
    assert payload["source_bout_count"] == 13
    assert payload["pre_event_shadow"] and not payload["generated_after_event_replay"]
    assert payload["source_original_stage_a_frozen"] is True
    assert payload["source_original_raw_sha256"] == frozen["raw_model_sha256"]
    assert payload["bet_authorized"] is False
    assert payload["new_model_trained"] is False
    assert payload["fanduel_odds_used"] is False
    assert payload["original_model_weights_or_picks_changed"] is False
    assert payload["original_10000_simulation_suites_changed"] is False
    assert all(not f["bet_authorized"] for f in payload["fights"])
    assert set(payload["fights"][0]["models"]) == {"historical","unified"}
    assert RAW.read_bytes() == original_raw_before
    assert FROZEN.read_bytes() == original_locked_before
    replay = m.build_sidecar(frozen,raw,raw_bytes,generated_date="2026-11-16")
    assert replay["generated_after_event_replay"] and not replay["pre_event_shadow"]


def test_no_odds_leaks_and_source_hash_integrity():
    m = module()
    raw_bytes = RAW.read_bytes()
    frozen = json.loads(FROZEN.read_text())
    raw = json.loads(raw_bytes)
    with pytest.raises(ValueError, match="hash"):
        m.build_sidecar(frozen,raw,raw_bytes+b"x",generated_date="2026-11-10")
    raw["odds_used"] = True
    with pytest.raises(ValueError, match="odds-blind"):
        m.build_sidecar(frozen,raw,raw_bytes,generated_date="2026-11-10")
    raw = json.loads(raw_bytes)
    frozen["stage_a_frozen"] = False
    with pytest.raises(ValueError, match="frozen"):
        m.build_sidecar(frozen,raw,raw_bytes,generated_date="2026-11-10")


def test_bad_fight_identity_refused():
    m = module()
    raw_bytes = RAW.read_bytes()
    frozen = json.loads(FROZEN.read_text())
    raw = json.loads(raw_bytes)
    raw["fights"][0]["a"] = "Invented Fighter"
    with pytest.raises(ValueError,match="identity mismatch"):
        m.build_sidecar(frozen,raw,raw_bytes,generated_date="2026-11-10")
