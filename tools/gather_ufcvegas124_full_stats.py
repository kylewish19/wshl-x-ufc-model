"""Download pinned Nov 8 2026 UFCStats scraper CSVs and VERIFY Nov 7.

This script does NOT train/retune any model. It requires all 14 frozen
postfight result records plus each fighter's full per-round strike/wrestling
row before declaring full-card availability. No missing stats synthesized.
The upstream archive is a THIRD-PARTY scrape of UFCStats, and is labeled as
such, not falsely claimed to be fetched live from official UFCStats.
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

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"data/raw/ufcvegas124_2026-11-07"
VERIFIED=ROOT/"data/results/ufcvegas124_2026-11-07_verified_outcomes.json"
STAGE_A=ROOT/"data/locks/ufcvegas124_2026-11-07/stage_a_final_selection.json"
UPSTREAM_REPO="Greco1899/scrape_ufc_stats"
UPSTREAM_COMMIT="c742842f29466758fedc3906dbad28d6d320a8da"
EVENT="UFC Fight Night: Cortes Acosta vs. Walker"
FILES=(
    "ufc_event_details.csv",
    "ufc_fight_details.csv",
    "ufc_fight_results.csv",
    "ufc_fight_stats.csv",
    "ufc_fighter_details.csv",
    "ufc_fighter_tott.csv",
)
EXTRA_ALIASES={
    "josehenrique":"josesouza",
    "josehenriquesouza":"josesouza",
    "josehenriqueferreira":"josesouza",
}
EXPECTED_BOUTS=14
EXPECTED_FIGHTER_ROUND_ROWS=68  # 2 * sum(official finish rounds 1+3+2+1+3+3+3+3+3+2+3+1+3+3)


def sha(p:Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(value):
    s=unicodedata.normalize("NFKD",str(value or ""))
    s="".join(c for c in s if not unicodedata.combining(c))
    s="".join(re.findall(r"[a-z0-9]+",s.casefold()))
    return EXTRA_ALIASES.get(s,s)


def split_bout(label):
    return re.split(r"\s+vs\.?\s+",str(label).strip(),maxsplit=1,flags=re.I)


def pair(label):
    sides=split_bout(label)
    if len(sides)!=2 or norm(sides[0])==norm(sides[1]):
        raise ValueError(f"Cannot parse valid two-fighter bout name: {label!r}")
    return frozenset(norm(x) for x in sides)


def method(s):
    x=str(s).upper().strip()
    if "DEC" in x:return "DEC"
    if "SUB" in x:return "SUB"
    if "KO" in x:return "KO"
    return "OTHER"


def parse_round(x):
    m=re.fullmatch(r"\s*Round\s+(\d+)\s*",str(x),re.I)
    if not m:raise ValueError(f"Invalid UFCStats round label {x}")
    return int(m.group(1))


def parse_pair_stats(label):
    m=re.fullmatch(r"\s*(\d+)\s+of\s+(\d+)\s*",str(label))
    if not m:raise ValueError(f"Invalid landed-attempted value: {label!r}")
    a,b=map(int,m.groups())
    if a>b:raise ValueError(f"Impossible landed>attempted: {label!r}")
    return a,b


def clock(t):
    m=re.fullmatch(r"\s*(\d+):([0-5]\d)\s*",str(t))
    if not m:return None
    return int(m.group(1))*60+int(m.group(2))


def main():
    if DEST.exists() and (DEST/"availability.json").exists():
        raise RuntimeError("Existing source snapshot found; use new versioned path, do not overwrite")
    expected_file=json.loads(VERIFIED.read_text())
    frozen=json.loads(STAGE_A.read_text())
    if expected_file["event_date"]!="2026-11-07" or len(expected_file["fights"])!=14:
        raise RuntimeError("Verified independent Nov7 official outcome baseline missing")
    if not frozen["stage_a_frozen"] or frozen["odds_used"] is not False:
        raise RuntimeError("Frozen Stage A provenance missing")
    if len(frozen["fights"])!=14:
        raise RuntimeError("Pre-event Stage A bout count differs from official 14")
    expected={}
    for f,y in zip(frozen["fights"],expected_file["fights"]):
        key=frozenset((norm(f["a"]),norm(f["b"])))
        if y["winner"] not in (f["a"],f["b"]) or f["fight_no"]!=y["fight_no"] or key in expected:
            raise RuntimeError(f"Corrupt official/frozen pairing {f['fight_no']}")
        expected[key]={"fight_no":f["fight_no"],"winner":norm(y["winner"]),
                       "method":y["method"],"round":y["round"],"time":y["time"],
                       "scheduled_rounds":f["scheduled_rounds"],
                       "official_display_name":f'{f["a"]} vs {f["b"]}'}
    if len(expected)!=14 or sum(2*y["round"] for y in expected.values())!=EXPECTED_FIGHTER_ROUND_ROWS:
        raise RuntimeError("14 official bouts or 68 required fighter-round rows drifted")

    DEST.mkdir(parents=True,exist_ok=True)
    receipt={}
    for filename in FILES:
        url=f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{filename}"
        dest=DEST/filename
        urllib.request.urlretrieve(url,dest)
        if dest.stat().st_size<2000:
            raise RuntimeError(f"Upstream source CSV suspiciously short: {filename}")
        receipt[filename]={"url":url,"sha256":sha(dest),"bytes":dest.stat().st_size}

    subsets={}
    for original,short in (
        ("ufc_event_details.csv","ufcvegas124_event_details.csv"),
        ("ufc_fight_details.csv","ufcvegas124_fight_details.csv"),
        ("ufc_fight_results.csv","ufcvegas124_fight_results.csv"),
        ("ufc_fight_stats.csv","ufcvegas124_fight_stats.csv"),
    ):
        frame=pd.read_csv(DEST/original)
        if "EVENT" not in frame:
            raise RuntimeError(f"Upstream missing {original}.EVENT")
        keep=frame["EVENT"].map(lambda x:norm(x)==norm(EVENT)).fillna(False)
        subset=frame.loc[keep].copy()
        subset.to_csv(DEST/short,index=False)
        subsets[original]=subset

    event,detail,result,stat=[subsets[k] for k in ("ufc_event_details.csv","ufc_fight_details.csv","ufc_fight_results.csv","ufc_fight_stats.csv")]
    problems=[]
    methods={}
    verified_result_rows={}
    seen=set()
    for row in result.to_dict("records"):
        label=row["BOUT"]
        try:key=pair(label)
        except ValueError as e:problems.append(str(e));continue
        if key in seen:
            problems.append(f"Duplicated official result bout: {label}")
            continue
        seen.add(key)
        exp=expected.get(key)
        if exp is None:
            problems.append(f"Unmatched source UFCStats result bout: {label}, {sorted(key)}")
            continue
        sides=split_bout(label)
        outcome=str(row["OUTCOME"]).strip().upper()
        if outcome not in ("W/L","L/W"):
            problems.append(f"UFCStats no decisive W/L status: {label} {outcome}")
            continue
        winner=norm(sides[0] if outcome=="W/L" else sides[1])
        outcome_method=method(row["METHOD"])
        try:rnd=int(row["ROUND"])
        except Exception:rnd=-1
        tm=str(row["TIME"]).strip()
        if (winner,outcome_method,rnd,tm)!=(exp["winner"],exp["method"],exp["round"],exp["time"]):
            problems.append({"fight":label,"issue":"Official UFC outcome disagrees with upstream UFCStats",
                "observed":(winner,outcome_method,rnd,tm),
                "official":(exp["winner"],exp["method"],exp["round"],exp["time"])})
        verified_result_rows[exp["fight_no"]]={"fight":label,"source_winner":winner,
                "source_method":str(row["METHOD"]),"source_finish_round":rnd,
                "source_finish_time":tm,"ufcstats_fight_url":row.get("URL")}
        methods[outcome_method]=methods.get(outcome_method,0)+1

    detail_bouts=set()
    for b in detail.get("BOUT",pd.Series(dtype=object)):
        try:detail_bouts.add(pair(b))
        except ValueError as e:problems.append(str(e))
    stat_bouts=set()
    unique_fighter_round_keys=set()
    stat_by_fight={}
    stat_key_duplicates=[]
    col_required={"BOUT","FIGHTER","ROUND","KD","SIG.STR.","TOTAL STR.","TD","SUB.ATT","CTRL"}
    if col_required - set(stat):
        problems.append(f"Missing essential UFCStats columns: {sorted(col_required-set(stat))}")
    else:
        for row in stat.to_dict("records"):
            try:
                k=pair(row["BOUT"])
                side=norm(row["FIGHTER"])
                rnd=parse_round(row["ROUND"])
                if k not in expected or side not in k or rnd>expected[k]["round"]:
                    raise ValueError(f"Unknown fighter/bout/round {row['BOUT']} {row['FIGHTER']} R{rnd}")
                for key in ("SIG.STR.","TOTAL STR.","TD"):
                    parse_pair_stats(row[key])
                ctrl=clock(row["CTRL"])
                if ctrl is None or ctrl>300:
                    raise ValueError(f"Control time out of range: {row['CTRL']}")
                for key in ("KD","SUB.ATT"):
                    val=float(row[key])
                    if val<0 or int(val)!=val:
                        raise ValueError(f"Invalid knockdown/submission count {key}:{row[key]}")
                stat_bouts.add(k)
                triplet=(k,side,rnd)
                if triplet in unique_fighter_round_keys:
                    stat_key_duplicates.append((str(row["BOUT"]),str(row["FIGHTER"]),rnd))
                unique_fighter_round_keys.add(triplet)
                stat_by_fight.setdefault(expected[k]["fight_no"],0)
                stat_by_fight[expected[k]["fight_no"]]+=1
            except Exception as e:
                problems.append(str(e))
    result_bouts=seen
    missing_result=sorted([expected[k]["official_display_name"] for k in set(expected)-result_bouts])
    missing_details=sorted([expected[k]["official_display_name"] for k in set(expected)-detail_bouts])
    missing_stats=sorted([expected[k]["official_display_name"] for k in set(expected)-stat_bouts])
    expected_stats={k["fight_no"]:2*k["round"] for k in expected.values()}
    mismatch_stats=[{"fight_no":n,"observed":stat_by_fight.get(n,0),"expected":v}
                    for n,v in expected_stats.items() if stat_by_fight.get(n,0)!=v]
    if len(event)!=1 or len(result)!=14 or len(detail)!=14 or len(stat)!=68:
        problems.append(f"Source count mismatch: events={len(event)}, results={len(result)}, details={len(detail)}, stat rows={len(stat)}")
    if result_bouts!=set(expected) or detail_bouts!=set(expected) or stat_bouts!=set(expected):
        problems.append("Missing or unmatched official fighter-pair identities")
    if methods!={"KO":6,"SUB":1,"DEC":7}:
        problems.append(f"Observed finish distribution differs from official result: {methods}")
    if stat_key_duplicates:problems.append("Duplicated fighter-round stat keys")
    if mismatch_stats:problems.append("Incorrect row count for at least one fight")
    validation={
        "status":"UFCSTATS_ARCHIVED_SCRAPE_2026_11_08_FULL_CARD_VERIFIED" if not problems else "INVALID_UNVERIFIED_DO_NOT_TRAIN",
        "checked_at_utc":datetime.now(timezone.utc).isoformat(),
        "event_date":"2026-11-07","event":EVENT,
        "upstream_repo":UPSTREAM_REPO,"upstream_commit":UPSTREAM_COMMIT,
        "upstream_snapshot_recorded_at_utc":"2026-11-08T18:04:23Z",
        "source_classification":"Third-party pinned CSV scrape originally sourced from UFCStats.com; not independent real-time UFCStats site verification",
        "official_outcomes_file":str(VERIFIED.relative_to(ROOT)),
        "official_outcomes_sha256":sha(VERIFIED),
        "frozen_stage_a_file":str(STAGE_A.relative_to(ROOT)),
        "frozen_stage_a_sha256":sha(STAGE_A),
        "source_csv_files":receipt,
        "unique_event_rows":len(event),"unique_result_bouts":len(result_bouts),
        "unique_detail_bouts":len(detail_bouts),"unique_stat_bouts":len(stat_bouts),
        "fighter_round_stat_rows":len(stat),
        "fighter_bout_aggregates_expected":28,
        "expected_fighter_round_stat_rows":68,
        "validated_results":list(verified_result_rows.values()),
        "observed_finish_methods":methods,
        "missing_result_bouts":missing_result,
        "missing_detail_bouts":missing_details,
        "missing_stat_bouts":missing_stats,
        "fighter_round_key_duplicates":stat_key_duplicates,
        "fighter_round_count_mismatches":mismatch_stats,
        "validation_issues":problems,
        "stats_have_no_zero_filled_missing_rows":True,
        "full_card_stats_available":not problems,
        "future_only_training_admissible":not problems,
        "direct_outcome_feature_leakage_prohibited":True,
        "no_champion_promotion_from_ingestion":True,
    }
    (DEST/"availability.json").write_text(json.dumps(validation,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:validation[k] for k in (
        "status","upstream_commit","unique_result_bouts","unique_detail_bouts",
        "unique_stat_bouts","fighter_round_stat_rows",
        "expected_fighter_round_stat_rows","observed_finish_methods",
        "missing_stat_bouts","fighter_round_count_mismatches","validation_issues",
        "full_card_stats_available",
    )},indent=2))
    if problems:
        raise RuntimeError(f"Nov7 full-stat import FAILED integrity checks: {len(problems)} reasons; training blocked")


if __name__=="__main__":
    main()
