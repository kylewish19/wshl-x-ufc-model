"""One reproducible, PRE-EVENT timing forecast per Nov 7 UFC fight.

The official Stage A lock is NOT edited. Because this output is derived only
after FanDuel prices were viewed, it is explicitly an ADDITIONAL pre-fight
research-grade, not a retroactive claim about what Stage A originally locked.

Selection rule, for every fight:
- use ONLY saved 10k current and unified timing simulation probabilities;
- eligible market families: GTD yes/no, the single displayed O/U threshold
  (if FanDuel showed that market), and Round 3 starts yes/no;
- choose the candidate maximizing min(current timing P, unified timing P);
  deterministic tie-break: reference P, then market name;
- no sportsbook PRICE is used to rank! Prices are annotated afterwards;
- do not force an official BET: official timing-price gates remain unchanged.

Round 2 Starts Yes is intentionally excluded from the primary competition:
it is a highly mechanically likely but often expensive low-information market.
Every other Round 2 outcome remains in the full 378-quote Stage B audit.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"data/locks/ufcvegas124_2026-11-07"
STAGE_A=DIR/"stage_a_final_selection.json"
PRICES=ROOT/"data/quotes/ufcvegas124_2026-11-07_fanduel_user_screenshots.json"
AUDIT=DIR/"stage_b_fanduel_full_price_audit.json"
DEST=DIR/"stage_b_one_timing_forecast_per_fight.json"


def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def get_candidates(lock:dict, screenshot:dict):
    """Deliberately cannot read or rank by market price."""
    p=lock["timing_current"]["sim_10000"]
    u=lock["timing_oof_unified_shadow"]["sim_10000"]
    labels=[]
    for outcome in ("YES","NO"):
        key=f"GTD_{outcome}"
        labels.append((key,f"Fight goes distance {outcome}","goes_distance"))
    if screenshot["total_rounds"] is not None:
        x=screenshot["total_rounds"]["threshold"]
        for outcome in ("OVER","UNDER"):
            key=f"{outcome}_{x}"
            labels.append((key,f"{outcome} {x} rounds","total_rounds"))
    for outcome in ("YES","NO"):
        key=f"ROUND_3_STARTS_{outcome}"
        labels.append((key,f"Round 3 starts {outcome}","round_to_start"))
    options=[]
    for key,market,group in labels:
        if key not in p or key not in u: raise RuntimeError(f"Missing frozen timing probability {key}")
        current=float(p[key])
        unified=float(u[key])
        if not 0<=current<=1 or not 0<=unified<=1:
            raise RuntimeError(f"Invalid timing p: {key}")
        options.append({
            "market":market,"group":group,"metric":key,
            "current_simulated_probability":current,
            "unified_shadow_simulated_probability":unified,
            "two_model_min_probability":min(current,unified),
        })
    return options


def build():
    freeze=json.loads(STAGE_A.read_text())
    quotes=json.loads(PRICES.read_text())
    audited=json.loads(AUDIT.read_text())
    if not freeze["stage_a_frozen"] or freeze["odds_used"] is not False:
        raise RuntimeError("Original Stage A must be frozen without sportsbook prices")
    if len(freeze["fights"])!=14 or len(quotes["quoted_markets"])!=14:
        raise RuntimeError("Require 14 frozen fights and 14 full FanDuel screenshots")
    if audited["stage_a_sha256"]!=sha(STAGE_A) or audited["source_quotes_sha256"]!=sha(PRICES):
        raise RuntimeError("Cannot reconcile frozen Stage A and screenshot-price audit")
    out=[]
    for f,q in zip(freeze["fights"],quotes["quoted_markets"]):
        if (f["a"],f["b"],f["fight_no"])!=(q["a"],q["b"],q["fight_no"]):
            raise RuntimeError("Bout matching failed")
        choices=get_candidates(f,q)
        best=sorted(choices,key=lambda v:(
            -v["two_model_min_probability"],
            -v["current_simulated_probability"],
            v["market"]
        ))[0]
        matches=[v for v in audited["all_market_comparisons"]
                 if v["fight_no"]==f["fight_no"] and v["market"]==best["market"]]
        if len(matches)!=1:raise RuntimeError(f'Cannot find exact FanDuel audited market: {best["market"]}')
        verified=matches[0]
        if abs(verified["raw_model_probability"]-best["current_simulated_probability"])>1e-9:
            raise RuntimeError("Probabilities changed from original Stage A")
        if abs(verified["unified_shadow_probability"]-best["unified_shadow_simulated_probability"])>1e-9:
            raise RuntimeError("Unified shadow mismatch")
        out.append({
            "fight_no":f["fight_no"],"fight":f'{f["a"]} vs {f["b"]}',
            "original_stage_a_posture":f["stage_a_posture"],
            **best,
            "fanduel_screenshot_odds":verified["american_odds"],
            "market_break_even_probability":verified["break_even"],
            "raw_model_ev_per_unit_unadjusted":verified["raw_ev_per_unit"],
            "stage_b_timing_market_approved":verified["eligible"],
            "timing_market_block_reasons":verified["block_reasons"],
            "research_status":"ONE_MODEL_FORECAST_FOR_GRADING_NOT_AN_APPROVED_BET",
            "selection_method":"max-min-two-model-probability; price-not-used-for-ranking",
        })
    if len(out)!=14 or len({v["fight_no"] for v in out})!=14:
        raise RuntimeError("Expected one unique forecast per all 14 fights")
    if any(r["stage_b_timing_market_approved"] for r in out):
        raise RuntimeError("Stage B full market audit unexpected approval; cannot silently promote")
    return {
        "event":freeze["event"],"event_date":freeze["event_date"],
        "status":"PRE_EVENT_RESEARCH_TIMING_FORECASTS_NOT_FROZEN_ODDS_BLIND_STAGE_A_BETS",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "original_stage_a_sha256":sha(STAGE_A),
        "snapshot_fanduel_quote_sha256":sha(PRICES),
        "full_stage_b_price_audit_sha256":sha(AUDIT),
        "research_fight_count":len(out),
        "model_source":"frozen Stage A 10,000-trial current model and separate unified timing shadow",
        "rule":"Per fight maximize min(current, unified) across GTD yes/no, posted O/U yes/no, Round3 starts yes/no. Price annotations only; do not include Round2-YES chalk in primary timing candidate competition.",
        "post_price_research_selection":True,
        "stage_a_historically_locked_timing_pick":False,
        "official_timing_bets_approved":0,
        "not_included_in_top5_two_tier_bets":True,
        "grade_these_predictions_separately_not_as_placed_bets":True,
        "model_family_reliability_warning":"Many outcomes fail sparse-history, model coherence, or 12pp timing-price edge gates. Ranking by confidence is not proof of profitability.",
        "fights":out,
    }


def main():
    o=build()
    if DEST.exists():
        raise RuntimeError(f"Will not overwrite existing pre-event selected picks: {DEST}")
    DEST.write_text(json.dumps(o,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":o["status"],"fights":o["research_fight_count"],
      "selected":[[x["fight_no"],x["market"],round(x["current_simulated_probability"],4),
                   x["fanduel_screenshot_odds"]] for x in o["fights"]]},indent=2))


if __name__=="__main__":
    main()
