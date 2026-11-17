"""Eligibility audit for a recent 2021-26 UFC historical training rebuild.

This does NOT fit, overwrite or promote a prediction model. Prior fighter
features are derived only from fights completed on earlier event dates.
Labels come only from completed fights, after the dated pre-fight snapshots
were constructed. Modern 2021-2025 training vs 2026 *retrospective* evaluation
is a research baseline split, NOT a pristine unused out-of-time dataset.

Source is a pinned third-party UFCStats-compatible archive. Data quality
flags should never be imputed as zero fighter performance.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import json

from .prefight_finish_resistance import ARCHIVE, _load_records, load_and_build

CUTOFF="2026-11-14"
MODERN_BEGIN="2021-01-01"
MODERN_TRAIN_END="2025-12-31"
DRAWS={"DRAW"}
METHODS={"KO_TKO","SUB","DEC"}


def audit_eligibility()->dict:
    snapshots,provenance=load_and_build(as_of_exclusive=CUTOFF)
    originals=_load_records(ARCHIVE,date.fromisoformat(CUTOFF))
    if len(originals)!=len(snapshots):
        # Avoid a silent many-to-one change of bout identity.
        raise ValueError("Historical source/feature row count mismatch")
    if len(snapshots)!=provenance["fights"]:
        raise ValueError("One pre-fight feature snapshot per original bout required")
    look={}
    for record in originals:
        key=(record["date"].isoformat(),record["event"],record["a"],record["b"])
        if key in look:raise ValueError("Duplicate fight in pinned source")
        look[key]=record
    if len(look)!=len(originals):
        raise ValueError("Source historical fight identity collision")
    by_year=defaultdict(lambda:{
        "events":set(),"bouts":0,"decisive":0,"draws":0,
        "both_current_fight_stat_rows_available":0,"either_current_stat_missing":0,
        "prior_evidence_any_debutant":0,"prior_evidence_any_under_five_ufc_bouts":0,
        "prior_fighter_stat_history_missing_or_partial":0,
        "round_format_anomalies":0,"methods":Counter(),
    })
    modern_training=0
    modern_2026=0
    for snap in snapshots:
        key=(snap["event_date"],snap["event"],snap["a"],snap["b"])
        actual=look.get(key)
        if actual is None or not snap["current_fight_result_not_a_feature"]:
            raise ValueError("Outcome and pre-fight feature identity mismatch")
        if key[0]>=CUTOFF:raise ValueError("Future outcome leaked")
        a,b=snap["a_pre"],snap["b_pre"]
        for side in (a,b):
            if side["prior_ufc_bouts"] < side["prior_stats_bouts"]:
                raise ValueError("More observed prior stats than bouts")
            if side["getups_directly_measured"]:
                raise ValueError("Getups are NOT directly measured")
        y=int(key[0][:4])
        row=by_year[y]
        row["events"].add((key[0],key[1]))
        row["bouts"]+=1
        row["methods"][actual["method"]]+=1
        if actual["method"] in METHODS:
            row["decisive"]+=1
        elif actual["method"] in DRAWS:
            row["draws"]+=1
        else:
            raise ValueError("Unknown normalized outcome method")
        both=actual["stats_a"] is not None and actual["stats_b"] is not None
        row["both_current_fight_stat_rows_available"]+=int(both)
        row["either_current_stat_missing"]+=int(not both)
        row["prior_evidence_any_debutant"]+=int(
            not a["prior_ufc_bouts"] or not b["prior_ufc_bouts"])
        row["prior_evidence_any_under_five_ufc_bouts"]+=int(
            min(a["prior_ufc_bouts"],b["prior_ufc_bouts"])<5)
        row["prior_fighter_stat_history_missing_or_partial"]+=int(
            a["prior_stats_missing_not_zero_filled"] or
            b["prior_stats_missing_not_zero_filled"])
        row["round_format_anomalies"]+=int(actual.get("round_format_mismatch",False))
        if MODERN_BEGIN<=key[0]<="2025-12-31":
            modern_training+=1
        if "2026-01-01"<=key[0]<CUTOFF:
            modern_2026+=1
    result={}
    for year in sorted(by_year):
        d=dict(by_year[year])
        d["event_count"]=len(d.pop("events"))
        d["methods"]=dict(d["methods"])
        result[str(year)]=d
    modern={y:x for y,x in result.items() if 2021<=int(y)<=2026}
    modern_n=sum(d["bouts"] for d in modern.values())
    def sumfield(field):return sum(d[field] for d in modern.values())
    if sumfield("decisive")+sumfield("draws")!=modern_n:
        raise ValueError("Method label totals differ from modern bouts")
    if modern_training+modern_2026!=modern_n:
        raise ValueError("Modern 2021-26 split does not include all recent fights")
    return {
        "schema":"WSHL_X_2021_2026_HISTORICAL_TRAINING_ELIGIBILITY_V1",
        "status":"DATA_INVENTORY_NOT_NEW_MODEL",
        "source":"data/raw/ufcvegas124_2026-11-07/availability.json",
        "source_grade":"PINNED_THIRD_PARTY_UFCSTATS_COMPATIBLE_NOT_DIRECT_PRIMARY",
        "as_of_exclusive":CUTOFF,
        "full_archive_before_cutoff_bouts":len(originals),
        "full_archive_quality":provenance,
        "all_years":result,
        "modern_2021_2026":{
            "training_window":"2021-01-01 through 2025-12-31",
            "retrospective_2026_evaluation_window":"2026-01-01 through 2026-11-13",
            "training_bouts_2021_2025":modern_training,
            "retrospective_test_bouts_2026":modern_2026,
            "total_bouts":modern_n,
            "decisive_bouts":sumfield("decisive"),
            "draws":sumfield("draws"),
            "both_fighter_stat_rows":sumfield("both_current_fight_stat_rows_available"),
            "missing_either_stat_row":sumfield("either_current_stat_missing"),
            "any_ufc_debutant":sumfield("prior_evidence_any_debutant"),
            "any_fighter_prior_ufc_bouts_under_five":sumfield(
                "prior_evidence_any_under_five_ufc_bouts"),
            "any_partial_pre_event_stat_history":sumfield(
                "prior_fighter_stat_history_missing_or_partial"),
            "round_format_anomalies":sumfield("round_format_anomalies"),
        },
        "labels_are_postfight_and_features_are_pre_event":True,
        "no_future_opponent_rating_or_result_features":True,
        "source_stats_missing_not_zero_filled":True,
        "direct_getups_not_observed":True,
        "retrospective_2026_already_seen_during_research_not_pristine":True,
        "earlier_pre2021_fights_used_only_as_prior_context_not_recent_target_training":True,
        "historical_split_does_not_replace_true_prospective_shadow_evaluation":True,
        "no_stage_a_b_or_fanduel_quotations_modified":True,
        "new_model_trained_or_promoted":False,
    }
