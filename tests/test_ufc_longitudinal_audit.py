"""Full-history evidence audit must be reproducible without model changes."""
import math
import json
import csv
from pathlib import Path
import pytest

from wshlx_ufc.longitudinal_audit import (
    ROOT, FULL, _clean153, _check_snapshots, _check_locks, audit
)


def test_153_rows_all_cumulative_prefixes_are_exact_and_grade_flags_consistent():
    original=(ROOT/FULL).read_bytes()
    clean=_clean153()
    assert len(clean)==153
    assert len({(r["event_date"],r["fight"]) for r in clean})==153
    assert sum(x["winner_correct"] for x in clean)==92
    assert sum(x["method_correct"] for x in clean)==79
    assert sum(x["joint_correct"] for x in clean)==48
    assert len(_check_snapshots(clean))==8
    assert (ROOT/FULL).read_bytes()==original


def test_seven_archived_stage_a_card_artifacts_match_exact_89_selected_winners():
    output=_check_locks(_clean153())
    assert len(output)==7
    assert sum(f["gradeable_bouts"] for f in output)==89
    assert all(f["matched_reference_winner_picks"]==f["gradeable_bouts"]
               for f in output)
    assert all(f["odds_blind_flag"] for f in output)
    assert sum(f["timestamped_final_sha_checked"] for f in output)==2
    assert output[-1]["date"]=="2026-11-07"


def test_reference_archive_stage_b_scenarios_and_simple_selected_fighter_ko():
    report=audit()
    assert report["scope"]["reconstructed_decisive_fights"]==153
    assert report["scope"]["dated_events_reconstructed"]==12
    assert report["scope"]["historical_fights_without_independent_stage_a_card_artifact"]==64
    assert report["scope"]["historical_fights_with_matching_stage_a_card_artifact"]==89
    assert report["reconstructed_reference_before_334"]["winner_correct"]==92
    assert report["reconstructed_reference_before_334"]["method_class_correct"]==79
    assert report["reconstructed_reference_before_334"]["exact_fighter_and_method"]==48
    assert report["sanity_check"]["chosen_fixed_method"]=="KO"
    # Exact fighter+method failures are more important than generic KO bias:
    # only 2/24 real submissions had the correct class selected, and
    # both also had the correct fighter; first 64 had ZERO sub recognition.
    sub=report["reconstructed_reference_before_334"]["method_recall"]["SUB"]
    assert sub=={"actual":24,"predicted":10,
                 "class_true_positive":2,
                 "exact_selected_fighter_true_positive":2}
    early_sub=report["earlier_first_64"]["method_recall"]["SUB"]
    assert early_sub["class_true_positive"]==0
    assert sum(report["reconstructed_reference_before_334"][
        "method_confusion_predicted_by_actual"]["KO"].values())==82
    assert report["sanity_check"]["subsequent_89_exact_model"]==33
    assert report["sanity_check"]["subsequent_89_exact_fixed_method"]==30
    assert report["sanity_check"]["all_153_exact_model"]==48
    assert report["sanity_check"]["all_153_exact_fixed_method"]==50
    assert report["scope"]["all_available_reference_decisive_fights"]==165
    assert report["reference_combined_mixed_vintages"]["winner_correct"]==100
    assert report["reference_combined_mixed_vintages"]["exact_fighter_and_method"]==49
    assert report["ufc334_reference"]["excluded"][0]["method"]=="DRAW"
    assert report["ufc334_reference"]["source_lock_verified_sha"]
    assert report["original_models_or_stage_a_b_changed"] is False
    assert report["new_predictor_trained_or_promoted"] is False


def test_stage_b_includes_only_documented_actionable_not_hypothetical_research():
    result=audit()["strategy_stage_b_recorded"]
    primary=result["post_recheck_actionable_scenario"]
    initial=result["original_sep19_frozen_scenario"]
    assert len(result["source_events"])==5
    assert (primary["wins"],primary["losses"])==(9,10)
    assert (initial["wins"],initial["losses"])==(10,10)
    assert math.isclose(primary["risked_units"],14)
    assert math.isclose(initial["risked_units"],14.5)
    assert math.isclose(primary["net_units"],-0.1660524405827695,abs_tol=2e-6)
    assert math.isclose(initial["net_units"],0.6739475594172305,abs_tol=2e-6)
    assert not result["actual_user_bankroll_or_bets_verified"]
    assert not result["market_beating_proven"]
    assert result["not_cumulative_research_virtual_unit_pnl"]


def test_early_rows_not_falsely_claimed_as_independent_pre_fight_locks():
    report=audit()
    history=report["original_stage_a_artifact_identity_verification"]
    assert len(history)==7
    assert history[0]["date"]=="2026-09-19"
    assert history[0]["has_pre_fight_timestamp_evidence"] is False
    assert report["scope"]["missing_earlier_projects_cannot_claim_entire_multimonth_history"]
    assert report["sanity_check"]["not_an_independent_prospectively_registered_benchmark"]
    assert report["strategy_stage_b_recorded"]["missing_or_zero_approved_events"][0]["status"]=="NO_FROZEN_STAGE_B_OFFICIAL_CARD_FOUND"


def test_historical_cumulative_grade_tampering_detected(tmp_path,monkeypatch):
    import wshlx_ufc.longitudinal_audit as module
    rows=(ROOT/FULL).read_text(encoding="utf-8")
    rows=rows.replace("Quillan Salkilld,Quillan Salkilld,KO,SUB,1,0,0",
                      "Quillan Salkilld,Quillan Salkilld,KO,SUB,0,0,0",1)
    bad=tmp_path/"modified.csv"
    bad.write_text(rows,encoding="utf-8")
    monkeypatch.setattr(module,"FULL",str(bad))
    monkeypatch.setattr(module,"ROOT",Path("/"))
    with pytest.raises(ValueError,match="flags inconsistent"):
        module._clean153()
