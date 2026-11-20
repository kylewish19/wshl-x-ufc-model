"""Leakage-safe *shadow-only* UFC strength-of-opposition feature builder.

Opponents are assigned an Elo-like pre-fight rating derived solely from UFC
bouts strictly before the current event day. For every previous opponent,
the fighter retains the opponent's rating AS OF THAT HISTORICAL MEETING,
not the opponent's final career/current rating (which would leak future form).

Do not mistake UFC-only Elo as full professional/regional opponent strength.
Unknown/debut opponents receive neutral 1500 ratings with uncertainty flags.
This module is research-only and is not wired into Reference, Historical,
Unified, original Stage A, FanDuel Stage B, or any betting decision.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd

from .historical_data import bout, col, normalize_events, outcome, txt

PRIOR_ELO = 1500.0
ELO_K = 24.0
SHRINK_N = 4.0


@dataclass
class FighterRecord:
    elo: float = PRIOR_ELO
    prior_bouts: int = 0
    prior_wins: int = 0
    prior_losses: int = 0
    prior_draws: int = 0
    opponents_at_meeting_pre_elo: list[float] = field(default_factory=list)
    defeated_opponents_at_meeting_pre_elo: list[float] = field(default_factory=list)

    def pre_fight_features(self) -> dict[str, float | int | bool]:
        n = self.prior_bouts
        w = self.prior_wins
        total = sum(self.opponents_at_meeting_pre_elo)
        beaten = sum(self.defeated_opponents_at_meeting_pre_elo)
        return {
            "ufc_prior_bouts": n,
            "ufc_prior_wins": w,
            "ufc_prior_losses": self.prior_losses,
            "ufc_prior_draws": self.prior_draws,
            "ufc_elo_pre": float(self.elo),
            "ufc_avg_opponent_elo_at_meeting_shrunk": float(
                (total + SHRINK_N * PRIOR_ELO) / (n + SHRINK_N)),
            "ufc_avg_beaten_opponent_elo_at_meeting_shrunk": float(
                (beaten + SHRINK_N * PRIOR_ELO) / (w + SHRINK_N)),
            "ufc_prior_opponents_recorded": n,
            "ufc_strength_uncertain": n < 5,
            "ufc_debutant": n == 0,
            "ufc_elo_not_regional_strength": True,
        }


def _date(x: object) -> date:
    d = pd.to_datetime(x,errors="raise")
    if pd.isna(d):
        raise ValueError("Missing event date")
    return d.date()


def _validate(fights: Sequence[Mapping]) -> list[dict]:
    """Target labels are retained only for AFTER-day Elo updates."""
    records = []
    seen = set()
    for fight in fights:
        when = _date(fight["date"])
        event = str(fight.get("event", "")).strip()
        a,b = str(fight["a"]).strip(),str(fight["b"]).strip()
        result = str(fight["outcome"]).upper().replace(" ","")
        if not (a and b and a!=b and event):
            raise ValueError("Invalid fighter / event identity")
        if result not in ("W/L","L/W","D/D"):
            raise ValueError("Invalid decided UFC result; NC should be skipped")
        key = (when,event,*sorted((a,b)))
        if key in seen:
            raise ValueError("Duplicated fight in history")
        seen.add(key)
        records.append({"date":when,"event":event,"a":a,"b":b,
                        "outcome":result})
    return sorted(records,key=lambda x:(x["date"],x["event"],x["a"],x["b"]))


def build_historical_opponent_quality(fights: Sequence[Mapping], *, query_date: str | None = None, query_bouts: Sequence[tuple[str, str]] = ()) -> list[dict]:
    """Derive each fight's pre-day snapshots, then update whole day afterward.

    Every fight on the same event DATE sees the identical state frozen before
    that date. This avoids intra-card leakage, duplicated results and accidental
    rating updates before earlier fights on the same night.
    """
    bouts = _validate(fights)
    state: defaultdict[str,FighterRecord] = defaultdict(FighterRecord)
    snapshots = []
    i = 0
    while i < len(bouts):
        d = bouts[i]["date"]
        batch = []
        while i < len(bouts) and bouts[i]["date"] == d:
            batch.append(bouts[i])
            i += 1
        frozen_pre_ratings = {}
        # Capture all pre-event features before seeing any outcome that day.
        for fight in batch:
            a,b = fight["a"],fight["b"]
            for name in (a,b):
                if name not in frozen_pre_ratings:
                    frozen_pre_ratings[name]=state[name].pre_fight_features()
            a_pre = dict(frozen_pre_ratings[a])
            b_pre = dict(frozen_pre_ratings[b])
            snapshots.append({
                "date":d.isoformat(),"event":fight["event"],
                "a":a,"b":b,
                "a_pre":a_pre,"b_pre":b_pre,
                "pre_a_elo_minus_b_elo":a_pre["ufc_elo_pre"]-b_pre["ufc_elo_pre"],
                "source_status":"UFC_RESULT_DERIVED_SHADOW_ONLY",
            })
        # Only now let this day update each fighter's rating and past-opponent
        # record. Opponent quality is stored at the time of the meeting.
        for fight in batch:
            a,b = fight["a"],fight["b"]
            pre_a=frozen_pre_ratings[a]["ufc_elo_pre"]
            pre_b=frozen_pre_ratings[b]["ufc_elo_pre"]
            e_a = 1/(1+10**((pre_b-pre_a)/400))
            result_a = {"W/L":1., "L/W":0., "D/D":0.5}[fight["outcome"]]
            delta=ELO_K*(result_a-e_a)
            state[a].elo += delta
            state[b].elo -= delta
            for name,opponent_pre,score in (
                (a,pre_b,result_a),(b,pre_a,1-result_a)):
                q=state[name]
                q.prior_bouts += 1
                q.opponents_at_meeting_pre_elo.append(float(opponent_pre))
                if score==1.0:
                    q.prior_wins += 1
                    q.defeated_opponents_at_meeting_pre_elo.append(
                        float(opponent_pre))
                elif score==0.0:
                    q.prior_losses += 1
                else:
                    q.prior_draws += 1
    if query_bouts:
        if query_date is None:
            raise ValueError("Prospective fighter queries require a strictly future date")
        future=_date(query_date)
        if bouts and future<=bouts[-1]["date"]:
            raise ValueError("Query must be after all completed source bouts")
        observed=set()
        for a,b in query_bouts:
            if not a or not b or a==b or a in observed or b in observed:
                raise ValueError("Duplicate or invalid fighter prospective query")
            observed.update((a,b))
            pa=state[a].pre_fight_features()
            pb=state[b].pre_fight_features()
            snapshots.append({
                "date":future.isoformat(),"event":"__PREFIGHT_QUERY_NO_RESULTS__",
                "a":a,"b":b,"a_pre":dict(pa),"b_pre":dict(pb),
                "pre_a_elo_minus_b_elo":pa["ufc_elo_pre"]-pb["ufc_elo_pre"],
                "source_status":"QUERY_ONLY_NO_RESULTS_OR_FUTURE_FEATURES",
                "query_only":True,
            })
    return snapshots


def load_ufcstats_results(events_csv: Path, results_csv: Path,
                          *, as_of_exclusive: str | None = None) -> list[dict]:
    """UFCStats-compatible archived CSV adapter, no network or model edits."""
    events = pd.read_csv(events_csv,low_memory=False)
    results = pd.read_csv(results_csv,low_memory=False)
    norm=normalize_events(events)
    date_by_event={str(x.event).strip():_date(x.date)
                   for x in norm.itertuples(index=False)}
    event_c,bout_c,result_c=(col(results,k) for k in ("EVENT","BOUT","OUTCOME"))
    if None in (event_c,bout_c,result_c):
        raise ValueError("UFCStats results require EVENT/BOUT/OUTCOME columns")
    history=[]
    cutoff = _date(as_of_exclusive) if as_of_exclusive is not None else None
    for row in results.to_dict("records"):
        ev=txt(row[event_c])
        when=date_by_event.get(ev)
        if when is None:
            continue
        if cutoff is not None and when >= cutoff:
            continue
        pair=bout(row[bout_c])
        result=outcome(row[result_c])
        if pair is None or result is None:
            continue
        if result not in (("W","L"),("L","W"),("D","D")):
            # NC and invalid outcomes never update a rating.
            continue
        history.append({
            "date":when.isoformat(),"event":ev,
            "a":pair[0],"b":pair[1],
            "outcome":"/".join(result),
        })
    return _validate(history)


def fit_as_of(fights: Sequence[Mapping], *, prediction_date: str) -> list[dict]:
    """Strict cutoff guard for building an upcoming event's prior-only history."""
    limit = _date(prediction_date)
    rows=_validate(fights)
    if any(x["date"] >= limit for x in rows):
        raise ValueError("Same-date or future fight result must not enter features")
    return build_historical_opponent_quality(rows)
