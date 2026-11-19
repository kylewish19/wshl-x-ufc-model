"""Research-only, source-hashed UFC pre-fight profile and fight-context fields.

New inputs absent from the existing 101-column matrix:
- DOB-derived age ON bout date, listed height and reach (2026 pinned profile
  snapshot; historical availability/revision uncertain and therefore tagged);
- prior UFC recency, last-365 bout count, and previous bouts at the SAME UFC
  weight-class, all strictly before the current event DATE.

Never treat a fighter's CURRENT profile weight as their historical class.
No regional stats, injury/availability, or verified observed get-ups exist.
No training, prices, production changes or fabricated missing values.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from pathlib import Path
import hashlib,json,re
import numpy as np
import pandas as pd

from .historical_data import bout,col,normalize_events,txt
from .prefight_finish_resistance import ARCHIVE

PROFILE_SOURCE="ufc_fighter_tott.csv"
RESULT_SOURCE="ufc_fight_results.csv"
EVENT_SOURCE="ufc_event_details.csv"

def checked_file(filename:str)->Path:
    manifest=json.loads((ARCHIVE/"availability.json").read_text())
    rule=manifest["source_csv_files"][filename]
    path=ARCHIVE/filename
    if path.stat().st_size!=rule["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest()!=rule["sha256"]:
        raise ValueError("Pinned source file provenance mismatch "+filename)
    return path

def _profile_name(value):
    return str(value).strip().casefold()

def inches_height(value):
    if value is None or str(value).strip() in ("","--","nan"):
        return None
    s=str(value).strip()
    m=re.fullmatch(r"""(\d+)\s*'\s*(\d+(?:\.\d+)?)\s*"?""",s)
    if not m:return None
    height=float(m.group(1))*12+float(m.group(2))
    return height if 45<=height<=95 else None

def inches_reach(value):
    if value is None or str(value).strip() in ("","--","nan"):
        return None
    m=re.search(r"(\d+(?:\.\d+)?)",str(value))
    if not m:return None
    reach=float(m.group(1))
    return reach if 40<=reach<=110 else None

def date_dob(value):
    try:
        d=pd.to_datetime(value,errors="coerce")
        return d.date() if pd.notna(d) else None
    except (ValueError,TypeError):
        return None

def load_profiles():
    profiles={}
    records=pd.read_csv(checked_file(PROFILE_SOURCE),low_memory=False)
    for row in records.to_dict("records"):
        name=_profile_name(row["FIGHTER"])
        if not name or name=="nan":continue
        fields={
            "dob":date_dob(row["DOB"]),
            "height_inches":inches_height(row["HEIGHT"]),
            "reach_inches":inches_reach(row["REACH"]),
        }
        if name in profiles:
            # Never silently join two different athlete identities.
            if profiles[name]!=fields:profiles[name]=None
        else:profiles[name]=fields
    return profiles

def load_weightclass_history(*,cutoff="2026-11-14"):
    events=pd.read_csv(checked_file(EVENT_SOURCE),low_memory=False)
    results=pd.read_csv(checked_file(RESULT_SOURCE),low_memory=False)
    ev_dates={str(x.event).strip():x.date.date()
              for x in normalize_events(events).itertuples(index=False)
              if pd.notna(x.date)}
    c_event=col(results,"EVENT");c_bout=col(results,"BOUT")
    c_weight=col(results,"WEIGHTCLASS")
    if any(x is None for x in (c_event,c_bout,c_weight)):
        raise ValueError("Source fight weight class and identity columns absent")
    records=[];seen=set()
    limit=date.fromisoformat(cutoff)
    for x in results.to_dict("records"):
        ev=txt(x[c_event]);when=ev_dates.get(ev)
        if when is None or when>=limit:continue
        a_b=bout(txt(x[c_bout]))
        if not a_b:continue
        a,b=a_b
        key=(when.isoformat(),ev,*sorted((a,b)))
        if key in seen:raise ValueError("Duplicate same-date source fight")
        seen.add(key)
        weight=txt(x[c_weight]).strip()
        records.append({"date":when,"event":ev,"a":a,"b":b,
                        "weightclass":weight if weight and weight!="--" else None,
                        "key":key})
    return sorted(records,key=lambda r:(r["date"],r["event"],r["a"],r["b"]))

