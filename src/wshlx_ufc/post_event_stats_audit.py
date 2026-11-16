"""Validate UFC 334 mirrored post-fight statistics before any possible training use.

Records are explicitly SECONDARY UFCStats-derived mirrors while direct
ufcstats.com endpoints are unavailable. File completeness and summation
checks do not make the source primary-verified or available pre-event.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/raw/ufc334_2026-11-14"
MANIFEST = BASE / "INGESTION_MANIFEST_PROVISIONAL.json"
TOTALS = BASE / "ufc334_complete_26_fighter_mirror_totals_PROVISIONAL.csv"
ROUNDS = BASE / "ufc334_fighter_mirror_per_round_PROVISIONAL.csv"
OUTCOMES = ROOT / "data/results/ufc334_2026-11-14_verified_outcomes.json"
FROZEN = ROOT / "data/locks/ufc334_2026-11-14/stage_a_final_selection.json"

CORE_FIELDS = (
    "sig_str_landed", "sig_str_attempted", "takedowns_landed",
    "takedowns_attempted", "control_seconds", "knockdowns",
)
PAIR_FIELDS = (
    ("head_sig_landed", "body_sig_landed", "leg_sig_landed", "sig_str_landed"),
    ("head_sig_attempted", "body_sig_attempted", "leg_sig_attempted", "sig_str_attempted"),
    ("distance_sig_landed", "clinch_sig_landed", "ground_sig_landed", "sig_str_landed"),
    ("distance_sig_attempted", "clinch_sig_attempted", "ground_sig_attempted", "sig_str_attempted"),
)
EXTRA_FIELDS = (
    "total_str_landed", "total_str_attempted", "submission_attempts",
    "reversals", "head_sig_landed", "head_sig_attempted", "body_sig_landed",
    "body_sig_attempted", "leg_sig_landed", "leg_sig_attempted",
    "distance_sig_landed", "distance_sig_attempted", "clinch_sig_landed",
    "clinch_sig_attempted", "ground_sig_landed", "ground_sig_attempted",
)


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def postevent_feature_cutoff_guard(*, source_as_of: str, prediction_date: str) -> None:
    """Never let stats first observed after event enter that event's pre-fight features."""
    if date.fromisoformat(source_as_of) >= date.fromisoformat(prediction_date):
        raise ValueError(
            "Post-event stats feature leakage: source is not known BEFORE prediction event"
        )


