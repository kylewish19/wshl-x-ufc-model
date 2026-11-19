"""UFC winner v3 research: strictly pre-event recent form and striking efficiency.

All source rounds and results come from the pinned SHA-checked
UFCStats-compatible archive. No current fight stats or winners enter features.
Every fight on same calendar date is snapshot before same-date updates.
This augments the prior 38-dimensional UFC matchup vector with SOURCE-OBSERVED
historical significant-strike efficiency, rates and short-window results;
it never fabricates regional MMA experience, get-ups or injury facts.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from math import log1p
import numpy as np

from .prefight_finish_resistance import _load_records, ARCHIVE
from .historical_feature_matrix import load_matrix

FIELDS=(
    "prior_recorded_stat_fights",
    "lifetime_sig_strikes_landed_per15",
    "lifetime_sig_strikes_absorbed_per15",
    "lifetime_sig_strike_accuracy",
    "lifetime_sig_strike_defense",
    "lifetime_td_accuracy",
    "lifetime_td_defense",
    "recent3_wins_fraction_smoothed",
    "recent5_wins_fraction_smoothed",
    "streak_signed_scaled",
    "recent3_sig_strikes_landed_per15",
    "recent3_sig_strikes_absorbed_per15",
    "recent3_knockdowns_per15",
    "recent3_takedowns_per15",
    "recent3_submission_attempts_per15",
    "last12months_bout_count",
    "recent3_stats_coverage",
    "no_previous_ufc_stats",
    "last3_sig_absorbed_per15_missing",
)
N=len(FIELDS)

def fighter_snapshot(history:list[dict],when:date):
    bouts=[x for x in history if x["date"]<when]
    if len(bouts)!=len(history):
        raise ValueError("A same-date or future fight slipped into prior-history")
    recent3=bouts[-3:]
    recent5=bouts[-5:]
    def by_stat(seq):
        valid=[x for x in seq if x["stat_available"]]
        minutes=sum(x["fight_minutes"] for x in valid)
        landed=sum(x["sig_landed"] for x in valid)
        attempted=sum(x["sig_attempted"] for x in valid)
        absorbed=sum(x["sig_absorbed"] for x in valid)
        faced=sum(x["sig_faced"] for x in valid)
        td_landed=sum(x["td_landed"] for x in valid)
        td_attempted=sum(x["td_attempted"] for x in valid)
        td_absorbed=sum(x["td_absorbed"] for x in valid)
        td_faced=sum(x["td_faced"] for x in valid)
        def per15(key):
            return 15*sum(x[key] for x in valid)/minutes if minutes else 0.
        return {
            "fights":len(valid),
            "sig_landed_p15":15*landed/minutes if minutes else 0.,
            "sig_absorbed_p15":15*absorbed/minutes if minutes else 0.,
            "accuracy":(landed+6)/(attempted+12), # conservative shrink
            "defense":(faced-absorbed+6)/(faced+12),
            "td_acc":(td_landed+2)/(td_attempted+4),
            "td_def":(td_faced-td_absorbed+2)/(td_faced+4),
            "kd_p15":per15("kd"),
            "td_p15":per15("td_landed"),
            "sub_p15":per15("sub_att"),
        }
    allstats=by_stat(bouts)
    recent=by_stat(recent3)
    wins3=sum(x["result"]=="W" for x in recent3)
    wins5=sum(x["result"]=="W" for x in recent5)
    streak=0
    for x in reversed(bouts):
        if x["result"]=="D":break
        if (x["result"]=="W") != (streak>0) and streak!=0:break
        streak+=1 if x["result"]=="W" else -1
    last_year=sum(0<(when-x["date"]).days<=365 for x in bouts)
    output=np.asarray([
        log1p(allstats["fights"]),
        np.log1p(allstats["sig_landed_p15"]),
        np.log1p(allstats["sig_absorbed_p15"]),
        allstats["accuracy"],allstats["defense"],
        allstats["td_acc"],allstats["td_def"],
        (wins3+1)/(len(recent3)+2),
        (wins5+2)/(len(recent5)+4),
        np.clip(streak,-6,6)/6.,
        np.log1p(recent["sig_landed_p15"]),
        np.log1p(recent["sig_absorbed_p15"]),
        np.log1p(recent["kd_p15"]),
        np.log1p(recent["td_p15"]),
        np.log1p(recent["sub_p15"]),
        log1p(last_year),
        recent["fights"]/len(recent3) if recent3 else 0.,
        float(allstats["fights"]==0),
        float(recent["fights"]==0),
    ],dtype=float)
    if output.shape!=(N,) or not np.all(np.isfinite(output)):
        raise ValueError("Nonfinite or wrong-dimension pre-fight recent form")
    return output

def construct_record_history(records:list[dict],*,cutoff:str):
    boundary=date.fromisoformat(cutoff)
    records=sorted(records,key=lambda x:(x["date"],x["event"],x["a"],x["b"]))
    history=defaultdict(list)
    snapshots={};seen=set()
    i=0
    while i<len(records):
        current=records[i]["date"]
        if current>=boundary:raise ValueError("Future record included")
        batch=[]
        while i<len(records) and records[i]["date"]==current:
            row=records[i];i+=1
            key=(current.isoformat(),row["event"],*sorted((row["a"],row["b"])))
            if key in seen:raise ValueError("Ambiguous historical fight")
            seen.add(key);batch.append(row)
        for row in batch:
            key=(current.isoformat(),row["event"],*sorted((row["a"],row["b"])))
            snapshots[key]={
                "a_name":row["a"],"b_name":row["b"],
                "a":fighter_snapshot(history[row["a"]],current),
                "b":fighter_snapshot(history[row["b"]],current),
            }
        # Strict whole-calendar-day update, including same-day repeat fighters.
        for row in batch:
            a,b=row["a"],row["b"]
            minutes=row["elapsed_seconds"]/60.
            if minutes<=0:raise ValueError("Invalid fight duration")
            for side,other,fighter,result in (
                ("a","b",a,row["result"][0]),
                ("b","a",b,row["result"][1]),
            ):
                own=row.get("stats_"+side)
                op=row.get("stats_"+other)
                available=own is not None and op is not None
                def fetch(s,key):
                    return float(s.get(key,0.)) if s else 0.
                state={
                    "date":current,"result":result,
                    "stat_available":available,
                    "fight_minutes":minutes if available else 0.,
                    "sig_landed":fetch(own,"sig_landed"),
                    "sig_attempted":fetch(own,"sig_attempted"),
                    "sig_absorbed":fetch(op,"sig_landed"),
                    "sig_faced":fetch(op,"sig_attempted"),
                    "td_landed":fetch(own,"td_landed"),
                    "td_attempted":fetch(own,"td_attempted"),
                    "td_absorbed":fetch(op,"td_landed"),
                    "td_faced":fetch(op,"td_attempted"),
                    "kd":fetch(own,"kd"),
                    "sub_att":fetch(own,"sub_att"),
                }
                if any(v<0 for k,v in state.items() if isinstance(v,(float,int))):
                    raise ValueError("Negative prior source fighter stats")
                history[fighter].append(state)
    return snapshots

def supplement_current_feature_matrix(features:list[dict],*,cutoff:str="2026-11-14"):
    raw=_load_records(ARCHIVE,date.fromisoformat(cutoff))
    matrix=construct_record_history(raw,cutoff=cutoff)
    output={};missing=[]
    for f in features:
        if not "2021-01-01"<=f["event_date"]<cutoff:continue
        key=(f["event_date"],f["event"],*sorted((f["fighter_a"],f["fighter_b"])))
        m=matrix.get(key)
        if m is None:
            missing.append(key);continue
        if (f["fighter_a"],f["fighter_b"])==(m["a_name"],m["b_name"]):
            output[f["bout_id"]]=(m["a"],m["b"])
        elif (f["fighter_a"],f["fighter_b"])==(m["b_name"],m["a_name"]):
            output[f["bout_id"]]=(m["b"],m["a"])
        else:raise ValueError("Same-date fighter identity mismatch")
    report={
        "schema":"WSHLX_PRIOR_STRIKING_AND_RECENT_FORM_V3",
        "source_class":"PINNED_SECONDARY_UFCSTATS_COMPATIBLE",
        "source_bout_count":len(raw),
        "historical_snapshots":len(matrix),
        "modern_rows_joined":len(output),
        "modern_rows_unmatched":len(missing),
        "example_unmatched":missing[:4],
        "source_values_only_prio_event":True,
        "same_day_frozen_before_update":True,
        "unmeasured_getups_injuries_regional_mma_not_added":True,
        "new_feature_columns":FIELDS,
    }
    return output,report
