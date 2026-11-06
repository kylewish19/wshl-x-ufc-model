"""Cumulative independent tracking remains strictly forward from Nov 7."""
from __future__ import annotations

from copy import deepcopy

import pytest

from wshlx_ufc.two_tier_card import LONGSHOTS, BEST_BETS, grade_two_tier
from tools.summarize_ufc_two_tier_results import aggregate


def fake_grade(date="2026-11-07", event="UFC Example"):
    card = {
        "event_date": date, "event": event, "stage_a_sha256": "a"*64,
        "selected": {
            LONGSHOTS: [{
                "candidate_id": "long", "fight_key": "alice|bob",
                "market": "Alice ML", "american_odds": 200, "stake_units": 0.5
            }],
            BEST_BETS: [{
                "candidate_id": "best", "fight_key": "charlie|denise",
                "market": "Charlie ML", "american_odds": -125, "stake_units": 1.0
            }],
        }
    }
    g = grade_two_tier(card, {"long": "W", "best": "L"})
    g["stage_b_sha256"] = "b"*64
    return g


def test_cumulative_two_tiers_separate_and_combined_correct():
    a = fake_grade()
    b = fake_grade("2026-11-14", "UFC Another")
    b["categories"][LONGSHOTS]["record"].update({"W": 0, "L": 1})
    b["categories"][LONGSHOTS]["pnl_units"] = -.5
    b["combined"]["pnl_units"] -= 1.5
    out = aggregate([a, b])
    assert out["tracked_events"] == 2
    long, best = out["categories"][LONGSHOTS], out["categories"][BEST_BETS]
    assert long["W"] == 1 and long["L"] == 1
    assert long["pnl_units"] == pytest.approx(.5)
    assert long["roi"] == pytest.approx(.5)
    assert best["W"] == 0 and best["L"] == 2
    assert best["pnl_units"] == pytest.approx(-2.0)
    assert best["roi"] == pytest.approx(-1)
    assert out["combined"]["pnl_units"] == pytest.approx(-1.5)


def test_cumulative_no_fabricated_data_or_duplicate_event():
    result = aggregate([])
    assert result["tracked_events"] == 0
    assert result["categories"][LONGSHOTS]["hit_rate"] is None
    assert result["categories"][BEST_BETS]["roi"] is None
    a = fake_grade()
    with pytest.raises(ValueError):
        aggregate([a, deepcopy(a)])
    a.pop("stage_b_sha256")
    with pytest.raises(ValueError):
        aggregate([a])
