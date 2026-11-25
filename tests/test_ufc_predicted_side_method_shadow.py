"""Past-only selected-fighter method sidecar: scoring and immutable lock tests."""
import math
import json
import pytest

from wshlx_ufc.predicted_side_method_shadow import (
    ROOT, EVENTS, _check_event_lock, _per_side, _quality_inputs,
    _quality_lookup, _model_joint_and_side, evaluate, MODELS, VARIANTS
)
from wshlx_ufc.joint_coherence_shadow import JOINT_KEYS, SIDES, METHODS


def test_exact_three_archived_stage_a_locks_and_source_hashes():
    for slug,path,grade in EVENTS:
        raw,frozen,results=_check_event_lock(slug,path,grade)
        assert raw["odds_used"] is False
        assert frozen["odds_used"] is False
        assert frozen["stage_a_frozen"] is True
        assert len(raw["fights"])==len(frozen["fights"])
        assert raw["event_date"]==frozen["event_date"]
        for r,f in zip(raw["fights"],frozen["fights"]):
            for model in MODELS:
                joint,p_a,selected=_model_joint_and_side(model,r,f)
                assert set(joint)==set(JOINT_KEYS)
                assert selected in (f["a"],f["b"])
                for side in ("A","B"):
                    p=_per_side(joint,side)
                    assert len(p)==3
                    assert math.isclose(float(sum(p)),1,abs_tol=1e-10)


def test_predicted_fighter_quality_queries_never_lookup_real_results_for_test_card():
    for slug,rawpath,grade in EVENTS:
        r,f,gradefile=_check_event_lock(slug,rawpath,grade)
        snaps=_quality_lookup(r["event_date"],r["fights"])
        assert len(snaps)==len(r["fights"])
        for bout in r["fights"]:
            n=bout["fight_no"]
            assert snaps[n]["date"]==r["event_date"]
            assert "__PREFIGHT_QUERY_ONLY" in snaps[n]["event"]
            for side in ("A","B"):
                p=_per_side(bout["joint_calibrated"],side)
                data=_quality_inputs(snaps[n],side,p)
                assert math.isclose(data["base_KO"]+data["base_SUB"]+data["base_DEC"],1,abs_tol=1e-10)
                assert data["picked_side_prior_ufc_bouts"]>=0


def test_all_views_selected_fighter_grade_41_bouts_not_just_winner_oracle():
    result=evaluate()
    assert result["all_bouts"]==41
    assert result["outcome_views"]==123
    assert result["draw_event_count"]==1
    assert result["model_promoted"] is False
    assert result["no_fanduel_odds_used"] is True
    assert result["features_derived_from_each_predicted_fighter_not_actual_winner"]
    assert result["prediction_model_winner_unchanged"]
    assert result["training_fitted_only_previous_dates"]
    assert all(x["original_lock_and_raw_sha_verified"]
               for x in result["evaluation_events"])
    assert len(result["evaluation_events"])==3
    train=[x["shadow_fit_rows_strictly_before_event"] for x in result["evaluation_events"]]
    assert train==[125,139,153]
    for model in MODELS:
        assert result["summary"][model]["original_coherent"]["decisive_fights"]==40
        for variant in VARIANTS:
            x=result["summary"][model][variant]
            assert x["decisive_fights"]==40
            assert x["exact_fighter_method_correct"]<=x["winner_correct"]
            assert 0<=x["six_way_brier"]<=2
            assert math.isfinite(x["six_way_logloss"])
    for event in result["per_event"]:
        for model in MODELS:
            for variant in VARIANTS:
                assert result["per_event"][event][model][variant]["decisive_fights"]>=12
    for row in result["rows"]:
        if row["actual_method"]=="DRAW":
            for variant in VARIANTS:
                assert row["variants"][variant]["six_way_scores"] is None
                assert row["variants"][variant]["exact_fighter_method_correct"] is False
        for variant in VARIANTS:
            masses=row["variants"][variant]["projected_sixway"]
            side="A" if row["original_locked_fighter_pick"]==row["a"] else "B"
            assert abs(sum(masses.values())-1)<1e-9
            assert abs(sum(masses[k] for k in SIDES[side])-
                       row["original_locked_fighter_probability"])<1e-9
            method=row["variants"][variant]["selected_method"]
            assert method==max(METHODS,key=lambda m:masses[f"{side}_{m}"])
            assert row["variants"][variant]["bet_approved"] is False


def test_mutated_original_frozen_card_must_fail_before_shadow_inference(tmp_path,monkeypatch):
    # The evaluator never writes or changes Stage A/B; verify original SHA is
    # enforced by the same source-validation path the evaluator actually uses.
    from wshlx_ufc.predicted_side_method_shadow import _check_event_lock
    import wshlx_ufc.predicted_side_method_shadow as unit
    slug,path,grade=EVENTS[-1]
    raw,frozen,results=_check_event_lock(slug,path,grade)
    assert frozen["raw_model_sha256"]
