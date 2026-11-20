"""No look-ahead and true selected-fighter exact method scoring for research."""
import numpy as np
import pandas as pd

from wshlx_ufc.resistance_method_shadow import (
    ROOT,VARIANTS,MODELS,_matrix,evaluate
)


def test_missing_pre_event_defensive_stats_use_neutral_not_zero_defense():
    row={
        "own_kd_per15":None,"opp_kd_absorbed_per15":None,
        "own_sub_attempts_per15":None,"own_takedowns_per15":None,
        "opp_prior_ko_loss_rate":.12,"opp_prior_sub_loss_rate":.09,
        "opp_survival_vs_finisher":.55,"opp_kd_nonko_survival":.5,
        "opp_submission_threat_nonloss":.75,"opp_takedown_defense":.58,
        "opp_control_absorbed_per15":None,
        "opponent_prior_dangerous_exposures":0,
        "opponent_prior_knockdown_exposures":0,
        "opp_prior_stats_coverage":0.0,
        "scheduled_seconds":900,
    }
    frame=pd.DataFrame([row])
    assert _matrix(frame,"finish",False).shape==(1,1)
    assert _matrix(frame,"finish",True).shape==(1,8)
    assert _matrix(frame,"sub",True).shape==(1,7)
    assert np.isfinite(_matrix(frame,"finish",True)).all()
    assert np.isfinite(_matrix(frame,"sub",True)).all()
    before=_matrix(frame,"finish",True)
    frame["actual_winner"]="Unknown"
    frame["actual_method"]="KO"
    assert np.allclose(before,_matrix(frame,"finish",True))
    assert np.allclose(before[0,1:7],0.0)


def test_resistance_candidates_use_only_previous_events_and_original_winner():
    results=evaluate()
    assert results["schema"].endswith("EXACT_METHOD_RESEARCH_V1")
    assert results["status"]=="RESEARCH_ONLY_NO_PROSPECTIVE_PROMOTION"
    assert results["model_promoted"] is False
    assert results["stage_b_wager_approval"] is False
    assert results["feature_not_actual_getups"] is True
    assert results["historical_dated_stats"]["direct_getups_available"] is False
    assert results["source_is_pinned_secondary_archive"] is True
    assert results["feature_training_rows"]==153
    assert len(results["event_evaluations"])==3
    assert [x["training_rows"] for x in results["event_evaluations"]]==[125,139,153]
    assert results["three_model_fight_records"]==123
    assert results["decisive_fights"]==40
    assert results["draws"]==1
    baseline_expected={"reference":9,"historical":13,"unified":14}
    for model in MODELS:
        for variant in VARIANTS:
            stat=results["summary"][model][variant]
            assert stat["decisive_fights"]==40
            assert stat["exact_fighter_method_correct"]<=stat["winner_correct"]
            assert stat["six_way_logloss"]>=0
            assert stat["six_way_brier"]>=0
            assert stat["winner_correct"]==results["summary"][model]["original_coherent"]["winner_correct"]
        assert results["summary"][model]["original_coherent"]["exact_fighter_method_correct"]==baseline_expected[model]
    for r in results["rows"]:
        assert r["resistance_source_is_previous_fights_only"] is True
        for variant in VARIANTS:
            assert r["variants"][variant]["bet_approved"] is False
            if r["actual_method"]=="DRAW":
                assert r["variants"][variant]["six_way_scores"] is None
                assert r["variants"][variant]["exact_fighter_method_correct"] is False
            if not r["winner_correct"]:
                assert r["variants"][variant]["exact_fighter_method_correct"] is False
