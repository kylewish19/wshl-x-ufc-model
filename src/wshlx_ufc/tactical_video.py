"""Produce WSHL_X tactical matchup scripts ONLY from sourced, bespoke research.

The research input is a separately reviewed editorial draft. No automatic
fabrication from winner/method/timing probabilities is permitted. Original Stage
A remains immutable; no sportsbook prices, winners, or fight results are loaded.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from wshlx_ufc.consensus_video import consensus_card

FORBIDDEN = re.compile(
    r"\b(reference model|unified model|historical model|the models?|model predicts|"
    r"our pick is|we pick|the winner is|fight ends by|odds are|"
    r"over \d+(?:\.\d+)? rounds|under \d+(?:\.\d+)? rounds)\b|"
    r"\b\d+(?:\.\d+)?\s*%",
    re.IGNORECASE,
)
HOST_CUE = "Now here are our WSHL_X winner, method, and timing picks."


def validate_and_build(lock: dict, research: dict, raw_sha: str | None = None,
                       consensus: dict | None = None) -> dict:
    """Validate documentary integrity, source coverage, and host-pick separation."""
    if not lock.get("stage_a_frozen") or lock.get("odds_used") is not False:
        raise ValueError("Only a frozen, odds-blind Stage A may be linked")
    if research.get("source_type") != "PRE_EVENT_PUBLIC_EDITORIAL_AND_UFC_PROFILE_RESEARCH":
        raise ValueError("Unrecognized scouting-research provenance")
    if research.get("no_original_lock_or_odds_mutation") is not True:
        raise ValueError("Research must not mutate model locks or odds")
    if (lock.get("event"), lock.get("event_date")) != (
            research.get("event"), research.get("event_date")):
        raise ValueError("The researched event does not match the model lock")
    if raw_sha is not None and lock.get("raw_model_sha256") != raw_sha:
        raise ValueError("Original raw Stage A SHA-256 differs from frozen manifest")
    rows = research.get("bouts")
    lock_fights = lock.get("fights")
    if not isinstance(rows, list) or not rows or len(rows) != len(lock_fights):
        raise ValueError("Every frozen fight requires its own tactical research")
    originals = {f["fight_no"]: (f["a"], f["b"]) for f in lock_fights}
    if len(originals) != len(lock_fights):
        raise ValueError("Duplicate original fights")
    # Optional for direct validation/backward compatibility. The production
    # create_reports() path always computes consensus from the verified raw lock.
    votes_by_fight = {}
    if consensus is not None:
        if (consensus.get("event"), consensus.get("event_date")) != (
                lock["event"], lock["event_date"]):
            raise ValueError("Consensus belongs to a different event")
        if consensus.get("original_raw_sha256") != lock.get("raw_model_sha256"):
            raise ValueError("Consensus uses a different original model SHA")
        if consensus.get("bets_approved_by_this_overlay") != 0:
            raise ValueError("Editorial consensus must not approve bets")
        c_fights = consensus.get("fights", [])
        votes_by_fight = {f["fight_no"]: f for f in c_fights}
        if len(votes_by_fight) != len(c_fights) or set(votes_by_fight) != set(originals):
            raise ValueError("Consensus fighter count/identities mismatch")
    done = set()
    result = []
    for row in rows:
        number = row.get("fight_no")
        if number in done or number not in originals:
            raise ValueError("Extra or duplicate tactical fight")
        done.add(number)
        if tuple(row.get("fighters", [])) != originals[number]:
            raise ValueError(f"Wrong fighters for tactical fight {number}")
        body = row.get("script", "").strip()
        if FORBIDDEN.search(body):
            raise ValueError(f"Fight {number} reveals model numbers or final selection in the narration")
        if not 65 <= len(body.split()) <= 260:
            raise ValueError(f"Fight {number} lacks a substantive, original matchup explanation")
        citations = row.get("source_urls", [])
        if (not citations or len(set(citations)) != len(citations)
                or not all(isinstance(c, str) and c.startswith("https://")
                           for c in citations)):
            raise ValueError(f"Fight {number} has no valid unique source URLs")
        if row.get("review_level") != "PUBLIC_WRITTEN_SOURCE_RESEARCH_NOT_CONTINUOUS_FIGHT_VIDEO":
            raise ValueError(f"Fight {number} has an unsupported footage-research claim")
        if not row.get("evidence_summary", "").strip():
            raise ValueError("Missing evidence limitations and provenance")
        # A reader sees matchup analysis first; the host's pick reveal follows.
        # Consensus never changes the narrative text, frozen model, or bet status.
        vote = votes_by_fight.get(number)
        revealed = {
            "winner": "[HOST REVEALS WINNER]",
            "method": "[HOST REVEALS METHOD]",
            "timing": "[HOST REVEALS TIMING PROP]",
        }
        reveal_metadata = {
            "winner_votes": None, "fighter_method_votes": None,
            "timing_votes": None, "method_coherence_warning": False,
            "original_stage_a_pass": False, "different_from_original_timing": False,
            "editorial_only_not_an_approved_bet": True,
        }
        if vote is not None:
            if vote.get("bout") != f"{originals[number][0]} vs {originals[number][1]}":
                raise ValueError(f"Consensus identity mismatch for fight {number}")
            w, m, t = vote["winner"], vote["winner_plus_method"], vote["timing"]
            if any(part.get("votes", 0) not in (2, 3) or part.get("selection") is None
                   for part in (w, m, t)):
                raise ValueError(f"No 2-of-3 consensus on all three outcomes for fight {number}")
            if (len(m["selection"]) != 2 or m["selection"][0] != w["selection"]):
                raise ValueError(f"Fighter+method consensus conflicts with winner for fight {number}")
            if t.get("approved_bet") is not False or m.get("approved_bet") is not False:
                raise ValueError("Video consensus cannot approve method/timing bets")
            revealed = {
                "winner": w["selection"],
                "method": f"{m['selection'][0]} by {m['selection'][1]}",
                "timing": t["display_market"],
            }
            reveal_metadata = {
                "winner_votes": w["votes"],
                "fighter_method_votes": m["votes"],
                "timing_votes": t["votes"],
                "method_coherence_warning": m["coherence_blocked"],
                "original_stage_a_pass": vote["original_stage_a_posture"] == "PASS",
                "different_from_original_timing": not t["same_as_original_frozen_timing"],
                "original_frozen_timing": vote["original_stage_a_primary_timing"],
                "editorial_only_not_an_approved_bet": True,
            }
        result.append({
            "fight_no": number, "fighters": list(originals[number]),
            "spoken_matchup_breakdown": body,
            "host_transition": HOST_CUE,
            "host_selection_fields": revealed,
            "host_reveal_vote_details": reveal_metadata,
            "research_sources": citations,
            "source_evidence_note": row["evidence_summary"],
            "review_status": "EDITORIAL_DRAFT_NEEDS_FINAL_FACT_AND_TAPE_CHECK",
            "no_model_names_or_probabilities_in_script": True,
            "no_pick_revealed": True,
        })
    if done != set(originals):
        raise ValueError("Unresearched fights remain")
    return {
        "schema": "WSHL_X_TACTICAL_SCRIPTS_V2" if consensus else "WSHL_X_TACTICAL_SCRIPTS_V1",
        "event": lock["event"], "event_date": lock["event_date"],
        "original_frozen_at_utc": lock.get("frozen_at_utc"),
        "stage_a_sha256": raw_sha or lock.get("raw_model_sha256"),
        "research_source": "PUBLIC_WRITTEN_PREFIGHT_EVIDENCE_NOT_CLAIMED_FULL_FIGHT_TAPE",
        "script_voice": "MATCHUP_TECHNIQUE_AND_TACTICAL_PATHS_NOT_MODEL_NUMBER_RECITATION",
        "status": "EDITORIAL_DRAFT_TO_BE_FACT_CHECKED_BEFORE_PUBLISHING",
        "original_model_picks_changed": False, "model_retrained": False,
        "automatically_filled_consensus_reveal": consensus is not None,
        "official_bets_authorized": False,
        "fight_count": len(result),
        "fights": sorted(result, key=lambda x: x["fight_no"]),
    }


def to_markdown(card: dict) -> str:
    """Clean, public-facing script; sourcing and warnings remain in the JSON audit."""
    lines = [
        "# WSHL_X — UFC tactical breakdown video scripts",
        "",
        f"## {card['event']} — {card['event_date']}",
        "",
    ]
    for f in card["fights"]:
        names = " vs. ".join(f["fighters"])
        revealed = f["host_selection_fields"]
        lines.extend([
            f"### {f['fight_no']}. {names}", "",
            "**Fight breakdown:**", "",
            f["spoken_matchup_breakdown"], "",
            f"**{f['host_transition']}**", "",
            "**WSHL_X UFC Picks:**", "",
            f"- **Winner:** {revealed['winner']}",
            f"- **Method:** {revealed['method']}",
            f"- **Timing:** {revealed['timing']}",
            "",
            "---", "",
        ])
    return "\n".join(lines) + "\n"


def create_reports(lock_path: Path, research_path: Path, markdown_out: Path,
                   json_out: Path, raw_path: Path | None = None) -> dict:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    packet = json.loads(research_path.read_text(encoding="utf-8"))
    if raw_path is None:
        raise ValueError("Original raw prediction file is required for consensus reveal")
    raw_bytes = raw_path.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    raw = json.loads(raw_bytes)
    verified_consensus = consensus_card(lock, raw, raw_bytes)
    card = validate_and_build(lock, packet, raw_sha=digest,
                              consensus=verified_consensus)
    for p in (markdown_out, json_out):
        p.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(to_markdown(card), encoding="utf-8")
    json_out.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    return card
