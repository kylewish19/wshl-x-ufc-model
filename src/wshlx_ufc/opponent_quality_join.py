"""Join frozen historical opponent-quality snapshots to retrospective method cases.

The join only retrieves two fighters' PRE-BOUT histories. Actual-winner
orientation is an explicitly labelled conditional-method research oracle;
an actual deployment must instead orient to the PREDICTED winning fighter.

Data source is the UFCStats-compatible archival results through Nov 7.
UFC334 provisional mirror stats are NOT used. Never silently fuzzy-match
fighters, supplement post-event features, or fill unknown opposition as bad.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd

from .prefight_opponent_quality import build_historical_opponent_quality, load_ufcstats_results

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data/raw/ufcvegas124_2026-11-07"
METHOD_ROWS = (
    ROOT / "reports/ufcvegas124_2026-11-07/full_stats/clean153_causal_method_inputs.csv"
)
FEATURE_NAMES = (
    "winner_prior_ufc_elo",
    "opponent_prior_ufc_elo",
    "quality_elo_gap",
    "winner_opponents_avg_prior_elo",
    "opponent_opponents_avg_prior_elo",
    "winner_prior_defeated_opponents_elo",
    "opponent_prior_defeated_opponents_elo",
    "winner_prior_schedule_strength_gap",
    "winner_elo_sample_uncertainty",
    "opponent_elo_sample_uncertainty",
)


def canonical(name: str) -> str:
    """Exact normalized identity; reject blank/ambiguous matches."""
    plain=unicodedata.normalize("NFKD",str(name))
    plain="".join(c for c in plain if not unicodedata.combining(c)).casefold()
    return re.sub(r"[^a-z0-9]+","",plain)


def _date(s: str) -> str:
    return str(s)[:10]


def matchup_index(snapshots: list[dict]) -> dict[tuple[str,tuple[str,str]],dict]:
    index={}
    for bout in snapshots:
        a,b=canonical(bout["a"]),canonical(bout["b"])
        if not a or not b or a==b:
            raise ValueError("Ambiguous archived fighter identity")
        key=(_date(bout["date"]),tuple(sorted((a,b))))
        if key in index:
            raise ValueError("Ambiguous same-day normalized matchup")
        index[key]=bout
    return index


def join_quality_to_conditional_method(
    method_rows: pd.DataFrame, prefight_snapshots: list[dict],
) -> tuple[pd.DataFrame,dict]:
    if method_rows["fight_key"].duplicated().any():
        raise ValueError("Historical method table has duplicate fights")
    index=matchup_index(prefight_snapshots)
    table=[]
    missing=[]
    for _,row in method_rows.iterrows():
        day=_date(row["event_date"])
        pa,pb=canonical(row["fighter_a"]),canonical(row["fighter_b"])
        key=(day,tuple(sorted((pa,pb))))
        snap=index.get(key)
        if snap is None:
            missing.append({"event_date":day,"bout":str(row["bout"])})
            table.append({k:np.nan for k in FEATURE_NAMES})
            continue
        a,b=canonical(snap["a"]),canonical(snap["b"])
        if {pa,pb}!={a,b}:
            raise ValueError("Name normalization collision")
        win=canonical(row["winner"])
        if win not in (a,b):
            raise ValueError("Method case winner not one of paired fighters")
        owner=snap["a_pre"] if win==a else snap["b_pre"]
        other=snap["b_pre"] if win==a else snap["a_pre"]
        table.append({
            "winner_prior_ufc_elo":owner["ufc_elo_pre"],
            "opponent_prior_ufc_elo":other["ufc_elo_pre"],
            "quality_elo_gap":owner["ufc_elo_pre"]-other["ufc_elo_pre"],
            "winner_opponents_avg_prior_elo":owner[
                "ufc_avg_opponent_elo_at_meeting_shrunk"],
            "opponent_opponents_avg_prior_elo":other[
                "ufc_avg_opponent_elo_at_meeting_shrunk"],
            "winner_prior_defeated_opponents_elo":owner[
                "ufc_avg_beaten_opponent_elo_at_meeting_shrunk"],
            "opponent_prior_defeated_opponents_elo":other[
                "ufc_avg_beaten_opponent_elo_at_meeting_shrunk"],
            "winner_prior_schedule_strength_gap":(
                owner["ufc_avg_opponent_elo_at_meeting_shrunk"]-
                other["ufc_avg_opponent_elo_at_meeting_shrunk"]),
            "winner_elo_sample_uncertainty":int(owner["ufc_strength_uncertain"]),
            "opponent_elo_sample_uncertainty":int(other["ufc_strength_uncertain"]),
        })
    enriched=method_rows.reset_index(drop=True).copy()
    quality=pd.DataFrame(table,columns=FEATURE_NAMES)
    for feature in FEATURE_NAMES:
        enriched[feature]=quality[feature].to_numpy()
    matched=len(method_rows)-len(missing)
    return enriched,{
        "method_rows":len(method_rows),
        "matched":matched,
        "missing":len(missing),
        "coverage":matched/len(method_rows) if len(method_rows) else 0.0,
        "missing_identity_cases":missing,
        "source_status":"HISTORICAL_PRIOR_ONLY_OPPONENT_QUALITY_SHADOW",
        "actual_winner_oracle_orientation":True,
        "not_directly_deployable_without_predicted_winner_orientation":True,
        "model_or_wager_changed":False,
    }


def load_and_join(*, prediction_history_exclusive: str = "2026-11-14"):
    history=load_ufcstats_results(
        ARCHIVE/"ufc_event_details.csv",
        ARCHIVE/"ufc_fight_results.csv",
        as_of_exclusive=prediction_history_exclusive,
    )
    snapshots=build_historical_opponent_quality(history)
    frame=pd.read_csv(METHOD_ROWS,low_memory=False)
    return join_quality_to_conditional_method(frame,snapshots)
