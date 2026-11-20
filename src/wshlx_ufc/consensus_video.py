"""Consensus-for-content overlay on frozen, odds-blind UFC three-view predictions.

The original champion, Historical shadow and Unified shadow are NOT three
independent statistical samples (Unified blends the other views). A 2/3 vote
is an editorial display rule, not a calibrated probability, promotion, or
authorized sportsbook wager. The original Stage A and Stage B are immutable.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

MODEL_KEYS = ("reference", "historical_shadow", "oof_unified_shadow")
METHOD_VOTE_KEYS = ("reference", "historical_own_fighter", "unified_own_fighter")
METHOD_NORMALIZE = {"KO/TKO": "KO/TKO", "KO": "KO/TKO", "SUB": "SUB", "DEC": "DEC"}
TIMING_MARKETS = (
    "GTD_YES", "GTD_NO", "OVER_1.5", "UNDER_1.5",
    "OVER_2.5", "UNDER_2.5",
    "ROUND_3_STARTS_YES", "ROUND_3_STARTS_NO",
)
TIMING_NAMES = {
    "GTD_YES": "Fight goes distance YES",
    "GTD_NO": "Fight goes distance NO",
    "OVER_1.5": "Over 1.5 rounds",
    "UNDER_1.5": "Under 1.5 rounds",
    "OVER_2.5": "Over 2.5 rounds",
    "UNDER_2.5": "Under 2.5 rounds",
    "ROUND_3_STARTS_YES": "Round 3 starts YES",
    "ROUND_3_STARTS_NO": "Round 3 starts NO",
}


def majority(votes):
    """Return the exact matching selection only with 2/3 or 3/3 votes."""
    if len(votes) != 3:
        raise ValueError("Exactly three model views are required")
    counts = Counter(votes)
    selection, n = counts.most_common(1)[0]
    if n < 2:
        return {"selection": None, "votes": 1, "consensus": "NO_CONSENSUS"}
    return {"selection": selection, "votes": n,
            "consensus": "UNANIMOUS" if n == 3 else "MAJORITY"}


def timing_top(probabilities):
    """Most probable eligible predeclared timing market; no sportsbook input."""
    for market in TIMING_MARKETS:
        if market not in probabilities:
            raise ValueError(f"Missing timing market: {market}")
        p = probabilities[market]
        if not isinstance(p, (float, int)) or not 0 <= p <= 1:
            raise ValueError(f"Bad timing probability: {market}")
    return max(TIMING_MARKETS, key=lambda k: probabilities[k])


def fight_consensus(frozen, raw):
    if (frozen["a"], frozen["b"], frozen["fight_no"]) != (
            raw["a"], raw["b"], raw["fight_no"]):
        raise ValueError("Original fight identities do not match")
    n = frozen["fight_no"]
    winners = [frozen["winner_views"][k]["pick"] for k in MODEL_KEYS]
    if not all(w in (frozen["a"], frozen["b"]) for w in winners):
        raise ValueError("Unknown fighter in frozen prediction")
    winner = majority(winners)
    original_methods = frozen["method"]["primary_method_forecast_for_grade"]
    methods = []
    for key in METHOD_VOTE_KEYS:
        name = original_methods[key]
        if name not in METHOD_NORMALIZE:
            raise ValueError("Unknown frozen method: " + str(name))
        methods.append(METHOD_NORMALIZE[name])
    # IMPORTANT: method votes refer to the model's OWN winner. Different
    # fighters' identical KO method votes must never be treated as consensus.
    paired = [(winners[i], methods[i]) for i in range(3)]
    pair_pick = majority(paired)
    historical = raw["historical_shadow"].get("timing_direct", {})
    current = frozen["timing_current"]["sim_10000"]
    unified = frozen["timing_oof_unified_shadow"]["sim_10000"]
    timing_sources = (current, historical, unified)
    timing_votes = [timing_top(v) for v in timing_sources]
    timing_pick = majority(timing_votes)
    gap_pp = float(frozen.get("method_timing_coherence", {}).get(
        "method_vs_current_timing_finish_discrepancy_pp", 0))
    warning = gap_pp > 15
    winner_votes = {k: winners[i] for i, k in enumerate(MODEL_KEYS)}
    method_votes = {k: {"fighter": winners[i], "method": methods[i]}
                    for i, k in enumerate(MODEL_KEYS)}
    timing_details = {k: {
        "market": timing_votes[i], "p": timing_sources[i][timing_votes[i]],
        "probability_kind": (
            "historical_direct" if k == "historical_shadow"
            else "simulated_10000")
    } for i, k in enumerate(MODEL_KEYS)}
    orig_time = frozen["primary_timing_forecast"]["market_key"]
    is_primary_match = timing_pick["selection"] == orig_time
    caution = []
    if warning:
        caution.append(
            "Method/timing finish probabilities differ by more than 15pp; "
            "DO NOT promote exact method to an official wager."
        )
    # Winner+method shadow joint probabilities sometimes do not reconcile
    # with standalone shadow winner probabilities; do not imply approved
    # exact fighter+method probabilities from majority vote.
    caution.append(
        "Some Historical/Unified six-way method masses do not reconcile with "
        "winner probabilities; consensus is NOT a validated exact-method EV."
    )
    if not is_primary_match:
        caution.append(
            "Three-way editorial timing vote differs from the original "
            "pre-price locked timing forecast. BOTH must remain preserved "
            "and graded separately, without changing the official lock."
        )
    if frozen["stage_a_posture"] == "PASS":
        caution.append(
            "Original Stage A is PASS. Consensus does NOT override PASS status."
        )
    caution.append(
        "Unified is a blend of other model components, not an independent "
        "third source. Majority votes are NOT confidence probabilities."
    )
    return {
        "fight_no": n,
        "bout": f"{frozen['a']} vs {frozen['b']}",
        "original_stage_a_reference_winner": frozen["official_reference_pick"],
        "original_stage_a_posture": frozen["stage_a_posture"],
        "original_stage_a_primary_timing": orig_time,
        "winner": {**winner, "model_votes": winner_votes},
        "winner_plus_method": {
            **pair_pick, "model_votes": method_votes,
            "only_pair_consistent_votes_count": True,
            "approved_bet": False,
            "warning_method_timing_gap_pp": round(gap_pp, 2),
            "coherence_blocked": warning,
        },
        "timing": {**timing_pick,
                   "display_market": (
                       TIMING_NAMES[timing_pick["selection"]]
                       if timing_pick["selection"] is not None else None),
                   "model_votes": timing_details,
                   "same_as_original_frozen_timing": is_primary_match,
                   "historical_uses_direct_probability": True,
                   "approved_bet": False},
        "review_cautions": caution,
        "video_alignment": (
            "TACTICAL_EXPLANATION_MUST_MATCH_THE_SUPPORTED_WIN_CONDITION; "
            "NEVER_CHANGE_A_MODEL_PICK_TO_MATCH_THE_SCRIPT"),
        "auto_tactical_alignment_verified": False,
        "video_publication_status": "EDITORIAL_MATCHUP_FACT_CHECK_REQUIRED",
        "model_weights_or_picks_changed": False,
    }


def consensus_card(frozen, raw, raw_bytes):
    if not frozen.get("stage_a_frozen") or frozen.get("odds_used") is not False:
        raise ValueError("Requires frozen odds-blind Stage A")
    if raw.get("odds_used") is not False:
        raise ValueError("Raw prediction was not odds blind")
    if frozen.get("event") != raw.get("event") or frozen.get("event_date") != raw.get("event_date"):
        raise ValueError("Events differ")
    if hashlib.sha256(raw_bytes).hexdigest() != frozen.get("raw_model_sha256"):
        raise ValueError("Original raw model SHA-256 differs from freeze")
    selected, original = frozen["fights"], raw["fights"]
    if len(selected) != len(original) or not selected:
        raise ValueError("Mismatch in count of fights")
    indexed = {f["fight_no"]: f for f in original}
    if (len(indexed) != len(original)
            or set(indexed) != {f["fight_no"] for f in selected}):
        raise ValueError("Duplicate or missing bouts")
    results = [fight_consensus(f, indexed[f["fight_no"]])
               for f in sorted(selected, key=lambda v: v["fight_no"])]
    return {
        "schema": "WSHL_X_FROZEN_THREE_VIEW_EDITORIAL_CONSENSUS_V1",
        "event": frozen["event"], "event_date": frozen["event_date"],
        "original_freeze_utc": frozen.get("frozen_at_utc"),
        "original_raw_sha256": frozen["raw_model_sha256"],
        "model_views_are_not_independent": True,
        "source": "ORIGINAL_FROZEN_STAGE_A_NO_STAGE_B_ODDS",
        "consensus_is_only_editorial_not_official_replacement": True,
        "bets_approved_by_this_overlay": 0,
        "winner_and_method_not_retrained": True,
        "timing_historical_uses_direct_rates_current_unified_use_simulations": True,
        "fighters": len(results), "fights": results,
    }


def to_markdown(card):
    rows = [
        "# WSHL_X UFC — Three-model consensus for on-camera pick reveal",
        "",
        f"**{card['event']}** — {card['event_date']}",
        "",
        "This is a NEW DERIVED content selection layer; the original champion",
        "selection, PASS/LEAN/SIDE flags and Stage B remain unchanged.",
        "Reference + Historical + Unified are related models, NOT independent votes.",
        "A majority does NOT guarantee accuracy or approve a bet.",
        "",
        "| # | Fight | Winner vote | Fighter + method vote | Timing vote | Notes |",
        "|---:|---|---|---|---|---|",
    ]
    for f in card["fights"]:
        w, m, t = f["winner"], f["winner_plus_method"], f["timing"]
        win = (f"{w['selection']} ({w['votes']}/3)" if w["selection"] else "NO CONSENSUS")
        method = (f"{m['selection'][0]} by {m['selection'][1]} "
                  f"({m['votes']}/3)" if m["selection"] else "NO CONSENSUS")
        timing = (f"{t['display_market']} ({t['votes']}/3)" if t["selection"] else "NO CONSENSUS")
        notes = []
        if m["coherence_blocked"]:
            notes.append("METHOD COHERENCE BLOCK")
        if not t["same_as_original_frozen_timing"]:
            notes.append("DIFFERS FROM ORIGINAL TIMING LOCK")
        if f["original_stage_a_posture"] == "PASS":
            notes.append("ORIGINAL PASS")
        rows.append(f"| {f['fight_no']} | {f['bout']} | {win} | {method} | {timing} | {', '.join(notes) or 'Research only'} |")
    rows.extend([
        "", "## Rules for videos and accountability", "",
        "1. Script: actual sourced striking/wrestling/grappling matchup, verified past",
        "opponents, opponent caliber, recent form, path to victory, and counter-path.",
        "2. Reveal winner+method and duration ONLY after the narrative. Do not recite model names.",
        "3. Only two or three exactly matching votes count as consensus;",
        "method vote is a WHOLE fighter+method pair, not KO/SUB/DEC across opponents.",
        "4. Timing votes choose a best candidate from the same fixed, nontrivial market",
        "set; Historical uses direct probabilities while the other two use 10k sims.",
        "5. A 2/3 agreement is not a price-approved bet or an implied win rate.",
        "6. No media explanation may overwrite or silently reinterpret the ORIGINAL",
        "Stage A predictions, method/timing warnings, or Stage B wager gates.",
        "7. The original Stage A timing forecast may be DIFFERENT and is graded separately.",
        "8. If evidence conflicts with the selection, acknowledge the risk; do not",
        "invent a positive explanation or use 'no way the opponent wins' certainty.",
        "",
    ])
    return "\n".join(rows)


def write_card(lock_path: Path, raw_path: Path, output_json: Path, output_md: Path):
    raw_bytes = raw_path.read_bytes()
    frozen = json.loads(lock_path.read_text(encoding="utf-8"))
    raw = json.loads(raw_bytes)
    result = consensus_card(frozen, raw, raw_bytes)
    for p in (output_json, output_md):
        p.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    output_md.write_text(to_markdown(result), encoding="utf-8")
    return result
