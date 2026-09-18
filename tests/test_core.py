import numpy as np
import pandas as pd
import pytest

from wshlx_ufc.features import assert_prefight_cutoff
from wshlx_ufc.grading import grade_multiclass
from wshlx_ufc.models import fighter_double_chance, joint_outcome_probabilities
from wshlx_ufc.simulation import simulate_joint_outcomes


def test_prefight_cutoff_rejects_leakage():
    frame = pd.DataFrame(
        {
            "event_date": ["2026-09-20T20:00:00Z"],
            "source_timestamp": ["2026-09-20T20:00:00Z"],
        }
    )
    with pytest.raises(ValueError):
        assert_prefight_cutoff(frame)


def test_joint_outcomes_sum_to_one():
    joint = joint_outcome_probabilities(
        0.62,
        {"KO": 0.30, "SUB": 0.20, "DEC": 0.50},
        {"KO": 0.45, "SUB": 0.10, "DEC": 0.45},
    )
    assert np.isclose(sum(joint.values()), 1.0)
    dc = fighter_double_chance(joint)
    assert all(0 <= x <= 1 for x in dc.values())


def test_seeded_simulation_is_reproducible():
    joint = {
        "A_KO": 0.20,
        "A_SUB": 0.10,
        "A_DEC": 0.25,
        "B_KO": 0.15,
        "B_SUB": 0.05,
        "B_DEC": 0.25,
    }
    a = simulate_joint_outcomes(joint, trials=10_000, seed=44)
    b = simulate_joint_outcomes(joint, trials=10_000, seed=44)
    assert a == b


def test_method_grade_tracks_sub_recall():
    classes = ["KO", "SUB", "DEC"]
    y = ["SUB", "KO", "DEC", "SUB"]
    p = np.array(
        [
            [0.10, 0.80, 0.10],
            [0.70, 0.15, 0.15],
            [0.10, 0.10, 0.80],
            [0.60, 0.20, 0.20],
        ]
    )
    grade = grade_multiclass(y, p, classes)
    assert grade.class_recall["SUB"] == 0.5
