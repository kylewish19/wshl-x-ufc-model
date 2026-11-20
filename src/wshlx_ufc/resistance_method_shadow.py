"""Selected-fighter KO/SUB/DEC candidate using historical survival/durability.

A challenger only: never replaces Reference/Historical/Unified, winner P,
frozen Stage A, 10000 simulations, Stage B, FanDuel gates or official picks.

Fitness checks:
* Pinned pre-Nov14 UFCStats-compatible source archive, never post-event
  current fight data; upcoming event can be queried without result insertion
* Method training uses a fighter's actual winner ONLY inside earlier labeled
  training examples; evaluation features always use BOTH original fighters
* Each evaluated card takes each model's ORIGINAL frozen selected fighter
* Historical method calibration fit excludes the evaluated event and future
* Exact fighter+method is always incorrect when original winner is incorrect
* Full six-way Brier and log-loss measured on decided fights only
"""
from __future__ import annotations
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .prefight_finish_resistance import load_and_build
from .opponent_quality_join import canonical
from .opponent_aware_method_shadow import _logit, _sigmoid, _base, _target
from .predicted_side_method_shadow import (
    ROOT,EVENTS,MODELS,_check_event_lock,_model_joint_and_side,_per_side,
    _score_joint,_totals,
)
from .joint_coherence_shadow import JOINT_KEYS,SIDES,METHODS,outcomes_for_event

VARIANTS=("original_coherent","intercept_only","resistance")
RIDGE=24.
RIDGE_INTERCEPT=12.
RESISTANCE_NAMES_FINISH=(
    "attacker_prior_kd_pace",
    "opponent_prior_kd_absorbed_pace",
    "opponent_ko_loss_rate",
    "opponent_finish_survival_vs_finisher",
    "attacker_sub_attempt_pace_vs_opponent_sub_loss",
    "opponent_knockdown_survival",
    "five_round",
)
RESISTANCE_NAMES_SUB=(
    "attacker_sub_attempt_pace",
    "opponent_sub_loss_rate",
    "opponent_submission_threat_nonloss",
    "attacker_takedown_access_vs_defense",
    "opponent_control_absorbed_pace",
    "opponent_prior_stats_quality",
)


def _safe(x,default=0.):
    try:
        f=float(x)
        return f if math.isfinite(f) else default
    except (TypeError,ValueError):
        return default


def _cap(x,lo,hi):
    return max(lo,min(hi,x))


def _snapshot_index(snapshots:list[dict])->dict:
    index={}
    for x in snapshots:
        a,b=canonical(x["a"]),canonical(x["b"])
        key=(x["event_date"],tuple(sorted((a,b))))
        if not a or not b or a==b or key in index:
            raise ValueError("Ambiguous historical fighter identity/date")
        index[key]=x
    return index


def _source_perspective(snap:dict,picked:str):
    a,b=canonical(snap["a"]),canonical(snap["b"])
    win=canonical(picked)
    if win==a:
        return snap["a_pre"],snap["b_pre"]
    if win==b:
        return snap["b_pre"],snap["a_pre"]
    raise ValueError("Predicted fighter not member of original bout")


def _strength_frame(owner:dict,other:dict,p:np.ndarray,scheduled:int)->dict:
    return {
        "base_KO":float(p[0]),"base_SUB":float(p[1]),
        "base_DEC":float(p[2]),
        "scheduled_seconds":float(scheduled),
        "own_ufc_prior_bouts":owner["prior_ufc_bouts"],
        "opponent_ufc_prior_bouts":other["prior_ufc_bouts"],
        "own_stat_bouts":owner["prior_stats_bouts"],
        "opponent_stat_bouts":other["prior_stats_bouts"],
        "own_kd_per15":owner["own_knockdowns_per15"],
        "own_sub_attempts_per15":owner["own_sub_attempts_per15"],
        "own_takedowns_per15":owner["own_takedowns_landed_per15"],
        "opp_kd_absorbed_per15":other["knockdowns_absorbed_per15"],
        "opp_prior_ko_loss_rate":other["ko_loss_rate_shrunk"],
        "opp_prior_sub_loss_rate":other["sub_loss_rate_shrunk"],
        "opp_survival_vs_finisher":other["dangerous_opponent_finish_survival"],
        "opp_kd_nonko_survival":other["knockdown_nonko_survival_rate"],
        "opp_submission_threat_nonloss":other["submission_threat_nonloss_rate"],
        "opp_takedown_defense":other["takedown_defense_rate_shrunk"],
        "opp_control_absorbed_per15":other["control_absorbed_sec_per15"],
        "opponent_prior_dangerous_exposures":other["prior_dangerous_opponent_bouts"],
        "opponent_prior_knockdown_exposures":other["prior_knockdown_bouts"],
        "opp_prior_stats_coverage":other["stats_coverage"],
    }


