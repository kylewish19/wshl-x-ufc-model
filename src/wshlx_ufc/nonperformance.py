from __future__ import annotations

from pathlib import Path
import pandas as pd


# Results that are official for records/betting but are not clean performance labels.
# The tuple values are normalized display strings as stored by the project parser.
KNOWN_NONPERFORMANCE_BOUTS = {
    (
        "UFC 323: Dvalishvili vs. Yan 2",
        "Alexandre Pantoja vs. Joshua Van",
    ): "injury_stoppage",
}


def normalize_text(value: object) -> str:
    return " ".join(str(value).strip().split())


def is_known_nonperformance_bout(event: object, bout: object) -> bool:
    key = (normalize_text(event), normalize_text(bout))
    return key in KNOWN_NONPERFORMANCE_BOUTS


def is_nonperformance_method(method: object) -> bool:
    s = normalize_text(method).upper()
    return (
        "DISQUAL" in s
        or s.startswith("DQ")
        or "NO CONTEST" in s
        or s in {"NC", "N/C"}
    )


def activity_dates_from_raw(raw_dir: Path) -> dict[str, pd.Timestamp]:
    """Return most recent official bout date for every fighter.

    Unlike performance history this intentionally includes DQ/NC/injury events,
    because those bouts still count as activity/layoff information.
    """
    events = pd.read_csv(raw_dir / "ufc_event_details.csv")
    results = pd.read_csv(raw_dir / "ufc_fight_results.csv")
    events["EVENT_KEY"] = events["EVENT"].map(normalize_text)
    events["EVENT_DATE"] = pd.to_datetime(events["DATE"], errors="coerce", utc=True)
    event_dates = dict(zip(events["EVENT_KEY"], events["EVENT_DATE"]))

    out: dict[str, pd.Timestamp] = {}
    for _, row in results.iterrows():
        date = event_dates.get(normalize_text(row.get("EVENT")))
        bout = normalize_text(row.get("BOUT"))
        if pd.isna(date) or " vs. " not in bout:
            continue
        a, b = bout.split(" vs. ", 1)
        for fighter in (a, b):
            key = "".join(ch.lower() for ch in fighter if ch.isalnum())
            prev = out.get(key)
            if prev is None or date > prev:
                out[key] = date
    return out


def apply_activity_recency(
    summary: dict[str, float],
    fighter_name: str,
    asof: pd.Timestamp,
    activity_dates: dict[str, pd.Timestamp],
) -> None:
    key = "".join(ch.lower() for ch in fighter_name if ch.isalnum())
    last = activity_dates.get(key)
    if last is None or last >= asof:
        return
    days = float((asof - last).total_seconds() / 86400.0)
    current = summary.get("days_since_last")
    if current is None or pd.isna(current) or days < float(current):
        summary["days_since_last"] = days
