"""Strict chronological and opponent-feature ablation tests for method shadow."""
import numpy as np
import pandas as pd
import pytest

from wshlx_ufc.opponent_aware_method_shadow import (
    DATA_PATH, FORBIDDEN_FEATURES, FINISH_FEATURES, SUB_FEATURES,
    backtest, features, fit_stage, predict
)


def test_opponent_aware_challenger_is_non_promoted_and_out_of_time():
    out = backtest()
    assert out["status"] == "RESEARCH_SHADOW_NOT_PROMOTED"
    assert out["training_set_rows"] == 153
    assert out["heldout_bouts"] == 89
    assert out["heldout_events"] == 7
    assert out["conditional_on_actual_winning_fighter_oracle"] is True
    assert out["not_exact_fighter_plus_method_or_wager_grading"] is True
    assert not out["champion_changed"] and out["no_fanduel_price_used"]
    assert out["no_current_event_training_in_its_own_fold"] is True
    assert not set(FINISH_FEATURES)&FORBIDDEN_FEATURES
    assert not set(SUB_FEATURES)&FORBIDDEN_FEATURES
    assert all(f["max_training_event_date"]<f["event_date"]
               for f in out["folds"])
    assert sum(f["held_out_bouts"] for f in out["folds"])==89


def test_fixed_prior_feature_hypothesis_not_better_than_intercept_ablation():
    out=backtest()
    b,i,o=(out["aggregate"][k]
           for k in ("baseline","intercept","opponent_features"))
    assert (b["n"],i["n"],o["n"])==(89,89,89)
    assert (b["correct"],i["correct"],o["correct"])==(39,49,49)
    assert abs(b["brier"]-0.6042237163155109)<1e-6
    assert abs(i["brier"]-0.5587456858189143)<1e-6
    assert abs(o["brier"]-0.5587843619502912)<1e-6
    assert abs(b["logloss"]-0.9735666749460414)<1e-6
    assert abs(i["logloss"]-0.9156359858831742)<1e-6
    assert abs(o["logloss"]-0.9164602972217838)<1e-6
    assert o["brier"]>i["brier"] and o["logloss"]>i["logloss"]
    assert out["incremental_feature_gain"]["extra_correct_method_labels"]==0


def test_future_event_outcome_cannot_appear_in_earlier_fold(tmp_path):
    f = pd.read_csv(DATA_PATH,low_memory=False)
    future=f.loc[f.event_date=="2026-11-07T00:00:00+00:00"].copy()
    assert len(future)==14
    train=f.loc[f.event_date<future.event_date.iloc[0]]
    assert len(train)==139
    fit=fit_stage(train,stage="finish",opponent_aware=True)
    sub=fit_stage(train,stage="sub",opponent_aware=True)
    original=predict(future,finish_beta=fit,sub_beta=sub,opponent_aware=True)
    assert original.shape==(14,3)
    assert np.allclose(original.sum(axis=1),1,atol=1e-10)
    corrupted=future.copy()
    corrupted.loc[:,"clean_actual_method"]="DEC"
    # Inference must not depend on actual method, even though fitting uses
    # method as the retrospective target.
    testing=predict(corrupted,finish_beta=fit,sub_beta=sub,opponent_aware=True)
    assert np.allclose(original,testing,rtol=0,atol=1e-12)


def test_missing_defense_and_zero_ufc_bouts_shrink_to_neutral_priors():
    f=pd.read_csv(DATA_PATH,low_memory=False).iloc[:1].copy()
    for field in ("opponent_ko_loss_rate","opponent_sub_loss_rate",
                  "opponent_sig_defense","opponent_td_defense",
                  "opponent_recent5_finish_rate","winner_finish_win_rate",
                  "winner_sub_win_rate","winner_ko_win_rate"):
        f[field]=float("nan")
    f["opponent_prior_bouts"]=0
    f["winner_prior_bouts"]=0
    for stage in ("finish","sub"):
        matrix=features(f,stage)
        assert matrix.shape==(1,len(FINISH_FEATURES if stage=="finish" else SUB_FEATURES))
        assert np.isfinite(matrix).all()
    # Do not turn unknown defenses into 'zero defense' or impossible KO loss.
    assert abs(features(f,"finish")[0,0]-2*(0.12+0.09-0.22))<1e-10
    assert abs(features(f,"finish")[0,1])<1e-10