def _data_match(index:dict,day:str,a:str,b:str)->dict:
    key=(day,tuple(sorted((canonical(a),canonical(b)))))
    snap=index.get(key)
    if snap is None:raise ValueError("No pre-event resistance snapshot for "+day+" "+a+" / "+b)
    if not snap["current_fight_result_not_a_feature"]:
        raise ValueError("Post-event features are not allowed")
    return snap


def _matrix(frame:pd.DataFrame,stage:str,resistance:bool)->np.ndarray:
    n=len(frame)
    if not resistance:return np.ones((n,1),dtype=float)
    val=lambda k,neutral:np.array([_safe(v,neutral) for v in frame[k]],dtype=float)
    own_kd=val("own_kd_per15",.35)
    opp_kd=val("opp_kd_absorbed_per15",.35)
    own_sa=val("own_sub_attempts_per15",.4)
    own_td=val("own_takedowns_per15",1.3)
    k_loss=val("opp_prior_ko_loss_rate",.12)
    sub_loss=val("opp_prior_sub_loss_rate",.09)
    dangerous=val("opp_survival_vs_finisher",.55)
    kd_survival=val("opp_kd_nonko_survival",.5)
    sub_survival=val("opp_submission_threat_nonloss",.75)
    td_def=val("opp_takedown_defense",.58)
    ctrl=val("opp_control_absorbed_per15",70.)
    stats=val("opp_prior_stats_coverage",0.)
    kd_expo=val("opponent_prior_knockdown_exposures",0.)
    danger_expo=val("opponent_prior_dangerous_exposures",0.)
    if stage=="finish":
        columns=[
            (np.clip(own_kd,0,3)-.35)/2,
            (np.clip(opp_kd,0,3)-.35)/2,
            np.clip(k_loss-.12,-.12,.5)*2,
            (np.clip(dangerous,0,1)-.55)*np.minimum(1,danger_expo/4),
            (np.clip(own_sa,0,4)-.4)*(sub_loss-.09)/2,
            (np.clip(kd_survival,0,1)-.5)*np.minimum(1,kd_expo/4),
            (val("scheduled_seconds",900)>=1500).astype(float)-.17,
        ]
    elif stage=="sub":
        columns=[
            (np.clip(own_sa,0,4)-.4)/3,
            np.clip(sub_loss-.09,-.09,.6)*2,
            np.clip(sub_survival-.75,-.75,.25),
            (1-np.clip(td_def,0,1))*np.clip(own_td,0,8)/8-.1,
            (np.clip(ctrl,0,300)-70)/300,
            np.clip(stats,0,1)-.85,
        ]
    else:raise ValueError("Method stage must be finish or sub")
    X=np.column_stack((np.ones(n),*columns))
    if not np.isfinite(X).all():raise ValueError("Resistance features nonfinite")
    return X


