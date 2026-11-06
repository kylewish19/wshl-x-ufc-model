"""Fetch and audit the first post-event UFCStats scraper snapshot for UFC 333.

This script NEVER uses event performance as a pre-fight feature. It preserves
the pinned official-stats export plus a per-event extract and provenance audit.
Missing or mismatched bouts/round-stat rows fail closed.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REPO = "Greco1899/scrape_ufc_stats"
# First archive refresh after UFC 333 (Oct. 24). Avoid later snapshots if possible.
UPSTREAM_COMMIT = "5d6622ffc349a1d0c6dd25158d737a96b889a3e0"
OUT = ROOT / "data/raw/ufc333_2026-10-24"
LOCK_GRADE = ROOT / "data/grades/ufc333_2026-10-24_stage_a_grade.json"
FILES = [
    "ufc_event_details.csv",
    "ufc_fight_details.csv",
    "ufc_fight_results.csv",
    "ufc_fight_stats.csv",
    "ufc_fighter_details.csv",
    "ufc_fighter_tott.csv",
]
EXPECTED_BOUTS = 14


def canon(s: object) -> str:
    s = str(s or "").casefold().replace("’", "'")
    return " ".join(re.findall(r"[a-z0-9]+", s))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def event_match(name: object) -> bool:
    x = canon(name)
    return x.startswith("ufc 333 ") and "volkanovski" in x and "evloev" in x


def clock(v: object) -> int:
    bits = str(v).strip().split(":")
    if len(bits) != 2:
        raise ValueError(f"Malformed finish clock: {v}")
    return 60 * int(bits[0]) + int(bits[1])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    grade = json.loads(LOCK_GRADE.read_text(encoding="utf-8"))
    expected_by_pair = {
        frozenset([canon(x["fight"].split(" vs ")[0]), canon(x["fight"].split(" vs ")[1])]): x
        for x in grade["bouts"]
    }
    if len(expected_by_pair) != EXPECTED_BOUTS:
        raise RuntimeError("Frozen grade does not contain 14 unique bouts")
    receipt = {}
    for name in FILES:
        url = f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{name}"
        path = OUT / name
        urllib.request.urlretrieve(url, path)
        receipt[name] = {"url": url, "bytes": path.stat().st_size, "sha256": sha256(path)}

    frame_names = {
        "event": ("ufc_event_details.csv", "ufc333_event_details.csv"),
        "details": ("ufc_fight_details.csv", "ufc333_fight_details.csv"),
        "results": ("ufc_fight_results.csv", "ufc333_fight_results.csv"),
        "stats": ("ufc_fight_stats.csv", "ufc333_fight_stats.csv"),
    }
    frames = {}
    for key, (input_name, filtered_name) in frame_names.items():
        df = pd.read_csv(OUT / input_name)
        if not {"EVENT"}.issubset(df):
            raise RuntimeError(f"{input_name} lacks EVENT column")
        event_df = df[df["EVENT"].map(event_match)].copy()
        event_df.to_csv(OUT / filtered_name, index=False)
        frames[key] = event_df

    ev, details, results, stats = [frames[k] for k in ("event", "details", "results", "stats")]
    unexpected_pairs = []
    resolved = []
    expected_round_rows = 0
    observed_result_pairs = set()
    for _, r in results.iterrows():
        text = str(r["BOUT"])
        fighters = re.split(r"\\s+vs\\.?\\s+", text, maxsplit=1, flags=re.I)
        if len(fighters) != 2:
            unexpected_pairs.append({"bout": text, "reason": "unrecognized BOUT separator"})
            continue
        pair = frozenset(canon(name) for name in fighters)
        row = expected_by_pair.get(pair)
        if row is None:
            unexpected_pairs.append({"bout": text, "reason": "not in frozen 14 bouts"})
            continue
        if pair in observed_result_pairs:
            unexpected_pairs.append({"bout": text, "reason": "duplicate bout"})
            continue
        observed_result_pairs.add(pair)
        decision_outcome = str(r["OUTCOME"]).strip().upper()
        if decision_outcome not in ("W/L", "L/W"):
            unexpected_pairs.append({"bout": text, "reason": f"nondecisive outcome {decision_outcome}"})
            continue
        parsed_winner = fighters[0] if decision_outcome == "W/L" else fighters[1]
        expected_method = row["actual"]["method_class"]
        upstream_method = str(r["METHOD"]).casefold()
        upstream_class = ("DEC" if "dec" in upstream_method else "SUB" if "sub" in upstream_method else "KO" if ("ko" in upstream_method or "tko" in upstream_method) else "OTHER")
        round_n = int(r["ROUND"])
        seconds = clock(r["TIME"])
        if canon(parsed_winner) != canon(row["actual"]["winner"]) or upstream_class != expected_method or round_n != int(row["actual"]["round"]) or seconds != int(row["actual"]["duration_seconds"]) - 300 * (round_n - 1):
            unexpected_pairs.append({
                "bout": text, "reason": "source vs frozen outcome mismatch",
                "parsed": [parsed_winner, upstream_class, round_n, seconds],
                "frozen": row["actual"],
            })
        expected_round_rows += 2 * round_n
        resolved.append({"fight_no": row["fight_no"], "bout": text, "winner": parsed_winner, "method": upstream_method, "round": round_n, "time": r["TIME"], "source_fight_url": str(r["URL"])})

    result_bouts = set(results["BOUT"].map(canon))
    detail_bouts = set(details["BOUT"].map(canon))
    stat_bouts = set(stats["BOUT"].map(canon))
    round_dupes = []
    if {"BOUT", "ROUND", "FIGHTER"}.issubset(stats):
        dups = stats.duplicated(subset=["BOUT", "ROUND", "FIGHTER"], keep=False)
        round_dupes = stats.loc[dups, ["BOUT", "ROUND", "FIGHTER"]].astype(str).to_dict("records")
    status = bool(
        len(ev) == 1
        and len(results) == EXPECTED_BOUTS
        and len(details) == EXPECTED_BOUTS
        and len(result_bouts) == EXPECTED_BOUTS
        and len(detail_bouts) == EXPECTED_BOUTS
        and len(stat_bouts) == EXPECTED_BOUTS
        and len(stats) == expected_round_rows
        and observed_result_pairs == set(expected_by_pair)
        and result_bouts == detail_bouts == stat_bouts
        and not unexpected_pairs
        and not round_dupes
    )
    audit = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "upstream_repo": UPSTREAM_REPO, "upstream_commit": UPSTREAM_COMMIT,
        "event_rows": int(len(ev)), "unique_result_bouts": len(result_bouts),
        "unique_detail_bouts": len(detail_bouts), "unique_stat_bouts": len(stat_bouts),
        "fighter_round_stat_rows": int(len(stats)),
        "expected_round_stat_rows_from_locked_outcomes": expected_round_rows,
        "unexpected_pairs": unexpected_pairs, "duplicate_fighter_round_keys": round_dupes,
        "missing_detail": sorted(result_bouts - detail_bouts),
        "missing_stats": sorted(result_bouts - stat_bouts),
        "full_card_stats_available": status,
        "resolved_bouts": sorted(resolved, key=lambda x: x["fight_no"]),
        "receipt": receipt,
        "time_integrity": "UFCStats per-round observations are POST-FIGHT. Causal model features must be snapped at each historical bout date before ingesting those results.",
    }
    (OUT / "availability.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "available": status, "result_bouts": len(result_bouts),
        "stats_bouts": len(stat_bouts), "stats_rows": len(stats),
        "expected_rows": expected_round_rows, "unexpected": unexpected_pairs,
    }, indent=2, sort_keys=True))
    if not status:
        raise RuntimeError("UFC 333 official round-stat export incomplete/mismatched: see availability.json")


if __name__ == "__main__":
    main()
