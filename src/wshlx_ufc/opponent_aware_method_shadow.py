"""Fixed-hypothesis opponent-aware KO/SUB/DEC challenger: research only.

Uses archived causal *pre-bout* fighter metrics and method baselines.
Training targets are methods CONDITIONAL ON THE ACTUAL WINNING FIGHTER:
even a successful conditional challenger is NOT a proven fighter+method pick.
Chronological expanding-window backtest is grouped by event date, never random.
This module neither trains an official model nor authorizes any betting market.

Compare baseline vs offset-intercept-only vs opponent-feature model to ensure
improvement is actually due to the defensive features, not finish-rate drift.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

DATA_PATH = (
    Path(__file__).resolve().parents[2] /
    "reports/ufcvegas124_2026-11-07/full_stats/clean153_causal_method_inputs.csv"
)
METHODS = ("KO", "SUB", "DEC")
RIDGE = 20.0
INTERCEPT_RIDGE = 10.0
MIN_INITIAL_DATES = 5
EPS = 1e-6
FINISH_FEATURES = (
    "opp_prior_finish_loss_rate_shrunk",
    "opp_sig_defense_shrunk",
    "winner_prior_finish_win_rate_shrunk",
    "winner_td_access_vs_opponent_td_defense",
    "opponent_recent_finish_rate_shrunk",
    "five_round_fight",
)
SUB_FEATURES = (
    "winner_prior_sub_win_rate_shrunk",
    "opp_prior_sub_loss_rate_shrunk",
    "winner_prior_ko_win_rate_shrunk",
    "opp_td_defense_shrunk",
    "winner_sub_attempt_rate",
)
FORBIDDEN_FEATURES = frozenset((
    "winner", "method", "clean_actual_method", "clean_displayed_method",
    "clean_winner_correct", "fight_result", "result", "fight_sig_landed",
    "fight_td_landed", "fight_kd", "postfight", "fanduel_odds",
))


def _numeric(df: pd.DataFrame, field: str) -> np.ndarray:
    if field not in df.columns:
        raise ValueError("Missing pre-fight field: " + field)
    return pd.to_numeric(df[field], errors="coerce").to_numpy(dtype=float)


def _shrunk(df: pd.DataFrame, field: str, count: str, prior: float) -> np.ndarray:
    x = _numeric(df, field)
    n = np.nan_to_num(_numeric(df, count), nan=0.0, posinf=0.0, neginf=0.0)
    n = np.clip(n, 0.0, 20.0)
    # Unknown metrics are neutral priors rather than zero defensive ability.
    x = np.where(np.isfinite(x), x, prior)
    return (n * x + 3.0 * prior) / (n + 3.0)


def _safe(df: pd.DataFrame, name: str, fallback: float) -> np.ndarray:
    v = _numeric(df, name)
    return np.where(np.isfinite(v), v, fallback)


def features(frame: pd.DataFrame, stage: str) -> np.ndarray:
    """Pre-register a small, bounded, fully pre-fight-safe feature family."""
    op_kol = _shrunk(frame, "opponent_ko_loss_rate", "opponent_prior_bouts", 0.12)
    op_sul = _shrunk(frame, "opponent_sub_loss_rate", "opponent_prior_bouts", 0.09)
    opp_td = _shrunk(frame, "opponent_td_defense", "opponent_prior_bouts", 0.58)
    if stage == "finish":
        opponent_str = _shrunk(frame,"opponent_sig_defense","opponent_prior_bouts",0.52)
        own_fin = _shrunk(frame,"winner_finish_win_rate","winner_prior_bouts",0.55)
        recent = _shrunk(frame,"opponent_recent5_finish_rate","opponent_prior_bouts",0.50)
        own_td = np.clip(_safe(frame,"winner_td_landed_per15",1.2),0.0,8.0)/8.0
        scheduled = (_safe(frame,"scheduled_seconds",900.0)>=1500.0).astype(float)
        cols = [
            2.0 * (op_kol + op_sul - 0.22),
            2.0 * (opponent_str - 0.52),
            2.0 * (own_fin - 0.55),
            (1.0-opp_td)*own_td-0.10,
            2.0 * (recent-0.50),
            scheduled-0.17,
        ]
    elif stage == "sub":
        own_sub = _shrunk(frame,"winner_sub_win_rate","winner_prior_bouts",0.20)
        own_ko = _shrunk(frame,"winner_ko_win_rate","winner_prior_bouts",0.36)
        own_sa = np.clip(_safe(frame,"winner_sub_att_per15",0.3),0.0,8.0)/8.0
        cols = [
            2.0*(own_sub-0.20), 2.0*(op_sul-0.09),
            2.0*(own_ko-0.36), 2.0*(opp_td-0.58), own_sa-0.06,
        ]
    else:
        raise ValueError("Unknown conditional-method stage")
    return np.stack(cols,axis=1)


def _sigmoid(logits: np.ndarray) -> np.ndarray:
    z = np.clip(logits, -35., 35.)
    return 1. / (1. + np.exp(-z))


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p,EPS,1.-EPS)
    return np.log(p/(1.-p))


def _base(frame: pd.DataFrame) -> np.ndarray:
    matrix = np.stack([_numeric(frame, "base_"+m) for m in METHODS],axis=1)
    if (np.any(~np.isfinite(matrix)) or np.any(matrix<=0.) or
            not np.allclose(matrix.sum(axis=1),1.0,atol=1e-5)):
        raise ValueError("Invalid pre-fight baseline conditional probabilities")
    return matrix


def _target(df: pd.DataFrame) -> np.ndarray:
    m = df["clean_actual_method"].astype(str).to_numpy()
    if set(m)-set(METHODS):
        raise ValueError("Only decided fight methods KO/SUB/DEC are gradeable")
    return m


def fit_stage(frame: pd.DataFrame, *, stage: str, opponent_aware: bool) -> np.ndarray:
    methods = _target(frame)
    probabilities = _base(frame)
    subset = methods!="DEC" if stage=="sub" else np.ones(len(frame),dtype=bool)
    if not np.any(subset):
        raise ValueError("No valid conditional-method training rows")
    if stage=="finish":
        y = (methods!="DEC").astype(float)[subset]
        offset = _logit(1-probabilities[subset,2])
    elif stage=="sub":
        y = (methods[subset]=="SUB").astype(float)
        offset = _logit(probabilities[subset,1] /
                        (probabilities[subset,0]+probabilities[subset,1]))
    else:
        raise ValueError("Unknown stage")
    X = np.ones((len(y),1),dtype=float)
    if opponent_aware:
        X = np.column_stack((X,features(frame,stage)[subset]))
    beta = np.zeros(X.shape[1])
    reg = np.full(X.shape[1],RIDGE)
    reg[0] = INTERCEPT_RIDGE
    for _ in range(50):
        p = _sigmoid(offset + X @ beta)
        w = p*(1.-p)
        grad = X.T @ (p-y) + reg*beta
        hess = (X.T*w) @ X + np.diag(reg)
        delta = np.linalg.solve(hess,grad)
        beta -= delta
        if np.max(np.abs(delta))<1e-10:
            break
    return beta


def predict(frame: pd.DataFrame, *, finish_beta: np.ndarray,
            sub_beta: np.ndarray, opponent_aware: bool) -> np.ndarray:
    base = _base(frame)
    def design(stage: str):
        x = np.ones((len(frame),1),dtype=float)
        return np.column_stack((x,features(frame,stage))) if opponent_aware else x
    finish = _sigmoid(_logit(1-base[:,2])+design("finish")@finish_beta)
    sub_cond = _sigmoid(
        _logit(base[:,1]/(base[:,0]+base[:,1]))+design("sub")@sub_beta
    )
    prob = np.stack((finish*(1-sub_cond),finish*sub_cond,1-finish),axis=1)
    if np.any(~np.isfinite(prob)) or not np.allclose(prob.sum(axis=1),1):
        raise ValueError("Invalid challenger output")
    return prob


def metrics(actual: np.ndarray, prob: np.ndarray) -> dict:
    truth = np.asarray(actual,dtype=str)
    if prob.shape != (len(truth),3):
        raise ValueError("Bad method dimension")
    labels = np.asarray(METHODS)
    observed = truth[:,None]==labels[None,:]
    pred = labels[np.argmax(prob,axis=1)]
    return {
        "n":int(len(truth)),
        "correct":int(np.sum(pred==truth)),
        "accuracy":float(np.mean(pred==truth)),
        "brier":float(np.mean(np.sum((prob-observed.astype(float))**2,axis=1))),
        "logloss":float(-np.mean(np.log(np.clip(
            prob[np.arange(len(truth)),np.argmax(observed,axis=1)],1e-12,1)))),
        "method_calls":{m:int(np.sum(pred==m)) for m in METHODS},
        "true_methods":{m:int(np.sum(truth==m)) for m in METHODS},
    }


def backtest(data_path: Path = DATA_PATH) -> dict:
    df = pd.read_csv(data_path,low_memory=False)
    if len(df)!=153:
        raise ValueError("Expected fixed 153 causal method feedback rows")
    if df["event_date"].isna().any() or "clean_actual_method" not in df:
        raise ValueError("Date and actual method required as labels")
    sorted_dates = sorted(df.event_date.unique())
    if len(sorted_dates)!=12 or not sorted_dates[-1].startswith("2026-11-07"):
        raise ValueError("Unexpected historical event cutoff")
    if "2026-11-14" in set(df.event_date.astype(str).str[:10]):
        raise ValueError("UFC334 may not be included in pre-event candidate fit")
    if set(FINISH_FEATURES)&FORBIDDEN_FEATURES or set(SUB_FEATURES)&FORBIDDEN_FEATURES:
        raise ValueError("Result or market data leaked into pre-fight candidate feature list")
    all_scored={key:{"y":[],"p":[]} for key in ("baseline","intercept","opponent_features")}
    fold_results=[]
    for event in sorted_dates[MIN_INITIAL_DATES:]:
        train=df.loc[df.event_date<event].copy()
        test=df.loc[df.event_date==event].copy()
        if not len(test) or len(train)<60 or train.event_date.max()>=event:
            raise ValueError("No chronological held-out event split")
        fitted={}
        for kind,aware in (("intercept",False),("opponent_features",True)):
            f = fit_stage(train,stage="finish",opponent_aware=aware)
            s = fit_stage(train,stage="sub",opponent_aware=aware)
            fitted[kind]=predict(test,finish_beta=f,sub_beta=s,opponent_aware=aware)
        probabilities={"baseline":_base(test),**fitted}
        results={}
        for name,p in probabilities.items():
            result=metrics(_target(test),p)
            results[name]=result
            all_scored[name]["y"].extend(_target(test))
            all_scored[name]["p"].extend(p.tolist())
        fold_results.append({
            "event_date":str(event)[:10],
            "max_training_event_date":str(train.event_date.max())[:10],
            "training_bouts":int(len(train)),
            "held_out_bouts":int(len(test)),
            "metrics":results,
        })
    aggregate={
        k:metrics(np.array(v["y"]),np.array(v["p"]))
        for k,v in all_scored.items()
    }
    selected_feature_gain={
        "brier_improvement_over_intercept": (
            aggregate["intercept"]["brier"]-aggregate["opponent_features"]["brier"]),
        "logloss_improvement_over_intercept": (
            aggregate["intercept"]["logloss"]-aggregate["opponent_features"]["logloss"]),
        "extra_correct_method_labels": (
            aggregate["opponent_features"]["correct"]-aggregate["intercept"]["correct"]),
    }
    return {
        "schema":"WSHL_X_OPPONENT_AWARE_METHOD_CONDITIONAL_ABLATION_V1",
        "status":"RESEARCH_SHADOW_NOT_PROMOTED",
        "training_set_rows":153,
        "source_file":str(data_path.relative_to(Path(__file__).resolve().parents[2])),
        "fitted_before_each_event_only":True,
        "initial_training_events":MIN_INITIAL_DATES,
        "heldout_events":len(fold_results),
        "heldout_bouts":len(all_scored["baseline"]["y"]),
        "conditional_on_actual_winning_fighter_oracle":True,
        "not_exact_fighter_plus_method_or_wager_grading":True,
        "features_prior_to_prediction_only":True,
        "baseline_forecast_origin":"PRE_BOUT_CAUSAL_RECONSTRUCTION_NOT_ORIGINAL_FIGHT_DAY_MARKET_SNAPSHOT",
        "regularization":{"intercept":INTERCEPT_RIDGE,"feature":RIDGE},
        "finish_features":list(FINISH_FEATURES),
        "submission_features":list(SUB_FEATURES),
        "folds":fold_results,
        "aggregate":aggregate,
        "incremental_feature_gain":selected_feature_gain,
        "promotion_decision":"REJECT_FEATURE_CHALLENGER_UNLESS_IT_BEATS_INTERCEPT_ONLY_ON_FUTURE_CHRONOLOGICAL_TESTS",
        "champion_changed":False,
        "no_current_event_training_in_its_own_fold":True,
        "no_fanduel_price_used":True,
        "nov14_uFC334_test_not_in_this_validation":True,
    }
