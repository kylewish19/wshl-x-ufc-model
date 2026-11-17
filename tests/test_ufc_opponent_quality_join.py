"""Verify the opponent-quality join never uses later results and reports coverage."""
import pandas as pd
import pytest

from wshlx_ufc.opponent_quality_join import (
    canonical, join_quality_to_conditional_method,
    load_and_join, FEATURE_NAMES,
)
from wshlx_ufc.prefight_opponent_quality import build_historical_opponent_quality


def test_normalized_fighter_identity_is_exact_not_fuzzy():
    assert canonical("João Silva")=="joaosilva"
    assert canonical("  João-Silva ")=="joaosilva"
    assert canonical("Joao Silva Jr.")!="joaosilva"
    assert canonical("Smith")!=canonical("Smyth")


def test_quality_join_uses_only_previous_dates_no_fight_result_features():
    prior=[
        {"date":"2026-08-01","event":"Old","a":"Jones","b":"Miller","outcome":"W/L"},
        {"date":"2026-08-08","event":"New","a":"Jones","b":"Smith","outcome":"W/L"},
    ]
    snapshots=build_historical_opponent_quality(prior)
    data=pd.DataFrame([{
        "event_date":"2026-08-08","event":"New",
        "fight_key":"2026-08-08|Jones vs. Smith","bout":"Jones vs. Smith",
        "fighter_a":"Jones","fighter_b":"Smith","winner":"Jones",
        "method":"KO","clean_actual_method":"KO",
    }])
    out,meta=join_quality_to_conditional_method(data,snapshots)
    assert meta["matched"]==1 and meta["missing"]==0
    assert out.iloc[0]["winner_prior_ufc_elo"]==1512
    assert out.iloc[0]["opponent_prior_ufc_elo"]==1500
    assert out.iloc[0]["quality_elo_gap"]==12
    assert out.iloc[0]["winner_prior_defeated_opponents_elo"]==1500
    assert all(pd.notna(out.iloc[0][col]) for col in FEATURE_NAMES)
    # Flip current fight's result; it may alter who our outcome-oriented
    # *research* case is, but cannot alter its pre-fight feature snapshots.
    flipped=[dict(x) for x in prior]
    flipped[1]["outcome"]="L/W"
    out2,meta2=join_quality_to_conditional_method(
        data,build_historical_opponent_quality(flipped)
    )
    for col in FEATURE_NAMES:
        assert out.iloc[0][col]==out2.iloc[0][col]


def test_real_hist_source_coverage_is_reported_not_guessed():
    enriched,meta=load_and_join()
    assert meta["method_rows"]==153
    assert meta["matched"]+meta["missing"]==153
    assert meta["coverage"]>=0.80,meta
    assert meta["source_status"]=="HISTORICAL_PRIOR_ONLY_OPPONENT_QUALITY_SHADOW"
    assert meta["not_directly_deployable_without_predicted_winner_orientation"]
    assert meta["model_or_wager_changed"] is False
    assert enriched.shape[0]==153
    for k in FEATURE_NAMES:
        assert k in enriched.columns
    assert int(enriched["quality_elo_gap"].notna().sum())==meta["matched"]


def test_missing_matchup_not_fabricated_as_weak_opposition():
    prior=[
        {"date":"2026-08-01","event":"Old","a":"Jones","b":"Miller","outcome":"W/L"}
    ]
    table=pd.DataFrame([{
        "event_date":"2026-08-08","fight_key":"new fight","bout":"Unknown vs. Fighter",
        "fighter_a":"Unknown","fighter_b":"Fighter","winner":"Unknown"
    }])
    enriched,metadata=join_quality_to_conditional_method(
        table,build_historical_opponent_quality(prior)
    )
    assert metadata["missing"]==1
    assert enriched["quality_elo_gap"].isna().all()
