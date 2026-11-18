"""Freeze original UFC Qatar 2026-11-21 Stage A, before FanDuel prop pricing.

Existing Reference, Historical and Unified model numbers are immutable.
Eleven screenshot/official-site bouts plus one media-reported late addition
are explicitly separated. No bet is approved, no challenger is promoted,
and an extreme two-UFC-debutant reference output is QUARANTINED, not altered.
"""
from __future__ import annotations
import hashlib, importlib.util, json, math, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/locks/ufcqatar_2026-11-21/stage_a_model_raw_three_view.json"
OUTPUT=RAW.parent/"stage_a_final_selection.json"
AUDIT=RAW.parent/"stage_a_final_audit.json"
SOURCE="https://www.ufc.com/event/ufc-fight-night-november-21-2026"
PREVIEW="https://www.ufc.com/news/fight-by-fight-preview-ufc-fight-night-prochazka-vs-stirling-qatar"
ADDITION="https://www.mmafighting.com/ufc/522129/ufc-signs-two-fighters-for-late-notice-undercard-matchup-for-ufc-qatar"
START_UTC="2026-11-21T15:00:00+00:00"
ALL_BOUTS=12

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def import_file(alias, path):
    spec=importlib.util.spec_from_file_location(alias,path)
    m=importlib.util.module_from_spec(spec)
    sys.modules[alias]=m
    spec.loader.exec_module(m)
    return m

CONTEXT={
 1:"Nurgozhay won two straight in 2026 after a difficult UFC start; Lorenz arrives from DWCS for his UFC debut. Absence of Lorenz UFC opponent-adjusted sample reduces confidence.",
 2:"Motta is returning from the June 2025 Sadykhov bout and carries UFC mixed results; Road to UFC winner Mar Fan lost his UFC debut to Kody Steele by submission. Both have meaningful finishing volatility.",
 3:"Matthews has 24 recorded UFC appearances and four wins in his last five according to the Nov16 UFC preview; Abdullayev has a single UFC win against Jefferson Nascimento. The three model winner heads disagree, and cross-promotion skill transfer is uncertain.",
 4:"Albazi and Costa are in a flyweight rematch. Albazi lost to Horiguchi in February; Costa enters on three straight stoppages. Model probabilities are close enough that this is a PASS rather than a forced lock.",
 5:"Gaziev's recent first-round win over Kennedy Nzechukwu contrasts with Teixeira's loss to Sergei Pavlovich. Heavyweight one-shot finishing variance and opponent-strength adjustment are key limitations.",
 6:"Both Topuria and Luna have short UFC histories and the model-selected side is not a strong, calibrated anchor. Prior UFC sample flags take precedence over nominal favorite status.",
 7:"Cannonier is an experienced older contender facing Aliskerov; age/durability and the opponent's skill make this an informative matchup, but UFC career-vintage extrapolation remains imperfect.",
 8:"Horiguchi rebounded to beat Albazi before losing to Manel Kape; Almabayev has a strong UFC record and submission wins over Alex Perez and Charles Johnson. The model winner heads disagree. Grappling scrambles and submission access matter.",
 9:"Hooker has a three-fight slide; Ortega is moving up to lightweight after substantial inactivity and retains high-level submission threat. Takedown/get-up resistance and Ortega's post-layoff form are uncertain.",
 10:"Sterling's wrestling and back-control are tested by Vallejos's four-fight UFC winning start and damaging recent finishes of Chikadze and Emmett. Striking finishing forecast requires successful anti-grappling access.",
 11:"Former champion Prochazka returns after April knockout loss to Stirling's teammate Carlos Ulberg; Stirling has recently accelerated his finishing, including Jan Blachowicz. Five-round southpaw/pressure collision and knockout variance remain high.",
 12:"MEDIA-REPORTED LATE ADDITION, NOT YET ON UFC EVENT PAGE WHEN CHECKED: John Mitchell and Shoaib Yousaf both UFC debutants. Their regional records are NOT measured UFC performance; original Reference 96.4% probability is an unsupported model extrapolation. AUTO-PASS; do not anchor parlays or place method/timing bets.",
}

