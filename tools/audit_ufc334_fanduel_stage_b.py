"""Full UFC334 2026-11-14 FanDuel snapshot price audit; 334 quoted prices.

Use original frozen 13-fight Stage A (reference + unified shadow) and 13
screenshots only; 24 duplicate draw quotes have NO probabilities and are
never selectable. Only Alatengheili/Diaz MONEYLINES were supplied; no props
are inferred. The two championship exact-round markets were collapsed.

All apparent/model raw EV is diagnostic. Original UFC model timing and
method calibration is not verified strongly enough to justify formally
staked selections; prior 0/5 longshot card reinforces conservatism.
This does NOT auto-approve any official bet, claim any personal wagers or
alter the 13-fight frozen Stage A. Weigh-ins Nov 13 are not yet available.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from wshlx_ufc.two_tier_card import (
    BEST_BETS,LONGSHOTS,break_even,expected_value,tier_for_odds,
)
from wshlx_ufc.market_compatibility import validate_market_spec

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"data/locks/ufc334_2026-11-14"
FREEZE=DIR/"stage_a_final_selection.json"
RAW=DIR/"stage_a_model_raw_three_view.json"
QUOTES=ROOT/"data/quotes/ufc334_2026-11-14_fanduel_user_screenshots.json"
OUT=DIR/"stage_b_all_334_fanduel_prices_audit.json"
UNVALIDATED_MIN_P="two_view_minimum_is_NOT_a_calibrated_probability_lower_bound"


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def _add(rows,*,f,market,group,spec,price,p=None,p_unified=None):
    n=f["fight_no"]
    if isinstance(price,bool) or type(price)!=int or -99<=price<=99:
        raise RuntimeError(f"Invalid original screenshot American odds: {n} {market}: {price}")
    tier=tier_for_odds(price)
    ev=break_even(price)
    if p is None:
        if group!="draw" or p_unified is not None or spec is not None:
            raise RuntimeError("Only unmodeled draw markets may lack a probability")
        rows.append({"fight_no":n,"fight":f"{f['a']} vs {f['b']}",
            "market":market,"group":group,"market_spec":None,
            "american_odds":price,"break_even_probability":ev,
            "tier":tier,"raw_current_probability":None,
            "raw_unified_probability":None,"raw_current_EV_per_unit":None,
            "unverified_robust_min_EV_per_unit":None,
            "status":"UNMODELED_DRAW_DO_NOT_BET","approved_official":False,
            "mechanical_precheck_pass":False,
            "block_reasons":["no_calibrated_draw_probability"]})
        return
    p=float(p);q=float(p_unified)
    if not (math.isfinite(p) and math.isfinite(q) and 0<=p<=1 and 0<=q<=1):
        raise RuntimeError(f"Bad frozen model probability {n} {market}")
    fam={"moneyline":"moneyline",
         "method_of_victory":"method","double_chance":"double_chance",
         "how_fight_ends":"method",
         "goes_distance":"timing","total_rounds":"timing","round_to_start":"timing"}[group]
    spec=validate_market_spec(spec,market_family=fam,scheduled_rounds=f["scheduled_rounds"])
    floor=min(p,q)
    reasons=[]
    if tier is None:
        reasons.append("outside_longshot_or_best_bet_american_price_ranges")
    if f["stage_a_posture"]=="PASS":
        reasons.append("frozen_stage_a_fight_PASS_research_only")
    if group=="moneyline":
        selected=f["a"] if spec["side"]=="a" else f["b"]
        if selected!=f["official_reference_pick"]:
            reasons.append("moneyline_opposes_frozen_reference_winner")
    if fam in ("method","double_chance"):
        reasons.append("fighter_method_double_chance_or_fight_end_model_not_independently_validated")
        if f["method_timing_coherence"]["method_market_blocked_if_discrepancy_over_15pp"]:
            reasons.append("method_timing_finish_marginals_disagree_over_15pp")
    if fam=="timing":
        density=f["evidence_density"]
        if min(int(density["a_prior_ufc_bouts"] or 0),
               int(density["b_prior_ufc_bouts"] or 0))<2:
            reasons.append("sparse_less_than_two_prior_UFC_fights_for_one_side")
        if f["method_timing_coherence"]["method_market_blocked_if_discrepancy_over_15pp"]:
            reasons.append("method_timing_finish_marginals_disagree_over_15pp")
        if p-ev<.12-1e-12:
            reasons.append("current_timing_edge_under_12pp")
        if floor-ev<.12-1e-12:
            reasons.append("two_view_timing_edge_under_12pp")
    value=expected_value(price,p);robust=expected_value(price,floor)
    if value<=0 or p<=ev:
        reasons.append("reference_model_raw_EV_not_positive")
    if robust<=0 or floor<=ev:
        reasons.append("two_model_raw_EV_not_positive")
    mechanical=len(reasons)==0
    # Date-specific sportsbook price independent verifications, correlated
    # method/timing calibration and a validated lower bound are NOT present.
    # Never silently claim the raw model probabilities alone suffice.
    reasons.append("independent_calibrated_conservative_probability_not_established")
    reasons.append("screenshot_quote_not_timestamp_verified_live_before_weigh_ins")
    rows.append({
        "fight_no":n,"fight":f"{f['a']} vs {f['b']}",
        "market":market,"group":group,"market_family":fam,"market_spec":spec,
        "original_frozen_reference_pick":f["official_reference_pick"],
        "american_odds":price,"tier":tier,
        "break_even_probability":ev,
        "raw_current_probability":p,"raw_unified_probability":q,
        "raw_min_two_view_probability":floor,
        "raw_current_edge_pp":100*(p-ev),
        "raw_min_two_view_edge_pp":100*(floor-ev),
        "raw_current_EV_per_unit":value,
        "unverified_robust_min_EV_per_unit":robust,
        "stage_a_research_posture":f["stage_a_posture"],
        "method_timing_gap_pp":f["method_timing_coherence"]["method_vs_current_timing_finish_discrepancy_pp"],
        "is_primary_stage_a_timing_market":fam=="timing" and (
            (spec["kind"]=="goes_distance" and f["primary_timing_forecast"]["market_key"]=="GTD_"+spec["outcome"])
            or (spec["kind"]=="total_rounds" and
                f["primary_timing_forecast"]["market_key"]==f"{spec['direction']}_{spec['threshold']}")
            or (spec["kind"]=="round_to_start" and
                f["primary_timing_forecast"]["market_key"]==f"ROUND_{spec['round']}_STARTS_{spec['outcome']}")
        ),
        "mechanical_precheck_pass":mechanical,
        "approved_official":False,
        "status":"PRE_EVENT_RESEARCH_ONLY_NOT_AN_APPROVED_BET",
        "block_reasons":reasons,
        "two_view_floor_not_independently_calibrated":True,
    })


def compute():
    frozen=json.loads(FREEZE.read_text())
    raw=json.loads(RAW.read_text())
    quotes=json.loads(QUOTES.read_text())
    if not frozen["stage_a_frozen"] or frozen["odds_used"] is not False:
        raise RuntimeError("Stage A must stay frozen and odds-blind")
    if frozen["raw_model_sha256"]!=sha(RAW):
        raise RuntimeError("Original raw model changed since freeze")
    if quotes["source_frozen_stage_a_sha256"]!=sha(FREEZE):
        raise RuntimeError("Screenshot manifest not tied to immutable Stage A")
    if quotes["event_date"]!=frozen["event_date"] or quotes["sportsbook"]!="FanDuel":
        raise RuntimeError("Invalid screenshot sportsbook/event")
    if len(frozen["fights"])!=len(raw["fights"])!=len(quotes["quoted_markets"])!=13:
        raise RuntimeError("Must audit exactly 13 fights")
    if quotes["total_markets"]!=334 or quotes["modeled_quote_count"]!=310:
        raise RuntimeError("Incomplete original screenshot price archive")
    rows=[];screenshot_counts={}
    for f,r,q in zip(frozen["fights"],raw["fights"],quotes["quoted_markets"]):
        n=f["fight_no"]
        if n!=r["fight_no"] or n!=q["fight_no"] or (f["a"],f["b"])!=(q["a"],q["b"]):
            raise RuntimeError(f"Fight/market identity drift {n}")
        start=len(rows)
        j=r["joint_calibrated"];u=r["oof_unified_shadow"]["joint_method"]
        t=f["timing_current"]["sim_10000"]
        ut=f["timing_oof_unified_shadow"]["sim_10000"]
        pa=f["official_reference_probability_a"];upa=r["oof_unified_shadow"]["winner_p_a"]
        def add(name,group,spec,price,p=None,pu=None):
            _add(rows,f=f,market=name,group=group,spec=spec,price=price,p=p,p_unified=pu)
        for side,abbr,p1,p2 in (("a","A",pa,upa),("b","B",1-pa,1-upa)):
            nm=f[side]
            add(f"{nm} ML","moneyline",{"kind":"moneyline","side":side},q["moneyline"][side],p1,p2)
            if q.get("method_of_victory") is None:continue
            for method,ref in (("KO_TKO","KO"),("SUB","SUB"),("DEC","DEC")):
                add(f"{nm} by {method}","method_of_victory",
                    {"kind":"method","side":side,"method":method},
                    q["method_of_victory"][side][method],j[f"{abbr}_{ref}"],u[f"{abbr}_{ref}"])
            for key,method in (("KO_OR_SUB",["KO_TKO","SUB"]),
                                ("KO_OR_DEC",["KO_TKO","DEC"]),
                                ("SUB_OR_DEC",["SUB","DEC"])):
                norm={"KO_TKO":"KO","SUB":"SUB","DEC":"DEC"}
                add(f"{nm} {key}","double_chance",
                    {"kind":"double_chance","side":side,"methods":method},
                    q["double_chance"][side][key],
                    sum(j[f"{abbr}_{norm[m]}"] for m in method),
                    sum(u[f"{abbr}_{norm[m]}"] for m in method))
        if q.get("method_of_victory") is None:
            if n!=2 or q.get("goes_distance") is not None or q.get("round_to_start") is not None:
                raise RuntimeError("Unexpected missing props for anything but bout #2")
        else:
            add("Draw (method market)","draw",None,q["method_of_victory"]["DRAW"])
            add("Draw (double chance market)","draw",None,q["double_chance"]["DRAW"])
            for status in ("YES","NO"):
                add(f"Fight goes distance {status}","goes_distance",
                    {"kind":"goes_distance","outcome":status},q["goes_distance"][status],
                    t[f"GTD_{status}"],ut[f"GTD_{status}"])
            tr=q["total_rounds"]
            if not isinstance(tr,dict):raise RuntimeError("No quoted round total for full screenshot")
            for direction in ("OVER","UNDER"):
                metric=f"{direction}_{tr['threshold']}"
                if metric not in t or metric not in ut:
                    raise RuntimeError("No model probability for supplied exact round line")
                add(f"{direction} {tr['threshold']} rounds","total_rounds",
                    {"kind":"total_rounds","direction":direction,"threshold":tr["threshold"]},
                    tr[direction],t[metric],ut[metric])
            for method,underlying in (("KO_TKO","KO"),("SUB","SUB"),("DEC","DEC")):
                add(f"Fight ends {method}","how_fight_ends",
                    {"kind":"fight_end_method","method":method},
                    q["how_fight_ends"][method],
                    j[f"A_{underlying}"]+j[f"B_{underlying}"],
                    u[f"A_{underlying}"]+u[f"B_{underlying}"])
            for round_name,price in q["round_to_start"].items():
                round_number=int(round_name)
                for status in ("YES","NO"):
                    key=f"ROUND_{round_number}_STARTS_{status}"
                    add(f"Round {round_number} starts {status}","round_to_start",
                        {"kind":"round_to_start","round":round_number,"outcome":status},
                        price[status],t[key],ut[key])
        expected=2 if n==2 else 31 if n in (12,13) else 27
        if len(rows)-start!=expected:
            raise RuntimeError(f"Fight {n} expected {expected} screenshot markets, got {len(rows)-start}")
        screenshot_counts[str(n)]={"fight":f"{f['a']} vs {f['b']}",
                                   "all_quoted":expected,
                                   "modeled":expected-(0 if n==2 else 2)}
    if len(rows)!=334 or sum(x["raw_current_probability"] is None for x in rows)!=24:
        raise RuntimeError("Unexpected quoted markets/draw counts")
    apparent=[r for r in rows if r.get("mechanical_precheck_pass")]
    if any(r["approved_official"] for r in rows):
        raise RuntimeError("Unverified odds/betting calibration cannot become approved")
    report={
        "event":frozen["event"],"event_date":frozen["event_date"],
        "stage":"B_PRICE_AUDIT_FANDUEL_SCREENSHOT_ONLY",
        "status":"334_FANDUEL_MARKETS_AUDITED_RESEARCH_ONLY_PENDING_CALIBRATED_APPROVAL",
        "graded_at_utc":None,"audited_at_utc":datetime.now(timezone.utc).isoformat(),
        "stage_a_original_sha256":sha(FREEZE),"raw_model_sha256":sha(RAW),
        "all_quotes_sha256":sha(QUOTES),
        "sportsbook":"FanDuel",
        "quote_timestamp_precise_utc":None,
        "price_source":"User-supplied Nov11 screenshot lines, not live API or direct account bets",
        "weigh_in_status":"Nov13 event weigh-ins have NOT occurred at capture time",
        "completeness":{
            "unique_fights":13,"fully_displayed_prop_fights":12,
            "moneyline_only_fights":1,"quotes":334,
            "modeled_quotes":310,"unmodeled_draw_quotes":24,
            "quoted_per_fight":screenshot_counts,
            "missing_markets_not_inferred":quotes["missing_markets"],
        },
        "warnings":[
            "Even if mechanical numeric/edge filters pass, no official wagers have a validated calibrated conservative probability floor or live verified FanDuel availability.",
            "Minimum(ref,unified) is only an unvalidated stress test, NOT a calibrated probability lower confidence bound.",
            "Some raw KO/SUB/DEC or timing probabilities contradict; do not force market approvals from impossible multi-family marginals.",
            "Bouts labeled PASS and low-data replacement fight cannot be promoted on apparent raw prices alone.",
            "Five research picks per tier need not imply five bets per tier; official profitable ROI cannot be inferred from raw EV estimates.",
            "The user's 13 fight lineup screenshots displayed early general moneyline odds; Stage A modeling did not use odds as inputs.",
        ],
        "original_stage_a_immutable":True,"all_334_markets":rows,
        "raw_mechanical_gate_pass_candidates":apparent,
        "raw_mechanical_gate_pass_count":len(apparent),
        "official_approved_card":{"top_5_longshots":[],"top_5_best_bets":[],
            "number_official_wagers":0,"official_stake_units":0,"official_roi":None,
            "reason":"Calibration, external fight-tape and screenshot freshness/official weigh-in due diligence pending; do not infer bet approvals."},
    }
    return report


def main():
    if OUT.exists():raise RuntimeError("Refusing to overwrite first complete pre-event price audit")
    result=compute()
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "status":result["status"],"quoted":result["completeness"]["quotes"],
        "modeled":result["completeness"]["modeled_quotes"],
        "raw_gate_candidates":[(x["fight_no"],x["market"],x["american_odds"])
                               for x in result["raw_mechanical_gate_pass_candidates"]],
        "official_bets":result["official_approved_card"]["number_official_wagers"],
    },indent=2))


if __name__=="__main__":main()
