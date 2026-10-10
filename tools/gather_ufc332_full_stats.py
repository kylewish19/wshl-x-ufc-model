from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REPO = "Greco1899/scrape_ufc_stats"
UPSTREAM_COMMIT = "1ccacc5cd4f642bd2deb8b278405a0205791bfa3"
EVENT = "UFC 332: Silva vs. Wang"
OUT = ROOT / "data/raw/ufc332_2026-10-03"
FILES = [
    "ufc_event_details.csv",
    "ufc_fight_details.csv",
    "ufc_fight_results.csv",
    "ufc_fight_stats.csv",
    "ufc_fighter_details.csv",
    "ufc_fighter_tott.csv",
]


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
    fighter_details = pd.read_csv(OUT / "ufc_fighter_details.csv")
    tott = pd.read_csv(OUT / "ufc_fighter_tott.csv")

    er = events.loc[events["EVENT"].map(norm) == EVENT].copy()
    dr = details.loc[details["EVENT"].map(norm) == EVENT].copy()
    rr = results.loc[results["EVENT"].map(norm) == EVENT].copy()
    sr = stats.loc[stats["EVENT"].map(norm) == EVENT].copy()

    er.to_csv(OUT / "ufc332_event_details.csv", index=False)
    dr.to_csv(OUT / "ufc332_fight_details.csv", index=False)
    rr.to_csv(OUT / "ufc332_fight_results.csv", index=False)
    sr.to_csv(OUT / "ufc332_fight_stats.csv", index=False)

    result_bouts = set(rr["BOUT"].map(norm))
    detail_bouts = set(dr["BOUT"].map(norm))
    stat_bouts = set(sr["BOUT"].map(norm))

    # Same-name identity audit: the UFCStats mirror contains two Anthony Romero
    # records. Preserve the Oct. 3 debutant's stable ID explicitly so later
    # card builders cannot silently use the older lightweight's static profile.
    romero_details = fighter_details.loc[
        (fighter_details.get("FIRST", pd.Series(index=fighter_details.index, dtype=object)).astype(str).str.strip() == "Anthony")
        & (fighter_details.get("LAST", pd.Series(index=fighter_details.index, dtype=object)).astype(str).str.strip() == "Romero")
    ].copy()
    romero_tott = tott.loc[tott["FIGHTER"].astype(str).str.strip() == "Anthony Romero"].copy()

    identity_audit = {
        "anthony_romero_expected_fighter_url": "http://ufcstats.com/fighter-details/4419acb81e6f0ea4",
        "anthony_romero_detail_rows": int(len(romero_details)),
        "anthony_romero_detail_urls": sorted(romero_details.get("URL", pd.Series(dtype=str)).astype(str).tolist()),
        "anthony_romero_tott_rows": int(len(romero_tott)),
        "note": "Do not resolve same-name Anthony Romero identity by display name alone in future card state construction.",
    }

    payload = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "upstream_repo": UPSTREAM_REPO,
        "upstream_commit": UPSTREAM_COMMIT,
        "event": EVENT,
        "event_rows": int(len(er)),
        "fight_detail_rows": int(len(dr)),
        "result_rows": int(len(rr)),
        "unique_result_bouts": int(len(result_bouts)),
        "fight_stat_rows": int(len(sr)),
        "unique_stat_bouts": int(len(stat_bouts)),
        "missing_detail_bouts": sorted(result_bouts - detail_bouts),
        "missing_stat_bouts": sorted(result_bouts - stat_bouts),
        "full_card_stats_available": (
            len(er) == 1
            and len(result_bouts) == 14
            and len(detail_bouts) == 14
            and len(stat_bouts) == 14
            and len(sr) == 50
            and not (result_bouts - detail_bouts)
            and not (result_bouts - stat_bouts)
        ),
        "expected_round_stat_rows": 50,
        "identity_audit": identity_audit,
        "receipt": receipt,
    }
    (OUT / "availability.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