def _fit(frame:pd.DataFrame,stage:str,resistance:bool):
    y=_target(frame)
    base=_base(frame)
    rows=np.ones(len(frame),dtype=bool) if stage=="finish" else y!="DEC"
    if not np.any(rows):raise ValueError("No training methods available")
    target=(y!="DEC").astype(float)[rows] if stage=="finish" else (
        y[rows]=="SUB").astype(float)
    odds=_logit(1-base[rows,2]) if stage=="finish" else _logit(
        base[rows,1]/(base[rows,0]+base[rows,1]))
    X=_matrix(frame,stage,resistance)[rows]
    b=np.zeros(X.shape[1])
    penalty=np.full(X.shape[1],RIDGE)
    penalty[0]=RIDGE_INTERCEPT
    for _ in range(50):
        p=_sigmoid(odds+X@b)
        w=p*(1-p)
        gradient=X.T@(p-target)+penalty*b
        hessian=(X.T*w)@X+np.diag(penalty)
        delta=np.linalg.solve(hessian,gradient)
        b-=delta
        if max(abs(z) for z in delta)<1e-10:break
    return b


def _predict(frame:pd.DataFrame,f:np.ndarray,s:np.ndarray,resistance:bool):
    original=_base(frame)
    finish=_sigmoid(_logit(1-original[:,2])+_matrix(frame,"finish",resistance)@f)
    sub=_sigmoid(_logit(original[:,1]/(original[:,0]+original[:,1]))
                 +_matrix(frame,"sub",resistance)@s)
    p=np.stack((finish*(1-sub),finish*sub,1-finish),axis=1)
    if not np.allclose(p.sum(axis=1),1,atol=1e-9) or not np.isfinite(p).all():
        raise ValueError("Candidate method distribution inconsistent")
    return p