def research(r):
    no=int(r["fight_no"])
    a,b=r["a"],r["b"]
    e=r["evidence_density"]
    n_a=int(e.get("a_prior_ufc_bouts") or 0)
    n_b=int(e.get("b_prior_ufc_bouts") or 0)
    pa=float(r["winner_reference_p_a"])
    p=max(pa,1-pa)
    votes={r["winner_reference_pick"],r["historical_shadow"]["winner_pick"],r["oof_unified_shadow"]["winner_pick"]}
    agree=len(votes)==1
    layoff=max([float(x) for x in (e.get("a_days_since_last"),e.get("b_days_since_last")) if x is not None and math.isfinite(float(x))] or [0])
    sparse=min(n_a,n_b)<2
    provisional=no==12
    extreme_sparse=provisional and n_a==0 and n_b==0 and p>.90
    if not agree or sparse or layoff>730 or provisional or p<.56 or extreme_sparse:
        tier,status="PASS","PASS"
    elif n_a>=5 and n_b>=5 and p>=.66 and not r["sparse_ufc_evidence"]:
        tier,status="B","SIDE"
    elif p>=.56:
        tier,status="C","LEAN"
    else:
        tier,status="PASS","PASS"
    if no in (5,11) and status=="SIDE":
        tier,status="C","LEAN"  # high knockout variance, don't force hard lock
    notes=[
        f"Reference {p*100:.1f}% for its selected fighter; prior UFC bouts {a} {n_a}, {b} {n_b}; model winner agreement {'yes' if agree else 'NO'}.",
        f"Original model probability is UNCHANGED. Official betting status {status}.",
    ]
    if sparse: notes.append("Sparse UFC evidence requires a cautious data-transfer penalty at the DECISION/BET GATE, not a post-hoc probability flip.")
    if layoff>730: notes.append("Long historical UFC inactivity; recency uncertainty persists.")
    if extreme_sparse: notes.append("MODEL EXTRAPOLATION OUTLIER QUARANTINED: 96.4% from zero UFC bouts on both sides is NOT a credible measured confidence.")
    if not agree: notes.append("Historical and/or Unified disagrees with the original Reference winner; no 2/3 consensus changes Reference.")
    return {
       "tier":tier, "status":status,
       "reason":" ".join(notes)+" "+CONTEXT[no]+" Screenshot moneylines ignored; FanDuel remains Stage B only.",
       "tape":"Official UFC Nov16 written fight-by-fight preview and matching source-form history were reviewed. Continuous full-fight tape was NOT played; no visual tape-review claim is made.",
    }

