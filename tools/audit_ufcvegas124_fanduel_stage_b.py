"""Full pre-event FanDuel price audit for frozen UFC Vegas 124 (2026-11-07).

Compares all user-screenshot lines to the actual Nov 7 frozen Stage A model.
Does not fabricate a calibrated lower-bound probability, backdate a quote,
promote invalid method prices, change raw picks, or turn PASS into a bet.

The Top5 tiering code is shared with existing policy. The output always
distinguishes mathematically positive *raw* model edges from QUALIFIED
official selections, and persists even when both categories are empty.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from wshlx_ufc.two_tier_card import (
    BEST_BETS, LONGSHOTS, break_even, expected_value, tier_for_odds,
)
from wshlx_ufc.coherence import finish_probability

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/"data/locks/ufcvegas124_2026-11-07"
QUOTES=ROOT/"data/quotes/ufcvegas124_2026-11-07_fanduel_user_screenshots.json"
FREEZE=LOCK/"stage_a_final_selection.json"
RAW=LOCK/"stage_a_model_raw_three_view.json"
COHERENCE=LOCK/"stage_a_coherence_audit.json"
OUT=LOCK/"stage_b_fanduel_full_price_audit.json"
SUMMARY=LOCK/"stage_b_two_tier_outcome.json"

WEIGHTS_LB={
    1:[169.5,171.0],2:[171.0,171.0],3:[186.0,185.5],4:[145.5,145.5],
    5:[145.5,146.0],6:[125.0,126.0],7:[234.0,253.5],8:[145.0,145.5],
    9:[125.5,126.0],10:[136.0,136.0],11:[206.0,205.0],
    12:[135.5,135.5],13:[115.5,116.0],14:[262.0,239.0],
}
WEIGH_SOURCE="https://www.ufc.com/news/official-weigh-in-results-ufc-fight-night-cortes-acosta-vs-walker"

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def _side_probability(view:dict, name:str)->float:
    p=float(view["probability"])
    return p if view["pick"]==name else 1-p

def _add(rows, *, no, market, group, side, price, p_current, p_unified, research, evidence, finish_gap):
    if not isinstance(price,int) or -99<=price<=99:
        raise ValueError(f"Invalid odds on fight {no}: {market}: {price}")
    tier=tier_for_odds(price)
    if p_current is None:
        rows.append(dict(fight_no=no, market=market,group=group,
                         fighter_side=side,american_odds=price,
                         raw_model_probability=None, raw_ev_per_unit=None,
                         break_even=break_even(price), tier=tier,
                         eligible=False, block_reasons=["no_draw_model_probability"]))
        return
    p=float(p_current)
    q=float(p_unified)
    if not 0<=p<=1 or not 0<=q<=1:
        raise ValueError(f"Bad model probability on fight {no}: {market}")
    implied=break_even(price)
    edge=p-implied
    ev=expected_value(price,p)
    floor=min(p,q)
    floor_edge=floor-implied
    floor_ev=expected_value(price,floor)
    reasons=[]
    if tier is None:
        reasons.append("outside_requested_price_bands")
    if side is not None and group=="moneyline" and side!=research["official_pick"]:
        reasons.append("oppose_frozen_reference_side_price_cannot_flip")
    if research["posture"]=="PASS":
        reasons.append("stage_a_research_pass")
    if group in ("method_of_victory","double_chance","how_fight_ends"):
        reasons.append("official_method_doublechance_family_blocked_by_stage_a_coherence")
    if group in ("goes_distance","total_rounds","round_to_start"):
        if min(evidence)<2:
            reasons.append("sparse_ufc_history_blocks_timing")
        if abs(finish_gap)>.15:
            reasons.append("timing_and_method_finish_models_disagree_gt_15pp")
        if edge <.12-1e-12:
            reasons.append("current_timing_edge_below_12pp")
        if floor_edge <.12-1e-12:
            reasons.append("unified_timing_shadow_edge_below_12pp")
    if edge<=0 or ev<=0:
        reasons.append("no_positive_raw_EV")
    if floor_edge<=0 or floor_ev<=0:
        reasons.append("no_positive_two_view_robustness_check")
    eligible=not reasons
    rows.append({
        "fight_no":no,"market":market,"group":group,"fighter_side":side,
        "american_odds":price,"tier":tier,"break_even":implied,
        "raw_model_probability":p,"unified_shadow_probability":q,
        "unverified_two_view_min_probability":floor,
        "raw_probability_edge_pp":100*edge,"raw_ev_per_unit":ev,
        "two_view_min_probability_edge_pp":100*floor_edge,
        "two_view_min_ev_per_unit":floor_ev,
        "method_timing_finish_gap_pp":100*finish_gap,
        "eligible":eligible,
        "block_reasons":reasons,
        "two_view_min_not_a_validated_calibrated_lower_bound":True,
    })

def compute():
    freeze=json.loads(FREEZE.read_text())
    raw=json.loads(RAW.read_text())
    quote=json.loads(QUOTES.read_text())
    coherence=json.loads(COHERENCE.read_text())
    if not freeze["stage_a_frozen"] or freeze["odds_used"]:
        raise RuntimeError("Stage A must be odds blind and immutable")
    if sha(RAW)!=freeze["raw_model_sha256"] or coherence["frozen_source_sha256"]!=sha(FREEZE):
        raise RuntimeError("Frozen model/audit provenance drift")
    if quote["sportsbook"]!="FanDuel" or quote["event_date"]!=freeze["event_date"]:
        raise RuntimeError("Non-FanDuel or wrong event")
    if len(freeze["fights"])!=14 or len(raw["fights"])!=14 or len(quote["quoted_markets"])!=14:
        raise RuntimeError("Expected all 14 fights")
    if len(WEIGHTS_LB)!=14:
        raise RuntimeError("Weigh-in source incomplete")
    rows=[]
    for f, r, q in zip(freeze["fights"],raw["fights"],quote["quoted_markets"]):
        i=f["fight_no"]
        if i!=r["fight_no"] or i!=q["fight_no"] or (f["a"],f["b"])!=(q["a"],q["b"]):
            raise RuntimeError(f"Snapshot and frozen card fight mismatch at {i}")
        j=r["joint_calibrated"]
        ju=r["oof_unified_shadow"]["joint_method"]
        t=f["timing_current"]["sim_10000"]
        tu=f["timing_oof_unified_shadow"]["sim_10000"]
        finish_gap=finish_probability(j)-t["GTD_NO"]
        evidence=(f["evidence_density"]["a_prior_ufc_bouts"],f["evidence_density"]["b_prior_ufc_bouts"])
        research={"official_pick":f["official_reference_pick"],"posture":f["stage_a_posture"]}
        def add(market,group,side,price,p,pu):
            _add(rows,no=i,market=market,group=group,side=side,price=price,p_current=p,
                 p_unified=pu,research=research,evidence=evidence,finish_gap=finish_gap)
        for side,key in (("a","A"),("b","B")):
            nm=f[side]
            add(f"{nm} ML","moneyline",nm,q["moneyline"][side],
                f["official_reference_probability_a"] if side=="a" else 1-f["official_reference_probability_a"],
                r["oof_unified_shadow"]["winner_p_a"] if side=="a" else 1-r["oof_unified_shadow"]["winner_p_a"])
            for m,tail in (("KO_TKO","KO"),("SUB","SUB"),("DEC","DEC")):
                add(f"{nm} by {m}","method_of_victory",nm,q["method_of_victory"][side][m],
                    j[f"{key}_{tail}"],ju[f"{key}_{tail}"])
            for pair,tails in (("KO_OR_SUB",("KO","SUB")),("KO_OR_DEC",("KO","DEC")),("SUB_OR_DEC",("SUB","DEC"))):
                add(f"{nm} {pair}","double_chance",nm,q["double_chance"][side][pair],
                    sum(j[f"{key}_{k}"] for k in tails),
                    sum(ju[f"{key}_{k}"] for k in tails))
        # Draw has no predictive probability in the model. Record both odds and fail closed.
        add("Draw: method of victory","method_of_victory",None,q["method_of_victory"]["DRAW"],None,None)
        add("Draw: double chance","double_chance",None,q["double_chance"]["DRAW"],None,None)
        for p in ("YES","NO"):
            name=f"GTD_{p}"
            add(f"Fight goes distance {p}","goes_distance",None,q["goes_distance"][p],t[name],tu[name])
        tr=q["total_rounds"]
        if tr is not None:
            for side in ("OVER","UNDER"):
                metric=f"{side}_{tr['threshold']}"
                add(f"{side} {tr['threshold']} rounds","total_rounds",None,tr[side],t[metric],tu[metric])
        for market,suffix in (("KO_TKO","KO"),("SUB","SUB"),("DEC","DEC")):
            add(f"Fight ends by {market}","how_fight_ends",None,q["how_fight_ends"][market],
                j["A_"+suffix]+j["B_"+suffix],ju["A_"+suffix]+ju["B_"+suffix])
        for n,pp in q["round_to_start"].items():
            for ans in ("YES","NO"):
                label=f"ROUND_{n}_STARTS_{ans}"
                add(f"Round {n} starts {ans}","round_to_start",None,pp[ans],t[label],tu[label])
        if i==14 and len(q["round_to_start"])!=4:
            raise RuntimeError("Five-round main-event round markets incomplete")

    # Rank the raw biggest discrepancies only as REJECTED watchlists, never as bets.
    def blocked_watch(tier):
        cand=[x for x in rows if x["tier"]==tier and x["raw_ev_per_unit"] is not None
              and x["raw_ev_per_unit"]>0 and not x["eligible"]]
        cand.sort(key=lambda x:(-x["raw_ev_per_unit"],x["fight_no"],x["market"]))
        out=[]; used=set()
        for m in cand:
            if m["fight_no"] not in used:
                out.append({k:m[k] for k in ("fight_no","market","american_odds","raw_model_probability",
                        "raw_probability_edge_pp","raw_ev_per_unit","block_reasons")})
                used.add(m["fight_no"])
            if len(out)>=5: break
        return out
    eligible=[r for r in rows if r["eligible"]]
    for row in eligible:
        if row["tier"] is None:
            raise RuntimeError("Eligible row fell outside tier")
    # None currently qualifies. Fail closed rather than artificially write an
    # empty official card if a future changed source would yield eligibility.
    if eligible:
        raise RuntimeError(f"{len(eligible)} qualifying market(s) found. Require timestamped, \
independently justified conservative-probability Stage B selection before freeze: "+
            repr([(r["fight_no"],r["market"],r["american_odds"]) for r in eligible]))
    modeled=sum(x["raw_model_probability"] is not None for x in rows)
    full={
        "event":freeze["event"],"event_date":freeze["event_date"],
        "status":"FULL_364_MARKET_PRICE_AUDIT_ZERO_QUALIFIED_TWO_TIER_BETS",
        "stage":"B_FANDUEL_SCREENSHOT_PRICE_COMPARISON",
        "stage_a_sha256":sha(FREEZE),"raw_model_sha256":sha(RAW),
        "source_quotes_sha256":sha(QUOTES),
        "odds_source":quote["source"],"sportsbook":"FanDuel",
        "exact_quote_timestamp_utc":None,
        "price_freshness":"Snapshot received from user pre-event; price must be checked in FanDuel before staking.",
        "research_and_model_history_unchanged":True,
        "weigh_in_verified":"All 28 athletes made weight in official UFC Friday weigh-in report",
        "official_weights_lb_by_bout_no":WEIGHTS_LB,
        "weigh_in_source":WEIGH_SOURCE,
        "completeness":{"fight_count":14,"quoted_market_prices":len(rows),
            "modeled_market_prices":modeled,
            "unmodeled_draw_quote_prices":len(rows)-modeled,
            "missing_markets_not_inferred":quote["missing_markets"]},
        "warnings":[
            "Raw model edge is NOT sufficient for a recommendation; the market-family, Stage A and sparse-data guards apply.",
            "Method, double-chance and fight-ending prices are blocked by 14-bout Stage A method-vs-timing coherence findings.",
            "The independent timing model was historically unreliable (initial tracked official timing bets 0-4); 12pp timing gate and 15pp severe-coherence diagnostic block apply.",
            "Minimum of current and unified-shadow probabilities is a stress test, NOT a separately validated calibrated lower bound.",
            "Do not invent missing method for draw or collapsed exact-round prices.",
        ],
        "all_market_comparisons":rows,
        "raw_positive_ev_but_rejected_watchlist":{
            LONGSHOTS:blocked_watch(LONGSHOTS),BEST_BETS:blocked_watch(BEST_BETS)},
    }
    summary={
        "event":freeze["event"],"event_date":freeze["event_date"],
        "frozen_at_utc":datetime.now(timezone.utc).isoformat(),
        "status":"STAGE_B_SCREENSHOT_AUDITED_NO_TWO_TIER_WAGERS_APPROVED",
        "stage_a_sha256":sha(FREEZE),"quotes_sha256":sha(QUOTES),
        "fanduel_only":True,
        "stage_a_odds_blind_preserved":True,
        "model_or_fight_side_flips":0,
        "total_fights":14,"quotes_count":len(rows),
        "weigh_in_source":WEIGH_SOURCE,"all_28_made_weight":True,
        "top_5_longshots":{"price_range":"+200 and longer","selected":[],"number_selected":0},
        "top_5_best_bets":{"price_range":"-150 through +190 inclusive","selected":[],"number_selected":0},
        "no_overlap":True,"no_forced_bets":True,
        "official_straight_bets_within_top5_tiers":[],
        "optional_favorite_2leg":None,
        "optional_favorite_3leg":None,
        "best_overall_outside_two_tiers":{
            "candidate":"Tatiana Suarez moneyline",
            "fanduel_snapshot_american_odds":-200,
            "reference_model_win_probability":freeze["fights"][12]["official_reference_probability"],
            "historical_shadow_win_probability":freeze["fights"][12]["winner_views"]["historical_shadow"]["probability"],
            "unified_shadow_win_probability":freeze["fights"][12]["winner_views"]["oof_unified_shadow"]["probability"],
            "market_implied_break_even":break_even(-200),
            "outside_top5_ranges":True,
            "status":"RESEARCH_WATCH_ONLY_NOT_PROMOTED_OR_INCLUDED_IN_TWO_TIER_TOP5",
            "reason":"High-quality three-model side with raw positive price edge, but -200 is outside the agreed Top5 Best Bets -150..+190 range. Three-model minima are not independently calibrated betting guarantees.",
        },
        "biggest_timing_discrepancy_to_protect":{
            "fight":"Davey Grant vs Elijah Smith",
            "market":"Fight goes distance YES +132",
            "simulated_probability":freeze["fights"][11]["timing_current"]["sim_10000"]["GTD_YES"],
            "unified_shadow_probability":freeze["fights"][11]["timing_oof_unified_shadow"]["sim_10000"]["GTD_YES"],
            "reason_rejected":"Timing-vs-method finish marginal discrepancy over 15pp, no validated joint family calibration; avoid post-hoc choosing whichever model yields a value edge.",
        },
        "full_market_comparison_file":str(OUT.relative_to(ROOT)),
        "notes":[
            "No apparent price-only edges were used to reverse any Stage A PASS or winner.",
            "All exact fighter+method and double-chance bets are barred for this event by frozen model coherence governance.",
            "0 bets in both categories is a valid, preferred outcome to forcing up to 10 underqualified wagers.",
        ],
    }
    return full,summary

def main():
    full,summary=compute()
    OUT.write_text(json.dumps(full,indent=2,sort_keys=True)+"\n")
    SUMMARY.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":summary["status"],"markets":summary["quotes_count"],
        "longshots":summary["top_5_longshots"]["number_selected"],
        "best_bets":summary["top_5_best_bets"]["number_selected"],
        "blocked_watchlist":full["raw_positive_ev_but_rejected_watchlist"]},indent=2))

if __name__=="__main__":
    main()
