"""Evidence-audited November 7 UFC card grading; NO pre-fight lock mutation.

Source of truth: immutable odds-blind Stage A, its RAW three model views,
separate pre-event one-timing-per-bout research card, archived FanDuel 5+5
research watchlist and November 8 verified 14-bout outcome file.

Outputs new versioned artifacts ONLY:
- 14 fight-level winner/method/timing model grading and probabilistic metrics
- 10 fixed original FanDuel quote 1u research hypothetical settlements/ROI
- 153-row cumulative previously frozen 139+14 official reference model ledger

Never conflate:
  exact fighter+method vs merely guessing the outcome method;
  current reference's conditional method if it wins vs challenger own pick;
  research-only 1u hypothetical P&L vs approved/placed official bets;
  post-price timing-selection research vs originally frozen Stage A picks;
  result grading vs importing verified per-fighter per-round UFCStats.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from wshlx_ufc.market_compatibility import _wins as settlement_wins
from wshlx_ufc.research_top5_ledger import candidate_id, grade_research_watchlist
from wshlx_ufc.two_tier_card import LONGSHOTS, BEST_BETS

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/"data/locks/ufcvegas124_2026-11-07"
STAGE_A=LOCK/"stage_a_final_selection.json"
RAW=LOCK/"stage_a_model_raw_three_view.json"
TIME=LOCK/"stage_b_one_timing_forecast_per_fight.json"
WATCH=LOCK/"stage_b_top5_ranked_research_review_compatible_cross_tier.json"
PENDING=LOCK/"stage_b_top5_research_units_pending.json"
ORIG_STAGE_B=LOCK/"stage_b_two_tier_outcome.json"
OUTCOMES=ROOT/"data/results/ufcvegas124_2026-11-07_verified_outcomes.json"
PRIOR=ROOT/"data/results/clean_ufc_139_2026-10-24.csv"

GRADE=ROOT/"data/results/ufcvegas124_2026-11-07_all_models_grading.json"
SETTLEMENTS=ROOT/"data/results/ufcvegas124_2026-11-07_top5_verified_settlements.json"
RESEARCH_GRADE=ROOT/"data/results/ufcvegas124_2026-11-07_top5_research_unit_grade.json"
CUMULATIVE=ROOT/"data/results/clean_ufc_153_2026-11-07.csv"

METHODS=("KO","SUB","DEC")
SIDES=("a","b")
METHOD_KEYS={("a","KO"):"A_KO",("a","SUB"):"A_SUB",("a","DEC"):"A_DEC",
             ("b","KO"):"B_KO",("b","SUB"):"B_SUB",("b","DEC"):"B_DEC"}


def _json(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _hash(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _validate_prob(p):
    value=float(p)
    if not math.isfinite(value) or not 0<=value<=1:
        raise RuntimeError(f"Invalid probability {p}")
    return value


def _winner_prob_a(f,view):
    val=f["winner_views"][view]
    _validate_prob(val["probability"])
    return val["probability"] if val["pick"]==f["a"] else 1-val["probability"]


def _prob_scores(probabilities,actual_label):
    s=sum(float(x) for x in probabilities.values())
    if abs(s-1)>2e-4:
        raise RuntimeError(f"Predictive distribution not normalized: {s}")
    for p in probabilities.values():
        _validate_prob(p)
    if actual_label not in probabilities:
        raise RuntimeError("Actual class missing from frozen probability vector")
    return {
        "multiclass_brier":sum((p-(1 if k==actual_label else 0))**2 for k,p in probabilities.items()),
        "log_loss":-math.log(max(float(probabilities[actual_label]),1e-15))
    }


def _top(p):
    return max(METHODS,key=lambda k:p[k])


def _method_dist(joint,side):
    # The 6-way scorer standardizes frozen A_KO/B_KO source keys into
    # lower-case side outcome labels a_KO/b_KO. Read that normalized object.
    values={k:_validate_prob(joint[f"{side}_{k}"]) for k in METHODS}
    total=sum(values.values())
    if not total or total>1.00001:
        raise RuntimeError("Invalid frozen 6-way method model")
    return {k:p/total for k,p in values.items()}


def _six_way(joint):
    scores={f"{side}_{method}":_validate_prob(joint[METHOD_KEYS[(side,method)]])
             for side in SIDES for method in METHODS}
    if abs(sum(scores.values())-1)>1e-5:
        raise RuntimeError("Not a normalized frozen 6-way joint distribution")
    return scores


def _timing_spec(metric):
    if metric.startswith("GTD_"):
        return {"kind":"goes_distance","outcome":metric[4:]}
    if metric.startswith("OVER_") or metric.startswith("UNDER_"):
        direction,threshold=metric.split("_",1)
        return {"kind":"total_rounds","direction":direction,"threshold":float(threshold)}
    if metric.startswith("ROUND_") and "_STARTS_" in metric:
        tok=metric.split("_")
        return {"kind":"round_to_start","round":int(tok[1]),"outcome":tok[-1]}
    raise RuntimeError(f"Unsupported locked timing market {metric}")


def _row_result(f,outcome):
    if outcome["winner"] not in (f["a"],f["b"]):
        raise RuntimeError(f'Unexpected actual winner {outcome["winner"]} in bout {f["fight_no"]}')
    if outcome["method"] not in METHODS:
        raise RuntimeError("Unrecognized official result method")
    r=outcome["round"]
    if type(r) is not int or not 1<=r<=f["scheduled_rounds"]:
        raise RuntimeError("Actual finish round conflicts with locked scheduled fight")
    elapsed=int(outcome["elapsed_seconds"])
    if not 1<=elapsed<=f["scheduled_rounds"]*300:
        raise RuntimeError("Actual elapsed time outside normal fight bounds")
    if outcome["method"]=="DEC" and elapsed!=f["scheduled_rounds"]*300:
        raise RuntimeError("Decision must go full scheduled distance")
    return "a" if outcome["winner"]==f["a"] else "b"


def _date_source_integrity(f,r,t,w,prior,pending,outcomes,stage_b):
    if not (f["stage_a_frozen"] is True and f["odds_used"] is False):
        raise RuntimeError("Original official winner/model odds blind lock changed")
    if f["raw_model_sha256"]!=_hash(RAW):
        raise RuntimeError("Frozen raw models no longer match Stage A SHA")
    if t["original_stage_a_sha256"]!=_hash(STAGE_A) or t["post_price_research_selection"] is not True:
        raise RuntimeError("Timing pre-event provenance lost")
    if w["stage_a_original_sha256"]!=_hash(STAGE_A) or w["stage_b_original_sha256"]!=_hash(ORIG_STAGE_B):
        raise RuntimeError("Ranked research watchlist no longer matches pre-event hashes")
    if pending["frozen_research_watchlist_sha256"]!=_hash(WATCH):
        raise RuntimeError("Pre-event 1u prices / PENDING ledger no longer match")
    if pending["status"]!="PRE_EVENT_PENDING_ONLY_NO_RESULTS" or pending["combined"]["record"]["PENDING"]!=10:
        raise RuntimeError("Pre-event pending ledger has retroactive result contamination")
    if stage_b["top_5_longshots"]["number_selected"]!=0 or stage_b["top_5_best_bets"]["number_selected"]!=0:
        raise RuntimeError("Official originally approved bet count was not zero")
    if outcomes["status"]!="VERIFIED_EVENT_OUTCOMES_POST_EVENT" or outcomes["bout_count"]!=14:
        raise RuntimeError("Results have not been independently verified")
    if not outcomes["source_urls"] or not all(u.startswith("https://") for u in outcomes["source_urls"]):
        raise RuntimeError("External evidence required")
    if not (f["event_date"]==r["event_date"]==t["event_date"]==w["event_date"]==
            outcomes["event_date"]==stage_b["event_date"]=="2026-11-07"):
        raise RuntimeError("Event identity mismatch")
    if any(len(seq)!=14 for seq in (f["fights"],r["fights"],t["fights"],outcomes["fights"])):
        raise RuntimeError("Exactly 14 fights required")
    if prior[0]!=["event_date","fight","locked_pick","actual_winner","displayed_method",
                  "actual_method","winner_correct","method_correct","joint_correct"] or len(prior)!=140:
        raise RuntimeError("139-row prior reference ledger schema drift")
    if any(row[0]=="2026-11-07" for row in prior[1:]):
        raise RuntimeError("Nov 7 already included in legacy reference ledger")


def compute():
    frozen=_json(STAGE_A)
    raw=_json(RAW)
    timing=_json(TIME)
    watch=_json(WATCH)
    pending=_json(PENDING)
    old_stage_b=_json(ORIG_STAGE_B)
    actual=_json(OUTCOMES)
    with PRIOR.open(newline="",encoding="utf-8") as fh:
        prior=list(csv.reader(fh))
    _date_source_integrity(frozen,raw,timing,watch,prior,pending,actual,old_stage_b)
    scored=[]
    timing_scores=[]
    joint_scores={"reference":[],"historical":[],"unified":[]}
    brier_scores={"reference":[],"historical":[],"unified":[]}
    logloss_scores={"reference":[],"historical":[],"unified":[]}
    three_method_class={"reference":[],"historical":[],"unified":[]}
    six_way_scores={"reference":[],"historical":[],"unified":[]}
    six_way_logloss={"reference":[],"historical":[],"unified":[]}
    for i,(f,r,t,y) in enumerate(zip(frozen["fights"],raw["fights"],timing["fights"],actual["fights"]),1):
        if any(k["fight_no"]!=i for k in (f,r,t,y)):
            raise RuntimeError(f"Fighter order drift at bout {i}")
        if t["fight"]!=f'{f["a"]} vs {f["b"]}':
            raise RuntimeError("Timing research pick changed matchup")
        actual_side=_row_result(f,y)
        actual_key=f"{actual_side}_{y['method']}"
        view_picks={k:f["winner_views"][kind]["pick"]
                    for k,kind in (("reference","reference"),("historical","historical_shadow"),("unified","oof_unified_shadow"))}
        views_joint={
            "reference":_six_way(r["joint_calibrated"]),
            "historical":_six_way(r["historical_shadow"]["joint_method"]),
            "unified":_six_way(r["oof_unified_shadow"]["joint_method"]),
        }
        method_cond_reference={
            "reference":f["method"]["current_conditional_if_official_winner"],
            "historical":f["method"]["historical_conditional_if_official_winner"],
            "unified":f["method"]["oof_unified_conditional_if_official_winner"],
        }
        views={}
        for key,win_pick in view_picks.items():
            if win_pick not in (f["a"],f["b"]):
                raise RuntimeError("Frozen winner not a participant")
            predicted_side="a" if win_pick==f["a"] else "b"
            p_a=_winner_prob_a(f,{"reference":"reference","historical":"historical_shadow",
                                  "unified":"oof_unified_shadow"}[key])
            bin_dist={"a":p_a,"b":1-p_a}
            winner_metric=_prob_scores(bin_dist,actual_side)
            brier_scores[key].append(winner_metric["multiclass_brier"])
            logloss_scores[key].append(winner_metric["log_loss"])
            side_method=_method_dist(views_joint[key],predicted_side)
            if key=="reference":
                # Explicitly check frozen current method conditional distribution,
                # not a restated/calibrated post-event version.
                for m in METHODS:
                    if abs(side_method[m]-method_cond_reference[key][m])>0.01:
                        raise RuntimeError("Reference conditional method changed")
            top=_top(side_method)
            top_for_reference_side=_top(method_cond_reference[key])
            winner_ok=win_pick==y["winner"]
            method_ok=top==y["method"]
            joint_ok=winner_ok and method_ok
            joint_scores[key].append(joint_ok)
            three_method_class[key].append(top_for_reference_side==y["method"])
            joint_metric=_prob_scores(views_joint[key],actual_key)
            six_way_scores[key].append(joint_metric["multiclass_brier"])
            six_way_logloss[key].append(joint_metric["log_loss"])
            views[key]={
                "pick":win_pick,
                "win_probability_at_prediction":f["winner_views"][
                    {"reference":"reference","historical":"historical_shadow",
                     "unified":"oof_unified_shadow"}[key]
                ]["probability"],
                "winner_correct":winner_ok,
                "own_selected_fighter_conditional_method":top,
                "own_selected_fighter_conditional_method_probabilities":side_method,
                "own_fighter_and_method_correct":joint_ok,
                "method_correct_given_own_fighter_won":method_ok if winner_ok else None,
                "reference_fighter_method_class_only":top_for_reference_side,
                "reference_fighter_method_class_matches_actual_ignoring_winner":top_for_reference_side==y["method"],
                "winner_multiclass_brier":winner_metric["multiclass_brier"],
                "winner_logloss":winner_metric["log_loss"],
                "joint_method_6class_brier":joint_metric["multiclass_brier"],
                "joint_method_6class_logloss":joint_metric["log_loss"],
            }
        tspec=_timing_spec(t["metric"])
        timing_win=settlement_wins(tspec, actual_side,y["method"],y["elapsed_seconds"],
                                   f["scheduled_rounds"]*300)
        timing_scores.append(timing_win)
        if not t["stage_b_timing_market_approved"]:
            status="RESEARCH_TIMING_FORECAST_NO_APPROVED_STAKE"
        else:
            raise RuntimeError("No timing wager approved in initial Stage B")
        scored.append({
            "fight_no":i, "fight":t["fight"],"stage_a_reference_posture":f["stage_a_posture"],
            "winner":y["winner"],"method":y["method"],"round":y["round"],"time":y["time"],
            "seconds_elapsed":y["elapsed_seconds"],"actual_details":y["detail"],
            "model_views":views,
            "timing_research":{
                "market":t["market"],"metric":t["metric"],
                "current_simulated_probability":t["current_simulated_probability"],
                "unified_shadow_probability":t["unified_shadow_simulated_probability"],
                "fanduel_snapshot_american_odds":t["fanduel_screenshot_odds"],
                "result":"W" if timing_win else "L","correct":timing_win,
                "status":status,"betting_gate_failures":t["timing_market_block_reasons"],
            },
        })
    scores={}
    for model in ("reference","historical","unified"):
        vals=[row["model_views"][model] for row in scored]
        w=sum(x["winner_correct"] for x in vals)
        j=sum(x["own_fighter_and_method_correct"] for x in vals)
        conditional=[x["method_correct_given_own_fighter_won"] for x in vals
                     if x["method_correct_given_own_fighter_won"] is not None]
        scores[model]={
            "winner_W":w,"winner_L":14-w,"winner_rate":w/14,
            "own_fighter_and_method_W":j,"own_fighter_and_method_L":14-j,
            "exact_winner_method_rate":j/14,
            "method_given_correct_winner_W":sum(conditional),
            "method_given_correct_winner_L":len(conditional)-sum(conditional),
            "method_given_correct_winner_rate":sum(conditional)/len(conditional),
            "reference_side_method_class_only_matches":sum(three_method_class[model]),
            "reference_side_method_class_only_total":14,
            "mean_winner_multiclass_brier":sum(brier_scores[model])/14,
            "mean_winner_logloss":sum(logloss_scores[model])/14,
            "mean_joint_method_six_class_brier":sum(six_way_scores[model])/14,
            "mean_joint_method_six_class_logloss":sum(six_way_logloss[model])/14,
            "actual_submission_method_recall_class_only":sum(
                1 for row in scored if row["method"]=="SUB" and
                row["model_views"][model]["reference_fighter_method_class_only"]=="SUB"
            ),
        }
    methods=Counter(y["method"] for y in actual["fights"])
    if methods!=Counter({"KO":6,"SUB":1,"DEC":7}):
        raise RuntimeError("Unexpected actual method result mix")
    if [scores[k]["winner_W"] for k in ("reference","historical","unified")]!=[9,11,11]:
        raise RuntimeError("Reference or challenger winner grading inconsistent with verified outcomes")
    if [scores[k]["own_fighter_and_method_W"] for k in ("reference","historical","unified")]!=[5,7,8]:
        raise RuntimeError("Winner+own-side method grading unexpectedly drifted")
    if sum(timing_scores)!=10:
        raise RuntimeError("14 timing picks should grade 10-4 on verified results")

    settlements={}
    for tier in (LONGSHOTS,BEST_BETS):
        for w in watch["categories"][tier]:
            n=w["fight_no"]
            f=frozen["fights"][n-1]
            y=actual["fights"][n-1]
            actual_side="a" if y["winner"]==f["a"] else "b"
            spec=w["market_spec"]
            if spec["kind"]=="total_rounds" and y["elapsed_seconds"]==round(spec["threshold"]*300):
                outcome="PUSH"
            else:
                outcome="W" if settlement_wins(spec,actual_side,y["method"],y["elapsed_seconds"],
                                             f["scheduled_rounds"]*300) else "L"
            settlements[candidate_id(tier,w["rank"],n)]=outcome
    top5=grade_research_watchlist(watch,settlements)
    if top5["categories"][LONGSHOTS]["record"]["L"]!=5:
        raise RuntimeError("Longshot grading expected 0-5 on verified results")
    best=top5["categories"][BEST_BETS]
    if (best["record"]["W"],best["record"]["L"])!=(2,3):
        raise RuntimeError("Best-bet grading expected 2-3 on verified results")
    if abs(top5["combined"]["hypothetical_net_units"]+5.12)>1e-8:
        raise RuntimeError("Original FanDuel P&L does not match -5.12u")
    outcome_input={
        "event_date":actual["event_date"],"event":actual["event"],
        "status":"VERIFIED_POST_EVENT_MARKET_SETTLEMENTS",
        "research_card_sha256":_hash(WATCH),"pre_event_pending_ledger_sha256":_hash(PENDING),
        "original_stage_b_sha256":_hash(ORIG_STAGE_B),
        "verified_bout_outcomes_sha256":_hash(OUTCOMES),
        "results_verified":True,
        "evidence":"Official UFC event https://www.ufc.com/event/ufc-fight-night-november-07-2026 ; Fightful https://www.fightful.com/mma/ufc-fight-night-cortes-acosta-vs-walker-results-11-7/ ; MMA Fighting https://www.mmafighting.com/fight-results/ufc ; time/round and market settlement derived from quoted typed FanDuel market contracts",
        "results":settlements,
        "staked_real_money":False,
        "price_source":"Original FanDuel user screenshots; virtual 1 unit per pick",
    }
    top5.update({
        "status":"VERIFIED_EVENT_RESEARCH_RESULTS",
        "frozen_research_watchlist_sha256":_hash(WATCH),
        "settlement_evidence":outcome_input["evidence"],
        "result_verification_provenance":actual["source_urls"],
        "settlement_input_sha256":hashlib.sha256((json.dumps(outcome_input,indent=2,sort_keys=True)+"\n").encode()).hexdigest(),
        "original_fanduel_snapshot_sha256":watch["fanduel_screenshot_sha256"],
        "graded_at_utc":datetime.now(timezone.utc).isoformat(),
    })
    output={
        "schema_version":"1.0","event":actual["event"],"event_date":actual["event_date"],
        "status":"POST_EVENT_GRADED_ALL_14_IMMUTABLE_STAGE_A_WINNERS_METHODS_AND_PRE_EVENT_TIMING",
        "graded_at_utc":datetime.now(timezone.utc).isoformat(),
        "original_stage_a_sha256":_hash(STAGE_A),"raw_model_sha256":_hash(RAW),
        "timing_research_sha256":_hash(TIME),
        "top5_research_sha256":_hash(WATCH),"original_stage_b_sha256":_hash(ORIG_STAGE_B),
        "verified_outcomes_sha256":_hash(OUTCOMES),
        "evidence_sources":actual["source_urls"],
        "fights":scored,
        "scoreboards":scores,
        "all_fights":14,
        "observed_finish_distribution":dict(methods),
        "single_primary_timing_research":{"W":sum(timing_scores),"L":14-sum(timing_scores),
            "accuracy":sum(timing_scores)/14,"status":"POST_PRICE_PRE_FIGHT_RESEARCH_NOT_ORIGINAL_STAGE_A"},
        "top5_hypothetical_research_1u":{
            "longshots":{k:top5["categories"][LONGSHOTS][k] for k in
                         ("record","hypothetical_net_units","hypothetical_roi")},
            "best_bets":{k:top5["categories"][BEST_BETS][k] for k in
                         ("record","hypothetical_net_units","hypothetical_roi")},
            "combined":top5["combined"],
        },
        "official_approved_betting_record":{"longshots":{"bets":0,"staked_units":0,"pnl_units":0},
                                            "best_bets":{"bets":0,"staked_units":0,"pnl_units":0},
                                            "total_bets":0,"staked_units":0,"pnl_units":0,
                                            "roi":None},
        "important_distinctions":[
            "Winner+method score is graded against each challenger's OWN chosen fighter and its own-side conditional method, not against reference fighter's conditional method when pick differs.",
            "Displayed method class match ignoring wrong fighter is a diagnostic, NOT a won exact fighter+method wager.",
            "The timing-one-per-fight selection was saved pre-event after screenshot prices had been seen, and is graded as pre-fight research, not original odds-blind Stage A.",
            "The Top 5 lists consisted only of PASS/research candidates. Hypothetical 1u units and ROI are not approved bets, not money staked and not evidence any bet was placed.",
            "Per-fight UFCStats rounds/knockdowns/takedowns/sig strikes are not silently invented and have not been imported into the ML training rows.",
            "No automatic re-training, challenger promotion, or betting gate relaxation based on 14 fights.",
        ],
    }

    extra=[]
    for row in scored:
        model=row["model_views"]["reference"]
        extra.append([
            actual["event_date"],row["fight"],model["pick"],row["winner"],
            model["own_selected_fighter_conditional_method"],row["method"],
            int(model["winner_correct"]),int(model["reference_fighter_method_class_matches_actual_ignoring_winner"]),
            int(model["own_fighter_and_method_correct"]),
        ])
    output_csv=io.StringIO()
    writer=csv.writer(output_csv,lineterminator="\n")
    writer.writerows(prior+extra)
    if len(prior)+len(extra)!=154:
        raise RuntimeError("Cumulative frozen grading would not contain 153 fights")
    summary_prior={
        "count":len(prior)-1,
        "winner_W":sum(int(row[6]) for row in prior[1:]),
        "displayed_method_class_match_W":sum(int(row[7]) for row in prior[1:]),
        "joint_W":sum(int(row[8]) for row in prior[1:]),
    }
    summary_after={
        "count":len(prior)+len(extra)-1,
        "winner_W":summary_prior["winner_W"]+scores["reference"]["winner_W"],
        "displayed_method_class_match_W":summary_prior["displayed_method_class_match_W"]+
                                        scores["reference"]["reference_side_method_class_only_matches"],
        "joint_W":summary_prior["joint_W"]+scores["reference"]["own_fighter_and_method_W"],
    }
    output["reference_prior_history_139"]=summary_prior
    output["reference_cumulative_153"]=summary_after
    if summary_prior != {"count":139,"winner_W":83,"displayed_method_class_match_W":70,"joint_W":43}:
        raise RuntimeError("139-row prior record not preserved")
    if summary_after!={"count":153,"winner_W":92,"displayed_method_class_match_W":79,"joint_W":48}:
        raise RuntimeError("Updated 153-row cumulative result inconsistent")
    return output,outcome_input,top5,output_csv.getvalue()


def main():
    output,settlement,top5,all_csv=compute()
    for p in (GRADE,SETTLEMENTS,RESEARCH_GRADE,CUMULATIVE):
        if p.exists():
            raise RuntimeError(f"Refusing to overwrite existing grading artifact: {p}")
    GRADE.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    SETTLEMENTS.write_text(json.dumps(settlement,indent=2,sort_keys=True)+"\n")
    RESEARCH_GRADE.write_text(json.dumps(top5,indent=2,sort_keys=True)+"\n")
    CUMULATIVE.write_text(all_csv)
    print(json.dumps({
        "event":output["event"],
        "winners":{k:v["winner_W"] for k,v in output["scoreboards"].items()},
        "exact_winner_plus_method":{k:v["own_fighter_and_method_W"] for k,v in output["scoreboards"].items()},
        "primary_timing":output["single_primary_timing_research"],
        "top5_hypothetical":output["top5_hypothetical_research_1u"],
        "cumulative_reference":output["reference_cumulative_153"],
        "result_files":[str(x.relative_to(ROOT)) for x in (GRADE,SETTLEMENTS,RESEARCH_GRADE,CUMULATIVE)],
    },indent=2))


if __name__=="__main__":
    main()
