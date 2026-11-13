"""Traceable, non-causal explanation of frozen WSHL_X UFC Stage A forecasts.

Only interprets existing model outputs. Never reads Stage B odds, changes locks,
trains models, or asserts that a contextual trait CAUSED a model prediction.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

METHODS = ("KO", "SUB", "DEC")
NAMES = {"KO": "KO/TKO", "SUB": "submission", "DEC": "decision"}
VIEWS = ("reference", "historical_shadow", "oof_unified_shadow")


def pct(p):
    return f"{100 * float(p):.1f}%"


def _joint(raw, model):
    return raw["joint_calibrated"] if model == "reference" else raw[model]["joint_method"]


def own_method(raw, model, fighter):
    if fighter not in (raw["a"], raw["b"]):
        raise ValueError("Selected fighter is not in this fight")
    side = "A" if fighter == raw["a"] else "B"
    six = _joint(raw, model)
    joint = {m: float(six[f"{side}_{m}"]) for m in METHODS}
    total = sum(joint.values())
    if not 0 < total <= 1:
        raise ValueError("Invalid joint probability")
    conditional = {m: joint[m] / total for m in METHODS}
    top = max(METHODS, key=lambda m: conditional[m])
    return {"joint": joint, "conditional": conditional, "win_mass": total,
            "top": top, "top_conditional_p": conditional[top],
            "top_exact_p": joint[top]}


def _context(f):
    e, a, b = f.get("evidence_density", {}), f["a"], f["b"]
    facts = []
    fields = (("prior_ufc_bouts", "Recorded prior UFC appearances", ""),
              ("age", "Recorded age", "years"),
              ("reach", "Recorded reach", "inches"),
              ("days_since_last", "Days since last appearance", "days"))
    for key, label, unit in fields:
        x, y = e.get("a_" + key), e.get("b_" + key)
        if x is not None and y is not None:
            fmt = (lambda v: f"{v:.1f}") if key == "age" else (lambda v: f"{v:g}")
            facts.append(f"{label}: {a} {fmt(x)}, {b} {fmt(y)} {unit}".strip())
    return facts


def _sourced_notes(fight_no, notes):
    approved, excluded = [], 0
    for note in (notes or {}).get(str(fight_no), []):
        if (note.get("reviewed_by_human") is True
                and note.get("source_url", "").startswith(("https://", "http://"))
                and note.get("claim", "").strip()
                and note.get("category") in {"striking", "grappling", "conditioning",
                                             "durability", "recent_form", "opponent_path", "other"}):
            approved.append({k: note.get(k) for k in
                             ("category", "claim", "source_url", "source_type")})
        else:
            excluded += 1
    return approved, excluded


def explain_fight(f, r, notes=None):
    if (f["fight_no"], f["a"], f["b"]) != (r["fight_no"], r["a"], r["b"]):
        raise ValueError("Locked and raw matchup mismatch")
    a, b = f["a"], f["b"]
    views = {}
    for model in VIEWS:
        locked = f["winner_views"][model]
        method = own_method(r, model, locked["pick"])
        if abs(method["win_mass"] - float(locked["probability"])) > 0.001:
            raise ValueError("Winner/joint method probability incoherence: " + model)
        views[model] = {"pick": locked["pick"], "p": float(locked["probability"]),
                        "method": method}
    reference = views["reference"]
    winner = reference["pick"]
    other = b if winner == a else a
    other_method = own_method(r, "reference", other)
    consensus = len({v["pick"] for v in views.values()}) == 1
    if f["stage_a_posture"] not in {"SIDE", "LEAN", "PASS"}:
        raise ValueError("Unsupported Stage A posture")
    timing = f["primary_timing_forecast"]
    gap = float(f.get("method_timing_coherence", {}).get(
        "method_vs_current_timing_finish_discrepancy_pp", 0))
    flagged = gap > 15
    notes_used, notes_skipped = _sourced_notes(f["fight_no"], notes)
    model_agreement = ("All three views agree on the winner."
                       if consensus else "The models disagree on the winner; this is a key uncertainty.")
    top_method = reference["method"]
    explanation = [
        f"Reference favors {winner} at {pct(reference['p'])}; Historical favors "
        f"{views['historical_shadow']['pick']} at {pct(views['historical_shadow']['p'])}; "
        f"Unified favors {views['oof_unified_shadow']['pick']} at "
        f"{pct(views['oof_unified_shadow']['p'])}.",
        model_agreement,
        f"Reference's leading method IF {winner} wins: {NAMES[top_method['top']]} "
        f"({pct(top_method['top_conditional_p'])} conditional); the actual "
        f"fighter + method joint probability is {pct(top_method['top_exact_p'])}.",
        f"Pre-price timing: {timing['market']} ({pct(timing['current_probability'])} "
        f"current, {pct(timing['unified_shadow_probability'])} Unified).",
        f"Reference gives {other} {pct(other_method['win_mass'])} to win; its leading "
        f"conditional method is {NAMES[other_method['top']]} "
        f"({pct(other_method['top_conditional_p'])}).",
    ]
    if flagged:
        explanation.append(
            f"WARNING: Method-versus-timing finish estimates differ by {gap:.1f} "
            "percentage points, so the method family is blocked from approval."
        )
    short_script = (
        f"WSHL_X UFC breakdown: {a} versus {b}. Our frozen Reference model "
        f"picks {winner}, {pct(reference['p'])}. Historical predicts "
        f"{views['historical_shadow']['pick']} at {pct(views['historical_shadow']['p'])}, "
        f"while Unified predicts {views['oof_unified_shadow']['pick']} at "
        f"{pct(views['oof_unified_shadow']['p'])}. {model_agreement} "
        f"If {winner} wins, {NAMES[top_method['top']]} is the leading Reference "
        f"method, with {pct(top_method['top_conditional_p'])} conditional probability. "
        f"The timing forecast is {timing['market']}, "
        f"{pct(timing['current_probability'])}. "
        f"{other} still has {pct(other_method['win_mass'])} Reference win probability. "
        f"Our official research classification is {f['stage_a_posture']}; "
        "this is not an approved wager."
    )
    outline = [
        ("Opening", f"Introduce {a} versus {b}; show frozen Reference pick and tier."),
        ("Models", model_agreement + " Display all three predicted sides and probabilities."),
        ("Matchup statistics", "Show sourced age, reach and experience facts without claiming feature attribution."),
        ("Method", explanation[2]),
        ("Timing and losing scenario", explanation[3] + " " + explanation[4]),
        ("Risk, verdict and sourcing", "Explain disagreements, method/timing coherence and missing fight footage."),
    ]
    return {
        "fight_no": f["fight_no"], "fight": f"{a} vs {b}",
        "reference_frozen_pick": winner, "reference_win_p": reference["p"],
        "stage_a_posture": f["stage_a_posture"],
        "model_views": views, "all_three_agree": consensus,
        "reasoning_from_archived_probabilities": explanation,
        "descriptive_context_not_feature_attribution": _context(f),
        "opponent_win_case": explanation[4],
        "selected_timing": {"market": timing["market"],
                            "current_p": timing["current_probability"],
                            "unified_p": timing["unified_shadow_probability"]},
        "method_timing_coherence_gap_pp": gap,
        "method_timing_flag": flagged,
        "tape_classification": f.get("tape_provenance", {}).get("classification", "UNKNOWN"),
        "reviewed_scouting_notes": notes_used, "rejected_scouting_notes": notes_skipped,
        "per_fight_feature_attribution_available": False,
        "tactical_research_complete": bool(notes_used),
        "video_script_roughly_one_minute": short_script,
        "long_form_video_chapters": [{"title": t, "content": c} for t, c in outline],
        "producer_warnings": [
            "Do not claim age, reach, or UFC experience CAUSED the model selection.",
            "No verified full-fight video review is recorded; no invented tactical observations.",
            "Conditional method probability is NOT unconditional fighter-plus-method probability.",
            "These are original odds-blind forecasts; a model PASS is not a bet.",
            "A 3–5 minute technical breakdown requires added sourced, reviewed scouting footage.",
        ],
        "derived_only": True, "original_frozen_pick_unchanged": True,
    }


def explain_card(lock, raw, raw_bytes, notes=None):
    if not lock.get("stage_a_frozen") or lock.get("odds_used") is not False:
        raise ValueError("Requires original frozen, odds-blind Stage A")
    if raw.get("odds_used") is not False:
        raise ValueError("Raw model odds integrity failed")
    if (lock.get("event"), lock.get("event_date")) != (raw.get("event"), raw.get("event_date")):
        raise ValueError("Different events")
    digest = hashlib.sha256(raw_bytes).hexdigest()
    if lock.get("raw_model_sha256") != digest:
        raise ValueError("Raw model file SHA-256 failed original lock check")
    if not lock["fights"] or len(lock["fights"]) != len(raw["fights"]):
        raise ValueError("Fight count changed")
    indexed = {f["fight_no"]: f for f in raw["fights"]}
    if len(indexed) != len(raw["fights"]) or set(indexed) != {f["fight_no"] for f in lock["fights"]}:
        raise ValueError("Fight identities differ")
    return {
        "schema": "WSHL_X_UFC_MODEL_BREAKDOWNS_V1",
        "event": lock["event"], "event_date": lock["event_date"],
        "original_frozen_at_utc": lock.get("frozen_at_utc"),
        "original_raw_sha256": digest,
        "data_origin": "FROZEN_STAGE_A_ONLY",
        "not_a_model_rerun": True, "no_odds_or_results_used": True,
        "no_model_promotion_or_changed_picks": True,
        "fight_count": len(lock["fights"]),
        "fights": [explain_fight(f, indexed[f["fight_no"]], notes)
                   for f in sorted(lock["fights"], key=lambda x: x["fight_no"])],
    }


def as_markdown(card):
    lines = [
        "# WSHL_X UFC model-grounded breakdowns: " + card["event"], "",
        "ORIGINAL Stage A selections preserved; scripts are research previews, not betting approvals.",
        "Raw input SHA-256: " + card["original_raw_sha256"], "",
        "Statistical comparisons are NOT verified feature contributions. "
        "Tactical observations require independently reviewed source evidence.", "",
    ]
    for f in card["fights"]:
        lines.extend([
            f"## {f['fight_no']}. {f['fight']}", "",
            f"**Reference:** {f['reference_frozen_pick']} {pct(f['reference_win_p'])} "
            f"({f['stage_a_posture']})", "",
            "**Archived model explanations:**",
        ])
        lines.extend(["- " + x for x in f["reasoning_from_archived_probabilities"]])
        lines.extend(["", "**Descriptive fighter comparisons (not model causal effects):**"])
        lines.extend(["- " + x for x in f["descriptive_context_not_feature_attribution"]]
                     or ["- No archived attributes supplied."])
        lines.extend(["", "**Verified tactical sources:**"])
        lines.extend(["- " + n["claim"] + " — " + n["source_url"]
                      for n in f["reviewed_scouting_notes"]]
                     or ["- Not yet independently reviewed; do not claim footage-based findings."])
        lines.extend(["", "**Short-form model forecast script:**", "",
                      f["video_script_roughly_one_minute"], "",
                      "**Long-form research structure:**"])
        lines.extend(["- " + x["title"] + ": " + x["content"]
                      for x in f["long_form_video_chapters"]])
        lines.extend(["", "**Producer warnings:**"])
        lines.extend(["- " + x for x in f["producer_warnings"]])
        lines.append("")
    return "\n".join(lines) + "\n"


def write_outputs(lock_path: Path, raw_path: Path, json_path: Path, md_path: Path,
                  notes_path: Path | None = None):
    raw_bytes = raw_path.read_bytes()
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    raw = json.loads(raw_bytes)
    notes = json.loads(notes_path.read_text(encoding="utf-8")) if notes_path else None
    card = explain_card(lock, raw, raw_bytes, notes)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(card, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(as_markdown(card), encoding="utf-8")
    return card
