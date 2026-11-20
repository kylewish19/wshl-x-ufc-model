"""Third shadow research cohort: 13 pre-fight unified winner+method predictions.

Nov7 unified exact-method record 8/14 was only a retrospective 1u
hypothetical price grade. To track this prospectively fairly, freeze all
thirteen 2026-11-14 Unified model outcomes and the ACTUAL original FanDuel
screenshots where quoted, without hindsight filtering or staking any money.

Fight #2 Alatengheili/Juan Diaz has ONLY ML quoted, so its exact-method
outcome is tracked for W/L but cannot be assigned a fabricated method
price or 1u virtual price return. All quotes remain research, not approved.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from wshlx_ufc.two_tier_card import break_even,expected_value

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"data/locks/ufc334_2026-11-14"
FROZEN=DIR/"stage_a_final_selection.json"
RAW=DIR/"stage_a_model_raw_three_view.json"
QUOTES=ROOT/"data/quotes/ufc334_2026-11-14_fanduel_user_screenshots.json"
OUTPUT=DIR/"unified_exact_method_13_picks_12_fanduel_quotes_pending.json"


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():raise RuntimeError("Refuse to edit existing locked Unified prediction cohort")
    a=json.loads(FROZEN.read_text())
    raw=json.loads(RAW.read_text())
    quote=json.loads(QUOTES.read_text())
    if not a["stage_a_frozen"] or a["odds_used"] is not False or a["raw_model_sha256"]!=sha(RAW):
        raise RuntimeError("Stage A original model no longer frozen")
    if quote["source_frozen_stage_a_sha256"]!=sha(FROZEN) or quote["total_markets"]!=334:
        raise RuntimeError("Original FanDuel quote snapshot mismatched")
    if not len(a["fights"])==len(raw["fights"])==len(quote["quoted_markets"])==13:
        raise RuntimeError("Full card must include 13 Unified exact method candidates")
    rows=[];priced=0
    for i,(fight,model,q) in enumerate(zip(a["fights"],raw["fights"],quote["quoted_markets"]),1):
        if fight["fight_no"]!=i or model["fight_no"]!=i or q["fight_no"]!=i:
            raise RuntimeError("Fight number mismatch")
        if (fight["a"],fight["b"])!=(q["a"],q["b"]):
            raise RuntimeError("Fighter identity mismatch")
        fighter=fight["winner_views"]["oof_unified_shadow"]["pick"]
        side="a" if fighter==fight["a"] else "b"
        lead="A_" if side=="a" else "B_"
        joint=model["oof_unified_shadow"]["joint_method"]
        labels=("KO","SUB","DEC")
        method=max(labels,key=lambda x:joint[lead+x])
        stored=fight["method"]["primary_method_forecast_for_grade"]["unified_own_fighter"]
        if method!=stored:
            raise RuntimeError(f"Unified pre-event own-fighter method mismatch at fight {i}")
        market_method="KO_TKO" if method=="KO" else method
        conditional=joint[lead+method]/sum(joint[lead+x] for x in labels)
        jointp=joint[lead+method]
        price=(q["method_of_victory"][side][market_method]
               if q["method_of_victory"] is not None else None)
        if price is not None:priced+=1
        rows.append({
            "fight_no":i,"fight":f"{fight['a']} vs {fight['b']}",
            "selected_fighter":fighter,"selected_method":market_method,
            "original_unified_winner_probability":fight["winner_views"]["oof_unified_shadow"]["probability"],
            "original_unified_conditional_method_probability":conditional,
            "original_unified_six_class_joint_probability":jointp,
            "original_fanduel_exact_method_american_odds":price,
            "original_fanduel_break_even_probability":break_even(price) if price is not None else None,
            "raw_six_class_model_EV_per_unit_unverified":expected_value(price,jointp) if price is not None else None,
            "reported_hypothetical_bet_status":"NO_ACTUAL_OR_APPROVED_BET",
            "model_result":"PENDING",
            "hypothetical_price_grade_status":"PENDING" if price is not None else "NO_METHOD_QUOTE_DONT_INFER_PRICE",
            "hypothetical_staked_units_if_price_available":1 if price is not None else 0,
            "hypothetical_units_settled":0,
            "hypothetical_net_units_to_date":0,
            "Stage_A_stored_pre_snapshot":True,
        })
    if priced!=12 or rows[1]["original_fanduel_exact_method_american_odds"] is not None:
        raise RuntimeError("Need 12 method quotes, Alatengheili/Diaz remains unpriced")
    payload={
        "event":a["event"],"event_date":a["event_date"],
        "status":"PRE_EVENT_UNIFIED_13_FIGHTER_METHOD_FORECASTS_12_PRICEABLE_SHADOWS_PENDING",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "model_role":"UNPROMOTED_UNIFIED_PROSPECTIVE_SHADOW",
        "purpose":"Independent research grade after event: all 13 exact winner+method outcomes; hypothetically price 12 with archived FanDuel; no retroactive filtering.",
        "frozen_stage_a_sha256":sha(FROZEN),"frozen_model_sha256":sha(RAW),
        "original_fanduel_snapshot_sha256":sha(QUOTES),
        "total_prediction_rows":13,"original_exact_method_price_count":12,
        "missing_quote_fights":[2],
        "hypothetical_virtual_units_per_priced_selection":1,
        "hypothetical_risk_if_all_priced_selections_were_staked":12,
        "actual_staked_units":0,"official_approved_units":0,
        "hypothetical_current_settled_risk_units":0,
        "hypothetical_current_net_units":0,
        "hypothetical_current_roi":None,
        "all_results_pending":True,
        "model_family_calibration_approval":False,
        "prices_only_user_screenshots_nov11":True,
        "no_bets_implied":True,
        "separate_from_both_top5_tiers":True,
        "rows":rows,
    }
    OUTPUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"model_rows":len(rows),"priced":priced,"unpriced":[2],
                      "no_actual_bets":True,"pending_all":True},indent=2))


if __name__=="__main__":main()
