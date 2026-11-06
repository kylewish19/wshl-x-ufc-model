"""Import 2026-10-31 UFC Vegas 123 as a retrospective *unpicked* event.

DO NOT attribute official winner/method/bet predictions to this event: the owner
was away and no UFC Vegas 123 Stage A snapshot was frozen before the fights.
Official outcomes serve as an external data-integrity cross-check, NOT as picks.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/raw/ufcvegas123_2026-10-31"
UPSTREAM_REPO = "Greco1899/scrape_ufc_stats"
# First available post-October-31 weekly UFCStats scrape
UPSTREAM_COMMIT = "3d4886d222e72be2c5336b49b98b721f5103d949"
FILES = [
    "ufc_event_details.csv",
    "ufc_fight_details.csv",
    "ufc_fight_results.csv",
    "ufc_fight_stats.csv",
    "ufc_fighter_details.csv",
    "ufc_fighter_tott.csv",
]

# Result/time reference: UFC October 31 event results, prelims and scorecards.
# In bout-name order, outcomes are verified AFTER the event, not used as model input.
OFFICIAL_RESULTS = [
    ("Renato Moicano", "Tom Nolan", "Tom Nolan", "KO", 3, "1:28"),
    ("Randy Brown", "Jacobe Smith", "Jacobe Smith", "DEC", 3, "5:00"),
    ("Ode' Osbourne", "Cody Durden", "Cody Durden", "DEC", 3, "5:00"),
    ("Yana Santos", "Luana Santos", "Luana Santos", "DEC", 3, "5:00"),
    ("Jean-Paul Lebosnoyani", "Farman Hasanov", "Jean-Paul Lebosnoyani", "KO", 3, "2:11"),
    ("Francis Marshall", "Dakota Hope", "Dakota Hope", "DEC", 3, "5:00"),
    ("Rodrigo Sezinando", "Theodor Berggren", "Rodrigo Sezinando", "KO", 2, "5:00"),
    ("Julian Erosa", "JeongYeong Lee", "Julian Erosa", "KO", 1, "1:31"),
    ("Zachary Reese", "Mickey Gall", "Zachary Reese", "DEC", 3, "5:00"),
    ("Nick Klein", "Joe Kropschot", "Joe Kropschot", "SUB", 2, "1:25"),
    ("Talita Alencar", "Piera Rodriguez", "Piera Rodriguez", "DEC", 3, "5:00"),
    ("Lucia Szabova", "Tainara Lisboa", "Lucia Szabova", "KO", 3, "3:20"),
]
EVENT_SOURCES = [
    "https://www.ufc.com/event/ufc-fight-night-october-31-2026",
    "https://www.ufc.com/news/ufc-fight-night-moicano-vs-nolan-results",
    "https://www.ufc.com/index.php/news/ufc-fight-night-moicano-vs-nolan-prelim-results",
    "https://www.ufc.com/news/ufc-fight-night-moicano-vs-nolan-official-scorecards",
]


def norm(s: object) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = "".join(re.findall("[a-z0-9]+", s.casefold()))
    # UFCStats may list the same fighter as Joseph or Joe.
    if s == "josephkropschot":
        return "joekropschot"
    return s


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def event_match(label: object) -> bool:
    s = str(label or "").casefold()
    return "moicano" in s and "nolan" in s and "ufc fight night" in s


def outclass(s: object) -> str:
    s = str(s).casefold().strip()
    if "dec" in s:
        return "DEC"
    if "sub" in s:
        return "SUB"
    if "ko" in s or "tko" in s:
        return "KO"
    return "OTHER"


def split_bout(bout: object) -> list[str]:
    return re.split(r"\s+vs\.?\s+", str(bout).strip(), maxsplit=1, flags=re.I)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = {}
    for name in FILES:
        u = f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{name}"
        p = OUT / name
        urllib.request.urlretrieve(u, p)
        receipt[name] = {"url": u, "sha256": sha256(p), "bytes": p.stat().st_size}

    inputs = [
        ("ufc_event_details.csv", "ufcvegas123_event_details.csv"),
        ("ufc_fight_details.csv", "ufcvegas123_fight_details.csv"),
        ("ufc_fight_results.csv", "ufcvegas123_fight_results.csv"),
        ("ufc_fight_stats.csv", "ufcvegas123_fight_stats.csv"),
    ]
    subsets = {}
    for source, name in inputs:
        df = pd.read_csv(OUT / source)
        if "EVENT" not in df.columns:
            raise RuntimeError(f"{source} missing EVENT")
        filtered = df.loc[df["EVENT"].map(event_match)].copy()
        filtered.to_csv(OUT / name, index=False)
        subsets[source] = filtered

    events, details, results, stats = (subsets[x[0]] for x in inputs)
    expected = {frozenset([norm(a), norm(b)]): {
        "bout": f"{a} vs {b}", "winner": winner,
        "method_class": method, "round": rnd, "time": clock,
    } for a, b, winner, method, rnd, clock in OFFICIAL_RESULTS}
    if len(expected) != 12:
        raise RuntimeError("Official UFC source list must have 12 distinct pairs")
    issues = []
    resolved = []
    round_rows_expected = 0
    seen_pairs = set()
    for _, r in results.iterrows():
        bout = str(r["BOUT"])
        fighters = split_bout(bout)
        if len(fighters) != 2:
            issues.append({"bout": bout, "issue": "cannot parse fighter pair"})
            continue
        pair = frozenset([norm(n) for n in fighters])
        exp = expected.get(pair)
        if exp is None:
            issues.append({"bout": bout, "issue": "not in official card"})
            continue
        if pair in seen_pairs:
            issues.append({"bout": bout, "issue": "duplicate bout"})
            continue
        seen_pairs.add(pair)
        outcome = str(r["OUTCOME"]).strip().upper()
        if outcome not in ("W/L", "L/W"):
            issues.append({"bout": bout, "issue": f"nondecisive outcome: {outcome}"})
            continue
        winner = fighters[0] if outcome == "W/L" else fighters[1]
        parsed_method = outclass(r["METHOD"])
        round_n = int(r["ROUND"])
        observed_clock = str(r["TIME"]).strip()
        if (
            norm(winner) != norm(exp["winner"])
            or parsed_method != exp["method_class"]
            or round_n != exp["round"]
            or observed_clock != exp["time"]
        ):
            issues.append({
                "bout": bout, "issue": "canonical source outcome differs from UFC verification",
                "upstream": {"winner": winner, "method": str(r["METHOD"]), "round": round_n, "time": observed_clock},
                "verified": exp,
            })
        round_rows_expected += round_n * 2
        resolved.append({
            "bout": bout, "winner": winner, "method_source": str(r["METHOD"]).strip(),
            "method_class": parsed_method, "round": round_n, "time": observed_clock,
            "details": str(r.get("DETAILS", "")).strip(),
            "ufcstats_fight_url": str(r.get("URL", "")).strip(),
            "special_stoppage": "doctor" in str(r["METHOD"]).casefold()
                                 or "doctor" in str(r.get("DETAILS", "")).casefold()
                                 or "cut" in str(r.get("DETAILS", "")).casefold(),
        })
    all_bouts = {key: {norm(x) for x in df["BOUT"].astype(str)} for key, df in (
        ("details", details), ("results", results), ("stats", stats)
    )}
    dupes = []
    if {"BOUT", "FIGHTER", "ROUND"}.issubset(stats):
        dup = stats.duplicated(subset=["BOUT", "ROUND", "FIGHTER"], keep=False)
        dupes = stats.loc[dup, ["BOUT", "ROUND", "FIGHTER"]].astype(str).to_dict("records")
    # Check that each statistics row corresponds to one of the 12 result bouts
    valid = bool(
        len(events) == 1 and len(results) == len(details) == 12
        and len(all_bouts["stats"]) == 12 and len(stats) == round_rows_expected
        and len(seen_pairs) == 12 and seen_pairs == set(expected)
        and all_bouts["details"] == all_bouts["results"] == all_bouts["stats"]
        and not issues and not dupes
    )
    outcome_distribution = {m: sum(x["method_class"] == m for x in resolved) for m in ("KO", "SUB", "DEC")}
    audit = {
        "record_type": "RETROSPECTIVE_OUTCOME_ONLY_NO_OFFICIAL_STAGE_A_OR_STAGE_B",
        "event_date": "2026-10-31",
        "event": "UFC Fight Night: Moicano vs Nolan (UFC Vegas 123)",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "upstream_repo": UPSTREAM_REPO, "upstream_commit": UPSTREAM_COMMIT,
        "event_rows": len(events), "unique_result_bouts": len(all_bouts["results"]),
        "unique_detail_bouts": len(all_bouts["details"]),
        "unique_stat_bouts": len(all_bouts["stats"]),
        "fighter_round_stat_rows": len(stats),
        "expected_round_stat_rows_from_results": round_rows_expected,
        "integrity_issues": issues, "round_key_duplicates": dupes,
        "missing_stat_bouts": sorted(all_bouts["results"] - all_bouts["stats"]),
        "result_methods": outcome_distribution,
        "full_card_stats_available": valid,
        "official_results": resolved, "receipt": receipt,
        "official_crosscheck_sources": EVENT_SOURCES,
        "governance": {
            "official_stage_a_frozen_before_event": False,
            "official_stage_b_fanduel_frozen_before_event": False,
            "count_as_official_prediction_record": False,
            "prospective_win_rate_unaffected": True,
            "use_after_event_for_future_training": True,
        },
    }
    (OUT / "availability.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "valid": valid, "bouts": len(all_bouts["results"]),
        "fighter_round_rows": len(stats), "expected_rows": round_rows_expected,
        "method_distribution": outcome_distribution, "issues": issues,
    }, indent=2))
    if not valid:
        raise RuntimeError("UFC Vegas123 full statistics failed validation; check availability.json")


if __name__ == "__main__":
    main()
