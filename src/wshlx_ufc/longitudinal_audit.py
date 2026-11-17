"""Longitudinal WSHL_X UFC **audit**, not a new betting model.

This intentionally separates:
 - 153 reconstructed gradeable fight rows, Aug08-Nov07, with 8 EXACT
   cumulative snapshots (not 8 independently sampled test sets);
 - separate original Stage A card artifacts present for 7 later dates;
 - 13 Nov14 UFC334 fights, one drawn/ungraded in winner/method;
 - only dated and approved *strategy* Stage B wager records, with Sep19
   frozen-vs-after-recheck ledger choices kept SEPARATE;
 - naive fighter+KO as a transparent sanity check against one fixed
   chosen fighter, not an ex-post proof of a viable profitable strategy.

No original predictions, training data, Stage A/B, FanDuel odds,
10,000 simulations, grading, or betting records are modified.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
FULL="data/results/clean_ufc_153_2026-11-07.csv"
SNAPSHOTS=((64,"2026-09-05"),(76,"2026-09-19"),
           (87,"2026-09-26"),(101,"2026-10-03"),
           (112,"2026-10-10"),(125,"2026-10-17"),
           (139,"2026-10-24"),(153,"2026-11-07"))
STAGE_A_ARTIFACTS={
    "2026-09-19":("data/locks/ufc331_2026-09-19/stage_a_official_selection_card.json","picks"),
    "2026-09-26":("data/locks/ufcvegas121_2026-09-26/stage_a_official_selection_card.json","picks"),
    "2026-10-03":("data/locks/ufc332_2026-10-03/stage_a_official_selection_card.json","picks"),
    "2026-10-10":("data/locks/ufcvegas122_2026-10-10/stage_a_official_selection_card.json","picks"),
    "2026-10-17":("data/locks/ufcedmonton_2026-10-17/stage_a_model_raw_v033.json","wrapped_raw"),
    "2026-10-24":("data/locks/ufc333_2026-10-24/stage_a_final_selection.json","final"),
    "2026-11-07":("data/locks/ufcvegas124_2026-11-07/stage_a_final_selection.json","final"),
}
UFC334_GRADE="data/results/ufc334_2026-11-14_all_models_grading.json"
UFC334_LOCK="data/locks/ufc334_2026-11-14/stage_a_final_selection.json"
UFC334_RAW="data/locks/ufc334_2026-11-14/stage_a_model_raw_three_view.json"
SOURCE_STAGE_B={
    "2026-09-19":"reports/ufc331_2026-09-19/post_event_grade.json",
    "2026-09-26":"reports/ufcvegas121_2026-09-26/post_event_grade.json",
    "2026-10-03":"reports/ufc332_2026-10-03/post_event_grade.json",
    "2026-10-10":"reports/ufcvegas122_2026-10-10/post_event_grade.json",
    "2026-10-17":"reports/ufcedmonton_2026-10-17/post_event_grade.json",
}
METHODS=("KO","SUB","DEC")

def _load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def _read(path:str):
    with (ROOT/path).open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))

def _sha(path:str):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

def _split(fight:str)->tuple[str,str]:
    parts=fight.split(" vs ")
    if len(parts)!=2 or not all(parts):
        raise ValueError("Non-normalized fight name "+fight)
    return parts[0],parts[1]

def _summarize(rows):
    n=len(rows)
    if not n:raise ValueError("Cannot score empty audit cohort")
    return {
        "fights":n,
        "winner_correct":sum(x["winner_correct"] for x in rows),
        "method_class_correct":sum(x["method_correct"] for x in rows),
        "exact_fighter_and_method":sum(x["joint_correct"] for x in rows),
        "winner_pct":sum(x["winner_correct"] for x in rows)/n,
        "method_class_pct":sum(x["method_correct"] for x in rows)/n,
        "exact_pct":sum(x["joint_correct"] for x in rows)/n,
        "actual_methods":dict(Counter(x["actual_method"] for x in rows)),
        "displayed_methods":dict(Counter(x["displayed_method"] for x in rows)),
        "fighter_pick_and_KO_exact":sum(
            x["winner_correct"] and x["actual_method"]=="KO" for x in rows),
        "fighter_pick_and_DEC_exact":sum(
            x["winner_correct"] and x["actual_method"]=="DEC" for x in rows),
        "fighter_pick_and_SUB_exact":sum(
            x["winner_correct"] and x["actual_method"]=="SUB" for x in rows),
    }

def _clean153():
    rows=_read(FULL)
    if len(rows)!=153:raise ValueError("Expected 153 clean historical results")
    seen=set()
    result=[]
    last=""
    for x in rows:
        if set(x)!={"event_date","fight","locked_pick","actual_winner",
                   "displayed_method","actual_method","winner_correct",
                   "method_correct","joint_correct"}:
            raise ValueError("Historical grade schema unexpectedly changed")
        day=x["event_date"]
        if not last<=day<="2026-11-07" or day<"2026-08-08":
            raise ValueError("Historical date ordering/cutoff incorrect")
        last=day
        a,b=_split(x["fight"])
        if x["locked_pick"] not in (a,b) or x["actual_winner"] not in (a,b):
            raise ValueError("Historical fighter identity mismatch")
        if x["actual_method"] not in METHODS or x["displayed_method"] not in METHODS:
            raise ValueError("Only clean KO/SUB/DEC methods allowed in 153 archive")
        id=(day,tuple(sorted((a,b))))
        if id in seen:raise ValueError("Duplicated date-and-matchup in grade ledger")
        seen.add(id)
        truth=int(x["actual_winner"]==x["locked_pick"])
        meth=int(x["actual_method"]==x["displayed_method"])
        exact=truth*meth
        if any(x[k] not in ("0","1") for k in
               ("winner_correct","method_correct","joint_correct")):
            raise ValueError("Grade values must be binary")
        if [truth,meth,exact]!=[int(x["winner_correct"]),
                                int(x["method_correct"]),int(x["joint_correct"])]:
            raise ValueError("Historical row flags inconsistent with actual outcome")
        result.append({**x,"winner_correct":truth,
                       "method_correct":meth,"joint_correct":exact})
    return result

def _check_snapshots(rows):
    expected=[{k:str(v) for k,v in x.items()} for x in rows]
    report=[]
    for number,last_day in SNAPSHOTS:
        path=f"data/results/clean_ufc_{number}_{last_day}.csv"
        original=_read(path)
        if len(original)!=number or original!=expected[:number]:
            raise ValueError(f"Original cumulative snapshot is NOT immutable prefix: {path}")
        if rows[number-1]["event_date"]!=last_day:
            raise ValueError("Snapshot does not end on named event date")
        report.append({"source":path,"rows":number,"ends_on":last_day,
                       "exact_prefix_of_latest":True,"sha256":_sha(path)})
    return report

def _check_locks(rows):
    by_date=defaultdict(list)
    for row in rows:
        by_date[row["event_date"]].append(row)
    output=[]
    used=0
    for day,(path,kind) in STAGE_A_ARTIFACTS.items():
        j=_load(path)
        if kind=="wrapped_raw":
            j=j["payload"]
        if j.get("odds_used") is not False or j.get("event_date")!=day:
            raise ValueError("Historical lock is not marked odds-blind or has wrong event")
        if kind=="picks":
            arr=j["picks"]
            lookup={x["fight"]:x["winner"] for x in arr}
        else:
            arr=j["fights"]
            lookup={
                f'{f["a"]} vs {f["b"]}': (
                    f["official_reference_pick"] if kind=="final" else
                    f["winner_reference_pick"])
                for f in arr
            }
        if len(lookup)!=len(arr):
            raise ValueError("Duplicate archived Stage A fight names")
        sample=by_date[day]
        for row in sample:
            if lookup.get(row["fight"]) != row["locked_pick"]:
                raise ValueError("Grade fighter pick disagrees with Stage A artifact "
                                 +row["fight"])
        # Early method label sources are distinct; do not silently assume
        # secondary_method equals reference-model calibrated TOP method.
        if kind=="final":
            if j["stage_a_frozen"] is not True or not j.get("frozen_at_utc"):
                raise ValueError("Post-Oct17 Stage A missing freeze evidence")
            raw_path=j["raw_model_path"]
            if j["raw_model_sha256"]!=_sha(raw_path):
                raise ValueError("Original raw forecast digest mismatch")
        output.append({
            "date":day,"source":path,"kind":kind,
            "source_bouts":len(arr),
            "gradeable_bouts":len(sample),
            "matched_reference_winner_picks":len(sample),
            "excluded_from_clean_grade":len(arr)-len(sample),
            "odds_blind_flag":True,
            "timestamped_final_sha_checked":kind=="final",
            "has_pre_fight_timestamp_evidence":bool(
                j.get("frozen_at_utc") or j.get("locked_at_utc")),
        })
        used+=len(sample)
    if used!=89:
        raise ValueError("Missing historical reference Stage A artifact coverage")
    return output

def _ufc334():
    grade=_load(UFC334_GRADE)
    lock=_load(UFC334_LOCK)
    if (grade["event_date"]!="2026-11-14" or
        lock["event_date"]!="2026-11-14" or
        lock["raw_model_sha256"]!=_sha(UFC334_RAW) or
        lock["stage_a_frozen"] is not True or lock["odds_used"] is not False):
        raise ValueError("UFC334 frozen source mismatch")
    original={f["fight_no"]:f for f in lock["fights"]}
    if len(original)!=13 or len(grade["fights"])!=13:
        raise ValueError("Missing UFC334 original fight result")
    rows=[]
    other=[]
    for f in grade["fights"]:
        n=f["fight_no"]
        frozen=original[n]
        a,b=_split(f["bout"])
        if (a,b)!=(frozen["a"],frozen["b"]):
            raise ValueError("UFC334 actual/frozen fight identity mismatch")
        method=f["actual"]["method"]
        if method=="DRAW":
            if f["actual"]["winner"] is not None:raise ValueError("DRAW with winner")
            other.append({"bout":f["bout"],"method":method})
            continue
        if method not in METHODS or f["actual"]["winner"] not in (a,b):
            raise ValueError("UFC334 unexpected decided result")
        ref=f["models"]["reference"]
        if ref["fighter"]!=frozen["official_reference_pick"]:
            raise ValueError("UFC334 original reference winner changed")
        hit=int(ref["fighter"]==f["actual"]["winner"])
        mc=int(ref["method"]==method)
        exact=hit*mc
        if exact!=int(ref["exact_fighter_method_correct"]):
            raise ValueError("UFC334 grader contradicts exact fighter+method")
        rows.append({
            "event_date":"2026-11-14","fight":f["bout"],
            "actual_method":method,"displayed_method":ref["method"],
            "winner_correct":hit,"method_correct":mc,"joint_correct":exact,
        })
    summ=_summarize(rows)
    if (summ["fights"]!=12 or summ["winner_correct"]!=8 or
        summ["exact_fighter_and_method"]!=1 or len(other)!=1):
        raise ValueError("UFC334 source grade changed")
    return {"source":UFC334_GRADE,"source_lock":UFC334_LOCK,
            "source_lock_verified_sha":True,"card_fights":13,
            "decisive_fights":12,"excluded":[*other],
            "reference":summ}

def _wagers():
    events=[]
    for day,path in SOURCE_STAGE_B.items():
        src=_load(path)
        if src["event_date"]!=day:raise ValueError("Stage B source event mismatch")
        if day=="2026-09-19":
            obj=src["stage_b"]
            primary=obj["final_actionable_after_aswell_recheck"]
            initial=obj["frozen_original_card"]
            events.append({
                "event_date":day,"source":path,
                "chosen_ledger":"POST_RECHECK_ACTIONABLE",
                "record":primary["record"],"risked_units":primary["risked_units"],
                "net_units":primary["units"],
                "initial_frozen_alternative":{
                    "record":initial["record"],
                    "risked_units":initial["risked_units"],
                    "net_units":initial["units"]},
            })
            continue
        obj=src["stage_b_grade"] if day=="2026-10-17" else src["stage_b"]
        risk=obj.get("total_risk_units",obj.get("risked_units"))
        pnl=obj.get("profit_loss_units",obj.get("pnl_units"))
        if risk is None or pnl is None:raise ValueError("Missing Stage B unit figures")
        events.append({"event_date":day,"source":path,
                       "chosen_ledger":"POST_EVENT_GRADED_STAGE_B",
                       "record":obj["record"],"risked_units":float(risk),
                       "net_units":float(pnl)})
    def summ(replace_first:bool):
        net=0.;risk=0.;w=l=0
        for i,x in enumerate(events):
            one=(x["initial_frozen_alternative"] if i==0 and replace_first
                 else x)
            a,b=(int(z) for z in one["record"].split("-"))
            w+=a;l+=b
            net+=one["net_units"];risk+=one["risked_units"]
        return {"strategy_events":len(events),
                "picks_with_stated_strategy_outcomes":w+l,
                "wins":w,"losses":l,
                "risked_units":risk,"net_units":net,"roi":net/risk}
    return {
        "source_events":events,
        "post_recheck_actionable_scenario":summ(False),
        "original_sep19_frozen_scenario":summ(True),
        "missing_or_zero_approved_events":[
            {"event_date":"2026-10-24","status":"NO_FROZEN_STAGE_B_OFFICIAL_CARD_FOUND"},
            {"event_date":"2026-11-07","status":"ZERO_APPROVED_WAGERS"},
            {"event_date":"2026-11-14","status":"ZERO_APPROVED_WAGERS_ONLY_RESEARCH_VIRTUAL_UNITS"},
        ],
        "actual_user_bankroll_or_bets_verified":False,
        "market_beating_proven":False,
        "not_cumulative_research_virtual_unit_pnl":True,
        "only_recorded_strategy_wagers_included":True,
    }

def audit()->dict:
    clean=_clean153()
    dates=sorted({x["event_date"] for x in clean})
    if len(dates)!=12 or dates[0]!="2026-08-08" or dates[-1]!="2026-11-07":
        raise ValueError("Unexpected reconstructed history scope")
    snapshots=_check_snapshots(clean)
    locks=_check_locks(clean)
    early=clean[:64]
    holdout=clean[64:]
    if early[-1]["event_date"]!="2026-09-05" or holdout[0]["event_date"]!="2026-09-19":
        raise ValueError("Initial history must end BEFORE validation window")
    method_counts=Counter(x["actual_method"] for x in early)
    chosen=max(METHODS,key=lambda m:method_counts[m])
    by_date=[
        {"event_date":d,**_summarize([x for x in clean if x["event_date"]==d])}
        for d in dates
    ]
    card334=_ufc334()
    return {
        "schema":"WSHL_X_LONGITUDINAL_EVIDENCE_FIRST_AUDIT_V1",
        "status":"AUDIT_ONLY_NO_PREDICTOR_PROMOTED",
        "scope":{
            "first_reconstructed_event":dates[0],
            "last_reconstructed_event":dates[-1],
            "dated_events_reconstructed":len(dates),
            "reconstructed_decisive_fights":len(clean),
            "historical_fights_without_independent_stage_a_card_artifact":64,
            "historical_fights_with_matching_stage_a_card_artifact":89,
            "later_ufc334_decisive_fights":12,
            "later_ufc334_excluded_draws":1,
            "all_available_reference_decisive_fights":165,
            "different_eras_and_model_vintages_not_one_homogeneous_backtest":True,
            "missing_earlier_projects_cannot_claim_entire_multimonth_history":True,
        },
        "reconstructed_reference_before_334":_summarize(clean),
        "reconstructed_each_event":by_date,
        "cumulative_ledger_prefix_verification":snapshots,
        "original_stage_a_artifact_identity_verification":locks,
        "earlier_first_64":_summarize(early),
        "subsequent_89":_summarize(holdout),
        "sanity_check":{
            "rule":"Using the exact same locked fighter, always choose a fixed method class learned as PLURALITY from first 64 ONLY",
            "first64_method_counts":dict(method_counts),
            "chosen_fixed_method":chosen,
            "subsequent_89_exact_model":sum(x["joint_correct"] for x in holdout),
            "subsequent_89_exact_fixed_method":sum(x["winner_correct"] and x["actual_method"]==chosen for x in holdout),
            "all_153_exact_model":sum(x["joint_correct"] for x in clean),
            "all_153_exact_fixed_method":sum(x["winner_correct"] and x["actual_method"]==chosen for x in clean),
            "not_an_independent_prospectively_registered_benchmark":True,
            "not_a_moneyline_edge_or_roi_claim":True,
        },
        "ufc334_reference":card334,
        "reference_combined_mixed_vintages":{
            "decisive_fights":len(clean)+card334["decisive_fights"],
            "winner_correct":sum(x["winner_correct"] for x in clean)+card334["reference"]["winner_correct"],
            "method_class_correct":sum(x["method_correct"] for x in clean)+card334["reference"]["method_class_correct"],
            "exact_fighter_and_method":sum(x["joint_correct"] for x in clean)+card334["reference"]["exact_fighter_and_method"],
        },
        "strategy_stage_b_recorded":_wagers(),
        "limitations":[
            "Only earliest dated 153 rows in repo, Aug08-Nov07: before Aug08 historical cards not verified by this audit.",
            "The 153-row grade is a reconstructed, clean post-event ledger; 64 rows predate matching separate Stage A artifact evidence in this repository.",
            "Separate old Stage A selection files exist for 7 later events (89 clean fights), but earliest four do not include complete pre-event timestamp proof.",
            "Clean ledger excludes a disqualification (Sep26) and a draw (Oct10); UFC334 separately excludes one draw.",
            "Top method CLASS accuracy ignores winner; exact fighter+method requires BOTH; do not confuse with given-actual-winner oracle studies.",
            "Always-KO baseline is chosen from first64 and compared on next89; hypothesis audited retrospectively, not independent prospective trial.",
            "Official Stage B are documented selections, NOT verified user-placed wagers; price/ROI edge vs closing FanDuel lines is NOT established.",
            "Sep19 initial-frozen and later actionable ledgers are alternatives, NOT additive stake histories.",
            "UFC334 FanDuel +0.2997u virtual research outcomes and Vegas124 hypothetical top5 are NOT real or approved wager PnL.",
            "The three dated model views are correlated; data is too small for model promotion.",
        ],
        "original_models_or_stage_a_b_changed":False,
        "new_predictor_trained_or_promoted":False,
        "fanduel_prices_reused_to_change_stage_a":False,
    }
