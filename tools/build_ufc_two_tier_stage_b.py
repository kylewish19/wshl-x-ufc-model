"""Create a permanently auditable UFC Top5/Top5 FanDuel Stage B card.

USAGE (ONLY AFTER verified FanDuel quotes are supplied, BEFORE fight starts):
  PYTHONPATH=src python tools/build_ufc_two_tier_stage_b.py \
      --stage-a data/locks/ufcvegas124_2026-11-07/stage_a_final_selection.json \
      --quotes data/quotes/ufcvegas124_2026-11-07_verified_fanduel.json \
      --output data/locks/ufcvegas124_2026-11-07/stage_b_top5_two_tier.json

The quotes input has shape:
{
  "event_date": "2026-11-07",
  "stage_a_sha256": "<SHA256 OF STAGE A FILE>",
  "sportsbook": "FanDuel",
  "prices_verified_before_fight": true,
  "candidates": [<candidate fields in wshlx_ufc.two_tier_card.select_two_tier>]
}

Never invent quotes, backdate, or overwrite a previous frozen Stage B.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from wshlx_ufc.two_tier_card import select_two_tier


def main():
    ap = argparse.ArgumentParser(description="Freeze two disjoint WSHL_X top-five straight-bet lists")
    ap.add_argument("--stage-a", required=True, type=Path)
    ap.add_argument("--quotes", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    raw = args.stage_a.read_bytes()
    stage_a = json.loads(raw)
    quotes = json.loads(args.quotes.read_text(encoding="utf-8"))
    if not stage_a.get("stage_a_frozen") or stage_a.get("odds_used") is not False:
        raise RuntimeError("A real, odds-blind frozen Stage A is required")
    digest = hashlib.sha256(raw).hexdigest()
    if quotes.get("stage_a_sha256") != digest:
        raise RuntimeError("FanDuel quotes were not validated against exact frozen Stage A")
    if quotes.get("event_date") != stage_a.get("event_date"):
        raise RuntimeError("Quotes and Stage A event date mismatch")
    if quotes.get("sportsbook") != "FanDuel" or quotes.get("prices_verified_before_fight") is not True:
        raise RuntimeError("Must use actual pre-fight FanDuel quotes, verified independently")
    if not isinstance(quotes.get("candidates"), list) or not quotes["candidates"]:
        raise RuntimeError("At least one reviewed pre-fight FanDuel price required")

    payload = select_two_tier(
        event=stage_a["event"],
        event_date=stage_a["event_date"],
        stage_a_sha256=digest,
        candidates=quotes["candidates"],
        verified_stage_a_fights=stage_a["fights"],
    )
    payload["quotes_source_sha256"] = hashlib.sha256(args.quotes.read_bytes()).hexdigest()
    payload["fan_duel_price_verification"] = "Pre-fight quote timestamps and original source file hash retained"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite already frozen Stage B: {args.output}")
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "STAGE_B_TWO_TIERS_FROZEN",
        "longshots": payload["counts"]["top_5_longshots"],
        "best_bets": payload["counts"]["top_5_best_bets"],
        "total_nonoverlapping_fights": payload["selected_total"],
        "rejected_candidates": len(payload["rejected"]),
        "path": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