def main():
    if OUTPUT.exists() or AUDIT.exists():
        raise FileExistsError("Refuse to overwrite a frozen prospective Qatar Stage A")
    raw=json.loads(RAW.read_text(encoding="utf-8"))
    if raw["event_date"]!="2026-11-21" or raw["odds_used"] is not False or raw["stage_a_frozen"] is not False:
        raise ValueError("Incorrect event/odds/raw-freeze state")
    if datetime.now(timezone.utc)>=datetime.fromisoformat(START_UTC):
        raise ValueError("Cannot create Stage A after first-fight start")
    if len(raw["fights"])!=ALL_BOUTS or [r["fight_no"] for r in raw["fights"]]!=list(range(1,ALL_BOUTS+1)):
        raise ValueError("Expected all 12 unique screenshot/late-bout fight slots")
    if sum(r["scheduled_seconds"]==1500 for r in raw["fights"])!=1:
        raise ValueError("Only Prochazka-Stirling is a five-round scheduled main event")
    original_builder=import_file("qatar_original_stage_a_selection_builder",ROOT/"tools/finalize_ufcvegas124_stage_a.py")
    previous=import_file("qatar_previous_method_timing_selection_policy",ROOT/"tools/finalize_ufc334_2026_11_14_stage_a.py")
    original_builder.RESEARCH={r["fight_no"]:research(r) for r in raw["fights"]}
    original_builder.OFFICIAL_METHOD={}
    fights=[]
    for rawrow in raw["fights"]:
        f=original_builder.build_fight(rawrow)
        f["primary_timing_forecast"]=previous.primary_timing(f)
        f["method_timing_coherence"]=previous.joint_timing_consistency(rawrow)
        f["method"]["primary_method_forecast_for_grade"]={
            "reference":f["method"]["top_method_current"],
            "historical_own_fighter":max(("KO","SUB","DEC"),key=lambda m:rawrow["historical_shadow"]["joint_method"][("A_" if rawrow["historical_shadow"]["winner_pick"]==f["a"] else "B_")+m]),
            "unified_own_fighter":max(("KO","SUB","DEC"),key=lambda m:rawrow["oof_unified_shadow"]["joint_method"][("A_" if rawrow["oof_unified_shadow"]["winner_pick"]==f["a"] else "B_")+m]),
            "all_three_model_methods_use_own_selected_fighter":True,
        }
        f["method"]["betting_status"]="UNPRICED_RESEARCH_ONLY_NO_APPROVED_FIGHTER_METHOD_BET"
        f["reported_late_addition_unconfirmed_on_official_event_site"]=bool(f["fight_no"]==12)
        if f["fight_no"]==12:
            f["model_extrapolation_quarantine"]=True
            if f["stage_a_posture"]!="PASS":
                raise AssertionError("No-UFC-prior outlier cannot be approved")
        fights.append(f)
    if len({(r["a"],r["b"]) for r in fights})!=ALL_BOUTS:
        raise ValueError("Duplicate fighter bout")
    if any(f["method"]["official_method_if_any"] is not None for f in fights):
        raise ValueError("No FanDuel prices: no approved method bets")
    stamp=datetime.now(timezone.utc).isoformat()
    frozen={
        "event":raw["event"],"event_date":"2026-11-21","frozen_at_utc":stamp,
        "stage_a_frozen":True,"odds_used":False,
        "freeze_type":"ORIGINAL_STAGE_A_UNPRICED_PRE_WEIGH_IN_WITH_ONE_REPORTED_PROVISIONAL_BOUT",
        "raw_model_path":str(RAW.relative_to(ROOT)),
        "raw_model_sha256":sha(RAW),"original_stage_a_raw_sha256":sha(RAW),
        "model_history_through":"2026-11-07",
        "simulation":{"current_joint_per_fight":10000,"current_timing_per_fight":10000,
                     "unified_joint_per_fight":10000,"unified_timing_per_fight":10000},
        "research":{
            "user_screened_fights":11,"official_ufc_site_fights_verified":11,
            "media_reported_addition_count":1,
            "media_reported_addition":"John Mitchell vs Shoaib Yousaf",
            "media_reported_bout_status":"PROVISIONAL_PENDING_UFC_EVENT_SITE_AND_WEIGH_IN_CONFIRMATION",
            "card_count_with_provisional":12,
            "official_card_url":SOURCE,"official_preview":PREVIEW,"independent_late_addition_report":ADDITION,
            "no_full_fight_video_claim":True,
            "fight_week_check":"Verify final card and Nov20 weigh-in; mark cancelled bouts VOID without altering this historical source lock.",
            "price_exposure":"User screenshots and public UFC site contain moneylines, but scripts did not read or use prices; no model flip based on them.",
        },
        "governance":{
            "champion_reference_unchanged":True,"historical_shadow_only":True,"unified_shadow_only":True,
            "model_reference_weights_fit_through":"2026-09-12",
            "all_training_and_fighter_stats_capped_at":"2026-11-07",
            "nov14_postfight_information_used_to_predict":False,
            "coherent_challenger_not_promoted":True,
            "provisional_bout_marked_PASS":True,
            "official_method_bets_approved":0,"official_timing_bets_approved":0,
            "fan_duel_stage_b_not_yet_run":True,"original_10000_simulations_unchanged":True,
            "one_primary_timing_forecast_per_fight":True,
        },
        "fights":fights,
    }
    OUTPUT.write_text(json.dumps(frozen,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    audit={
        "event":raw["event"],"event_date":frozen["event_date"],
        "raw_sha256":sha(RAW),"final_sha256":sha(OUTPUT),
        "fights":len(fights),"official_site_fights":11,"provisional_fights":1,
        "frozen_at_utc":stamp,"stage_a_frozen":True,"odds_used":False,
        "primary_timing_picks":len([f for f in fights if f["primary_timing_forecast"]["stage_a_primary_timing_for_grade"]]),
        "winner_disagreements":[f["fight_no"] for f in fights if any(f["shadow_disagreement"].values())],
        "passes":[f["fight_no"] for f in fights if f["stage_a_posture"]=="PASS"],
        "joint_vs_timing_inconsistency_over_15pp":[f["fight_no"] for f in fights if f["method_timing_coherence"]["method_market_blocked_if_discrepancy_over_15pp"]],
        "both_debutants_outlier_pass":fights[11]["stage_a_posture"]=="PASS",
        "no_model_promotion_or_fanduel_bets":True,
    }
    AUDIT.write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":"STAGE_A_12_FIGHTS_INCLUDES_ONE_LATE_PROVISIONAL","frozen_at":stamp,
                      "final_sha256":audit["final_sha256"],"passes":audit["passes"],
                      "method_vs_timing_conflicts":audit["joint_vs_timing_inconsistency_over_15pp"],
                      "confirmed_in_UFC_site":11,"late_provisional":1},indent=2))
if __name__=="__main__":
    main()
