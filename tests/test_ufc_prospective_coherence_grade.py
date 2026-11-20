"""Postevent scoring works only from independently verified frozen shadow."""
from datetime import datetime,timezone
import json
from pathlib import Path
import pytest

from wshlx_ufc.prospective_coherence import create_lock,check_lock_against_source
from wshlx_ufc.prospective_coherence_grade import grade_prospective_shadow

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/"data/locks/ufc334_2026-11-14"
RESULT=ROOT/"data/results/ufc334_2026-11-14_all_models_grading.json"


def fixture():
    raw=(OLD/"stage_a_model_raw_three_view.json").read_bytes()
    freeze=(OLD/"stage_a_final_selection.json").read_bytes()
    schedule=json.dumps({
        "schema":"WSHL_X_UFC_EVENT_START_MANIFEST_V1",
        "event_slug":"UNIT_TEST_HISTORICAL_CARD_NOT_A_REAL_PRE_EVENT_LOCK",
        "event_date":"2026-11-14",
        "first_fight_not_before_utc":"2026-11-14T15:00:00+00:00",
        "source_url":"https://www.ufc.com/event/UNIT-TEST-ONLY",
        "main_event_fighters":["Ciryl Gane","Josh Hokit"],
        "card_roster_complete":False,
    },sort_keys=True).encode()
    shadow=create_lock(raw_bytes=raw,frozen_bytes=freeze,
         schedule_bytes=schedule,as_of_utc=datetime(2026,11,12,tzinfo=timezone.utc))
    actual=json.loads(RESULT.read_bytes())
    oldcard=json.loads(raw)
    by_no={f["fight_no"]:f for f in actual["fights"]}
    outcomes=[]
    for fight in oldcard["fights"]:
        r=by_no[fight["fight_no"]]["actual"]
        outcomes.append({
            "fight_no":fight["fight_no"],"a":fight["a"],"b":fight["b"],
            "winner":r["winner"],
            "method":r["method"],
        })
    labels={
        "event_slug":shadow["event_slug"],
        "event_date":shadow["event_date"],
        "results_verified":True,
        "results_source_url":"https://www.ufc.com/event/UNIT-TEST-ONLY",
        "verified_at_utc":"2026-11-15T14:00:00+00:00",
        "fights":outcomes,
    }
    return json.dumps(shadow,sort_keys=True).encode(),raw,freeze,schedule,labels


def _grade(shadow,raw,freeze,schedule,labels,now=None):
    return grade_prospective_shadow(
        lock_bytes=shadow,raw_bytes=raw,frozen_bytes=freeze,
        schedule_bytes=schedule,results_bytes=json.dumps(labels).encode(),
        as_of_utc=now or datetime(2026,11,16,tzinfo=timezone.utc),
    )


def test_three_model_real_old_fights_fixture_grades_without_retraining():
    shadow,raw,freeze,schedule,labels=fixture()
    result=_grade(shadow,raw,freeze,schedule,labels)
    assert result["schema"]=="WSHL_X_PROSPECTIVE_COHERENCE_POST_EVENT_SHADOW_GRADE_V1"
    assert result["decisive_fights"]==12
    assert result["excluded_draw_nc_dq"]==1
    assert result["event_date"]=="2026-11-14"
    assert result["bet_authorized"] is False
    assert result["model_promoted"] is False
    assert result["results_only_in_grading_not_in_predictions"]
    for model in ("reference","historical","unified"):
        model_results=result["summary"][model]
        fixed_wins={
            "reference":8,"historical":6,"unified":7
        }[model]
        for variant in ("raw_archived","winner_aligned","winner_and_timing_aligned"):
            score=model_results[variant]
            assert score["decisive_fights"]==12
            assert score["original_winner_correct"]==fixed_wins
            assert score["exact_fighter_method_correct"]<=fixed_wins
            assert score["six_way_logloss"]>0
            assert 0<score["six_way_brier"]<2
        assert model_results["original_direct_GTD_NO"]["unchanged_by_all_reconciliations"]
    assert len(result["fights"])==13


def test_incomplete_unverified_or_early_results_refused():
    shadow,raw,freeze,schedule,labels=fixture()
    changed=dict(labels)
    changed["results_verified"]=False
    with pytest.raises(ValueError,match="verified"):
        _grade(shadow,raw,freeze,schedule,changed)
    changed=dict(labels)
    changed["fights"]=labels["fights"][:-1]
    with pytest.raises(ValueError,match="Every original frozen fight"):
        _grade(shadow,raw,freeze,schedule,changed)
    changed=json.loads(json.dumps(labels))
    changed["fights"][0]["b"]="Fake Opponent"
    with pytest.raises(ValueError,match="identities"):
        _grade(shadow,raw,freeze,schedule,changed)
    with pytest.raises(ValueError,match="progress"):
        _grade(shadow,raw,freeze,schedule,labels,
               now=datetime(2026,11,14,16,tzinfo=timezone.utc))


def test_pre_event_shadow_must_match_exact_original_projections_even_after_result():
    shadow,raw,freeze,schedule,labels=fixture()
    edited=json.loads(shadow)
    j=edited["fights"][0]["models"]["historical"]["distributions"]["winner_and_timing_aligned"]
    j["A_KO"]+=0.02
    with pytest.raises(ValueError,match="differ from original"):
        _grade(json.dumps(edited).encode(),raw,freeze,schedule,labels)


def test_method_draw_and_invalid_outcomes_not_silently_given_accuracy():
    shadow,raw,freeze,schedule,labels=fixture()
    draws=[f for f in labels["fights"] if f["method"]=="DRAW"]
    assert len(draws)==1
    assert draws[0]["winner"] is None
    bad=json.loads(json.dumps(labels))
    bad["fights"][0]["method"]="UNKNOWN"
    with pytest.raises(ValueError,match="Unknown graded"):
        _grade(shadow,raw,freeze,schedule,bad)
