"""Cumulative UFC research-only Top5 Longshots vs Best Bets W/L/P&L/ROI.

Only fully audited post-event 1-unit *hypothetical* research grades enter
this ledger; do not merge with actually-approved bet ledgers. The pending
pre-event snapshot is excluded by requiring status VERIFIED_EVENT_RESEARCH_RESULTS.

Example:
 PYTHONPATH=src python tools/summarize_ufc_top5_research_units.py \
    data/results/ufcvegas124_2026-11-07_top5_research_unit_grade.json \
    --output reports/two_tier_tracking/cumulative_hypothetical_research_units.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from wshlx_ufc.two_tier_card import TIERS
from wshlx_ufc.research_top5_ledger import OUTCOMES


def aggregate_research_grades(grades):
    totals={
        tier:{
            "researched_candidates":0,
            "record":{k:0 for k in OUTCOMES},
            "settled_hypothetical_risk_units":0.0,
            "net_hypothetical_units":0.0,
        }
        for tier in TIERS
    }
    seen=set()
    for grade in grades:
        if grade.get("ledger_type")!="TWO_TIER_RESEARCH_ONLY_HYPOTHETICAL_ONE_UNIT_PER_PICK":
            raise ValueError("This cumulative ledger accepts research-only hypothetical grades")
        if grade.get("status")!="VERIFIED_EVENT_RESEARCH_RESULTS":
            raise ValueError("Cannot include PENDING-only pre-event snapshots as graded event results")
        if grade.get("approved_betting_stakes_not_conflated") is not True:
            raise ValueError("Research unit record misclassified as approved bets")
        if not grade.get("frozen_research_watchlist_sha256") or not grade.get("settlement_input_sha256"):
            raise ValueError("Event settlement / pre-event card provenance required")
        key=(grade["event_date"],grade["event"])
        if key in seen:
            raise ValueError("Duplicate event grade not allowed")
        seen.add(key)
        for tier in TIERS:
            source=grade["categories"][tier]
            target=totals[tier]
            target["researched_candidates"]+=int(source["displayed_candidates"])
            for name in OUTCOMES:
                target["record"][name]+=int(source["record"][name])
            target["settled_hypothetical_risk_units"]+=float(source["hypothetical_settled_risk_units"])
            target["net_hypothetical_units"]+=float(source["hypothetical_net_units"])
    for target in totals.values():
        settled=target["record"]["W"]+target["record"]["L"]
        target["W_L"]=f'{target["record"]["W"]}-{target["record"]["L"]}'
        target["hypothetical_hit_rate"]=target["record"]["W"]/settled if settled else None
        target["hypothetical_roi"]=target["net_hypothetical_units"]/target["settled_hypothetical_risk_units"] if target["settled_hypothetical_risk_units"] else None
        target["net_hypothetical_units"]=round(target["net_hypothetical_units"],6)
    allrisk=sum(x["settled_hypothetical_risk_units"] for x in totals.values())
    allnet=sum(x["net_hypothetical_units"] for x in totals.values())
    return {
        "ledger_type":"CUMULATIVE_TOP5_RESEARCH_ONLY_HYPOTHETICAL_ONE_UNIT",
        "events":len(seen),
        "categories":totals,
        "combined":{"researched_candidates":sum(x["researched_candidates"] for x in totals.values()),
                    "W":sum(x["record"]["W"] for x in totals.values()),
                    "L":sum(x["record"]["L"] for x in totals.values()),
                    "PUSH":sum(x["record"]["PUSH"] for x in totals.values()),
                    "VOID":sum(x["record"]["VOID"] for x in totals.values()),
                    "PENDING":sum(x["record"]["PENDING"] for x in totals.values()),
                    "settled_hypothetical_risk_units":allrisk,
                    "net_hypothetical_units":round(allnet,6),
                    "hypothetical_roi":allnet/allrisk if allrisk else None,
                    },
        "not_actual_wagers_not_approved_bet_pnl":True,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("grades",nargs="*",type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    if args.output.exists():
        raise RuntimeError("Refusing to overwrite cumulative report; version a correction separately")
    grades=[json.loads(file.read_text()) for file in args.grades]
    out=aggregate_research_grades(grades)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2))


if __name__=="__main__":
    main()
