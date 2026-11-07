"""Freeze pending 1u hypothetical ledger, then later grade verified outcomes.

Before fights, establish exactly which FanDuel screenshot prices, candidates
and frozen card are being scored (all should read PENDING, +0.00u so far):
    PYTHONPATH=src python tools/track_ufc_top5_research_units.py \
      --card data/locks/ufcvegas124_2026-11-07/stage_b_top5_ranked_research_review_compatible_cross_tier.json \
      --output data/locks/ufcvegas124_2026-11-07/stage_b_top5_research_units_pending.json

AFTER verified completion, grade only with externally confirmed settlements:
    PYTHONPATH=src python tools/track_ufc_top5_research_units.py \
      --card data/locks/ufcvegas124_2026-11-07/stage_b_top5_ranked_research_review_compatible_cross_tier.json \
      --settlements data/results/ufcvegas124_2026-11-07_top5_verified_settlements.json \
      --output data/results/ufcvegas124_2026-11-07_top5_research_unit_grade.json

settlements JSON shape:
{
  "event_date": "2026-11-07",
  "research_card_sha256": "<exact SHA256 of frozen research watchlist>",
  "results_verified": true,
  "evidence": "official result details and settlement sources",
  "results": {
    "top_5_longshots:1:13": "W",
    "top_5_best_bets:1:5": "L"
  }
}
Omit a candidate if still PENDING. W/L/PUSH/VOID not inferred.
This is the RESEARCH simulated-1u ledger, NEVER user wagers or official bets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from wshlx_ufc.research_top5_ledger import grade_research_watchlist


def main():
    ap=argparse.ArgumentParser(description="Track screenshot-priced UFC Top5 research picks as 1u hypothetical singles")
    ap.add_argument("--card", required=True, type=Path)
    ap.add_argument("--settlements", type=Path, default=None)
    ap.add_argument("--output", required=True, type=Path)
    args=ap.parse_args()
    if args.output.exists():
        raise RuntimeError("Cannot overwrite existing pre-event or post-event ledger file")
    raw=args.card.read_bytes()
    card=json.loads(raw)
    card_sha=hashlib.sha256(raw).hexdigest()
    results={}
    evidence=None
    source_sha=None
    if args.settlements:
        data=args.settlements.read_bytes()
        payload=json.loads(data)
        if payload.get("event_date")!=card.get("event_date"):
            raise RuntimeError("Result event identity doesn't match frozen watchlist")
        if payload.get("research_card_sha256")!=card_sha:
            raise RuntimeError("Result file must reference exact frozen pre-event research watchlist")
        if payload.get("results_verified") is not True or not isinstance(payload.get("evidence"),str) or not payload["evidence"].strip():
            raise RuntimeError("Refusing to grade without verified results and actual source provenance")
        if not isinstance(payload.get("results"),dict):
            raise RuntimeError("Malformed settlement mapping")
        results=payload["results"]
        evidence=payload["evidence"]
        source_sha=hashlib.sha256(data).hexdigest()
    grade=grade_research_watchlist(card,results)
    grade.update({
        "frozen_research_watchlist_sha256":card_sha,
        "produced_at_utc":datetime.now(timezone.utc).isoformat(),
        "status":"VERIFIED_EVENT_RESEARCH_RESULTS" if args.settlements else "PRE_EVENT_PENDING_ONLY_NO_RESULTS",
        "settlement_evidence":evidence,
        "settlement_input_sha256":source_sha,
        "original_fanduel_snapshot_sha256":card["fanduel_screenshot_sha256"],
    })
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(grade,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "status":grade["status"],
        "event":grade["event"],
        "category_totals":{tier:{
            "prices":[x["american_odds"] for x in group["selections"]],
            "W":group["record"]["W"],"L":group["record"]["L"],
            "PENDING":group["record"]["PENDING"],
            "hypothetical_net_units":group["hypothetical_net_units"],
            "hypothetical_roi":group["hypothetical_roi"],
        } for tier,group in grade["categories"].items()},
        "combined":grade["combined"],"file":str(args.output),
    },indent=2))


if __name__=="__main__":
    main()
