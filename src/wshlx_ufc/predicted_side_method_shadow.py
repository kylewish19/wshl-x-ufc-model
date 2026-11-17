"""Pre-fight *predicted-fighter-oriented* winner+method SHADOW grading.

This is the missing step beyond earlier conditional-on-actual-winner studies.
It combines the exact saved Stage A winner selection with KO/SUB/DEC for
THAT SELECTED FIGHTER, and grades the pair together, including wrong sides.

Its training data remains the same 153 reconstructed causal method feedback
examples, with each event training strictly BEFORE that event date. Its
opponent-quality inputs are historical UFC-only Elo at the time of each
previous meeting, never a fighter's future career rating. Two candidate
calibrators are compared with the own-model raw baseline method:
 - intercept_only (finish/decision and submission/KO logit intercepts)
 - quality_only (the intercepts + opponent historical quality)

The three historic event forecasts ARE retrospectively re-evaluated after
our model changes, not pre-registered prospective performance. This tool
cannot promote a model or authorize a betting price. Archived Stage A/B
and all model weight artifacts remain untouched.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .opponent_quality_join import (
    ARCHIVE, canonical, load_and_join,
)
from .prefight_opponent_quality import (
    build_historical_opponent_quality, load_ufcstats_results,
)
from .quality_aware_method_shadow import (
    fit, predict,
)
from .joint_coherence_shadow import (
    ROOT, EVENTS, JOINT_KEYS, SIDES, METHODS,
    outcomes_for_event,
)

VARIANTS = ("original_coherent", "intercept_only", "quality_only")
MODELS = ("reference", "historical", "unified")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_event_lock(slug: str, raw_path: str, grade_path: str) -> tuple[dict, dict, dict]:
    path = ROOT / raw_path
    raw_bytes = path.read_bytes()
    raw = json.loads(raw_bytes)
    grade = _read_json(ROOT / grade_path)
    lock = _read_json(path.with_name("stage_a_final_selection.json"))
    sha = hashlib.sha256(raw_bytes).hexdigest()
    if (
        lock.get("stage_a_frozen") is not True
        or lock.get("odds_used") is not False
        or raw.get("odds_used") is not False
        or lock.get("raw_model_sha256") != sha
    ):
        raise ValueError("No verified odds-blind frozen Stage A/raw match")
    if not (
        raw["event_date"] == grade["event_date"] == lock["event_date"]
    ):
        raise ValueError("Raw, locked, and graded event dates mismatch")
    if len(raw["fights"]) != len(lock["fights"]):
        raise ValueError("A different fight card was locked")
    if [f["fight_no"] for f in raw["fights"]] != [
        f["fight_no"] for f in lock["fights"]
    ]:
        raise ValueError("Original fight identity ordering changed")
    for r, f in zip(raw["fights"], lock["fights"]):
        if r["a"] != f["a"] or r["b"] != f["b"]:
            raise ValueError("Frozen fighter pair mismatch")
    return raw, lock, grade


def _quality_lookup(event_day: str, bouts: list[dict]) -> dict[int,dict]:
    """Pretend draw records exist ONLY to query the pre-event snapshots.

    The fake draw targets never enter a fitted model, never get graded or
    written as observed outcomes; returned data is strictly the pre-event
    snapshot before those placeholder rows would have any state effect.
    They are not part of the actual UFC results history. The same-day
    cutoff is enforced and each competitor can appear only once.
    """
    names=[]
    for f in bouts:
        names.extend((canonical(f["a"]),canonical(f["b"])))
    if len(set(names)) != len(names) or "" in names:
        raise ValueError("Current event has duplicate or unknown fighter identity")
    older = load_ufcstats_results(
        ARCHIVE/"ufc_event_details.csv",
        ARCHIVE/"ufc_fight_results.csv",
        as_of_exclusive=event_day,
    )
    if any(x["date"].isoformat() >= event_day for x in older):
        raise ValueError("Future event history leaked into pre-event features")
    event_token="__PREFIGHT_QUERY_ONLY_NOT_AN_ACTUAL_UFC_RESULT__"
    placeholders = [
        {
            "date": event_day, "event": event_token,
            "a":f["a"], "b":f["b"], "outcome":"D/D",
        } for f in bouts
    ]
    history = build_historical_opponent_quality(older+placeholders)
    snapshots=[x for x in history if x["date"]==event_day and
               x["event"]==event_token]
    if len(snapshots)!=len(bouts):
        raise ValueError("Prefight query missing requested bout features")
    look = {
        (canonical(x["a"]),canonical(x["b"])): x
        for x in snapshots
    }
    out={}
    for f in bouts:
        key=(canonical(f["a"]),canonical(f["b"]))
        if key not in look:
            raise ValueError("Unable to match query to original fighter side")
        out[f["fight_no"]]=look[key]
    return out


def _model_joint_and_side(model: str, raw: dict, locked: dict):
    if model == "reference":
        joint = raw["joint_calibrated"]
        p_a = float(raw["winner_reference_p_a"])
        picked = locked["official_reference_pick"]
        assert picked == raw["winner_reference_pick"]
    elif model == "historical":
        shadow=raw["historical_shadow"]
        joint=shadow["joint_method"]
        p_a=float(shadow["winner_p_a"])
        picked=locked["winner_views"]["historical_shadow"]["pick"]
        assert picked == shadow["winner_pick"]
    elif model == "unified":
        shadow=raw["oof_unified_shadow"]
        joint=shadow["joint_method"]
        p_a=float(shadow["winner_p_a"])
        picked=locked["winner_views"]["oof_unified_shadow"]["pick"]
        assert picked == shadow["winner_pick"]
    else:
        raise ValueError("Model must be original reference, historical or unified")
    if picked not in (raw["a"],raw["b"]) or not 0<p_a<1:
        raise ValueError("Frozen winner selection not compatible with model side")
    if not all(k in joint for k in JOINT_KEYS) or any(
        not math.isfinite(float(joint[k])) or float(joint[k]) <= 0
        for k in JOINT_KEYS
    ):
        raise ValueError("Malformed six-way model original distribution")
    if abs(sum(joint[k] for k in JOINT_KEYS)-1)>1e-5:
        raise ValueError("Original six-way model distribution not normalized")
    # Frozen selection can be below/above 50%; never revise it.
    return joint,p_a,picked


def _per_side(joint: dict, side: str) -> np.ndarray:
    keys=SIDES[side]
    sum_side=sum(joint[k] for k in keys)
    if sum_side<=0:
        raise ValueError("Impossible selected side method distribution")
    return np.array([joint[k]/sum_side for k in keys],dtype=float)


def _quality_inputs(snap: dict, fighter_side: str, base: np.ndarray) -> dict:
    if fighter_side not in ("A","B"):
        raise ValueError("Invalid side")
    first,other=(snap["a_pre"],snap["b_pre"]) if fighter_side=="A" else (
        snap["b_pre"],snap["a_pre"]
    )
    return {
        "base_KO":float(base[0]),
        "base_SUB":float(base[1]),
        "base_DEC":float(base[2]),
        "quality_elo_gap":first["ufc_elo_pre"]-other["ufc_elo_pre"],
        "winner_prior_schedule_strength_gap":(
            first["ufc_avg_opponent_elo_at_meeting_shrunk"]
            - other["ufc_avg_opponent_elo_at_meeting_shrunk"]
        ),
        "winner_prior_defeated_opponents_elo":(
            first["ufc_avg_beaten_opponent_elo_at_meeting_shrunk"]
        ),
        "opponent_prior_defeated_opponents_elo":(
            other["ufc_avg_beaten_opponent_elo_at_meeting_shrunk"]
        ),
        "opponent_prior_ufc_elo":other["ufc_elo_pre"],
        "picked_side_prior_ufc_bouts":first["ufc_prior_bouts"],
        "opponent_prior_ufc_bouts":other["ufc_prior_bouts"],
    }


def _score_joint(joint: dict, *, fighter_side: str, method: str):
    truth=f"{fighter_side}_{method}"
    return {
        "brier":float(sum((joint[k] - int(k==truth))**2 for k in JOINT_KEYS)),
        "logloss":float(-math.log(max(1e-12,joint[truth]))),
    }


def _totals(rows: list[dict], model: str, variant: str):
    decided=[r for r in rows if r["model"]==model and
             r["actual_method"]!="DRAW"]
    if not decided:
        raise ValueError("No decisive test cases")
    return {
        "decisive_fights":len(decided),
        "winner_correct":sum(x["winner_correct"] for x in decided),
        "exact_fighter_method_correct":sum(
            x["variants"][variant]["exact_fighter_method_correct"]
            for x in decided
        ),
        "conditional_method_correct_when_selected_fighter_wins":sum(
            x["variants"][variant]["selected_method"]==x["actual_method"]
            for x in decided if x["winner_correct"]
        ),
        "six_way_brier":float(np.mean([
            x["variants"][variant]["six_way_scores"]["brier"] for x in decided
        ])),
        "six_way_logloss":float(np.mean([
            x["variants"][variant]["six_way_scores"]["logloss"] for x in decided
        ])),
    }


def evaluate() -> dict:
    training,coverage=load_and_join()
    if len(training)!=153 or coverage["matched"]!=153:
        raise ValueError("Historical training quality join incomplete")
    rows=[]
    event_audits=[]
    for slug,raw_path,grade_path in EVENTS:
        raw,frozen,grade=_check_event_lock(slug,raw_path,grade_path)
        date=raw["event_date"]
        results=outcomes_for_event(slug,grade)
        earlier=training[training.event_date.str[:10]<date]
        if earlier.empty or any(earlier.event_date.str[:10]>=date):
            raise ValueError("Same-event outcome leaked into fitted calibrator")
        candidate_params={}
        for kind in ("intercept","quality_only"):
            candidate_params[kind]={
                "finish":fit(earlier,"finish",kind),
                "sub":fit(earlier,"sub",kind),
            }
        snaps=_quality_lookup(date,raw["fights"])
        for f,original in zip(raw["fights"],frozen["fights"]):
            n=f["fight_no"]
            if n not in results:
                raise ValueError("Missing independently graded result")
            actual=results[n]
            if actual["method"]=="DRAW":
                if actual["winner"] is not None:
                    raise ValueError("Draw must have no winning fighter")
            elif actual["winner"] not in (f["a"],f["b"]):
                raise ValueError("Actual fighter differs from frozen fight")
            per_model={}
            for model in MODELS:
                joint,p_a,pick=_model_joint_and_side(model,f,original)
                saved={x:_per_side(joint,x) for x in ("A","B")}
                side="A" if pick==f["a"] else "B"
                # Work in all six outcomes; selection is fixed and no true
                # actual winner orientation enters ANY feature.
                frame=pd.DataFrame([
                    _quality_inputs(snaps[n],x,saved[x])
                    for x in ("A","B")
                ])
                projected={}
                for kind,par in candidate_params.items():
                    calibrated=predict(
                        frame,par["finish"],par["sub"],kind
                    )
                    projected[kind]={
                        key:float(calibrated[0 if key[0]=="A" else 1,
                                              METHODS.index(key[2:])])
                        * (p_a if key[0]=="A" else 1-p_a)
                        for key in JOINT_KEYS
                    }
                original_coherent={
                    key:float(saved[key[0]][METHODS.index(key[2:])])
                    * (p_a if key[0]=="A" else 1-p_a)
                    for key in JOINT_KEYS
                }
                all_versions={"original_coherent":original_coherent,**projected}
                per_variant={}
                for candidate,masses in all_versions.items():
                    if abs(sum(masses.values())-1)>1e-9:
                        raise ValueError("Six-state mass not normalized")
                    if abs(sum(masses[k] for k in SIDES["A"])-p_a)>1e-9:
                        raise ValueError("Selected winner marginal was modified")
                    selected_method=max(
                        METHODS,key=lambda m:masses[side+"_"+m]
                    )
                    exact=(actual["method"]!="DRAW"
                           and pick==actual["winner"]
                           and selected_method==actual["method"])
                    scores=(None if actual["method"]=="DRAW" else
                            _score_joint(
                                masses,
                                fighter_side=(
                                    "A" if f["a"]==actual["winner"] else "B"
                                ),
                                method=actual["method"],
                            ))
                    per_variant[candidate]={
                        "selected_method":selected_method,
                        "exact_fighter_method_correct":bool(exact),
                        "six_way_scores":scores,
                        "projected_sixway":masses,
                        "bet_approved":False,
                    }
                rows.append({
                    "event":slug,"event_date":date,"fight_no":n,
                    "a":f["a"],"b":f["b"],"model":model,
                    "original_locked_fighter_pick":pick,
                    "original_locked_fighter_probability":(
                        p_a if side=="A" else 1-p_a),
                    "actual_winner":actual["winner"],
                    "actual_method":actual["method"],
                    "winner_correct":(
                        actual["method"]!="DRAW" and pick==actual["winner"]),
                    "quality_inputs_use_predicted_side":True,
                    "predicted_side_ufc_prior_bouts":(
                        snaps[n]["a_pre" if side=="A" else "b_pre"][
                            "ufc_prior_bouts"
                        ]),
                    "variants":per_variant,
                })
        event_audits.append({
            "event":slug,"event_date":date,
            "frozen_source":raw_path,
            "original_fight_count":len(raw["fights"]),
            "shadow_fit_rows_strictly_before_event":len(earlier),
            "prior_quality_from_ufc_derived_archive":True,
            "original_lock_and_raw_sha_verified":True,
            "fake_draw_query_result_persisted_as_real_result":False,
        })
    summary={
        model:{
            candidate:_totals(rows,model,candidate)
            for candidate in VARIANTS
        } for model in MODELS
    }
    per_event={
        event:{
            model:{
                candidate:_totals(
                    [x for x in rows if x["event"]==event],
                    model,candidate,
                ) for candidate in VARIANTS
            } for model in MODELS
        } for event,_,_ in EVENTS
    }
    return {
        "schema":"WSHL_X_SELECTED_FIGHTER_EXACT_METHOD_BACKTEST_RESEARCH_V1",
        "status":"RETROSPECTIVE_SHADOW_ONLY_NOT_PROSPECTIVELY_FROZEN",
        "evaluation_events":event_audits,
        "all_bouts":len(rows)//3,
        "outcome_views":len(rows),
        "draw_event_count":sum(
            x["actual_method"]=="DRAW" for x in rows if x["model"]=="reference"
        ),
        "source_153_method_training_as_of":"2026-11-07",
        "source_ufc_history_through":"2026-11-07",
        "training_fitted_only_previous_dates":True,
        "features_derived_from_each_predicted_fighter_not_actual_winner":True,
        "prediction_model_winner_unchanged":True,
        "original_stage_a_b_and_simulations_unchanged":True,
        "no_fanduel_odds_used":True,
        "no_betting_authorization":True,
        "pre_existing_snapshots_reused_after_development":True,
        "this_evaluation_is_retrospective_not_pre_registered":True,
        "original_historical_unified_joint_winner_marginal_coherence_fixed_in_comparison":True,
        "candidate_calibrator_trained_on_reference_baseline_not_model_specific":True,
        "regional_opposition_quality_not_in_ufc_only_elo":True,
        "historical_data_source_is_third_party_ufcstats_compatible":True,
        "training_quality_join":coverage,
        "summary":summary,
        "per_event":per_event,
        "rows":rows,
        "model_promoted":False,
    }


if __name__=="__main__":
    out=evaluate()
    print("SELECTED_FIGHTER_METHOD_SUMMARY_START")
    print(json.dumps({
        k:out[k] for k in (
            "schema","status","all_bouts","outcome_views","draw_event_count",
            "evaluation_events","summary","per_event","model_promoted",
        )
    },sort_keys=True))
    print("SELECTED_FIGHTER_METHOD_SUMMARY_END")
