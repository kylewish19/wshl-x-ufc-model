"""Guard the pre-price November 7 UFC Vegas 124 odds-blind model freeze.

Includes explicit fail-closed evidence that independent method and timing
models disagree. Research coherence shadows must never overwrite Stage A.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from wshlx_ufc.coherence import (
    JOINT_KEYS, finish_probability, reconcile_joint_with_finish_marginal,
)

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "data/locks/ufcvegas124_2026-11-07"


def load(name: str):
    return json.loads((LOCK / name).read_text())


def digest(name: str):
    return hashlib.sha256((LOCK / name).read_bytes()).hexdigest()


def test_causal_pre_price_frozen_fourteen():
    raw = load("stage_a_model_raw_three_view.json")
    f = load("stage_a_final_selection.json")
    audit = load("stage_a_final_audit.json")
    assert len(raw["fights"]) == len(f["fights"]) == 14
    assert f["stage_a_frozen"] and audit["stage_a_frozen"]
    assert raw["odds_used"] is f["odds_used"] is audit["odds_used"] is False
    assert f["event_date"] == "2026-11-07"
    assert f["freeze_type"] == "STAGE_A_ODDS_BLIND_WEIGH_IN_VERIFICATION_PENDING"
    assert digest("stage_a_model_raw_three_view.json") == f["raw_model_sha256"] == audit["raw_model_sha256"]
    assert raw["model_state"]["fighter_history_through"] == "2026-10-31"
    assert raw["model_state"]["clean_feedback_rows"] == 139
    assert raw["model_state"]["historical_artifact_fitted_through"] == "2026-10-17"
    assert f["governance"]["current_retrained_shadows_fit_through"] == "2026-10-31"
    assert f["governance"]["model_reference_weights_fit_through"] == "2026-09-12"
    assert f["governance"]["pr_1_merged"] is False
    assert f["governance"]["challenger_promoted"] is False
    assert audit["side_flips_from_reference"] == 0
    assert audit["shadow_side_disagreements"] == [7, 14]
    assert audit["passes"] == [1, 4, 5, 7, 8, 9, 11, 14]
    assert audit["official_methods"] == []
    assert [f["stage_a_posture"] for f in f["fights"]].count("SIDE") == 2
    assert [f["stage_a_posture"] for f in f["fights"]].count("LEAN") == 4
    assert [f["stage_a_posture"] for f in f["fights"]].count("PASS") == 8
    assert len({(r["a"], r["b"]) for r in raw["fights"]}) == 14
    assert [r["scheduled_seconds"] for r in raw["fights"]] == [900] * 13 + [1500]


def test_all_raw_probability_outputs_consistent_with_own_model():
    raw = load("stage_a_model_raw_three_view.json")
    for row in raw["fights"]:
        for joint_name in ("joint_calibrated", "joint_baseline", "joint_residual"):
            p = row[joint_name]
            assert set(p) == set(JOINT_KEYS)
            assert all(0 <= v <= 1 for v in p.values())
            assert abs(sum(p.values()) - 1) < 1e-7
        for name in ("joint_calibrated_sim_10000",):
            sim = row[name]
            assert set(sim) == set(JOINT_KEYS)
            assert abs(sum(sim.values()) - 1) < 1e-7
        for name in ("timing_v033_direct", "timing_v033_sim_10000"):
            t = row[name]
            assert abs(t["GTD_YES"] + t["GTD_NO"] - 1) < 1e-8
            assert abs(t["OVER_2.5"] + t["UNDER_2.5"] - 1) < 1e-8
        assert row["oof_unified_shadow"]["status"].endswith("NOT_PROMOTED")
        assert abs(row["oof_unified_shadow"]["winner_p_a"]) <= 1.0
        assert row["sparse_ufc_evidence"] is (min(
            row["evidence_density"]["a_prior_ufc_bouts"],
            row["evidence_density"]["b_prior_ufc_bouts"]
        ) < 2)


def test_reconciliation_preserves_winner_and_timing_marginals_no_model_promotion():
    raw, f = load("stage_a_model_raw_three_view.json"), load("stage_a_final_selection.json")
    coh = load("stage_a_coherence_shadow.json")
    audit = load("stage_a_coherence_audit.json")
    assert coh["status"] == "SHADOW_ONLY_METHOD_TIMING_COHERENCE_RECONCILIATION_BEFORE_PRICING"
    assert audit["fights"] == len(coh["fights"]) == len(raw["fights"]) == 14
    assert coh["odds_used"] is False
    assert coh["policy"]["promoted_model"] is False
    assert coh["policy"]["new_official_method_picks"] == 0
    assert coh["policy"]["all_exact_method_market_prices_blocked"] is True
    assert coh["source_frozen_stage_a_sha256"] == digest("stage_a_final_selection.json")
    assert audit["severe_gap_count"] == 10
    assert audit["impossible_exact_fighter_finish_count"] == 2
    assert [x["fight_no"] for x in audit["impossible_cases"]] == [5, 10]
    for row, source, locked in zip(coh["fights"], raw["fights"], f["fights"]):
        original = row["current_joint_original_frozen_unchanged"]
        assert original == source["joint_calibrated"]
        target = source["timing_v033_direct"]["GTD_NO"]
        adjusted = row["candidate_joint_reconciled_shadow"]
        assert adjusted == reconcile_joint_with_finish_marginal(original, target)
        assert abs(finish_probability(adjusted) - target) < 1e-9
        assert abs(sum(adjusted[k] for k in ("A_KO", "A_SUB", "A_DEC")) -
                   source["winner_reference_p_a"]) < 1e-9
        assert locked["official_reference_pick"] == source["winner_reference_pick"]
        assert row["method_props_price_gate"] == "BLOCKED_UNTIL_PROSPECTIVE_COHERENCE_CALIBRATION"


def test_toy_ipf_handles_unbalanced_finish_and_keeps_conditional_ko_sub_ratio():
    original = {
        "A_KO": 0.41, "A_SUB": 0.09, "A_DEC": 0.10,
        "B_KO": 0.19, "B_SUB": 0.06, "B_DEC": 0.15,
    }
    target = 0.37
    out = reconcile_joint_with_finish_marginal(original, target)
    assert abs(sum(out.values()) - 1) < 1e-9
    assert math.isclose(out["A_KO"] + out["A_SUB"] + out["A_DEC"], 0.6, abs_tol=1e-9)
    assert math.isclose(out["B_KO"] + out["B_SUB"] + out["B_DEC"], 0.4, abs_tol=1e-9)
    assert math.isclose(finish_probability(out), target, abs_tol=1e-9)
    assert math.isclose(out["A_KO"] / (out["A_KO"] + out["A_SUB"]), .41 / .50, abs_tol=1e-9)
    assert math.isclose(out["B_KO"] / (out["B_KO"] + out["B_SUB"]), .19 / .25, abs_tol=1e-9)


def test_reject_invalid_reconciliation_inputs():
    p = {"A_KO": .3, "A_SUB": .1, "A_DEC": .1, "B_KO": .2, "B_SUB": .1, "B_DEC": .2}
    with pytest.raises(ValueError):
        reconcile_joint_with_finish_marginal(p, 1.1)
    with pytest.raises(ValueError):
        reconcile_joint_with_finish_marginal({**p, "B_DEC": -.1}, .3)
    with pytest.raises(ValueError):
        reconcile_joint_with_finish_marginal({**p, "B_DEC": .3}, .3)
