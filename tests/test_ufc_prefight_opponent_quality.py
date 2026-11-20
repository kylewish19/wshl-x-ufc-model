"""Chronological UFC opponent-quality schedule; no opponent career lookahead."""
import pytest
from pathlib import Path

from wshlx_ufc.prefight_opponent_quality import (
    PRIOR_ELO, build_historical_opponent_quality, fit_as_of,
    load_ufcstats_results,
)


def example():
    return [
        {"date":"2026-09-05","event":"Test A","a":"Alpha","b":"Beta","outcome":"W/L"},
        {"date":"2026-09-12","event":"Test B","a":"Charlie","b":"Alpha","outcome":"W/L"},
        {"date":"2026-09-12","event":"Test B","a":"Beta","b":"Delta","outcome":"L/W"},
        {"date":"2026-09-19","event":"Test C","a":"Alpha","b":"Delta","outcome":"W/L"},
    ]


def test_history_and_opponent_ratings_are_frozen_before_each_day():
    rows=build_historical_opponent_quality(example())
    assert len(rows)==4
    opening=rows[0]
    assert opening["a_pre"]["ufc_prior_bouts"]==0
    assert opening["b_pre"]["ufc_prior_bouts"]==0
    assert opening["a_pre"]["ufc_elo_pre"]==PRIOR_ELO
    assert opening["a_pre"]["ufc_avg_opponent_elo_at_meeting_shrunk"]==PRIOR_ELO
    day2=rows[1:3]
    alpha=next(x for x in day2 if "Alpha" in (x["a"],x["b"]))
    beta=next(x for x in day2 if "Beta" in (x["a"],x["b"]))
    alpha_pre=alpha["a_pre"] if alpha["a"]=="Alpha" else alpha["b_pre"]
    beta_pre=beta["a_pre"] if beta["a"]=="Beta" else beta["b_pre"]
    assert alpha_pre["ufc_elo_pre"]==PRIOR_ELO+12
    assert beta_pre["ufc_elo_pre"]==PRIOR_ELO-12
    assert alpha_pre["ufc_prior_wins"]==1
    assert beta_pre["ufc_prior_losses"]==1
    # Beta's next opponent does not retroactively change the rating of the
    # Beta that Alpha defeated on Sep5; strength tracked AT meeting time.
    assert alpha_pre["ufc_avg_beaten_opponent_elo_at_meeting_shrunk"]==PRIOR_ELO
    assert "winner" not in alpha and "method" not in alpha
    assert all(x["source_status"]=="UFC_RESULT_DERIVED_SHADOW_ONLY" for x in rows)


def test_same_day_result_modification_cannot_change_same_day_features():
    source=example()
    baseline=build_historical_opponent_quality(source)
    opposite=[dict(x) for x in source]
    opposite[1]["outcome"]="L/W"
    opposite[2]["outcome"]="W/L"
    modified=build_historical_opponent_quality(opposite)
    assert baseline[:3]==modified[:3]
    assert baseline[3]!=modified[3]
    # Current fight's result cannot be a current-fight input.
    last=[dict(x) for x in source]
    last[-1]["outcome"]="L/W"
    assert baseline==build_historical_opponent_quality(last)


def test_strict_prediction_cutoff_prevents_future_result_leakage():
    fights=example()
    with pytest.raises(ValueError,match="Same-date or future"):
        fit_as_of(fights,prediction_date="2026-09-19")
    safe=fit_as_of(fights[:3],prediction_date="2026-09-19")
    assert len(safe)==3
    assert safe[-1]["date"]<"2026-09-19"


def test_real_ufc_stats_csv_archive_only_historical_no_current_event_results():
    root=Path(__file__).resolve().parents[1]
    raw=root/"data/raw/ufcvegas124_2026-11-07"
    historical=load_ufcstats_results(
        raw/"ufc_event_details.csv",
        raw/"ufc_fight_results.csv",
        as_of_exclusive="2026-11-14",
    )
    assert len(historical)>3000
    assert all(x["date"].isoformat()<"2026-11-14" for x in historical)
    history=build_historical_opponent_quality(historical)
    assert len(history)==len(historical)
    assert all("winner" not in x and "fight_method" not in x for x in history)
    assert history[-1]["date"]<"2026-11-14"
    # Known fighters do have substantive pre-event opponent history.
    assert any(x["a_pre"]["ufc_prior_bouts"]>=10 for x in history)
    assert any(x["a_pre"]["ufc_strength_uncertain"] for x in history)


def test_non_decision_outcome_protected():
    fights=example()
    fights[0]["outcome"]="NC/NC"
    with pytest.raises(ValueError, match="Invalid decided"):
        build_historical_opponent_quality(fights)
