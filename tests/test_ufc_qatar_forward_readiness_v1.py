"""Nov 21 source SHA safety and pre-event abstention integration tests."""
from datetime import datetime
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location(
    "wshlx_qatar_readiness",ROOT/"tools/audit_ufcqatar_forward_selection_readiness.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def sample():
    source={
        "event":"UFC Fight Night: Prochazka vs Stirling",
        "event_date":"2026-11-21","stage_a_frozen":True,"odds_used":False,
        "fights":[
            {"fight_no":i,"a":f"Athlete A{i}","b":f"Athlete B{i}",
             "stage_a_posture":"PASS" if i in (1,12) else "MODEL_ONLY"}
            for i in range(1,13)],
    }
    q={"A_KO":.2,"A_SUB":.1,"A_DEC":.2,
       "B_KO":.2,"B_SUB":.1,"B_DEC":.2}
    research={
        "event_date":"2026-11-21",
        "primary_architecture_locked_before_results":"direct_paired230",
        "primary_selection_policy_locked_before_results":"winner_marginal_method",
        "original_frozen_sha256":{"stage_a_final_selection.json":"0"*64},
        "betting_picks_approved":0,"FanDuel_odds_used":False,
        "all_prior_official_research_predictions_UNCHANGED":True,
        "created_and_locked_utc":"2026-11-19T23:00:00+00:00",
        "earliest_fight_utc":"2026-11-21T15:00:00+00:00",
        "fights_predicted":12,
        "research_fights":[
            {"fight_no":i,"a":f"Athlete A{i}","b":f"Athlete B{i}",
             "original_Stage_A_posture_unchanged":"PASS" if i in (1,12) else "MODEL_ONLY",
             "independent_external_source_ids_both_verified":i not in (1,12),
             "not_an_approved_wager":True,"original_provisional_12th":i==12,
             "six_joint":q}
            for i in range(1,13)],
    }
    return source,research

def test_original_predictions_are_read_only_and_no_unsupported_leans_are_made():
    a,b=sample()
    old_a,old_b=deepcopy(a),deepcopy(b)
    report=m.build(a,b,"0"*64,"a"*64,[],
                   now="2026-11-20T14:00:00+00:00")
    assert a==old_a and b==old_b
    assert report["research_calibration"]["prospective_fights"]==0
    assert report["candidate_selection"]["num_selected"]==0
    assert report["new_official_betting_picks"]==0
    assert report["reviewed_bouts"]==12
    quality=report["candidate_selection"]["all_reviews"]
    assert sum(not row["source_qa_verified"] for row in quality)==2
    assert len({row["bout_id"] for row in quality})==12

def test_never_recalculate_after_event_or_retroactively_swap_model_or_fighters():
    a,b=sample()
    with pytest.raises(ValueError,match="after opening fight"):
        m.build(a,b,"0"*64,"a"*64,[],now="2026-11-21T16:00:00+00:00")
    with pytest.raises(ValueError,match="wrong event|Wrong fight"):
        m.build({**a,"event_date":"2026-11-22"},b,"0"*64,"a"*64,[],
                now="2026-11-20T14:00:00+00:00")
    b["research_fights"][3]["b"]="Wrong new fighter"
    with pytest.raises(ValueError,match="fighter/date/number"):
        m.build(a,b,"0"*64,"a"*64,[],now="2026-11-20T14:00:00+00:00")

def test_refuses_original_stagea_sha_changes_and_modified_selected_policy():
    a,b=sample()
    with pytest.raises(ValueError,match="original SHA"):
        m.build(a,b,"different-sha","a"*64,[],
                now="2026-11-20T14:00:00+00:00")
    b["primary_selection_policy_locked_before_results"]="global_best_cell"
    with pytest.raises(ValueError,match="policy"):
        m.build(a,b,"0"*64,"a"*64,[],
                now="2026-11-20T14:00:00+00:00")

def test_prospective_calibration_never_reads_after_event_grading():
    a,b=sample()
    prior=[{"model_id":m.PRIMARY,"event_date":"2026-11-21",
            "event_id":"same_event","bout_id":"future",
            "locked_before_event":True,"independently_verified":True,
            "selected_exact_probability":.3,"exact_hit":1}]
    with pytest.raises(ValueError,match="Future"):
        m.build(a,b,"0"*64,"a"*64,prior,now="2026-11-20T14:00:00+00:00")
