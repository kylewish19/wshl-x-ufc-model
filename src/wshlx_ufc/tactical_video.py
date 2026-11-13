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

FORBIDDEN = re.compile(
    r"\b(reference model|unified model|historical model|the models?|model predicts|"
    r"our pick is|we pick|the winner is|fight ends by|odds are|"
    r"over \d+(?:\.\d+)? rounds|under \d+(?:\.\d+)? rounds)\b|"
    r"\b\d+(?:\.\d+)?\s*%",
    re.IGNORECASE,
)
HOST_CUE = "Now here are our WSHL_X winner, method, and timing picks."


def validate_and_build(lock: dict, research: dict, raw_sha: str | None = None) -> dict:
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
        result.append({
            "fight_no": number, "fighters": list(originals[number]),
            "spoken_matchup_breakdown": body,
            "host_transition": HOST_CUE,
            "host_selection_fields": {
                "winner": "[HOST REVEALS WINNER]",
                "method": "[HOST REVEALS METHOD]",
                "timing": "[HOST REVEALS TIMING PROP]",
            },
            "research_sources": citations,
            "source_evidence_note": row["evidence_summary"],
            "review_status": "EDITORIAL_DRAFT_NEEDS_FINAL_FACT_AND_TAPE_CHECK",
            "no_model_names_or_probabilities_in_script": True,
            "no_pick_revealed": True,
        })
    if done != set(originals):
        raise ValueError("Unresearched fights remain")
    return {
        "schema": "WSHL_X_TACTICAL_SCRIPTS_V1",
        "event": lock["event"], "event_date": lock["event_date"],
        "original_frozen_at_utc": lock.get("frozen_at_utc"),
        "stage_a_sha256": raw_sha or lock.get("raw_model_sha256"),
        "research_source": "PUBLIC_WRITTEN_PREFIGHT_EVIDENCE_NOT_CLAIMED_FULL_FIGHT_TAPE",
        "script_voice": "MATCHUP_TECHNIQUE_AND_TACTICAL_PATHS_NOT_MODEL_NUMBER_RECITATION",
        "status": "EDITORIAL_DRAFT_TO_BE_FACT_CHECKED_BEFORE_PUBLISHING",
        "original_model_picks_changed": False, "model_retrained": False,
        "official_bets_authorized": False,
        "fight_count": len(result),
        "fights": sorted(result, key=lambda x: x["fight_no"]),
    }


def to_markdown(card: dict) -> str:
    lines = [
        "# WSHL_X — UFC tactical breakdown video scripts",
        "",
        f"## {card['event']} — {card['event_date']}",
        "",
        "**How to use:** Read only each spoken script on camera. THEN reveal your",
        "WSHL_X winner, method and timing picks in the blank host fields.",
        "The video script deliberately does not list model names, percentages,",
        "sportsbook prices, or the final selections.",
        "",
        "**Fact-check status:** Written-source research drafts. These are NOT",
        "claims that complete fight tape was watched. The producer should verify",
        "technical assertions and late fight-week changes before publication.",
        "",
    ]
    for f in card["fights"]:
        names = " vs. ".join(f["fighters"])
        lines.extend([
            f"### {f['fight_no']}. {names}", "",
            "**Spoken fight breakdown:**", "",
            f["spoken_matchup_breakdown"], "",
            f"**Transition:** {f['host_transition']}", "",
            "- Winner: [YOU REVEAL]",
            "- Method: [YOU REVEAL]",
            "- Timing prop: [YOU REVEAL]",
            "",
            "**Evidence / research sources:**",
        ])
        lines.extend([f"- {url}" for url in f["research_sources"]])
        lines.extend(["", f"*Research note: {f['source_evidence_note']}*", "", "---", ""])
    return "\n".join(lines) + "\n"


def create_reports(lock_path: Path, research_path: Path, markdown_out: Path,
                   json_out: Path, raw_path: Path | None = None) -> dict:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    packet = json.loads(research_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(raw_path.read_bytes()).hexdigest() if raw_path else None
    card = validate_and_build(lock, packet, raw_sha=digest)
    for p in (markdown_out, json_out):
        p.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(to_markdown(card), encoding="utf-8")
    json_out.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    return card