def audit_mirrored_ufc334_stats(
    manifest_path: Path = MANIFEST, totals_path: Path = TOTALS,
    rounds_path: Path = ROUNDS, results_path: Path = OUTCOMES,
    frozen_path: Path = FROZEN,
) -> dict:
    manifest = json.loads(manifest_path.read_text())
    results = json.loads(results_path.read_text())
    locked = json.loads(frozen_path.read_text())
    totals, rounds = read_csv(totals_path), read_csv(rounds_path)
    if not manifest.get("post_event_only") or manifest.get("allow_training") is not False:
        raise ValueError("Provisional mirrored data must stay in post-event-only quarantine")
    if not manifest["source_classification"].startswith("UFCSTATS_DERIVED_SECONDARY"):
        raise ValueError("Cannot claim primary UFCStats provenance")
    if not locked.get("stage_a_frozen") or locked.get("odds_used"):
        raise ValueError("Original Stage A no longer frozen/odds-blind")
    if manifest["event_date"] != locked["event_date"] != results["event_date"]:
        raise ValueError("Mismatched events")
    if results["status"] != "VERIFIED_POST_EVENT_OUTCOMES":
        raise ValueError("Outcomes not verified")
    if len(locked["fights"]) != len(results["fights"]) != 13:
        raise ValueError("Expected 13 UFC334 bouts")
    if len(totals) != 26 or len(rounds) != 72:
        raise ValueError("Expected 26 fighter totals and 72 fighter-round rows")
    if date.fromisoformat(manifest["retrieved_as_of_date"]) <= date.fromisoformat(manifest["event_date"]):
        raise ValueError("Post-event dataset claims to predate event")
    original = {int(x["fight_no"]): x for x in locked["fights"]}
    outcomes = {int(x["fight_no"]): x for x in results["fights"]}
    grouped_rounds = defaultdict(list)
    seen = set()
    for row in rounds:
        n, fighter, opponent, corner = int(row["fight_no"]), row["fighter"], row["opponent"], row["corner"]
        if n not in original or corner not in ("a", "b"):
            raise ValueError("Unexpected fight / corner in round stats")
        if fighter != original[n][corner] or opponent != original[n]["b" if corner=="a" else "a"]:
            raise ValueError("Fighter identities inconsistent with frozen card")
        k = (n, fighter, int(row["round"]))
        if k in seen:
            raise ValueError("Duplicate fighter and round record")
        seen.add(k)
        if not 1 <= int(row["round"]) <= outcomes[n]["round"]:
            raise ValueError("Invalid fight round")
        for field in CORE_FIELDS:
            if int(row[field]) < 0:
                raise ValueError("Negative statistic")
        for won, attempts in (("sig_str_landed", "sig_str_attempted"),
                              ("takedowns_landed", "takedowns_attempted")):
            if int(row[won]) > int(row[attempts]):
                raise ValueError("Landed > attempted")
        if int(row["control_seconds"]) > 300:
            raise ValueError("Control exceeds one round")
        if row["source_url"] != "https://fightingdata.com/events/ufc-334-gane-vs-hokit/":
            raise ValueError("Unknown source provenance")
        grouped_rounds[(n, fighter)].append(row)
    counts = defaultdict(int)
    for row in totals:
        n = int(row["fight_no"])
        if n not in original:
            raise ValueError("Unknown bout")
        corner, fighter = row["corner"], row["fighter"]
        if corner not in ("a", "b") or fighter != original[n][corner]:
            raise ValueError("Fighter identity mismatch")
        if row["opponent"] != original[n]["b" if corner == "a" else "a"]:
            raise ValueError("Opposition identity mismatch")
        if row["cagealmanac_source_url"] != f"https://cagealmanac.com/fights/{9002-n}":
            raise ValueError("Bout-specific mirror source not matched")
        if int(row["finish_round"]) != outcomes[n]["round"] or row["method"] != outcomes[n]["method"]:
            raise ValueError("Fight duration or method not aligned with verified result")
        expected_result = ("DRAW" if outcomes[n]["winner"] is None
                           else "W" if fighter == outcomes[n]["winner"] else "L")
        if row["result"] != expected_result:
            raise ValueError("Fighter result mismatches independently verified outcome")
        rounds_for_fighter = grouped_rounds[(n, fighter)]
        if len(rounds_for_fighter) != outcomes[n]["round"]:
            raise ValueError("Missing round record")
        if sorted(int(x["round"]) for x in rounds_for_fighter) != list(
                range(1, outcomes[n]["round"]+1)):
            raise ValueError("Missing chronological round")
        for field in CORE_FIELDS:
            if sum(int(x[field]) for x in rounds_for_fighter) != int(row[field]):
                raise ValueError("Round sums do not match fight total: " + fighter + " " + field)
        for col in EXTRA_FIELDS:
            if int(row[col]) < 0:
                raise ValueError("Invalid extra mirrored fight statistic")
        if int(row["total_str_landed"]) > int(row["total_str_attempted"]):
            raise ValueError("Total landed exceeds attempts")
        if (int(row["total_str_landed"]) < int(row["sig_str_landed"])
                or int(row["total_str_attempted"]) < int(row["sig_str_attempted"])):
            raise ValueError("Significant strikes exceed total strikes")
        for field_a, field_b, field_c, total in PAIR_FIELDS:
            if sum(int(row[key]) for key in (field_a, field_b, field_c)) != int(row[total]):
                raise ValueError("Striking target/position split inconsistent: " + fighter)
        counts[n] += 1
    if set(counts) != set(range(1,14)) or any(n != 2 for n in counts.values()):
        raise ValueError("Missing fight or fighter")
    return {
        "event": manifest["event"], "event_date": manifest["event_date"],
        "total_fights": len(counts), "fighter_totals": len(totals),
        "fighter_rounds": len(rounds),
        "fully_reconciled_core_stats": True,
        "primary_ufcstats_access": False,
        "source_status": manifest["data_grade"],
        "training_authorized": False,
        "stage_a_predictions_changed": False,
        "research_only_mirrored_results": True,
        "unavailable_as_prior_event_features_for_ufc334": True,
    }
