from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REPO = "Greco1899/scrape_ufc_stats"
UPSTREAM_COMMIT = "a3c5452eee2f5bb4f5eae4ce958f0f23dd8863d8"
EVENT = "UFC 331: Van vs. Pantoja 2"
OUT = ROOT / "data/raw/ufc331_2026-09-19"

FILES = [
    "ufc_event_details.csv",
    "ufc_fight_results.csv",
    "ufc_fight_stats.csv",
    "ufc_fighter_tott.csv",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(filename: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / filename
    url = f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{filename}"
    urllib.request.urlretrieve(url, path)
    return path


def main():
    receipt = {}
    for name in FILES:
        p = download(name)
        receipt[name] = {
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
            "source": f"{UPSTREAM_REPO}@{UPSTREAM_COMMIT}",
        }

    events = pd.read_csv(OUT / "ufc_event_details.csv")
    results = pd.read_csv(OUT / "ufc_fight_results.csv")
    stats = pd.read_csv(OUT / "ufc_fight_stats.csv")

    event_rows = events.loc[events["EVENT"].astype(str).str.strip() == EVENT].copy()
    result_rows = results.loc[results["EVENT"].astype(str).str.strip() == EVENT].copy()
    stat_rows = stats.loc[stats["EVENT"].astype(str).str.strip() == EVENT].copy()

    # Save only UFC 331 slices for durable model provenance.
    event_rows.to_csv(OUT / "ufc331_event_details.csv", index=False)
    result_rows.to_csv(OUT / "ufc331_fight_results.csv", index=False)
    stat_rows.to_csv(OUT / "ufc331_fight_stats.csv", index=False)

    result_bouts = set(result_rows["BOUT"].astype(str).str.strip())
    stat_bouts = set(stat_rows["BOUT"].astype(str).str.strip())
    missing_stat_bouts = sorted(result_bouts - stat_bouts)

    summary = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "upstream_repo": UPSTREAM_REPO,
        "upstream_commit": UPSTREAM_COMMIT,
        "event": EVENT,
        "event_rows": int(len(event_rows)),
        "result_rows": int(len(result_rows)),
        "unique_result_bouts": int(len(result_bouts)),
        "fight_stat_rows": int(len(stat_rows)),
        "unique_stat_bouts": int(len(stat_bouts)),
        "missing_stat_bouts": missing_stat_bouts,
        "full_card_stats_available": (
            len(event_rows) == 1
            and len(result_bouts) == 12
            and len(stat_bouts) == 12
            and not missing_stat_bouts
        ),
        "receipt": receipt,
    }
    (OUT / "availability.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
