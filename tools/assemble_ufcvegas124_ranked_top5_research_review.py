"""Nov 7 UFC: populate exactly five research-display candidates per FanDuel tier.

The pre-event Stage A and initial 378-price Stage B audits are immutable.
All ten are *blocked* by already-documented gates, so this is a labeled
RESEARCH REVIEW, NOT a new set of ten approved bets.

A same fight can occur once per price tier if—and ONLY if—its two typed
market specifications can both win. This uses the permanent shared
market_compatibility engine and fails closed on unsupported outcomes.

Selection was analyst-curated to balance odds, model agreement, fight
history, and category diversity from the FULL screenshot candidate set.
The rankings are NOT a new learned model, a calibrated EV estimate or a
claim of live FanDuel availability. Preserve source caveats/provenance.

Run: PYTHONPATH=src python tools/assemble_ufcvegas124_ranked_top5_research_review.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from wshlx_ufc.two_tier_card import BEST_BETS, LONGSHOTS, tier_for_odds, fight_key
from wshlx_ufc.market_compatibility import can_both_win, validate_market_spec

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"data/locks/ufcvegas124_2026-11-07"
STAGE_A=DIR/"stage_a_final_selection.json"
QUOTES=ROOT/"data/quotes/ufcvegas124_2026-11-07_fanduel_user_screenshots.json"
AUDIT=DIR/"stage_b_fanduel_full_price_audit.json"
STAGE_B=DIR/"stage_b_two_tier_outcome.json"
OUTPUT=DIR/"stage_b_top5_ranked_research_review_compatible_cross_tier.json"

# 5 reviewed markets/category, in deliberate triage order. Nothing outside
# screenshot market data and frozen models is invented. Key = (bout #, audit market label).
WATCH={
    LONGSHOTS:[
        (13,"Fight goes distance NO",
         {"kind":"goes_distance","outcome":"NO"},
         "Most established grappling matchup among longshot timing options. Current-model edge 8.3pp is BELOW the 12pp timing gate: PASS, not an approved bet."),
        (4,"Fight goes distance YES",
         {"kind":"goes_distance","outcome":"YES"},
         "Both timing views near 49%, but a short-notice UFC debutant and method/timing incoherence create high uncertainty: PASS."),
        (3,"Fight goes distance YES",
         {"kind":"goes_distance","outcome":"YES"},
         "Current and unified timing models agree on roughly 42%; one UFC bout for Kondratavicius and a severe finish mismatch: PASS."),
        (5,"Murtazali Magomedov by SUB",
         {"kind":"method","side":"b","method":"SUB"},
         "All three conditional method views favor Magomedov submission, but each differs substantially; original fight PASS and exact-method family remains blocked."),
        (1,"Jonny Parsons by KO_TKO",
         {"kind":"method","side":"a","method":"KO_TKO"},
         "All three conditional method views favor KO/TKO, but one UFC bout/long inactivity makes model's huge raw edge unreliable: PASS."),
    ],
    BEST_BETS:[
        (5,"Murtazali Magomedov ML",
         {"kind":"moneyline","side":"b"},
         "All winner model views favor Magomedov, but the fight remains a research PASS due to tiny UFC samples."),
        (1,"Jonny Parsons ML",
         {"kind":"moneyline","side":"a"},
         "Three winner model views agree on Parsons, but the fighter's multiyear UFC absence and sparse opponent data bar promotion."),
        (9,"Mitch Raposo ML",
         {"kind":"moneyline","side":"a"},
         "Three winner views favor Raposo; cannot promote because Degli has zero UFC fights in the frozen training set."),
        (4,"OVER 1.5 rounds",
         {"kind":"total_rounds","direction":"OVER","threshold":1.5},
         "Both timing models estimate ~67%, but short-notice debutant opponent, sparse matchup data and finish-family disagreement block."),
        (12,"Fight goes distance YES",
         {"kind":"goes_distance","outcome":"YES"},
         "Timing current+unified view show an apparent edge, but the method-joint model contradicts finish timing by over 15pp; PASS."),
    ],
}


def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    stage_a=json.loads(STAGE_A.read_text())
    quotes=json.loads(QUOTES.read_text())
    audit=json.loads(AUDIT.read_text())
    stage_b=json.loads(STAGE_B.read_text())
    if not stage_a.get("stage_a_frozen") or stage_a.get("odds_used") is not False:
        raise RuntimeError("Stage A changed or is not odds blind")
    if audit["stage_a_sha256"]!=_sha(STAGE_A) or audit["source_quotes_sha256"]!=_sha(QUOTES):
        raise RuntimeError("Full price audit no longer matches frozen inputs")
    if stage_b["stage_a_sha256"]!=_sha(STAGE_A) or stage_b["quotes_sha256"]!=_sha(QUOTES):
        raise RuntimeError("Initial immutable official Stage B source mismatch")
    if not (stage_b["top_5_longshots"]["number_selected"]==0 and stage_b["top_5_best_bets"]["number_selected"]==0):
        raise RuntimeError("Source Stage B contains bets. Review cannot silently override those bets")
    if len(stage_a["fights"])!=len(quotes["quoted_markets"])!=14:
        raise RuntimeError("Expected 14 snapshot fights")
    if len(audit["all_market_comparisons"])!=378:
        raise RuntimeError("Expected all 378 snapshot market prices")
    if any(len(WATCH[t])!=5 for t in (LONGSHOTS,BEST_BETS)):
        raise RuntimeError("Exactly five researched slots per tier required for this event")

    out={LONGSHOTS:[], BEST_BETS:[]}
    seen={}
    same_bout=[]
    for tier in (LONGSHOTS,BEST_BETS):
        for rank,(n,label,spec,rationale) in enumerate(WATCH[tier],1):
            if not isinstance(rationale,str) or not rationale.strip():
                raise ValueError("All research slots require real written reasons")
            locked=stage_a["fights"][n-1]
            screenshot=quotes["quoted_markets"][n-1]
            if (locked["a"],locked["b"],locked["fight_no"])!=(screenshot["a"],screenshot["b"],screenshot["fight_no"]):
                raise RuntimeError("Market quote no longer maps to frozen fight")
            market_rows=[x for x in audit["all_market_comparisons"]
                if x["fight_no"]==n and x["market"]==label]
            if len(market_rows)!=1:
                raise RuntimeError(f"Missing or ambiguous user screenshot market {n} {label}")
            market=market_rows[0]
            if market["eligible"]:
                raise RuntimeError("Unexpected newly approved wager; do not conflate with watchlist")
            if tier_for_odds(market["american_odds"])!=tier:
                raise ValueError(f"Price outside {tier}: fight {n} / {label}")
            if market["raw_model_probability"] is None:
                raise ValueError("Cannot research-model a draw market")
            if market["raw_ev_per_unit"]<=0:
                raise ValueError("This research display requires at least positive *raw* EV before uncertainty: not an approval")
            spec=validate_market_spec(spec,market_family={
                "moneyline":"moneyline", "method":"method","goes_distance":"timing",
                "total_rounds":"timing"
            }[spec["kind"]],scheduled_rounds=locked["scheduled_rounds"])
            if label.endswith(" ML") and (locked["a"] if spec["side"]=="a" else locked["b"]) not in label:
                raise RuntimeError("Moneyline side identity does not match quoted market")
            key=fight_key(locked["a"],locked["b"])
            prior=seen.get(key,[])
            if any(x["tier"]==tier for x in prior):
                raise RuntimeError("Cannot have two same-fight reviewed markets in same category")
            if any(
                not can_both_win(spec,x["market_spec"],scheduled_rounds=locked["scheduled_rounds"])
                or spec==x["market_spec"]
                for x in prior
            ):
                raise RuntimeError(f"INCOMPATIBLE opposite-tier same-fight watch markets: {label}")
            row={
                "rank":rank, "fight_no":n,
                "fight":f'{locked["a"]} vs {locked["b"]}',
                "fight_key":key,
                "market":label,
                "market_spec":spec,
                "sportsbook":"FanDuel",
                "screenshot_american_odds":market["american_odds"],
                "raw_current_probability":market["raw_model_probability"],
                "unified_shadow_probability":market["unified_shadow_probability"],
                "break_even_probability":market["break_even"],
                "raw_current_probability_edge_pp":market["raw_probability_edge_pp"],
                "raw_unadjusted_ev_per_unit":market["raw_ev_per_unit"],
                "research_notes":rationale,
                "original_stage_a_posture":locked["stage_a_posture"],
                "status":"PASS_RESEARCH_ONLY_NOT_APPROVED_OR_BETTABLE",
                "reasons_not_approved":market["block_reasons"],
                "not_in_official_betting_grade":True,
                "not_previously_frozen_official_stage_b_bet":True,
            }
            if not row["reasons_not_approved"]:
                raise RuntimeError("Refuse to label a qualifying market research-only")
            seen.setdefault(key,[]).append({"tier":tier,"market_spec":spec,"market":label})
            out[tier].append(row)
    for key, pair in seen.items():
        if len(pair)==2:
            same_bout.append({"fight_key":key,"best_bet":next(x["market"] for x in pair if x["tier"]==BEST_BETS),
                "longshot":next(x["market"] for x in pair if x["tier"]==LONGSHOTS),
                "can_both_win":True,"correlated":True})
        elif len(pair)>2:
            raise RuntimeError("Overexposure: over two markets per fight")
    return {
        "event":stage_a["event"],"event_date":stage_a["event_date"],
        "report_type":"POST_PRICE_RANKED_FANDUEL_TWO_TIER_RESEARCH_WATCHLIST",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "stage_a_original_sha256":_sha(STAGE_A),
        "stage_b_original_sha256":_sha(STAGE_B),
        "full_price_audit_sha256":_sha(AUDIT),
        "fanduel_screenshot_sha256":_sha(QUOTES),
        "source_quotes_count":378,
        "exact_fanduel_quote_timestamp_utc":None,
        "input_price_freshness":"Previously shared FanDuel screenshots; not live/re-verified quotes",
        "selection_rule":"Analyst-triaged ranked research opportunities among 378 screenshot prices using frozen raw current+unified probabilities, source risk, method incoherence and line range; NOT an independently validated calibrated EV ranking and NOT an automatic model-learned preference.",
        "stage_a_or_original_stage_b_mutated":False,
        "qualified_bets_in_either_category":0,
        "presented_research_candidates":{LONGSHOTS:5,BEST_BETS:5},
        "one_per_fight_within_each_tier":True,
        "same_fight_cross_tier_allowed_only_if_outcomes_can_coexist":True,
        "same_fight_exposure_warning":"Compatible is not independent; a loss can wipe out both. Do not parlay or force bets from PASS statuses.",
        "distinct_fights_reviewed":len(seen),
        "compatible_same_fight_pairs":same_bout,
        "categories":out,
        "note":"All 10 options are explicitly PASS/research-only, none is an official wager. Actual placed bets not asserted. Freeze is prospective to results, not backdated before the initial FanDuel screens.",
    }


def main():
    output=build()
    if OUTPUT.exists():
        raise RuntimeError("Refusing to overwrite already published ranked watchlist")
    OUTPUT.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"saved":str(OUTPUT.relative_to(ROOT)),
        "source_quote_count":output["source_quotes_count"],
        "research_watchlist":output["presented_research_candidates"],
        "official_bets":output["qualified_bets_in_either_category"],
        "distinct_fights":output["distinct_fights_reviewed"],
        "compatible_pairs":output["compatible_same_fight_pairs"]},indent=2))

if __name__=="__main__":
    main()
