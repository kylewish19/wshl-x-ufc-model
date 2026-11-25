"""No-leakage, no-bet six-class method probability coherence research tests."""
import json
import math
from pathlib import Path

import pytest

from wshlx_ufc.joint_coherence_shadow import (
    JOINT_KEYS, ROOT, STORED, compute, project,
    six_way_scores, check_stored_experiment,
)

EVENTS = (
    "data/locks/ufc333_2026-10-24/stage_a_model_raw_three_view.json",
    "data/locks/ufcvegas124_2026-11-07/stage_a_model_raw_three_view.json",
    "data/locks/ufc334_2026-11-14/stage_a_model_raw_three_view.json",
)


def test_reconcile_all_41_fights_two_shadow_models_exactly_without_mutating_input():
    visited = 0
    for path in EVENTS:
        event = json.loads((ROOT/path).read_text())
        for fight in event["fights"]:
            for model in ("historical_shadow", "oof_unified_shadow"):
                obj = fight[model]
                raw = obj["joint_method"]
                before = raw.copy()
                a, t = obj["winner_p_a"], obj["timing_direct"]["GTD_NO"]
                winner = project(raw, winner_p_a=a)
                with_timing = project(raw, winner_p_a=a, finish_p=t)
                assert raw == before
                for result in (winner, with_timing):
                    assert set(result) == set(JOINT_KEYS)
                    assert math.isclose(sum(result.values()),1.0,abs_tol=1e-10)
                    assert all(0 < v < 1 for v in result.values())
                    assert math.isclose(
                        sum(result[k] for k in ("A_KO","A_SUB","A_DEC")),a,abs_tol=1e-10)
                    assert math.isclose(
                        result["A_KO"]/result["A_SUB"],raw["A_KO"]/raw["A_SUB"],rel_tol=1e-9)
                    assert math.isclose(
                        result["B_KO"]/result["B_SUB"],raw["B_KO"]/raw["B_SUB"],rel_tol=1e-9)
                assert math.isclose(
                    sum(with_timing[k] for k in ("A_KO","A_SUB","B_KO","B_SUB")),t,abs_tol=1e-10)
                visited += 1
    assert visited == 82


def test_three_event_probabilistic_holdout_matches_saved_report():
    fresh = check_stored_experiment()
    for model in ("historical","unified"):
        assert fresh[model]["fight_count"] == 41
        assert fresh[model]["all"]["original"]["n"] == 40
        orig = fresh[model]["all"]["original"]
        samewinner = fresh[model]["all"]["winner_aligned"]
        coherent = fresh[model]["all"]["winner_timing_aligned"]
        # Simply fixing winner's 2-class marginal is NOT a demonstrated improvement.
        assert samewinner["mean_brier"] > orig["mean_brier"]
        assert samewinner["mean_logloss"] > orig["mean_logloss"]
        # Timing+winner projection looks promising across 40, but this is
        # not a prospective promotion gate, and per-event scores are mixed.
        assert coherent["mean_brier"] < orig["mean_brier"]
        assert coherent["mean_logloss"] < orig["mean_logloss"]
    assert fresh["historical"]["event"]["ufc334_2026-11-14"]["winner_timing_aligned"]["mean_brier"] > (
        fresh["historical"]["event"]["ufc334_2026-11-14"]["original"]["mean_brier"]
    )
    stored = json.loads(STORED.read_text())
    assert stored["status"] == "POST_EVENT_CHALLENGER_NOT_PROMOTED"
    assert stored["scope"].startswith("Three previously frozen")
    assert stored["limitations"]
    assert stored["summary"]["historical"]["all"]["original"]["n"] == 40


def test_bad_probability_inputs_refused():
    j = {k:1/6 for k in JOINT_KEYS}
    for kwargs in (
        {"winner_p_a": 0.0}, {"winner_p_a": 1.0},
        {"winner_p_a": 0.5, "finish_p": 0.0},
        {"winner_p_a": 0.5, "finish_p": 1.0},
        {"winner_p_a": -0.1}, {"winner_p_a": float("nan")},
    ):
        with pytest.raises(ValueError):
            project(j, **kwargs)
    bad = dict(j)
    bad["A_DEC"] = -1.0
    with pytest.raises(ValueError):
        project(bad, winner_p_a=0.5)


def test_draw_is_not_a_six_way_method_outcome():
    with pytest.raises(ValueError):
        six_way_scores({k:1/6 for k in JOINT_KEYS},
                       fighter_side="A",method="DRAW")
