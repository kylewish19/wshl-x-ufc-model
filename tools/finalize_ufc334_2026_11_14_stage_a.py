"""Freeze UFC334 13-fight odds-blind Stage A with ONE timing forecast per bout.

This is a 13-fight prospective Nov11 freeze for the Nov14 event.
There was no need for numerical betting lines at any stage of modeling.
User screenshot *did* display moneylines, so governance transparently
discloses visibility while enforcing NO PRICE INPUT in script/models.

The previously graded Nov7 reference/historical/unified source objects
are unchanged. Methods and GTD are all FOR RESEARCH, not approved wagers.
Preliminary research lacks continuous full-fight video review. Every
reference winner pick is retained even when the wager posture is PASS.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/locks/ufc334_2026-11-14/stage_a_model_raw_three_view.json"
OUTPUT=RAW.parent/"stage_a_final_selection.json"
AUDIT=RAW.parent/"stage_a_final_audit.json"
GOVERNANCE_REF="https://www.ufc.com/event/ufc-334"
UFC_UPDATE="https://www.ufc.com/index.php/news/updates-polymarket-ufc-334-gane-vs-hokit"
TRIALS=10_000

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_builders():
    path=ROOT/"tools/finalize_ufcvegas124_stage_a.py"
    spec=importlib.util.spec_from_file_location("ufc124_finalizer_builders_for_ufc334",path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def evidence_research(r):
    no=int(r["fight_no"])
    a,b=r["a"],r["b"]
    density=r["evidence_density"]
    ca=int(density["a_prior_ufc_bouts"] or 0)
    cb=int(density["b_prior_ufc_bouts"] or 0)
    pa=float(r["winner_reference_p_a"])
    p=max(pa,1-pa)
    names=[r["winner_reference_pick"],
           r["historical_shadow"]["winner_pick"],
           r["oof_unified_shadow"]["winner_pick"]]
    all_agree=len(set(names))==1
    long_absence=max((float(d) for d in
                     (density.get("a_days_since_last"),density.get("b_days_since_last"))
                     if d is not None and math.isfinite(float(d))),default=0)
    short_notice=no==2
    special_reasons={
        1:"Sanches has zero completed UFC bouts in this historical dataset; transferring DWCS/regional performance is uncertain.",
        2:"Alatengheili replaces injured Yanez on late notice; opponent Diaz has only one recorded UFC bout.",
        3:"Mesquita's elite submission résumé competes with Chiasson's longer UFC experience. Reference differs from both historical and unified.",
        9:"Hasan's current UFC data contain only one bout, despite substantial non-UFC finishing history.",
        12:"Nunes' lengthy Octagon absence and Harrison's smaller UFC-specific sample make this five-round title fight distributionally uncertain.",
        13:"Heavyweight title fight: Gane is the reference pick, Hokit is the historical pick, and unified win probability is near 50%. High style and sample uncertainty.",
    }
    notes=[f"Reference winner probability {p*100:.1f}%; UFC bouts {a}={ca}, {b}={cb}; three winner views {'agree' if all_agree else 'DISAGREE'}."]
    if not all_agree:
        notes.append("Three-model winner disagreement blocks confident betting side classification.")
    if min(ca,cb)<2:
        notes.append("Sparse UFC sample (<2 prior UFC bouts for at least one fighter).")
    if long_absence>730:
        notes.append(f"Potential long-layoff transfer issue (max recorded inactivity {int(long_absence)} days).")
    if short_notice:
        notes.append("Short-notice replacement must be considered before Stage B.")
    if no in special_reasons:
        notes.append(special_reasons[no])
    if (not all_agree or min(ca,cb)<2 or long_absence>730 or
        short_notice or p<0.56 or no in (12,13)):
        tier,status="PASS","PASS"
    elif min(ca,cb)>=5 and p>=.66:
        tier,status="B","SIDE"
    elif p>=.56:
        tier,status="C","LEAN"
    else:
        tier,status="PASS","PASS"
    if no==5 and status=="SIDE":
        tier,status="C","LEAN"  # 3 UFC bouts for Johnson; no artificial elite grade
    return {
        "tier":tier,"status":status,
        "reason":" ".join(notes)+" Price information from screenshots is excluded from predictions; all posture grades are evidence-risk rules only.",
        "tape":"Official UFC card, Nov10 UFC update and written fight-by-fight preview consulted; no claim that uninterrupted full fight tape was reviewed or manually annotated.",
    }

def primary_timing(r):
    cur=r["timing_current"]["sim_10000"]
    uni=r["timing_oof_unified_shadow"]["sim_10000"]
    # Exclude the mechanically common, often high-vig R2-starts YES.
    # Stage A has no bookmaker prices; use standard method-free markets,
    # not a threshold chosen from whichever posted line seemed favorable.
    types=[
        ("GTD_YES","Fight goes distance YES","goes_distance"),
        ("GTD_NO","Fight goes distance NO","goes_distance"),
        ("OVER_1.5","Over 1.5 rounds","total_rounds"),
        ("UNDER_1.5","Under 1.5 rounds","total_rounds"),
        ("OVER_2.5","Over 2.5 rounds","total_rounds"),
        ("UNDER_2.5","Under 2.5 rounds","total_rounds"),
        ("ROUND_3_STARTS_YES","Round 3 starts YES","round_to_start"),
        ("ROUND_3_STARTS_NO","Round 3 starts NO","round_to_start"),
    ]
    possible=[]
    for key,market,family in types:
        if key not in cur or key not in uni:
            raise RuntimeError(f"Missing original simulated timing market {key}")
        pc=float(cur[key]);pu=float(uni[key])
        if not 0<=pc<=1 or not 0<=pu<=1:
            raise RuntimeError("Timing probabilities invalid")
        possible.append({
            "market_key":key,"market":market,"family":family,
            "current_probability":pc,"unified_shadow_probability":pu,
            "min_two_model_probability":min(pc,pu),
        })
    selected=sorted(possible,key=lambda x:(
        -x["min_two_model_probability"],-x["current_probability"],x["market_key"]
    ))[0]
    return {
        **selected,"selected_pre_fanduel_prop_prices":True,
        "selection_policy":"maximize min(current and unified simulated timing P), then reference P, then deterministic metric label; eligible standard GTD, O/U 1.5 or 2.5, Round3 starts; never routine Round2 YES chalk",
        "not_a_betting_recommendation":True,
        "stage_a_primary_timing_for_grade":True,
    }

def joint_timing_consistency(rawrow):
    j=rawrow["joint_calibrated"]
    p_finish=sum(float(j[k]) for k in ("A_KO","A_SUB","B_KO","B_SUB"))
    cur=float(rawrow["timing_v033_sim_10000"]["GTD_NO"])
    uni=float(rawrow["oof_unified_shadow"]["timing_sim_10000"]["GTD_NO"])
    discrepancy=abs(p_finish-cur)
    return {
        "reference_method_joint_finish_probability":p_finish,
        "current_timing_simulated_finish_probability":cur,
        "unified_timing_simulated_finish_probability":uni,
        "method_vs_current_timing_finish_discrepancy_pp":100*discrepancy,
        "method_market_blocked_if_discrepancy_over_15pp":bool(discrepancy>0.15),
        "market_family_coherence_not_automatically_solved":True,
    }

def main():
    if OUTPUT.exists() or AUDIT.exists():
        raise RuntimeError("Refusing to rewrite an already frozen UFC334 Stage A")
    raw=json.loads(RAW.read_text())
    if raw["event"]!="UFC 334: Gane vs Hokit" or raw["event_date"]!="2026-11-14":
        raise RuntimeError("Wrong event loaded")
    if raw["stage_a_frozen"] is not False or raw["odds_used"] is not False:
        raise RuntimeError("Raw model must be unpriced and still unfinalized")
    if len(raw["fights"])!=13:
        raise RuntimeError("Expected 13 actual UFC334 fights before freezing")
    if [x["fight_no"] for x in raw["fights"]]!=list(range(1,14)):
        raise RuntimeError("13 fights must be unique and in intended order")
    if sum(x["scheduled_seconds"]==1500 for x in raw["fights"])!=2:
        raise RuntimeError("Both five-round title bouts missing")
    builder=load_builders()
    builder.RESEARCH={int(r["fight_no"]):evidence_research(r) for r in raw["fights"]}
    builder.OFFICIAL_METHOD={}
    fights=[]
    for r in raw["fights"]:
        x=builder.build_fight(r)
        x["primary_timing_forecast"]=primary_timing(x)
        x["method_timing_coherence"]=joint_timing_consistency(r)
        x["method"]["primary_method_forecast_for_grade"]={
            "reference":x["method"]["top_method_current"],
            "historical_own_fighter":max(
                (label for label in ("KO","SUB","DEC")),
                key=lambda label:r["historical_shadow"]["joint_method"][
                    ("A_" if r["historical_shadow"]["winner_pick"]==r["a"] else "B_")+label
                ]),
            "unified_own_fighter":max(
                (label for label in ("KO","SUB","DEC")),
                key=lambda label:r["oof_unified_shadow"]["joint_method"][
                    ("A_" if r["oof_unified_shadow"]["winner_pick"]==r["a"] else "B_")+label
                ]),
            "all_three_model_methods_use_their_own_selected_fighter":True,
        }
        x["method"]["betting_status"]="UNPRICED_AND_FAMILY_COHERENCE_GATES_UNVERIFIED_NO_APPROVED_METHOD_BET"
        fights.append(x)
    if len({(r["a"],r["b"]) for r in fights})!=13:
        raise RuntimeError("Duplicate bout in final Stage A")
    if any(x["method"]["official_method_if_any"] for x in fights):
        raise RuntimeError("Cannot claim an official method wager before FanDuel Stage B")
    if not all(x["primary_timing_forecast"]["selected_pre_fanduel_prop_prices"] for x in fights):
        raise RuntimeError("Timing must be frozen before FanDuel markets")
    payload={
        "event":raw["event"],"event_date":raw["event_date"],
        "frozen_at_utc":datetime.now(timezone.utc).isoformat(),
        "stage_a_frozen":True,"odds_used":False,
        "freeze_type":"STAGE_A_ODDS_BLIND_MODEL_INPUTS_FROZEN_BEFORE_PROP_PRICE_GATE",
        "odds_exposure_transparency":"User lineup screenshots displayed preliminary moneyline prices; neither this runner nor our reference, historical, or unified model used any prices or price-related override. No sportsbook data are stored in Stage A.",
        "original_stage_a_raw_sha256":sha(RAW),
        "raw_model_sha256":sha(RAW),
        "raw_model_path":str(RAW.relative_to(ROOT)),
        "model_history_through":"2026-11-07",
        "simulation":{"current_joint_per_fight":10000,"current_timing_per_fight":10000,
                      "unified_joint_per_fight":10000,"unified_timing_per_fight":10000},
        "governance":{
            "reference_champion_unchanged":True,
            "historical_shadow_only":True,"unified_shadow_only":True,
            "model_reference_weights_fit_through":"2026-09-12",
            "current_shadows_fit_through":"2026-11-07",
            "historical_winner_shadow_fit_through":"2026-11-07",
            "historical_method_timing_fit_through":"2026-10-17",
            "oof_unified_weights_fit_cutoff":"2026-10-17",
            "method_timing_family_incoherence_overrides_not_permitted":True,
            "no_method_bets_approved":True,"no_timing_bets_approved":True,
            "no_bets_without_FanDuel_prices":True,
            "tape_not_claimed_as_continuously_reviewed":True,
            "title_bouts":2,
            "odds_influenced_stage_a":False,
            "challenger_promoted":False,
        },
        "research":{
            "official_current_card_url":GOVERNANCE_REF,
            "official_nov10_change_url":UFC_UPDATE,
            "card_bout_count":13,
            "original_user_unique_screenshots":12,
            "missing_user_screenshot_fight_added_from_UFC_official_event":"Stephen Thompson vs Charles Radtke",
            "replacement_identified":"Alatengheili for Adrian Yanez vs Juan Diaz",
            "cancelled_bout_excluded":"Nazim Sadykhov vs Jefferson Nascimento",
            "weigh_in_and_late_updates":"Recheck official Nov13 weigh-ins and withdrawals before Stage B; freeze original picks rather than rewrite probabilities",
            "tape_provenance":"Official written preview and source stats, not continuous watched full-fight video",
        },
        "fights":fights,
    }
    OUTPUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    audit={
        "event":raw["event"],"event_date":raw["event_date"],"stage_a_frozen":True,
        "odds_used":False,"fights":len(fights),
        "simulation":payload["simulation"],
        "raw_model_sha256":payload["raw_model_sha256"],
        "winner_disagreements":[r["fight_no"] for r in fights if
            any(r["shadow_disagreement"].values())],
        "passes":[r["fight_no"] for r in fights if r["stage_a_posture"]=="PASS"],
        "primary_timing_per_fight":len([r for r in fights if
            r["primary_timing_forecast"]["stage_a_primary_timing_for_grade"]]),
        "method_vs_timing_discrepancy_over_15pp":[r["fight_no"] for r in fights if
            r["method_timing_coherence"]["method_market_blocked_if_discrepancy_over_15pp"]],
        "no_method_or_timing_bet_approved_before_prices":True,
        "champion_not_promoted":True,
    }
    AUDIT.write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "status":"STAGE_A_13_FIGHTS_FROZEN_BEFORE_FANDUEL_PROP_REVIEW",
        "fights":len(fights),"pass_fights":audit["passes"],
        "disagreement_fights":audit["winner_disagreements"],
        "primary_timing_picks":audit["primary_timing_per_fight"],
        "method_timing_conflicts":audit["method_vs_timing_discrepancy_over_15pp"],
        "artifact_sha256":sha(OUTPUT),
    },indent=2))

if __name__=="__main__":
    main()
