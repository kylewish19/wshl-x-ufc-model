"""Finishing-method v5 must pick exact fighter+method, not class-only."""
import importlib.util,sys
from pathlib import Path
import numpy as np
import pytest

TOOLPATH=Path(__file__).resolve().parents[1]/"tools"
sys.path.insert(0,str(TOOLPATH))
spec=importlib.util.spec_from_file_location(
    "worldwide_method_v5_under_test",TOOLPATH/"benchmark_worldwide_method_v5.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fake():
    return {"event_date":"2025-05-01","event":"Fixture UFC","bout_id":"fixture1"}

def test_six_outcomes_require_both_winner_and_correct_method():
    c=np.array([[.5,.4,.1],[.1,.2,.7]],float)
    winner_correct=m.grade(fake(),{"label_a_win":1,"label_method":"KO_TKO"},
        "winner_v4_boost73","worldwide_MMA_multinomial54",.7,c)
    assert winner_correct["winner_hit"]==1 and winner_correct["exact_hit"]==1
    wrong_method=m.grade(fake(),{"label_a_win":1,"label_method":"SUB"},
        "winner_v4_boost73","worldwide_MMA_multinomial54",.7,c)
    assert wrong_method["winner_hit"]==1 and wrong_method["exact_hit"]==0
    assert wrong_method["winner_correct_method_wrong"]==1
    wrong_winner=m.grade(fake(),{"label_a_win":0,"label_method":"KO_TKO"},
        "winner_v4_boost73","worldwide_MMA_multinomial54",.7,c)
    assert wrong_winner["winner_hit"]==0 and wrong_winner["exact_hit"]==0

def test_conditional_multinomial_labels_no_global_sub_quota_or_planted_favorability():
    assert m.MODEL_TYPES==(
        "prior_UFC_only_multinomial38",
        "worldwide_MMA_multinomial54",
        "worldwide_MMA_hierarchical54")
    assert m.WINNERS==("winner_v4_boost73","winner_v3_logit57")
    assert "fix_submission_count" not in dir(m)
    with pytest.raises(ValueError):
        m.grade(fake(),{"label_a_win":1,"label_method":"SUB"},
            "winner_v4_boost73","worldwide_MMA_multinomial54",.6,
            np.ones((2,3)))
