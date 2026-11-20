"""Historical strength-of-schedule vs simple calibration: shadow-only research.

Quality features are derived from fighters' opponents' ratings *before* each
previous UFC bout, never retrospective final rating. Causal method labels are
conditional on actual winner (diagnostic oracle), NOT approved exact-method
picks. No original model is trained or overwritten by this module.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from .opponent_aware_method_shadow import (
    _target, _base, _logit, _sigmoid, features, metrics, fit_stage,
    MIN_INITIAL_DATES, INTERCEPT_RIDGE, RIDGE,
)
from .opponent_quality_join import load_and_join

QUALITY_FEATURES = (
    "pre_fight_elo_gap_scaled",
    "prior_strength_of_schedule_gap_scaled",
    "prior_wins_opponent_quality_gap_scaled",
    "opponent_prior_ufc_elo_scaled",
    "quality_snapshot_missing_indicator",
)


def quality_features(frame: pd.DataFrame) -> np.ndarray:
    get=lambda name:pd.to_numeric(frame[name],errors="coerce").to_numpy(float)
    gap=get("quality_elo_gap")
    sched=get("winner_prior_schedule_strength_gap")
    beaten=get("winner_prior_defeated_opponents_elo")
    op_beaten=get("opponent_prior_defeated_opponents_elo")
    op_rating=get("opponent_prior_ufc_elo")
    mask=np.isfinite(gap)&np.isfinite(sched)&np.isfinite(beaten)&np.isfinite(op_beaten)&np.isfinite(op_rating)
    return np.column_stack((
        np.clip(np.nan_to_num(gap,nan=0),-400,400)/100.,
        np.clip(np.nan_to_num(sched,nan=0),-400,400)/100.,
        np.clip(np.nan_to_num(beaten-op_beaten,nan=0),-400,400)/100.,
        np.clip(np.nan_to_num(op_rating,nan=1500)-1500,-400,400)/100.,
        (~mask).astype(float),
    ))


def design(frame: pd.DataFrame, stage: str, kind: str) -> np.ndarray:
    X=np.ones((len(frame),1))
    if kind=="intercept":
        return X
    if kind=="quality_only":
        return np.column_stack((X,quality_features(frame)))
    if kind=="opponent_only":
        return np.column_stack((X,features(frame,stage)))
    if kind=="quality_plus_opponent":
        return np.column_stack((X,features(frame,stage),quality_features(frame)))
    raise ValueError("Unknown conditional-method shadow")


def fit(frame: pd.DataFrame, stage: str, kind: str):
    if kind in ("intercept","opponent_only"):
        return fit_stage(frame,stage=stage,opponent_aware=(kind=="opponent_only"))
    methods=_target(frame)
    baseline=_base(frame)
    sub=stage=="sub"
    subset=methods!="DEC" if sub else np.ones(len(frame),dtype=bool)
    y=(methods[subset]=="SUB" if sub else methods[subset]!="DEC").astype(float)
    offset=(_logit(baseline[subset,1]/(baseline[subset,0]+baseline[subset,1]))
            if sub else _logit(1-baseline[subset,2]))
    X=design(frame,stage,kind)[subset]
    coefficients=np.zeros(X.shape[1])
    reg=np.full(X.shape[1],RIDGE)
    reg[0]=INTERCEPT_RIDGE
    for _ in range(50):
        p=_sigmoid(offset+X@coefficients)
        grad=X.T@(p-y)+reg*coefficients
        hess=(X.T*(p*(1-p)))@X+np.diag(reg)
        delta=np.linalg.solve(hess,grad)
        coefficients-=delta
        if np.max(np.abs(delta))<1e-10:
            break
    return coefficients


def predict(frame: pd.DataFrame, finish: np.ndarray, sub: np.ndarray, kind: str):
    base=_base(frame)
    f=_sigmoid(_logit(1-base[:,2])+design(frame,"finish",kind)@finish)
    s=_sigmoid(_logit(base[:,1]/(base[:,0]+base[:,1]))
               +design(frame,"sub",kind)@sub)
    p=np.column_stack((f*(1-s),f*s,1-f))
    if not np.allclose(p.sum(axis=1),1,atol=1e-9) or not np.isfinite(p).all():
        raise ValueError("Invalid quality-conditional method probability simplex")
    return p


def study() -> dict:
    df,quality_audit=load_and_join()
    if len(df)!=153:
        raise ValueError("Only pre-Nov14 153 conditional-method cases allowed")
    if quality_audit["coverage"]<0.80:
        raise ValueError("Too many fighter identity mismatches for quality evaluation")
    dates=sorted(df.event_date.unique())
    if len(dates)!=12 or not dates[-1].startswith("2026-11-07"):
        raise ValueError("Incorrect chronology")
    kind=("baseline","intercept","opponent_only","quality_only","quality_plus_opponent")
    scored={k:{"actual":[],"p":[]} for k in kind}
    folds=[]
    for event in dates[MIN_INITIAL_DATES:]:
        training=df.loc[df.event_date<event].copy()
        testing=df.loc[df.event_date==event].copy()
        if training.event_date.max()>=event or len(training)<60:
            raise ValueError("Later fight outcomes leaked into fit")
        p={"baseline":_base(testing)}
        for name in kind[1:]:
            finish=fit(training,"finish",name)
            sub=fit(training,"sub",name)
            p[name]=predict(testing,finish,sub,name)
        fold={"event_date":str(event)[:10],"trained_through":str(training.event_date.max())[:10],
              "train_n":len(training),"test_n":len(testing),"metrics":{}}
        for name in kind:
            y=_target(testing)
            fold["metrics"][name]=metrics(y,p[name])
            scored[name]["actual"].extend(list(y))
            scored[name]["p"].extend(p[name].tolist())
        folds.append(fold)
    overall={name:metrics(np.asarray(o["actual"]),np.asarray(o["p"])) for name,o in scored.items()}
    best_simple=overall["intercept"]
    q=overall["quality_plus_opponent"]
    quality_only=overall["quality_only"]
    return {
        "schema":"WSHL_X_153_PRIOR_UFC_ELO_QUALITY_CONDITIONAL_METHOD_SHADOW_V1",
        "status":"RETROSPECTIVE_RESEARCH_ONLY_NO_AUTOMATIC_PROMOTION",
        "date":"2026-11-16",
        "source_CSV":"clean153_causal_method_inputs.csv",
        "source_opponent_quality":"UFCStats-compatible result archive through Nov07",
        "past_only_elo_ratings":True,
        "quality_match_coverage":quality_audit,
        "initial_training_bouts":64,
        "folds":folds,
        "overall":overall,
        "incremental_quality_vs_intercept":{
            "top_method_extra_hits":q["correct"]-best_simple["correct"],
            "brier_reduction":best_simple["brier"]-q["brier"],
            "logloss_reduction":best_simple["logloss"]-q["logloss"],
        },
        "quality_only_vs_intercept":{
            "top_method_extra_hits":quality_only["correct"]-best_simple["correct"],
            "brier_reduction":best_simple["brier"]-quality_only["brier"],
            "logloss_reduction":best_simple["logloss"]-quality_only["logloss"],
        },
        "holdout_methods_conditional_on_actual_winner":True,
        "not_exact_selected_fighter_plus_method_betting_performance":True,
        "source_is_third_party_ufcstats_compatible_not_direct_primary_export":True,
        "nov14_ufc334_stats_or_results_not_training_inputs":True,
        "original_stage_a_b_simulation_weights_changed":False,
        "method_candidate_not_for_stage_b_pricing":True,
    }


if __name__ == "__main__":
    print(json.dumps(study(),indent=2))