def construct_metadata(records,profiles):
    """Freeze each calendar day before updating any fighter on that day."""
    history=defaultdict(list);out={};i=0
    while i<len(records):
        day=records[i]["date"];batch=[]
        while i<len(records) and records[i]["date"]==day:
            batch.append(records[i]);i+=1
        for r in batch:
            details={"weight_class_pre_event_listing":r["weightclass"],"source_a":r["a"],"source_b":r["b"]}
            for side,fighter in (("a",r["a"]),("b",r["b"])):
                h=history[fighter];p=profiles.get(_profile_name(fighter))
                dob=p["dob"] if p else None
                age=(day-dob).days/365.2425 if dob else None
                if age is not None and not 16<=age<=75:
                    age=None
                same=sum(x["weightclass"]==r["weightclass"] for x in h) if r["weightclass"] else None
                last=(day-h[-1]["date"]).days if h else None
                recently=sum(0<(day-x["date"]).days<=365 for x in h)
                details[side]={
                    "age_on_event_day":age,
                    "height_inches":p["height_inches"] if p else None,
                    "reach_inches":p["reach_inches"] if p else None,
                    "prior_same_weightclass_bouts":same,
                    "days_since_last_ufc_bout":last,
                    "prior_ufc_bouts_last365":recently,
                    "profile_found":p is not None,
                    "prior_ufc_fights_in_result_source":len(h),
                }
            if r["key"] in out:raise ValueError("Duplicate context identity")
            out[r["key"]]=details
        # Update only AFTER all this day's matchups are frozen.
        for r in batch:
            for fighter in (r["a"],r["b"]):
                history[fighter].append({"date":day,"weightclass":r["weightclass"]})
    return out

def feature_context(source_feature,metadata):
    key=(source_feature["event_date"],source_feature["event"],
         *sorted((source_feature["fighter_a"],source_feature["fighter_b"])))
    row=metadata.get(key)
    if row is None:return None
    # Current fighter order must match source mapping, not alphabetical order.
    # The original UFCStats bout parser stores source A/B in the same order;
    # source_feature fighter_a/b may be flipped if builders normalize. Resolve
    # against pre-populated direct identities from the keyed context below.
    return row

def metadata_for_features(features):
    rows=load_weightclass_history()
    profiles=load_profiles()
    indexed=construct_metadata(rows,profiles)
    matched={};missing=[]
    for f in features:
        if not "2021-01-01"<=f["event_date"]<"2026-11-14":continue
        key=(f["event_date"],f["event"],*sorted((f["fighter_a"],f["fighter_b"])))
        record=indexed.get(key)
        if record is None:
            missing.append({"date":f["event_date"],"a":f["fighter_a"],"b":f["fighter_b"]})
            continue
        # Explicit source-pair orientation; never attach one fighter's DOB,
        # reach or recency data to the opponent after an order reversal.
        if f["fighter_a"]==record["source_a"] and f["fighter_b"]==record["source_b"]:
            matched[f["bout_id"]]=record
        elif f["fighter_a"]==record["source_b"] and f["fighter_b"]==record["source_a"]:
            matched[f["bout_id"]]={
                **record,"a":record["b"],"b":record["a"],
                "source_a":f["fighter_a"],"source_b":f["fighter_b"],
            }
        else:
            raise ValueError("Weightclass metadata fighter identity mismatch")
    return matched,{
        "source_fight_records":len(rows),"source_profiles":len(profiles),
        "feature_bouts_joined":len(matched),"feature_bouts_unmatched":len(missing),
        "missing_samples":missing[:15],
        "profile_source_snapshot":"PINNED_2026_11_08_SECONDARY_NOT_HISTORICALLY_VERSIONED",
        "physical_profile_age_can_be_backcomputed_from_DOB":True,
        "reach_and_height_may_have_historically_changed":True,
        "regional_results_or_getups_directly_observed":False,
        "same_day_result_update_forbidden":True,
    }
