"""Research-only historical resistance features, frozen BEFORE each UFC event.

KDs absorbed, threatened submission attempts, takedowns faced and control
absorbed are from previously completed fights. A reversal is NOT a get-up:
UFCStats does not directly measure get-up count, so no such feature is made.
Sources are pinned secondary UFCStats-compatible CSVs, not the UFCStats site.
This module never rewrites Stage A/B, model predictions, odds or bet decisions.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from pathlib import Path
import hashlib
import json
import pandas as pd
from .historical_data import aggregate_fight_stats, bout, col, method, normalize_events, num, outcome, rounds, secs, txt

ROOT=Path(__file__).resolve().parents[2]
ARCHIVE=ROOT/"data/raw/ufcvegas124_2026-11-07"
FIELDS=("prior_bouts","prior_stats_bouts","prior_ko_losses","prior_sub_losses",
        "knockdown_bouts","knockdown_nonko_survivals","knockdowns_absorbed",
        "submission_threat_bouts","submission_threat_nonloss",
        "control_60s_bouts","control_60s_nonsub",
        "dangerous_opponent_bouts","dangerous_opponent_avoided_finish",
        "takedowns_faced","takedowns_allowed","control_absorbed_sec",
        "knockdowns_delivered","submission_attempts_made",
        "takedowns_landed","control_generated_sec",
        "prior_fight_minutes")
def _fresh():
    return {k:0 for k in FIELDS}|{"wins":0,"finish_wins":0}

def _smooth(a,b,prior=0.5,alpha=4):
    return (a+alpha*prior)/(b+alpha)

def snap(record):
    x=record
    n=x["prior_bouts"]
    return {
      "prior_ufc_bouts":n,
      "prior_stats_bouts":x["prior_stats_bouts"],
      "stats_coverage":x["prior_stats_bouts"]/n if n else 0.,
      "ko_loss_rate_shrunk":_smooth(x["prior_ko_losses"],n,.12),
      "sub_loss_rate_shrunk":_smooth(x["prior_sub_losses"],n,.09),
      "prior_knockdowns_absorbed":x["knockdowns_absorbed"],
      "own_knockdowns_per15":15*x["knockdowns_delivered"]/x["prior_fight_minutes"] if x["prior_fight_minutes"] else None,
      "own_sub_attempts_per15":15*x["submission_attempts_made"]/x["prior_fight_minutes"] if x["prior_fight_minutes"] else None,
      "own_takedowns_landed_per15":15*x["takedowns_landed"]/x["prior_fight_minutes"] if x["prior_fight_minutes"] else None,
      "own_control_generated_sec_per15":15*x["control_generated_sec"]/x["prior_fight_minutes"] if x["prior_fight_minutes"] else None,
      "knockdowns_absorbed_per15":15*x["knockdowns_absorbed"]/x["prior_fight_minutes"] if x["prior_fight_minutes"] else None,
      "prior_knockdown_bouts":x["knockdown_bouts"],
      "knockdown_nonko_survival_rate":_smooth(x["knockdown_nonko_survivals"],x["knockdown_bouts"],.5),
      "prior_submission_threat_bouts":x["submission_threat_bouts"],
      "submission_threat_nonloss_rate":_smooth(x["submission_threat_nonloss"],x["submission_threat_bouts"],.75),
      "prior_control_60s_bouts":x["control_60s_bouts"],
      "control_60s_nonsub_rate":_smooth(x["control_60s_nonsub"],x["control_60s_bouts"],.75),
      "prior_dangerous_opponent_bouts":x["dangerous_opponent_bouts"],
      "dangerous_opponent_finish_survival":_smooth(x["dangerous_opponent_avoided_finish"],x["dangerous_opponent_bouts"],.55),
      "takedown_defense_rate_shrunk":_smooth(x["takedowns_faced"]-x["takedowns_allowed"],x["takedowns_faced"],.58,3),
      "prior_takedowns_faced":x["takedowns_faced"],
      "control_absorbed_sec_per15":15*x["control_absorbed_sec"]/x["prior_fight_minutes"] if x["prior_fight_minutes"] else None,
      "history_under_5_ufc_bouts":n<5,
      "getups_directly_measured":False,
      "prior_stats_missing_not_zero_filled":x["prior_stats_bouts"]<n,
    }

def build_from_records(records,*,as_of_exclusive:str,query_bouts=None):
    """All bouts on a calendar date get features from PREVIOUS dates only."""
    cutoff=date.fromisoformat(as_of_exclusive)
    records=sorted(records,key=lambda r:(r["date"],r["event"],r["a"],r["b"]))
    state=defaultdict(_fresh);seen=set();snapshots=[]
    counts={"fights":0,"missing_fighter_stats":0,"complete_stat_bouts":0,
            "knockdown_nonko_survival_bouts":0,"prior_threat_submission_bouts":0,
            "historical_round_format_mismatches":0}
    i=0
    while i<len(records):
        day=records[i]["date"]
        if not isinstance(day,date) or day>=cutoff:
            raise ValueError("Same-date/future fight result leakage")
        batch=[]
        while i<len(records) and records[i]["date"]==day:
            item=records[i];i+=1
            key=(day,item["event"],*sorted((item["a"],item["b"])))
            if key in seen:raise ValueError("Duplicate fight result")
            seen.add(key);batch.append(item)
        frozen={}
        # Freeze opponent finishing record too: updating one fighter must
        # not affect any same-date fighter's opponent-threat features.
        frozen_threat={
            name:(state[name]["wins"],state[name]["finish_wins"])
            for x in batch for name in (x["a"],x["b"])
        }
        for x in batch:
            for f in (x["a"],x["b"]):
                if f not in frozen:frozen[f]=snap(state[f])
            snapshots.append({
                "event_date":day.isoformat(),"event":x["event"],
                "a":x["a"],"b":x["b"],
                "a_pre":dict(frozen[x["a"]]),"b_pre":dict(frozen[x["b"]]),
                "current_fight_result_not_a_feature":True,
            })
        for x in batch:
            a,b=x["a"],x["b"]
            for fighter,enemy,side,opp_side,result in (
                (a,b,"a","b",x["result"][0]),
                (b,a,"b","a",x["result"][1]),
            ):
                own=state[fighter]
                # Only PRE-DATE opponent finishing record; never information
                # from this match or any other match on this same date.
                opp_wins,opp_finishes=frozen_threat[enemy]
                dangerous=opp_wins>=3 and _smooth(
                    opp_finishes,opp_wins,.55,2)>=.6
                survived=not(result=="L" and x["method"] in ("KO_TKO","SUB"))
                if dangerous:
                    own["dangerous_opponent_bouts"]+=1
                    own["dangerous_opponent_avoided_finish"]+=int(survived)
                own["prior_bouts"]+=1
                if result=="W":
                    own["wins"]+=1
                    own["finish_wins"]+=int(x["method"] in ("KO_TKO","SUB"))
                loss_ko=result=="L" and x["method"]=="KO_TKO"
                loss_sub=result=="L" and x["method"]=="SUB"
                own["prior_ko_losses"]+=int(loss_ko)
                own["prior_sub_losses"]+=int(loss_sub)
                me=x.get("stats_"+side);op=x.get("stats_"+opp_side)
                if me is None or op is None:
                    counts["missing_fighter_stats"]+=1
                    continue
                own["prior_stats_bouts"]+=1
                own["prior_fight_minutes"]+=x["elapsed_seconds"]/60.
                own["knockdowns_delivered"]+=int(round(me.get("kd",0)))
                own["submission_attempts_made"]+=int(round(me.get("sub_att",0)))
                own["takedowns_landed"]+=int(round(me.get("td_landed",0)))
                own["control_generated_sec"]+=int(round(me.get("ctrl_sec",0)))
                kd=int(round(op.get("kd",0)))
                att=int(round(op.get("td_attempted",0)))
                made=int(round(op.get("td_landed",0)))
                sub=int(round(op.get("sub_att",0)))
                ctrl=int(round(op.get("ctrl_sec",0)))
                if min(kd,att,made,sub,ctrl)<0 or made>att:
                    raise ValueError("Invalid source KD, TD, SUB or CTRL")
                own["knockdowns_absorbed"]+=kd
                own["knockdown_bouts"]+=int(kd>0)
                own["knockdown_nonko_survivals"]+=int(kd>0 and not loss_ko)
                own["submission_threat_bouts"]+=int(sub>0)
                own["submission_threat_nonloss"]+=int(sub>0 and not loss_sub)
                own["control_60s_bouts"]+=int(ctrl>=60)
                own["control_60s_nonsub"]+=int(ctrl>=60 and not loss_sub)
                own["takedowns_faced"]+=att
                own["takedowns_allowed"]+=made
                own["control_absorbed_sec"]+=ctrl
                counts["knockdown_nonko_survival_bouts"]+=int(kd>0 and not loss_ko)
                counts["prior_threat_submission_bouts"]+=int(sub>0)
            counts["fights"]+=1
            counts["historical_round_format_mismatches"]+=int(
                x.get("round_format_mismatch",False))
            counts["complete_stat_bouts"]+=int(
                x.get("stats_a") is not None and x.get("stats_b") is not None)
    if query_bouts:
        # The upcoming card reads PREVIOUS results only. No invented
        # placeholder outcomes or synthetic fights enter the history.
        unique=[]
        for a,b in query_bouts:
            if not a or not b or a==b or a in unique or b in unique:
                raise ValueError("Current card has ambiguous fighter identities")
            unique.extend((a,b))
            snapshots.append({
                "event_date":cutoff.isoformat(),
                "event":"__PREFIGHT_QUERY_NO_RESULTS__",
                "a":a,"b":b,
                "a_pre":snap(state[a]),"b_pre":snap(state[b]),
                "current_fight_result_not_a_feature":True,
                "query_only":True,
            })
    return snapshots,{**counts,"snapshot_rows":len(snapshots),
                     "fighters":len(state),"direct_getups_available":False,
                     "query_bouts":len(query_bouts or [])}

def _load_records(root:Path,cutoff:date):
    events=pd.read_csv(root/"ufc_event_details.csv",low_memory=False)
    results=pd.read_csv(root/"ufc_fight_results.csv",low_memory=False)
    stats=pd.read_csv(root/"ufc_fight_stats.csv",low_memory=False)
    days={str(x.event).strip():x.date.date()
          for x in normalize_events(events).itertuples(index=False)
          if pd.notna(x.date)}
    sums=aggregate_fight_stats(stats)
    cols={k:col(results,k) for k in ("EVENT","BOUT","OUTCOME","METHOD","ROUND","TIME","WEIGHTCLASS")}
    tf=col(results,"TIME FORMAT","TIME_FORMAT")
    if any(cols[k] is None for k in ("EVENT","BOUT","OUTCOME","METHOD","ROUND","TIME")):
        raise ValueError("Missing fight result columns")
    out=[]
    for x in results.to_dict("records"):
        event=txt(x[cols["EVENT"]]);day=days.get(event)
        if day is None or day>=cutoff:continue
        b=txt(x[cols["BOUT"]]);pair=bout(b)
        res=outcome(x[cols["OUTCOME"]]);meth=method(x[cols["METHOD"]])
        if not pair or res not in (("W","L"),("L","W"),("D","D")) or meth not in ("KO_TKO","SUB","DEC","DRAW"):continue
        n=rounds(x[tf] if tf else None,x[cols["WEIGHTCLASS"]] if cols["WEIGHTCLASS"] else None)
        r=int(num(x[cols["ROUND"]]));elapsed=(r-1)*300+secs(x[cols["TIME"]])
        if r<1 or elapsed<0:raise ValueError("Invalid source duration")
        out.append({"date":day,"event":event,"a":pair[0],"b":pair[1],"result":res,
                    "method":meth,"elapsed_seconds":elapsed,
                    "round_format_mismatch":r>n,
                    "stats_a":sums.get((event,b,pair[0])),"stats_b":sums.get((event,b,pair[1]))})
    return out

def load_and_build(*,as_of_exclusive:str="2026-11-14",
                   root:Path=ARCHIVE,query_bouts=None):
    cutoff=date.fromisoformat(as_of_exclusive)
    manifest=json.loads((root/"availability.json").read_text())
    for name in ("ufc_event_details.csv","ufc_fight_results.csv","ufc_fight_stats.csv"):
        original=manifest["source_csv_files"][name]
        path=root/name
        if path.stat().st_size!=original["bytes"]:
            raise ValueError("Pinned secondary archive size mismatch "+name)
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if sha!=original["sha256"]:
            raise ValueError("Pinned secondary archive SHA mismatch "+name)
    snapshots,counts=build_from_records(_load_records(root,cutoff),
                                        as_of_exclusive=as_of_exclusive,
                                        query_bouts=query_bouts)
    return snapshots,{**counts,"as_of_exclusive":as_of_exclusive,
                      "source_classification":"PINNED_SECONDARY_UFCSTATS_COMPATIBLE",
                      "source_sha256":manifest["source_csv_files"]["ufc_fight_stats.csv"]["sha256"],
                      "getups_directly_measured":False,
                      "not_official_stats_site_direct":True,
                      "model_or_bet_promotion":False}
