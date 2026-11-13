"""Freeze Nov14 UFC334 Top5 + Top5 research watchlist at original FanDuel prices.

Actual approved bets: ZERO pending validated conservative probability
calibration, official Friday weigh-ins / independent fresh price check.
Five of the available positive-raw-EV candidates PER category are
ANALYST-REVIEW RESEARCH ONLY, explicitly not a newly learned betting model.

Markets may appear from the same fight across the 2 price groups ONLY if
both outcomes can win together. One per fight WITHIN a tier. 1u
HYPOTHETICAL future grading is independent from approved bet P&L.
Do not rewrite 13-fight Stage A, quoted price snapshots or full audit.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from wshlx_ufc.two_tier_card import (
    BEST_BETS,LONGSHOTS,fight_key,tier_for_odds,
)
from wshlx_ufc.market_compatibility import can_both_win,validate_market_spec,MARKET_FAMILY_FOR_KIND
from wshlx_ufc.research_top5_ledger import grade_research_watchlist

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"data/locks/ufc334_2026-11-14"
STAGE_A=DIR/"stage_a_final_selection.json"
RAW=DIR/"stage_a_model_raw_three_view.json"
AUDIT=DIR/"stage_b_all_334_fanduel_prices_audit.json"
QUOTES=ROOT/"data/quotes/ufc334_2026-11-14_fanduel_user_screenshots.json"
WATCHFILE=DIR/"stage_b_top5_ranked_research_review_compatible_cross_tier.json"
SUMMARY=DIR/"stage_b_two_tier_outcome.json"
PENDING=DIR/"stage_b_top5_research_units_pending.json"

# Five research-only candidates per category, strictly using available
# pre-event screenshot prices and immutable model probabilities. Ranks are
# NOT ordered by raw EV: extreme UFC timing/method predictions are unreliable.
# Research-only method/timing family gates are NEVER waived.
WATCH={
    BEST_BETS:[
        (8,"Charles Radtke ML",
         "Reference, historical and unified winner views favor Radtke although the book prices Thompson as favorite; screenshot +126 vs two-view probabilities 63.6%/74.5%. This is the best side to investigate but the probability floor and actual fight tape are not independently validated."),
        (7,"OVER 1.5 rounds",
         "Exact original Stage A primary timing outcome and both timing views near 69%; method-joint finish probability disagrees by 17.8pp. Watch only, no timing bet approval."),
        (6,"Terrance McKinney KO_OR_DEC",
         "Winner consensus favors McKinney, though his specific method mixture remains unreliable; two-model joint method outcomes imply a raw edge but this is BLOCKED method-family research."),
        (5,"Donte Johnson KO_OR_SUB",
         "Strong three-view Johnson winner preference. However current versus unified method distributions differ materially and method-family calibration has not passed a betting gate."),
        (9,"OVER 1.5 rounds",
         "Both timing models put survival beyond 7:30 near 58% at +138, but Hasan has only one recorded UFC bout and the entire matchup is PASS. Not an approved selection."),
    ],
    LONGSHOTS:[
        (8,"Charles Radtke by KO_TKO",
         "All three winner views back Radtke and the KO/TKO raw 6-way probabilities appear above the +480 break-even. This is a BLOCKED exact-method candidate; compatible but highly correlated with Best Bet Radtke ML."),
        (7,"Fight goes distance YES",
         "Both simulated timing views exceed 51% at +285, but the 17.8pp finish-family disagreement makes this a high-uncertainty blocked research longshot. Compatible with Dober-Duncan O1.5."),
        (6,"Round 3 starts YES",
         "Extremely large apparent raw edge at +640: current/unified timing roughly 50%. The locked PRIMARY timing pick for this fight is GTD NO, NOT this alternative; long-horizon survival calibration is unreliable. Score as a separate shadow only, never pretend it was the Stage A primary timing prediction."),
        (3,"Fight goes distance YES",
         "About 46% simulated fight-distance probability and +200 price, but Chiasson-Mesquita was a frozen PASS with three-model winner disagreement and a severe method/timing mismatch. No betting approval."),
        (11,"Yousri Belgaroui by KO_TKO",
         "The historical and unified winner views narrowly back Belgaroui; reference opposes him. Large apparent KO method edge at +470 is not validated and fight remains PASS with >15pp method/timing contradiction."),
    ],
}


def read(p):return json.loads(p.read_text())


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def produce():
    stage=read(STAGE_A);audit=read(AUDIT);quote=read(QUOTES)
    if not stage["stage_a_frozen"] or stage["odds_used"] is not False:
        raise RuntimeError("Frozen Stage A missing or altered")
    if stage["raw_model_sha256"]!=sha(RAW):
        raise RuntimeError("Stage A raw model hash changed")
    if audit["stage_a_original_sha256"]!=sha(STAGE_A) or audit["all_quotes_sha256"]!=sha(QUOTES):
        raise RuntimeError("Price audit does not match original card and screenshot")
    if audit["completeness"]["quotes"]!=334 or audit["completeness"]["modeled_quotes"]!=310:
        raise RuntimeError("334 / 310 market audit incomplete")
    if audit["official_approved_card"]["number_official_wagers"]!=0:
        raise RuntimeError("Approved betting picks cannot silently become research only")
    if any(len(WATCH[tier])!=5 for tier in (BEST_BETS,LONGSHOTS)):
        raise RuntimeError("Five research candidates per category required on this display")
    result={BEST_BETS:[],LONGSHOTS:[]};used={};pairs=[]
    for tier in (BEST_BETS,LONGSHOTS):
        for rank,(n,market,rationale) in enumerate(WATCH[tier],1):
            f=stage["fights"][n-1]
            matches=[x for x in audit["all_334_markets"]
                     if x["fight_no"]==n and x["market"]==market]
            if len(matches)!=1:
                raise RuntimeError(f"Missing or ambiguous screenshot market n={n} {market}")
            m=matches[0]
            if m["approved_official"] or m["raw_current_probability"] is None:
                raise RuntimeError("Research watch cannot include official bets or unmodeled draws")
            if tier_for_odds(m["american_odds"])!=tier:
                raise RuntimeError(f"Research price outside requested {tier}")
            if m["raw_current_EV_per_unit"]<=0 or m["unverified_robust_min_EV_per_unit"]<=0:
                raise RuntimeError("Watch must show positive unadjusted EV from both raw frozen views")
            if not m["block_reasons"]:
                raise RuntimeError("Research-only candidate unexpectedly lacks risk blockers")
            spec=m["market_spec"]
            spec=validate_market_spec(spec,market_family=MARKET_FAMILY_FOR_KIND[spec["kind"]],
                                      scheduled_rounds=f["scheduled_rounds"])
            key=fight_key(f["a"],f["b"])
            priors=used.get(key,[])
            if any(z["tier"]==tier for z in priors):
                raise RuntimeError("Two picks from same fight inside a Top5 category")
            if any(spec==z["market_spec"] or not can_both_win(spec,z["market_spec"],
                                         scheduled_rounds=f["scheduled_rounds"])
                   for z in priors):
                raise RuntimeError(f"Incompatible opposite-tier research outcome {market}")
            row={
                "rank":rank,"fight_no":n,
                "fight":f"{f['a']} vs {f['b']}",
                "fight_key":key,"scheduled_rounds":f["scheduled_rounds"],
                "market":market,"market_family":m["market_family"],
                "market_spec":spec,
                "sportsbook":"FanDuel",
                "screenshot_american_odds":m["american_odds"],
                "raw_current_probability":m["raw_current_probability"],
                "unified_shadow_probability":m["raw_unified_probability"],
                "break_even_probability":m["break_even_probability"],
                "raw_current_probability_edge_pp":m["raw_current_edge_pp"],
                "unverified_two_view_min_probability_edge_pp":m["raw_min_two_view_edge_pp"],
                "raw_unadjusted_ev_per_unit":m["raw_current_EV_per_unit"],
                "raw_min_model_ev_per_unit_unvalidated":m["unverified_robust_min_EV_per_unit"],
                "research_notes":rationale,
                "original_stage_a_posture":f["stage_a_posture"],
                "stage_a_primary_timing_prediction":f["primary_timing_forecast"]["market"],
                "is_original_primary_timing_market":m["is_primary_stage_a_timing_market"],
                "stage_a_reference_winner":f["official_reference_pick"],
                "status":"PASS_RESEARCH_ONLY_NOT_APPROVED_OR_BETTABLE",
                "reasons_not_approved":m["block_reasons"],
                "not_in_official_betting_grade":True,
                "not_previously_frozen_official_stage_b_bet":True,
            }
            result[tier].append(row)
            used.setdefault(key,[]).append({"tier":tier,"market":market,"market_spec":spec})
    for key,val in used.items():
        if len(val)==2:
            a=next(x for x in val if x["tier"]==BEST_BETS)
            b=next(x for x in val if x["tier"]==LONGSHOTS)
            pairs.append({"fight_key":key,"best_bet":a["market"],"longshot":b["market"],
                          "can_both_win":True,"highly_correlated":True})
        if len(val)>2:raise RuntimeError("Too many exposures on one bout")
    if len(pairs)!=3 or len(used)!=7:
        raise RuntimeError("Expected exactly three tested cross-tier pairs and seven fights")
    status={
        "event":stage["event"],"event_date":stage["event_date"],
        "report_type":"POST_PRICE_RANKED_FANDUEL_TWO_TIER_RESEARCH_WATCHLIST",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "stage_a_original_sha256":sha(STAGE_A),
        "stage_b_original_sha256":sha(AUDIT),
        "full_price_audit_sha256":sha(AUDIT),
        "fanduel_screenshot_sha256":sha(QUOTES),
        "source_quotes_count":334,
        "exact_fanduel_quote_timestamp_utc":None,
        "input_price_freshness":"User FanDuel screenshot quotes captured Nov11; not live verified on Nov13 weigh-in/fight day",
        "selection_rule":"Analyst-triaged 5+5 positive RAW model-expected-value research scenarios, checking agreement, known source quality, screenshot market definitions, method/timing failures and same-fight compatibility. NOT a validated calibrated EV or a fitted preference model. Not sorted solely by exaggerated longshot raw EV.",
        "stage_a_or_original_stage_b_mutated":False,
        "qualified_bets_in_either_category":0,
        "presented_research_candidates":{BEST_BETS:5,LONGSHOTS:5},
        "one_per_fight_within_each_tier":True,
        "same_fight_cross_tier_allowed_only_if_outcomes_can_coexist":True,
        "same_fight_exposure_warning":"Three logically compatible same-fight pairs can still lose together and are strongly correlated; do not interpret as two independent edges.",
        "distinct_fights_reviewed":len(used),
        "compatible_same_fight_pairs":pairs,
        "categories":result,
        "all_research_only":True,
        "official_bets_approved":0,
        "note":"All ten displayed slots are frozen research PASS, not ten approved bets or proof of money staked. The 1u hypothetical independent ledger is used for grade-after-event only.",
    }
    summary={
        "event":stage["event"],"event_date":stage["event_date"],
        "status":"FANDUEL_STAGE_B_RESEARCH_WATCHLIST_FROZEN_PRE_EVENT_NO_OFFICIAL_BETS",
        "stage_a_sha256":sha(STAGE_A),
        "quotes_sha256":sha(QUOTES),
        "full_audit_sha256":sha(AUDIT),
        "top_5_best_bets":{"research_presented":5,"approved_selected":[],"approved_number":0},
        "top_5_longshots":{"research_presented":5,"approved_selected":[],"approved_number":0},
        "research_watchlist_path":str(WATCHFILE.relative_to(ROOT)),
        "notes":[
            "Research displays five candidates in each FanDuel price tier, not five approved stakes.",
            "Pre-event no bookmaker verified conservative calibration bound; method families all fail market validation and timings can fail 12pp and >15pp coherence safeguards.",
            "Radtke ML is numerically promising but no independent source, calibration, physical tape or official weigh-in verification clears final authorization.",
            "Miller-McKinney +640 R3 starts and extreme +900 GTD share model calibration warnings; ONLY +640 is on research watch, neither is approved.",
            "Original Stage A timing selections are graded separately from later odds-priced research timing markets.",
        ],
        "original_stage_a_mutated":False,
        "snapshot_odds_not_live":True,
        "official_betting_stakes_units":0,
        "official_betting_net_units":0,
        "official_betting_roi":None,
    }
    return status,summary


def main():
    if any(p.exists() for p in (WATCHFILE,SUMMARY,PENDING)):
        raise RuntimeError("Cannot overwrite prior pre-event two-tier research locks")
    card,summary=produce()
    # Grade as PRE-EVENT pending to establish all odds and 1u shadow exposure
    # WITHOUT inventing winners or implying bets placed.
    pending=grade_research_watchlist(card)
    if pending["combined"]["displayed_candidates"]!=10 or pending["combined"]["record"]["PENDING"]!=10:
        raise RuntimeError("Research ledger should start with 10 unsettled candidates")
    WATCHFILE.write_text(json.dumps(card,indent=2,sort_keys=True)+"\n")
    SUMMARY.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    pending.update({
        "status":"PRE_EVENT_PENDING_ONLY_NO_RESULTS",
        "frozen_research_watchlist_sha256":sha(WATCHFILE),
        "fanduel_screenshot_sha256":sha(QUOTES),
        "source_price_timestamp_utc":None,
        "event_not_yet_started":True,
        "approved_bets_coincidence":False,
        "no_results_graded":True,
        "produced_at_utc":datetime.now(timezone.utc).isoformat(),
    })
    PENDING.write_text(json.dumps(pending,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "status":summary["status"],
        "best_bet_research":card["presented_research_candidates"][BEST_BETS],
        "longshot_research":card["presented_research_candidates"][LONGSHOTS],
        "same_fight_compatible_pairs":card["compatible_same_fight_pairs"],
        "pending":pending["combined"]["record"],
        "official_approved":0,"no_actual_bets_claimed":True,
    },indent=2))


if __name__=="__main__":main()
