"""Grade WSHL_X Top-5 Longshots and Top-5 Best Bets independently.

Example:
  PYTHONPATH=src python tools/grade_ufc_two_tier_stage_b.py \
    --card data/locks/ufcvegas124_2026-11-07/stage_b_top5_two_tier.json \
    --outcomes data/grades/ufcvegas124_2026-11-07_two_tier_verified_outcomes.json \
    --output data/grades/ufcvegas124_2026-11-07_two_tier_grade.json

Outcomes input:
{
  "event_date": "2026-11-07",
  "stage_b_sha256": "<SHA256 OF LOCKED STAGE B CARD>",
  "results_verified": true,
  "evidence": "Official UFC result links/market settlement provenance",
  "results": {
    "unique_candidate_id": "W", "other_candidate_id": "L"
  }
}
Valid values: W, L, PUSH, VOID; leave out when awaiting settlement.
Never overwrite a prior grade; use a documented new revision for corrections.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from wshlx_ufc.two_tier_card import grade_two_tier


def main():
    parser = argparse.ArgumentParser(description="Grade frozen FanDuel UFC Top5 + Top5 picks")
    parser.add_argument("--card", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    card_bytes = args.card.read_bytes()
    card = json.loads(card_bytes)
    outcome_source = json.loads(args.outcomes.read_text())
    digest = hashlib.sha256(card_bytes).hexdigest()

    if outcome_source.get("stage_b_sha256") != digest:
        raise RuntimeError("Outcome data must reference exact frozen Stage B SHA256")
    if outcome_source.get("event_date") != card.get("event_date"):
        raise RuntimeError("Cannot grade another event's prices")
    if outcome_source.get("results_verified") is not True:
        raise RuntimeError("Only evidence-verified UFC outcomes/market settlements may be graded")
    if not outcome_source.get("evidence"):
        raise RuntimeError("Missing official evidence/provenance for grading")
    if not isinstance(outcome_source.get("results"), dict):
        raise RuntimeError("Missing result object")
    grade = grade_two_tier(card, outcome_source["results"])
    grade.update({
        "graded_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage_b_sha256": digest,
        "result_sources": outcome_source["evidence"],
        "result_input_sha256": hashlib.sha256(args.outcomes.read_bytes()).hexdigest(),
        "tracking_policy": "Separate Top5 +200 longshot and Top5 -150..+190 best-bet W/L/stakes/ROI; no 3-leg substitutes",
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise RuntimeError("Grade file already exists; do not rewrite without versioned correction")
    args.output.write_text(json.dumps(grade, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "event": grade["event"],
        "categories": {name: {
            "W": group["record"]["W"], "L": group["record"]["L"],
            "risk": group["settled_risk_units"],
            "pnl": group["pnl_units"], "roi": group["roi"]
        } for name, group in grade["categories"].items()},
        "total": grade["combined"],
        "path": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
