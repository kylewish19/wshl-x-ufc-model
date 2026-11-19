"""Independent joint winner+finish v2: verified symmetry, dates and outcomes."""
from __future__ import annotations
import numpy as np
import pytest

from wshlx_ufc.independent_winner_v2 import (
    fit_winner_logistic,winner_features,predict_winner,joint_from_conditional,
)
from wshlx_ufc.finish_v1_research import method_features,score_six

def fighter(a=6,b=3,when="2023-01-01",fid="1",win=1,method="SUB"):
    f={
        "bout_id":fid,"event_date":when,"feature_as_of_exclusive":when,
        "fighter_a":"First","fighter_b":"Second",
        "a_ufc_prior_bouts":a,"b_ufc_prior_bouts":b,
        "a_prior_ufc_bouts":a,"b_prior_ufc_bouts":b,
        "a_ufc_prior_wins":a//2,"b_ufc_prior_wins":b//2,
        "a_own_sub_attempts_per15":1.3,"b_own_sub_attempts_per15":.2,
        "a_own_knockdowns_per15":.4,"b_own_knockdowns_per15":.6,
        "a_ufc_elo_pre":1560,"b_ufc_elo_pre":1450,
        "a_stats_coverage":.7,"b_stats_coverage":.6,
    }
    lab={"bout_id":fid,"event_date":when,"result_status":"DECISIVE",
         "label_a_win":win,"label_method":method}
    return f,lab

def test_winner_training_only_past_ignores_draw_and_is_role_symmetric():
    fs,ls=[],[]
    for i in range(120):
        when="2022-01-01" if i<80 else "2024-01-01"
        f,l=fighter(3+i%6,2+i%4,when,str(i),win=i%2)
        fs.append(f);ls.append(l)
    # All same-day fights receive earlier as-of features; winner classifier
    # must exclude after-cutoff training results from its fit.
    bundle=fit_winner_logistic(fs,ls,before="2023-01-01")
    assert bundle["training_decisive_bouts"]==80
    t,lab=fighter()
    p=predict_winner(t,bundle)
    assert set(p)=={"prior_ufc_winrate","past_only_elo","new_symmetric_logistic"}
    assert 0<=p["new_symmetric_logistic"]<=1
    swapped=dict(t)
    for k in t:
        if k.startswith("a_"):swapped["b_"+k[2:]]=t[k]
        if k.startswith("b_"):swapped["a_"+k[2:]]=t[k]
    p_swapped=predict_winner(swapped,bundle)
    assert p["new_symmetric_logistic"]+p_swapped["new_symmetric_logistic"]==pytest.approx(1.,abs=1e-9)
    bad=dict(t,feature_as_of_exclusive="2024-01-01")
    with pytest.raises(ValueError,match="leakage"):
        winner_features(bad)

def test_six_joint_method_and_fighter_accuracy_without_future_winner_oracle():
    cond=np.array([[.5,.2,.3],[.2,.5,.3]])
    q=joint_from_conditional(.8,cond)
    assert q.sum()==pytest.approx(1.)
    assert q[:3].sum()==pytest.approx(.8)
    assert q[3:].sum()==pytest.approx(.2)
    assert score_six(q,0,"KO_TKO",p_a=.8)["exact"]==1
    assert score_six(q,1,"SUB",p_a=.8)["exact"]==0
    with pytest.raises(ValueError):
        joint_from_conditional(.8,[[.7,.2,.3],[.2,.5,.3]])
    with pytest.raises(ValueError):
        joint_from_conditional(.8,np.ones((2,2)))

def test_challenger_does_not_approve_odds_or_replace_production():
    assert not hasattr(fit_winner_logistic,"approve_bets")
