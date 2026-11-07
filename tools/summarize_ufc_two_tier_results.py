"""Accumulate verified event grades for WSHL_X's two nonoverlapping Top-5 tiers.

Only grade files generated from frozen FanDuel two-tier cards are allowed.
Unpicked cards and hypothetical/parlay suggestions never enter these results.
No input files -> report an empty sample, not an invented 0% success rate.

Example:
  PYTHONPATH=src python tools/summarize_ufc_two_tier_results.py \
      data/grades/*_two_tier_grade.json \
      --output reports/two_tier_tracking/season_summary.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from wshlx_ufc.two_tier_card import TIERS


def aggregate(grades: list[dict]):
    events = set()
    category = {}
    for tier in TIERS:
        category[tier] = {
            "W": 0, "L": 0, "PUSH": 0, "VOID": 0, "PENDING": 0,
            "selected": 0, "settled_risk_units": 0.0, "pnl_units": 0.0,
        }
    for grade in grades:
        event = grade["event_date"], grade["event"]
        if event in events:
            raise ValueError(f"Duplicate event grade: {event}")
        events.add(event)
        if not grade["stage_a_sha256"] or not grade.get("stage_b_sha256"):
            raise ValueError("Not an audited frozen Stage B card grade")
        for tier in TIERS:
            data = grade["categories"][tier]
            dst = category[tier]
            dst["selected"] += int(data["selected"])
            for outcome in ("W", "L", "PUSH", "VOID", "PENDING"):
                dst[outcome] += int(data["record"][outcome])
            dst["settled_risk_units"] += float(data["settled_risk_units"])
            dst["pnl_units"] += float(data["pnl_units"])
    for tier in TIERS:
        d = category[tier]
        settled = d["W"] + d["L"]
        d["record"] = f'{d["W"]}-{d["L"]}'
        d["hit_rate"] = d["W"] / settled if settled else None
        d["roi"] = (d["pnl_units"] / d["settled_risk_units"]
                    if d["settled_risk_units"] else None)
        d["pending_not_counted_as_losses"] = True
    total = {
        "selected": sum(d["selected"] for d in category.values()),
        "W": sum(d["W"] for d in category.values()),
        "L": sum(d["L"] for d in category.values()),
        "PUSH": sum(d["PUSH"] for d in category.values()),
        "VOID": sum(d["VOID"] for d in category.values()),
        "PENDING": sum(d["PENDING"] for d in category.values()),
        "settled_risk_units": sum(d["settled_risk_units"] for d in category.values()),
        "pnl_units": sum(d["pnl_units"] for d in category.values()),
    }
    total["roi"] = (total["pnl_units"] / total["settled_risk_units"]
                    if total["settled_risk_units"] else None)
    return {
        "policy": "WSHL_X_UFC_TOP5_TWO_TIERS_EFFECTIVE_2026-11-07",
        "tracked_events": len(events),
        "categories": category, "combined": total,
        "note": "Official pre-event recommended straight-bet records; not proof of real wager placement. No parlay or retrospective-unpicked grades.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("grade_paths", type=Path, nargs="*")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    grades = [json.loads(p.read_text()) for p in args.grade_paths]
    results = aggregate(grades)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
