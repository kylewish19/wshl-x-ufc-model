"""Finish v1 regression: role symmetry, leakage, six-class integrity, no bet gate."""
import numpy as np
import pytest

from wshlx_ufc.finish_v1_research import (
    METHODS, method_features, training_rows, prior_win_probability,
    coherent_six, score_six, HierarchicalFinish, MultinomialFinish,
    NonlinearFinish, train_candidate_family, predict_family,
)

def fighter(a=5,b=2):
    return {
        "bout_id":"x", "event_date":"2023-01-01",
        "feature_as_of_exclusive":"2023-01-01",
        "fighter_a":"First","fighter_b":"Second",
        "a_prior_ufc_bouts":a,"b_prior_ufc_bouts":b,
        "a_ufc_prior_bouts":a,"b_ufc_prior_bouts":b,
        "a_ufc_prior_wins":a//2,"b_ufc_prior_wins":b//2,
        "a_own_sub_attempts_per15":1.5,"b_own_sub_attempts_per15":.2,
        "a_own_knockdowns_per15":.5,"b_own_knockdowns_per15":.1,
        "a_ufc_elo_pre":1530,"b_ufc_elo_pre":1450,
        "a_takedown_defense_rate_shrunk":.75,
        "b_takedown_defense_rate_shrunk":.55,
        "a_submission_threat_nonloss_rate":.9,
        "b_submission_threat_nonloss_rate":.5,
        "a_stats_coverage":.8,"b_stats_coverage":.6,
    }

def outcome(f,method="SUB",a_win=1,status="DECISIVE"):
    return {"bout_id":f["bout_id"],"result_status":status,
            "label_method":method,"label_a_win":a_win}

def test_past_only_features_are_fighter_role_symmetric_not_name_order():
    f=fighter(7,2)
    swapped={**f}
    for k in list(f):
        if k.startswith("a_"):
            swapped["b_"+k[2:]]=f[k]
        if k.startswith("b_"):
            swapped["a_"+k[2:]]=f[k]
    assert np.array_equal(method_features(f,"a"),method_features(swapped,"b"))
    assert np.array_equal(method_features(f,"b"),method_features(swapped,"a"))
    assert method_features(f,"a").shape==method_features(f,"b").shape
    assert method_features(f,"a").size>=30
    with pytest.raises(ValueError,match="side"):
        method_features(f,"winner_in_hindsight")

def test_missing_rates_are_encoded_with_missing_flags_not_fake_stats():
    f=fighter(0,0)
    for k in ("a_own_sub_attempts_per15","b_own_sub_attempts_per15"):
        f[k]=None
    x=method_features(f,"a")
    assert np.all(np.isfinite(x))
    assert x[-4]==1 and x[-3]==1
    assert x[-6]==1 and x[-5]==1
    assert prior_win_probability(f)==.5
    assert np.isfinite(method_features(f,"b")).all()

def test_winner_plus_method_exact_six_marginals_and_normalization():
    cond=np.array([[.2,.6,.2],[.7,.1,.2]])
    q=coherent_six(.75,cond)
    assert q.shape==(6,)
    assert q.sum()==pytest.approx(1)
    assert q[:3].sum()==pytest.approx(.75)
    assert q[3:].sum()==pytest.approx(.25)
    assert score_six(q,0,"SUB",p_a=.75)["exact"]==1
    assert score_six(q,1,"KO_TKO",p_a=.75)["exact"]==0
    with pytest.raises(ValueError):
        coherent_six(.75,[[.2,.6,.1],[.7,.1,.2]])
    with pytest.raises(ValueError):
        coherent_six(1.01,cond)
    with pytest.raises(ValueError):
        score_six(q,0,"UNSUPPORTED",p_a=.75)

def test_training_excludes_current_and_future_dates_and_draws():
    early=fighter()
    mid={**early,"bout_id":"mid","event_date":"2023-06-01","feature_as_of_exclusive":"2023-06-01"}
    late={**early,"bout_id":"late","event_date":"2024-04-01","feature_as_of_exclusive":"2024-04-01"}
    draw={**early,"bout_id":"draw","event_date":"2023-07-01","feature_as_of_exclusive":"2023-07-01"}
    X,y=training_rows([early,mid,late,draw],[
        outcome(early,"SUB"),outcome(mid,"KO_TKO",0),
        outcome(late,"DEC"),outcome(draw,status="DRAW",a_win=None),
    ],"2024-01-01")
    assert len(X)==len(y)==2
    assert set(y)=={"KO_TKO","SUB"}
    changed={**early,"feature_as_of_exclusive":"2023-01-02"}
    with pytest.raises(ValueError,match="Not as-of"):
        training_rows([changed],[outcome(early)],"2024-01-01")

def test_independent_models_use_both_candidate_fighter_sides():
    rng=np.random.default_rng(19)
    X=rng.normal(size=(160,38))
    y=np.array(["DEC"]*80+["KO_TKO"]*55+["SUB"]*25)
    for model in (HierarchicalFinish(),MultinomialFinish(),NonlinearFinish()):
        model.fit(X,y)
        pred=model.predict(X[:2])
        assert pred.shape==(2,3)
        assert np.all(np.isfinite(pred))
        assert np.all(pred>=0)
        assert np.allclose(pred.sum(axis=1),1)
    f=fighter()
    rows=[]
    labels=[]
    for i in range(160):
        g={**f,"bout_id":str(i),"event_date":"2022-01-01","feature_as_of_exclusive":"2022-01-01"}
        rows.append(g)
        labels.append(outcome(g,y[i],i%2))
    bundle=train_candidate_family(rows,labels,"2024-01-01")
    got=predict_family(f,bundle)
    assert set(got)=={"global_prior","hierarchical","multinomial","nonlinear"}
    for six in got.values():
        assert six.shape==(6,)
        assert np.allclose(six.sum(),1)
        assert six[:3].sum()==pytest.approx(prior_win_probability(f))

def test_zero_UFC_history_does_not_claim_high_confidence_from_finish_model():
    f=fighter(0,0)
    assert prior_win_probability(f)==.5
    # Actual approved betting posture is governed by the separate frozen
    # Stage A/B gates, never by predictions from this research module.
    assert not hasattr(HierarchicalFinish, "approve_wager")
