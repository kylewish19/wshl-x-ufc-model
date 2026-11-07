from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REPO = "Greco1899/scrape_ufc_stats"
UPSTREAM_COMMIT = "3e2f3db5751c14b5d4ea52e41921982ca23b9b23"
EVENT = "UFC Fight Night: Buckley vs. Malott"
OUT = ROOT / "data/raw/ufcedmonton_2026-10-17"
FILES = [
    "ufc_event_details.csv",
    "ufc_fight_details.csv",
    "ufc_fight_results.csv",
    "ufc_fight_stats.csv",
    "ufc_fighter_details.csv",
    "ufc_fighter_tott.csv",
]
EXPECTED_BOUTS = 13
EXPECTED_STAT_ROWS = 50


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, dict[str, object]] = {}

    for name in FILES:
        url = f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{name}"
        path = OUT / name
        urllib.request.urlretrieve(url, path)
        receipt[name] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "url": url,
        }

    events = pd.read_csv(OUT / "ufc_event_details.csv")
    details = pd.read_csv(OUT / "ufc_fight_details.csv")
    results = pd.read_csv(OUT / "ufc_fight_results.csv")
    stats = pd.read_csv(OUT / "ufc_fight_stats.csv")

    er = events.loc[events["EVENT"].map(norm) == EVENT].copy()
    dr = details.loc[details["EVENT"].map(norm) == EVENT].copy()
    rr = results.loc[results["EVENT"].map(norm) == EVENT].copy()
    sr = stats.loc[stats["EVENT"].map(norm) == EVENT].copy()

    er.to_csv(OUT / "ufcedmonton_event_details.csv", index=False)
    dr.to_csv(OUT / "ufcedmonton_fight_details.csv", index=False)
    rr.to_csv(OUT / "ufcedmonton_fight_results.csv", index=False)
    sr.to_csv(OUT / "ufcedmonton_fight_stats.csv", index=False)

    result_bouts = set(rr["BOUT"].map(norm))
    detail_bouts = set(dr["BOUT"].map(norm))
    stat_bouts = set(sr["BOUT"].map(norm))
    draw_rows = rr.loc[rr["OUTCOME"].map(norm).str.upper().eq("D/D")]
    decisive_rows = rr.loc[~rr["OUTCOME"].map(norm).str.upper().eq("D/D")]

    payload = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "upstream_repo": UPSTREAM_REPO,
        "upstream_commit": UPSTREAM_COMMIT,
        "event": EVENT,
        "event_rows": int(len(er)),
        "fight_detail_rows": int(len(dr)),
        "result_rows": int(len(rr)),
        "decisive_result_rows": int(len(decisive_rows)),
        "draw_result_rows": int(len(draw_rows)),
        "draw_bouts": sorted(draw_rows["BOUT"].map(norm).tolist()),
        "unique_result_bouts": int(len(result_bouts)),
        "fight_stat_rows": int(len(sr)),
        "unique_stat_bouts": int(len(stat_bouts)),
        "missing_detail_bouts": sorted(result_bouts - detail_bouts),
        "missing_stat_bouts": sorted(result_bouts - stat_bouts),
        "full_card_stats_available": (
            len(er) == 1
            and len(result_bouts) == EXPECTED_BOUTS
            and len(detail_bouts) == EXPECTED_BOUTS
            and len(stat_bouts) == EXPECTED_BOUTS
            and len(sr) == EXPECTED_STAT_ROWS
            and len(decisive_rows) == EXPECTED_BOUTS
            and len(draw_rows) == 0
            and not (result_bouts - detail_bouts)
            and not (result_bouts - stat_bouts)
        ),
        "expected_bouts": EXPECTED_BOUTS,
        "expected_round_stat_rows": EXPECTED_STAT_ROWS,
        "draw_policy": "No draw occurred on UFC Edmonton; all 13 bouts are decisive and eligible for the binary winner target after identity/result verification.",
        "receipt": receipt,
    }
    (OUT / "availability.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
