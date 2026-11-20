"""Grade a PRE-COMMITTED coherent method shadow AFTER an event concludes.

No re-fitting or prediction changes. This file never reads sportsbook odds,
and it cannot change Stage A/B. Requires verified results for every original
frozen fight and a SHA-verified shadow. Actual winners and methods are labels,
never inputs when creating the pre-fight shadow.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math

from .prospective_coherence import (
    MODEL_NAMES, VARIANTS, check_lock_against_source, _time
)
from .joint_coherence_shadow import METHODS, SIDES, JOINT_KEYS, six_way_scores

EXCLUDED_METHODS=("DRAW","NC","DQ")


def _method(raw: str) -> str:
    mapping={
        "KO":"KO", "KO/TKO":"KO", "KO_TKO":"KO", "TKO":"KO",
        "SUB":"SUB", "SUBMISSION":"SUB",
        "DEC":"DEC", "DECISION":"DEC",
        "DRAW":"DRAW","NC":"NC","NO CONTEST":"NC",
        "DQ":"DQ","DISQUALIFICATION":"DQ",
    }
    val=mapping.get(str(raw).upper().strip())
    if val is None:
        raise ValueError("Unknown graded outcome class; do not silently drop "+str(raw))
    return val


def grade_prospective_shadow(*,lock_bytes:bytes,raw_bytes:bytes,
                             frozen_bytes:bytes,schedule_bytes:bytes,
                             results_bytes:bytes,as_of_utc:datetime)->dict:
    lock=json.loads(lock_bytes)
    check_lock_against_source(lock,raw_bytes,frozen_bytes,schedule_bytes)
    observed=json.loads(results_bytes)
    now=as_of_utc.astimezone(timezone.utc) if (
        isinstance(as_of_utc,datetime) and as_of_utc.tzinfo is not None
    ) else None
    if now is None:
        raise ValueError("Grade timestamp must have timezone offset")
    start=_time(lock["utc_event_earliest_start"])
    if now <= start+timedelta(hours=8):
        raise ValueError("Event may still be in progress; grade only afterwards")
    if (not observed.get("results_verified") is True or
        not observed.get("results_source_url","").startswith("https://") or
        _time(observed["verified_at_utc"]) < start or
        observed["event_date"]!=lock["event_date"] or
        observed["event_slug"]!=lock["event_slug"]):
        raise ValueError("Results require verified, dated, source-linked post-event evidence")
    results=observed["fights"]
    pairs={}
    for f in results:
        n=int(f["fight_no"])
        if n in pairs:
            raise ValueError("Duplicated result fight number")
        pairs[n]=f
    if len(pairs)!=len(lock["fights"]):
        raise ValueError("Every original frozen fight must have a verified outcome")
    per_fight=[]
    buffers={m:{v:[] for v in VARIANTS} for m in MODEL_NAMES}
    timing={m:[] for m in MODEL_NAMES}
    excluded=0
    for fight in lock["fights"]:
        n=fight["fight_no"]
        if n not in pairs:
            raise ValueError("A frozen fight has no result")
        actual=pairs[n]
        if (actual["a"],actual["b"])!=(fight["a"],fight["b"]):
            raise ValueError("Results fighter identities or order differ from original lock")
        final_method=_method(actual["method"])
        winner=actual.get("winner")
        if final_method in ("NC","DRAW"):
            if winner is not None:
                raise ValueError("NC/draw must not name a winning fighter")
        elif winner not in (fight["a"],fight["b"]):
            raise ValueError("Decided result winner must match fight identity")
        supported=final_method in METHODS
        excluded+=int(not supported)
        side=("A" if winner==fight["a"] else "B" if winner==fight["b"] else None)
        model_rows={}
        for model in MODEL_NAMES:
            original=fight["models"][model]
            fixed_pick=original["original_frozen_fighter_pick"]
            selected_side="A" if fixed_pick==fight["a"] else "B"
            winner_correct=supported and fixed_pick==winner
            variants={}
            for v in VARIANTS:
                selection=original["variant_selections"][v]
                predicted_method=selection["selected_method_given_frozen_winner"]
                if selection["frozen_winner_pick"]!=fixed_pick:
                    raise ValueError("Research variant changed original selected fighter")
                if predicted_method not in METHODS:
                    raise ValueError("Research variant method label invalid")
                exact=bool(winner_correct and predicted_method==final_method)
                scores=(six_way_scores(
                    original["distributions"][v],
                    fighter_side=side,
                    method=final_method,
                ) if supported else None)
                variants[v]={
                    "predicted_winner":fixed_pick,
                    "predicted_method":predicted_method,
                    "winner_correct":bool(winner_correct),
                    "exact_fighter_method_correct":exact,
                    "scores":scores,
                }
                if supported:
                    buffers[model][v].append({
                        "winner_correct":bool(winner_correct),
                        "exact":exact,"scores":scores,
                        "real_method":final_method,
                        "predicted_method":predicted_method,
                    })
            direct=original["original_direct_gtd_no"]
            duration=(None if not supported else {
                "p_gtd_no":direct,
                "observed_finish":final_method in ("KO","SUB"),
                "gtd_no_brier":(
                    direct-int(final_method in ("KO","SUB"))
                )**2,
            })
            if duration is not None:
                timing[model].append(duration)
            model_rows[model]={
                "original_frozen_winner":fixed_pick,
                "variants":variants,
                "unchanged_direct_timing_grade":duration,
            }
        per_fight.append({
            "fight_no":n,"a":fight["a"],"b":fight["b"],
            "verified_winner":winner,"verified_method":final_method,
            "is_six_way_gradeable":supported,
            "model_rows":model_rows,
        })
    summary={}
    for model in MODEL_NAMES:
        summary[model]={}
        for variant in VARIANTS:
            samples=buffers[model][variant]
            if not samples:
                raise ValueError("No decisive bouts for six-way score")
            summary[model][variant]={
                "decisive_fights":len(samples),
                "original_winner_correct":sum(x["winner_correct"] for x in samples),
                "exact_fighter_method_correct":sum(x["exact"] for x in samples),
                "six_way_brier":sum(x["scores"]["brier"] for x in samples)/len(samples),
                "six_way_logloss":sum(x["scores"]["logloss"] for x in samples)/len(samples),
                "KO_recall":(
                    sum(x["real_method"]=="KO" and x["predicted_method"]=="KO"
                        and x["winner_correct"] for x in samples)/
                    max(1,sum(x["real_method"]=="KO" for x in samples))
                ),
                "SUB_recall":(
                    sum(x["real_method"]=="SUB" and x["predicted_method"]=="SUB"
                        and x["winner_correct"] for x in samples)/
                    max(1,sum(x["real_method"]=="SUB" for x in samples))
                ),
                "DEC_recall":(
                    sum(x["real_method"]=="DEC" and x["predicted_method"]=="DEC"
                        and x["winner_correct"] for x in samples)/
                    max(1,sum(x["real_method"]=="DEC" for x in samples))
                ),
            }
        direct=timing[model]
        summary[model]["original_direct_GTD_NO"]={
            "scored":len(direct),
            "brier":sum(z["gtd_no_brier"] for z in direct)/len(direct),
            "unchanged_by_all_reconciliations":True,
        }
    return {
        "schema":"WSHL_X_PROSPECTIVE_COHERENCE_POST_EVENT_SHADOW_GRADE_V1",
        "status":"PROSPECTIVE_SHADOW_GRADED_UNPROMOTED",
        "event_slug":lock["event_slug"],
        "event_date":lock["event_date"],
        "graded_at_utc":now.isoformat(),
        "source_pre_event_shadow_lock_sha256":hashlib.sha256(lock_bytes).hexdigest(),
        "source_verified_results_sha256":hashlib.sha256(results_bytes).hexdigest(),
        "verified_results_source":observed["results_source_url"],
        "source_pre_fight_raw_sha256":lock["source_raw_sha256"],
        "decisive_fights":len(per_fight)-excluded,
        "excluded_draw_nc_dq":excluded,
        "fights":per_fight,
        "summary":summary,
        "odds_used":False,
        "original_stage_a_b_and_models_changed":False,
        "bet_authorized":False,
        "model_promoted":False,
        "results_only_in_grading_not_in_predictions":True,
    }
