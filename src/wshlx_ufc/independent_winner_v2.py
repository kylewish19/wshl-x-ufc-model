"""Independent winner head trained from as-of fighter matchup differences.

Separate from Reference/Historical/Unified and from bookmaker prices.
Fighter role reversal negates the feature vector and guarantees symmetry:
P(A wins | A,B) + P(B wins | B,A) == 1 exactly.
Used ONLY in the Finish v2 research runner, not in existing Stage A.
"""
from __future__ import annotations
import math
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .finish_v1_research import method_features, prior_win_probability
from .historical_baselines import _winner_probabilities

def winner_features(f:dict)->np.ndarray:
    if f["feature_as_of_exclusive"]!=f["event_date"]:
        raise ValueError("Future leakage: fighter history must be event-date exclusive")
    v=method_features(f,"a")-method_features(f,"b")
    if not np.all(np.isfinite(v)):
        raise ValueError("Nonfinite pre-event fighter advantage")
    return v

def fit_winner_logistic(features:list[dict],labels:list[dict],*,before:str):
    byid={x["bout_id"]:x for x in labels}
    if len(byid)!=len(labels):
        raise ValueError("Duplicate results")
    X=[];y=[]
    for f in features:
        if not "2021-01-01"<=f["event_date"]<before:
            continue
        label=byid[f["bout_id"]]
        if label["result_status"]!="DECISIVE":
            continue
        a_win=int(label["label_a_win"])
        v=winner_features(f)
        X.extend((v,-v))
        y.extend((a_win,1-a_win))
    if len(X)<200:
        raise ValueError("Insufficient chronological winner training bouts")
    # Fit-intercept False plus symmetric data guarantee side-swap coherence.
    # C is fixed before test, never fitted to event outcomes.
    model=make_pipeline(
        StandardScaler(),
        LogisticRegression(C=.20,fit_intercept=False,max_iter=2000),
    )
    model.fit(np.asarray(X,float),np.asarray(y,int))
    return {"name":"winner_symmetric_logistic_v1","fit_before_exclusive":before,
            "training_decisive_bouts":len(X)//2,"classifier":model,
            "research_only_no_production_winner_change":True}

def predict_winner(f:dict,bundle:dict)->dict[str,float]:
    v=winner_features(f).reshape(1,-1)
    p=float(bundle["classifier"].predict_proba(v)[0,1])
    # Independently compute swapped view and fail if symmetry is broken.
    inverse=float(bundle["classifier"].predict_proba(-v)[0,1])
    if not (0<=p<=1) or abs(p+inverse-1)>1e-10:
        raise ValueError("Fighter-order reversal broke winner coherence")
    return {
       "prior_ufc_winrate":float(prior_win_probability(f)),
       "past_only_elo":float(_winner_probabilities(f)["past_only_ufc_elo"]),
       "new_symmetric_logistic":p,
    }

def joint_from_conditional(p_a:float,conditional:np.ndarray)->np.ndarray:
    c=np.asarray(conditional,float)
    if c.shape!=(2,3):
        raise ValueError("Requires both potential winners' KO/SUB/DEC probabilities")
    if np.min(c)<0 or np.max(np.abs(c.sum(axis=1)-1))>1e-8:
        raise ValueError("Conditional method distributions invalid")
    if not 0<=p_a<=1:
        raise ValueError("Winner probability invalid")
    out=np.r_[p_a*c[0],(1-p_a)*c[1]]
    if abs(out.sum()-1)>1e-8 or abs(out[:3].sum()-p_a)>1e-8:
        raise ValueError("Joint model marginal mismatch")
    return out
