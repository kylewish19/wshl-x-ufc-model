"""Prospective-only coherence locking, real original card integrity, no wager."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import math
import pytest

from wshlx_ufc.prospective_coherence import (
    create_lock,check_lock_against_source,MODEL_NAMES,VARIANTS,_time
)
from wshlx_ufc.joint_coherence_shadow import JOINT_KEYS,SIDES,FINISH_KEYS

ROOT=Path(__file__).resolve().parents[1]
OLD_DIR=ROOT/"data/locks/ufc334_2026-11-14"


def _inputs():
    raw=(OLD_DIR/"stage_a_model_raw_three_view.json").read_bytes()
    frozen=(OLD_DIR/"stage_a_final_selection.json").read_bytes()
    # TEST-ONLY fixture for a HISTORICAL completed card. Never save this as
    # genuine prospective or submit it to betting / public selection ledgers.
    schedule={
      "schema":"WSHL_X_UFC_EVENT_START_MANIFEST_V1",
      "event_slug":"TEST_FIXTURE_HISTORICAL_UFC334",
      "event_date":"2026-11-14",
      "card_roster_complete":False,
      "first_fight_not_before_utc":"2026-11-14T15:00:00+00:00",
      "main_event_fighters":["Ciryl Gane","Josh Hokit"],
      "source_url":"https://www.ufc.com/event/test-fixture-NOT-REAL-PROSPECTIVE",
    }
    return raw,frozen,json.dumps(schedule,sort_keys=True).encode()


def test_all_three_original_views_project_frozen_winner_and_finish_without_mutating_stage_a():
    raw,frozen,schedule=_inputs()
    immutable=(raw[:],frozen[:])
    payload=create_lock(
        raw_bytes=raw,frozen_bytes=frozen,schedule_bytes=schedule,
        as_of_utc=datetime(2026,11,12,12,0,tzinfo=timezone.utc),
    )
    check_lock_against_source(payload,raw,frozen,schedule)
    assert (raw,frozen)==immutable
    assert payload["source_original_fight_count"]==13
    assert payload["model_promoted"] is False
    assert payload["new_model_trained"] is False
    assert payload["fanduel_odds_used"] is False
    assert payload["original_stage_a_and_stage_b_unchanged"]
    assert payload["original_10000_simulations_unchanged"]
    assert payload["video_consensus_overlay_changed"] is False
    assert payload["models_present"]==list(MODEL_NAMES)
    assert payload["variants"]==list(VARIANTS)
    frozen_fights={f["fight_no"]:f for f in json.loads(frozen)["fights"]}
    for f in payload["fights"]:
        assert f["bet_authorized"] is False
        original=frozen_fights[f["fight_no"]]
        assert f["original_stage_a_posture"]==original["stage_a_posture"]
        for name in MODEL_NAMES:
            view=f["models"][name]
            assert view["original_frozen_fighter_pick"] in (f["a"],f["b"])
            assert view["wager_gate"]=="UNAPPROVED_SHADOW_ONLY"
            pa=view["original_frozen_winner_p_a"]
            gtd=view["original_direct_gtd_no"]
            for variant in VARIANTS:
                j=view["distributions"][variant]
                assert set(j)==set(JOINT_KEYS)
                assert math.isclose(sum(j.values()),1,abs_tol=1e-9)
                assert all(0<x<1 for x in j.values())
                selection=view["variant_selections"][variant]
                assert selection["frozen_winner_changed"] is False
                assert selection["bet_authorized"] is False
                assert selection["frozen_winner_pick"]==view["original_frozen_fighter_pick"]
            for variant in ("winner_aligned","winner_and_timing_aligned"):
                j=view["distributions"][variant]
                assert math.isclose(sum(j[k] for k in SIDES["A"]),pa,abs_tol=1e-9)
            jt=view["distributions"]["winner_and_timing_aligned"]
            assert math.isclose(sum(jt[k] for k in FINISH_KEYS),gtd,abs_tol=1e-9)
            assert view["original_direct_timing_markets_untouched"]["GTD_NO"]==gtd
    assert json.loads(frozen)==json.loads(immutable[1])


def test_historical_replays_cannot_be_locked_from_real_today_and_before_stage_a():
    raw,frozen,schedule=_inputs()
    with pytest.raises(ValueError,match="already started"):
        create_lock(raw_bytes=raw,frozen_bytes=frozen,schedule_bytes=schedule,
                    as_of_utc=datetime(2026,11,16,tzinfo=timezone.utc))
    with pytest.raises(ValueError,match="frozen before"):
        create_lock(raw_bytes=raw,frozen_bytes=frozen,schedule_bytes=schedule,
                    as_of_utc=datetime(2026,11,10,tzinfo=timezone.utc))
    with pytest.raises(ValueError,match="timezone aware"):
        create_lock(raw_bytes=raw,frozen_bytes=frozen,schedule_bytes=schedule,
                    as_of_utc=datetime(2026,11,12,12))
    with pytest.raises(ValueError,match="UTC offset"):
        _time("2026-11-14T15:00:00")


def test_odds_source_digest_and_identity_are_required():
    raw,frozen,schedule=_inputs()
    t=datetime(2026,11,12,12,tzinfo=timezone.utc)
    tampered=json.loads(raw)
    tampered["fights"][0]["joint_calibrated"]["A_KO"]+=1e-7
    with pytest.raises(ValueError,match="raw SHA"):
        create_lock(raw_bytes=json.dumps(tampered).encode(),frozen_bytes=frozen,
                    schedule_bytes=schedule,as_of_utc=t)
    payload=create_lock(raw_bytes=raw,frozen_bytes=frozen,
                        schedule_bytes=schedule,as_of_utc=t)
    with pytest.raises(ValueError,match="Source SHA"):
        check_lock_against_source(payload,raw,frozen,schedule+b"x")
    locked=json.loads(frozen)
    locked["odds_used"]=True
    with pytest.raises(ValueError,match="Odds-blind"):
        create_lock(raw_bytes=raw,frozen_bytes=json.dumps(locked).encode(),
                    schedule_bytes=schedule,as_of_utc=t)
    locked=json.loads(frozen)
    locked["fights"][0]["b"]="Invented Fighter"
    with pytest.raises(ValueError,match="fighter pair"):
        create_lock(raw_bytes=raw,frozen_bytes=json.dumps(locked).encode(),
                    schedule_bytes=schedule,as_of_utc=t)
    bogus=json.loads(schedule)
    bogus["main_event_fighters"]=["Fighter Not Here","Another"]
    with pytest.raises(ValueError,match="missing UFC-verified main event"):
        create_lock(raw_bytes=raw,frozen_bytes=frozen,
                    schedule_bytes=json.dumps(bogus).encode(),as_of_utc=t)


def test_new_qatar_manifest_is_real_event_metadata_not_fabricated_picks():
    q=json.loads((ROOT/"research/events/ufcqatar_2026-11-21.json").read_text())
    assert q["event_date"]=="2026-11-21"
    assert q["main_event_fighters"]==["Jiri Prochazka","Navajo Stirling"]
    assert q["first_fight_not_before_utc"]=="2026-11-21T15:00:00+00:00"
    assert q["card_roster_complete"] is False
    assert "ufc.com" in q["source_url"]
    assert q["original_stage_a_or_stage_b_modified"] is False
