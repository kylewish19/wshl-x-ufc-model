"""Direct six-class world MMA model: symmetric six labels and true exact grading."""
import importlib.util,sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location(
    "wshlx_direct_six_v7",ROOT/"tools/benchmark_worldwide_direct_six_v7.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fight(label_a,method):
    return {"result_status":"DECISIVE","label_a_win":label_a,"label_method":method}

def test_full_six_fighter_and_method_state_both_needed():
    assert [m.outcome(fight(1,met)) for met in ("KO_TKO","SUB","DEC")]==[0,1,2]
    assert [m.outcome(fight(0,met)) for met in ("KO_TKO","SUB","DEC")]==[3,4,5]
    with pytest.raises(ValueError):m.outcome({"result_status":"DRAW"})

def test_swapping_opponents_swaps_six_states_not_just_methods():
    assert m.SWAP.tolist()==[3,4,5,0,1,2]
    qa=np.array([.20,.10,.05,.15,.35,.15])
    assert np.allclose(qa[m.SWAP][m.SWAP],qa)
    for i in range(6):assert m.SWAP[m.SWAP[i]]==i

def test_global_six_maximum_may_differ_from_winner_marginal_decision():
    # No cherry-picked labels, both legitimate prespecified policies.
    q=np.array([.31,.02,.02,.30,.21,.14]) # A KO largest cell, B has 65% overall
    assert q.sum()==pytest.approx(1.)
    assert m.select_prediction(q,"global_best_cell")==0
    assert m.select_prediction(q,"winner_marginal_method")==3
    with pytest.raises(ValueError):m.select_prediction(q,"invented_policy")

def test_original_chronological_years_and_coefficient_training_gates():
    assert m.C_GRID==(.005,.025,.10)
    assert m.ARCHS==("direct_diff115","direct_paired230","direct_boost_diff115")
    assert m.FOLDS[0][3]=="2023-01-01"
    assert m.FOLDS[1][3]=="2024-01-01"
    assert m.FOLDS[2][3]=="2025-01-01"

def test_mirror_representation_shapes_for_two_fighters():
    row={"Xa":np.arange(115,dtype=float),"Xb":np.arange(115,dtype=float)+2}
    assert np.allclose(m.representation(row,"direct_diff115"),-m.representation(row,"direct_diff115",True))
    assert np.allclose(m.representation(row,"direct_paired230")[:115],row["Xa"])
    assert np.allclose(m.representation(row,"direct_paired230",True)[:115],row["Xb"])
    cases=[dict(row,truth=i) for i in range(6)]
    X,y=m.create_training(cases,"direct_diff115")
    assert X.shape==(12,115)
    assert y.tolist()==[0,3,1,4,2,5,3,0,4,1,5,2]
    with pytest.raises(ValueError,match="Missing independent"):
        m.create_training([dict(row,truth=3)]*6,"direct_diff115")

def test_exact_outcome_grade_is_not_method_class_hit_alone():
    f={"event_date":"2025-04-12","event":"Synthetic","bout_id":"qq"}
    q=np.array([.20,.10,.05,.15,.35,.15])
    grade=m.grade_direct(f,fight(0,"SUB"),"direct_diff115","global_best_cell",q)
    assert grade["exact_hit"]==1 and grade["winner_hit"]==1
    g=m.grade_direct(f,fight(1,"SUB"),"direct_diff115","global_best_cell",q)
    assert g["exact_hit"]==0 and g["method_class_hit"]==1
    assert g["winner_hit"]==0

def test_floating_point_50_50_fighter_tie_cannot_turn_original_A_pick_into_B():
    # Exact A/B tie in the original winner head: A wins the deterministic
    # tie break in the original score_six function, regardless of whether
    # adding three conditional cells yields 0.49999999999999994.
    q=np.array([.2,.2,.1,.2,.2,.1],dtype=float)
    q[0]-=1e-16
    q[3]+=1e-16
    assert q.sum()==pytest.approx(1.0)
    assert m.select_prediction(q,"winner_marginal_method")<3
    f={"event_date":"2026-01-31","event":"Synthetic","bout_id":"tie"}
    b=m.grade_base(f,fight(0,"KO_TKO"),"factorized_v3plusv5",.5,
        np.array([[.5,.25,.25],[.5,.25,.25]]))
    assert b["winner_hit"]==0 and b["exact_hit"]==0
    assert b["p_a_win"]==.5
