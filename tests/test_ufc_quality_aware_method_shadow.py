"""Quality-of-opposition historical fighter-method ablation remains research only."""
import json
from pathlib import Path
import numpy as np
import pytest
from wshlx_ufc.quality_aware_method_shadow import (
    study, design, quality_features, predict, QUALITY_FEATURES
)
from wshlx_ufc.opponent_quality_join import load_and_join

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/"reports/ufc334_2026-11-14/QUALITY_AWARE_METHOD_153_7FOLD_RESEARCH_RESULTS.json"


def test_full_153_matched_quality_and_real_89_bout_heldout_research():
    observed=study()
    saved=json.loads(RESULTS.read_text())
    assert saved["coverage"]["matched"]==153
    assert observed["quality_match_coverage"]["matched"]==153
    assert observed["quality_match_coverage"]["missing"]==0
    assert len(observed["folds"])==7
    assert all(x["trained_through"]<x["event_date"] for x in observed["folds"])
    assert sum(x["test_n"] for x in observed["folds"])==89
    for model in ("baseline","intercept","opponent_only","quality_only","quality_plus_opponent"):
        this=observed["overall"][model]
        snapshot=saved["overall"][model]
        assert this["n"]==snapshot["n"]==89
        assert this["correct"]==snapshot["hits"]
        assert abs(this["brier"]-snapshot["brier"])<1e-6
        assert abs(this["logloss"]-snapshot["logloss"])<1e-6
    assert observed["overall"]["quality_plus_opponent"]["correct"]==48
    assert observed["overall"]["quality_only"]["correct"]==49
    assert observed["overall"]["intercept"]["correct"]==49
    assert observed["incremental_quality_vs_intercept"]["top_method_extra_hits"]==-1
    assert observed["status"]=="RETROSPECTIVE_RESEARCH_ONLY_NO_AUTOMATIC_PROMOTION"
    assert observed["holdout_methods_conditional_on_actual_winner"]
    assert observed["not_exact_selected_fighter_plus_method_betting_performance"]
    assert observed["nov14_ufc334_stats_or_results_not_training_inputs"]


def test_quality_method_predictor_inputs_do_not_use_current_fight_outcome():
    df,meta=load_and_join()
    assert meta["matched"]==153
    future=df.loc[df.event_date==df.event_date.max()].copy()
    X=design(future,"finish","quality_plus_opponent")
    assert X.shape==(14,1+6+len(QUALITY_FEATURES))
    original=X.copy()
    # All actual-method and result fields may change without changing
    # pre-fight fighter/opponent rating or style input features.
    for field in ("winner","method","clean_actual_method","clean_winner_correct"):
        if field in future:
            future[field]="NOT_A_REAL_RESULT"
    after=design(future,"finish","quality_plus_opponent")
    assert np.allclose(original,after,rtol=0,atol=1e-10)


def test_unknown_opponent_rating_missingness_is_visible_neutral_not_bad():
    df,meta=load_and_join()
    damaged=df.iloc[:1].copy()
    for k in ("quality_elo_gap","winner_prior_schedule_strength_gap",
              "winner_prior_defeated_opponents_elo",
              "opponent_prior_defeated_opponents_elo",
              "opponent_prior_ufc_elo"):
        damaged.loc[:,k]=float("nan")
    x=quality_features(damaged)
    assert x.shape==(1,len(QUALITY_FEATURES))
    assert np.isfinite(x).all()
    assert np.allclose(x[0,:4],0)
    assert x[0,-1]==1
