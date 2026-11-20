"""Assemble November 14 UFC 334 original 13 screenshot files into full price snapshot.

Exactly 334 prices are expected: 10 non-title fights with 27 prices,
two five-round title fights with 31, one moneyline-only replacement bout
with two prices. Missing Alatengheili-Diaz props and collapsed title round
betting MUST remain unknown; never infer or fill.

This script NEVER changes the separately frozen Stage A predictions.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/"data/locks/ufc334_2026-11-14/stage_a_final_selection.json"
Q=ROOT/"data/quotes"
DEST=Q/"ufc334_2026-11-14_fanduel_user_screenshots.json"
FILES=[
 "ufc334_2026-11-14_fanduel_fight_01_elder_sanches.json",
 "ufc334_2026-11-14_fanduel_fight_02_alatengheili_diaz_partial.json",
 "ufc334_2026-11-14_fanduel_fight_03_chiasson_mesquita.json",
 "ufc334_2026-11-14_fanduel_fight_04_gordon_costa.json",
 "ufc334_2026-11-14_fanduel_fight_05_johnson_almeida.json",
 "ufc334_2026-11-14_fanduel_fight_06_miller_mckinney.json",
 "ufc334_2026-11-14_fanduel_fight_07_dober_duncan.json",
 "ufc334_2026-11-14_fanduel_fight_08_thompson_radtke.json",
 "ufc334_2026-11-14_fanduel_fight_09_hasan_gurule.json",
 "ufc334_2026-11-14_fanduel_fight_10_medic_holland.json",
 "ufc334_2026-11-14_fanduel_fight_11_borralho_belgaroui.json",
 "ufc334_2026-11-14_fanduel_fight_12_harrison_nunes.json",
 "ufc334_2026-11-14_fanduel_fight_13_gane_hokit.json",
]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def count_prices(q):
    def one(v):
        if isinstance(v,bool) or not isinstance(v,int) or -99<=v<=99:
            raise ValueError(f"Invalid American odds {v!r}")
        return 1
    count=0
    for x in q["moneyline"].values():count+=one(x)
    for group in ("method_of_victory","double_chance"):
        obj=q.get(group)
        if obj is None:continue
        for side,entries in obj.items():
            if side=="DRAW":count+=one(entries)
            else:
                for v in entries.values():count+=one(v)
    for group in ("goes_distance","how_fight_ends"):
        obj=q.get(group)
        if obj is not None:
            for v in obj.values():count+=one(v)
    if q.get("total_rounds") is not None:
        count+=one(q["total_rounds"]["OVER"])
        count+=one(q["total_rounds"]["UNDER"])
        if q["total_rounds"]["threshold"] not in (0.5,1.5,2.5,3.5,4.5):
            raise RuntimeError("Unrecognized screenshot round total")
    for vals in (q.get("round_to_start") or {}).values():
        for v in vals.values():count+=one(v)
    return count


def build():
    frozen=json.loads(LOCK.read_text())
    if frozen["event_date"]!="2026-11-14" or not frozen["stage_a_frozen"] or frozen["odds_used"]:
        raise RuntimeError("Missing immutable UFC334 Stage A")
    if len(frozen["fights"])!=13:
        raise RuntimeError("Expected exactly 13 unique UFC334 bouts")
    quotes=[]; receipts={};missing=[];counts=[]
    for n,name in enumerate(FILES,1):
        file=Q/name
        item=json.loads(file.read_text())
        locked=frozen["fights"][n-1]
        if (locked["a"],locked["b"],locked["fight_no"])!=(item["a"],item["b"],item["fight_no"]):
            raise RuntimeError(f"Screenshot {n} is mapped to wrong frozen bout")
        if item["event_date"]!=frozen["event_date"] or item["sportsbook"]!="FanDuel":
            raise RuntimeError(f"Non-FanDuel screenshot or event mismatch at {n}")
        if not item.get("stage_a_locked") or item.get("odds_used_in_stage_a") is not False:
            raise RuntimeError(f"Screenshot {n} modified frozen Stage A governance")
        if item.get("full_event_pricing_complete") is True:
            raise RuntimeError(f"Do not claim all markets available before aggregation")
        if locked["scheduled_rounds"]==5:
            if item.get("scheduled_rounds")!=5:raise RuntimeError("Five round event markets not identified")
            if set((item.get("round_to_start") or {}).keys())!={"2","3","4","5"}:
                raise RuntimeError("Five-round title starts prices are incomplete")
        else:
            if item.get("scheduled_rounds",3)!=3:
                raise RuntimeError("Unexpected championship rounds")
        count=count_prices(item)
        expected=2 if n==2 else 31 if n in (12,13) else 27
        if count!=expected:raise RuntimeError(f"Screen {n}: expected {expected} posted price values, got {count}")
        if n==2:
            if item["method_of_victory"] is not None or item["double_chance"] is not None or item["goes_distance"] is not None:
                raise RuntimeError("Missing replacement-fight props were synthesized")
            missing.append({"fight_no":n,"fight":f"{locked['a']} vs {locked['b']}",
                            "missing":["Method","Double Chance","GTD","Round totals","Round starts","How fight ends"],
                            "status":"ONLY_TWO_MONEYLINE_PRICES_VISIBLE"})
        if n in (12,13):
            missing.append({"fight_no":n,"fight":f"{locked['a']} vs {locked['b']}",
                            "missing":["5-round Round Betting section collapsed (exact round prop prices)"],
                            "status":"EXACT_ROUND_PROPS_NOT_SHOWN"})
        normalized={k:v for k,v in item.items()
                    if k not in ("market_count","full_fight_pricing_complete")}
        normalized["observed_market_count"]=count
        quotes.append(normalized)
        receipts[str(n)]={"file":str(file.relative_to(ROOT)),"sha256":sha(file),
                          "posted_market_count":count}
        counts.append(count)
    if sum(counts)!=334 or counts!=[27,2]+[27]*9+[31,31]:
        raise RuntimeError(f"Incorrect quote completeness: {counts} sum {sum(counts)}")
    return {
        "event":frozen["event"],"event_date":frozen["event_date"],"sportsbook":"FanDuel",
        "source":"13 user screenshot sets on 2026-11-11; exact time unknown, FanDuel only, not independently live-verified",
        "assembled_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_frozen_stage_a_sha256":sha(LOCK),
        "quoted_markets":quotes,"source_receipts":receipts,
        "total_markets":sum(counts),"uniquely_quoted_fights":len(quotes),
        "complete_displayed_fights":12,"moneyline_only_fights":1,
        "draw_quote_count":24,"modeled_quote_count":310,
        "missing_markets":missing,
        "not_an_authorization_to_bet":True,
        "all_prices_snapshot_only":True,
    }


def main():
    if DEST.exists():raise RuntimeError("Refusing to overwrite quoted markets from event")
    x=build()
    DEST.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "count":x["total_markets"],"fights":x["uniquely_quoted_fights"],
        "complete_displayed":x["complete_displayed_fights"],
        "moneyline_only":x["moneyline_only_fights"],"source_sha":sha(DEST)
    },indent=2))


if __name__=="__main__":main()