def evaluate()->dict:
    # ONE source ingest, with all historical snapshots plus future query at
    # Nov14. Inference never processes Nov14 fight outcomes as features.
    last_slug,last_raw,last_grade=EVENTS[-1]
    last_locked=_check_event_lock(last_slug,last_raw,last_grade)[1]
    pairs=[(x["a"],x["b"]) for x in last_locked["fights"]]
    snapshots,coverage=load_and_build(
        as_of_exclusive="2026-11-14",query_bouts=pairs)
    index=_snapshot_index(snapshots)
    historical=pd.read_csv(
        ROOT/"reports/ufcvegas124_2026-11-07/full_stats/clean153_causal_method_inputs.csv",
        low_memory=False)
    if len(historical)!=153:raise ValueError("Unexpected historic training data")
    cases=[]
    for row in historical.to_dict("records"):
        day=row["event_date"][:10]
        snap=_data_match(index,day,row["fighter_a"],row["fighter_b"])
        owner,other=_source_perspective(snap,row["winner"])
        p=np.array([float(row["base_"+m]) for m in METHODS])
        case=_strength_frame(owner,other,p,int(row["scheduled_seconds"]))
        case["event_date"]=row["event_date"]
        case["clean_actual_method"]=row["clean_actual_method"]
        cases.append(case)
    frame=pd.DataFrame(cases)
    if len(frame)!=153 or frame["event_date"].isna().any():
        raise ValueError("Missing historical feature rows")
    rows=[]
    event_info=[]
    for slug,path,result_path in EVENTS:
        raw,frozen,grade=_check_event_lock(slug,path,result_path)
        event_day=raw["event_date"]
        labels=outcomes_for_event(slug,grade)
        train=frame.loc[frame.event_date.str[:10]<event_day].copy()
        if len(train)<100 or np.any(train.event_date.str[:10]>=event_day):
            raise ValueError("Train overlap with evaluation event")
        candidates={
            "intercept_only":(
                _fit(train,"finish",False),_fit(train,"sub",False),False),
            "resistance":(
                _fit(train,"finish",True),_fit(train,"sub",True),True),
        }
        for fight,lock in zip(raw["fights"],frozen["fights"]):
            n=fight["fight_no"]
            observed=labels[n]
            if observed["method"]!="DRAW" and observed["winner"] not in (
                fight["a"],fight["b"]):
                raise ValueError("Actual winner mismatch")
            snap=_data_match(index,event_day,fight["a"],fight["b"])
            for model in MODELS:
                joint,p_a,picked=_model_joint_and_side(model,fight,lock)
                condition={side:_per_side(joint,side) for side in ("A","B")}
                frames=[]
                for side in ("A","B"):
                    f=fight["a"] if side=="A" else fight["b"]
                    owner,other=_source_perspective(snap,f)
                    frames.append(_strength_frame(owner,other,condition[side],
                                                 int(fight["scheduled_seconds"])))
                inference=pd.DataFrame(frames)
                predicted={
                    "original_coherent":{
                        k:condition[k[0]][METHODS.index(k[2:])]*(
                            p_a if k[0]=="A" else 1-p_a)
                        for k in JOINT_KEYS}
                }
                for name,(fc,sc,has_factors) in candidates.items():
                    array=_predict(inference,fc,sc,has_factors)
                    predicted[name]={
                        k:float(array[0 if k[0]=="A" else 1,
                                      METHODS.index(k[2:])])*(
                            p_a if k[0]=="A" else 1-p_a)
                        for k in JOINT_KEYS}
                chosen_side="A" if picked==fight["a"] else "B"
                true_side=("A" if observed["winner"]==fight["a"] else "B"
                           if observed["winner"]==fight["b"] else None)
                variants={}
                for name,masses in predicted.items():
                    if (not np.isfinite(list(masses.values())).all()
                            or abs(sum(masses.values())-1)>1e-8
                            or abs(sum(masses[k] for k in SIDES["A"])-p_a)>1e-8):
                        raise ValueError("Method challenger changed frozen winner marginal")
                    top=max(METHODS,key=lambda m:masses[chosen_side+"_"+m])
                    variants[name]={
                        "selected_method":top,
                        "exact_fighter_method_correct":bool(
                            true_side==chosen_side and top==observed["method"]),
                        "six_way_scores":(
                            None if true_side is None else
                            _score_joint(masses,fighter_side=true_side,
                                         method=observed["method"])),
                        "bet_approved":False,
                    }
                rows.append({
                    "event":slug,"fight_no":n,"model":model,
                    "original_locked_fighter_pick":picked,
                    "original_locked_fighter_probability":(
                        p_a if chosen_side=="A" else 1-p_a),
                    "actual_winner":observed["winner"],
                    "actual_method":observed["method"],
                    "winner_correct":bool(true_side==chosen_side),
                    "resistance_source_is_previous_fights_only":True,
                    "variants":variants,
                })
        event_info.append({
            "event":slug,"date":event_day,
            "training_rows":int(len(train)),"fights":len(raw["fights"]),
            "pre_event_source_verified":True,
        })
    summary={m:{v:_totals(rows,m,v) for v in VARIANTS} for m in MODELS}
    by_event={e[0]:{m:{v:_totals([r for r in rows if r["event"]==e[0]],m,v)
                         for v in VARIANTS} for m in MODELS} for e in EVENTS}
    return {
        "schema":"WSHL_X_FINISH_RESISTANCE_SELECTED_FIGHTER_EXACT_METHOD_RESEARCH_V1",
        "status":"RESEARCH_ONLY_NO_PROSPECTIVE_PROMOTION",
        "historical_dated_stats":coverage,
        "feature_training_rows":len(frame),
        "event_evaluations":event_info,
        "three_model_fight_records":len(rows),
        "decisive_fights":40,"draws":1,
        "source_is_pinned_secondary_archive":True,
        "historical_model_winner_marginals_unchanged":True,
        "original_stage_a_b_models_weights_simulations_unchanged":True,
        "stage_b_wager_approval":False,
        "feature_not_actual_getups":True,
        "retrospective_challenger_not_prospective_pre_registered":True,
        "method_targets_only_used_to_train_on_older_fights":True,
        "summary":summary,"by_event":by_event,
        "rows":rows,"model_promoted":False,
    }


if __name__=="__main__":
    result=evaluate()
    print("RESISTANCE_METHOD_BENCHMARK_START")
    print(json.dumps({k:result[k] for k in (
        "schema","status","historical_dated_stats","feature_training_rows",
        "event_evaluations","decisive_fights","draws","summary",
        "by_event","model_promoted",
    )},sort_keys=True))
    print("RESISTANCE_METHOD_BENCHMARK_END")
