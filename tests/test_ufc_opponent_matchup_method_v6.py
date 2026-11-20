"""Method v6 critical guards: opponent ordering, leakage, and exact scoring."""
import importlib.util
import sys
from pathlib import Path
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location(
    "wshlx_method_v6_under_test",ROOT/"tools/benchmark_opponent_matchup_method_v6.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fixture():
    f={"bout_id":"synthetic-fight","event_date":"2025-02-01",
       "feature_as_of_exclusive":"2025-02-01",
       "fighter_a":"Alpha","fighter_b":"Beta","event":"Synthetic"}
    # method_features requires 31 source fields - create keyspace matching
    # historical source resistance and Elo/quality schema, with 0-UFC.
    from wshlx_ufc.historical_feature_matrix import RESISTANCE,QUALITY
    for side in ("a","b"):
        for field in (*RESISTANCE,*QUALITY):
            f[f"{side}_{field}"]=None
        f[f"{side}_prior_ufc_bouts"]=0
        f[f"{side}_ufc_prior_bouts"]=0
    ra=np.array([0.,.5,.5,.5,.8,.1,.1,.2,.3,.5,.7,0.,0.,1.,1.,1.])
    rb=np.array([0.,.5,.5,.5,.1,.8,.1,.5,.2,.3,.7,0.,0.,1.,1.,1.])
    # Explicitly give the two fighters contrasting recent offense/defense.
    ua=np.full(19,.2); ub=np.full(19,.4)
    ua[6]=.8;ub[6]=.3
    regional={f["bout_id"]:(ra,rb,True)}
    recent={f["bout_id"]:(ua,ub)}
    return f,regional,recent

def test_prior_only_and_bilateral_features_are_ordered_and_finite():
    f,regional,recent=fixture()
    aa,bb,v=m.vectors(f,regional,recent)
    assert aa.shape==bb.shape==(115,) and v
    assert np.isfinite(aa).all() and np.isfinite(bb).all()
    # Base UFO method baseline and 16 own regional columns are identical to
    # earlier v5; the NEXT 16 MUST be the OPPONENT regional stats.
    assert np.allclose(aa[38:54],regional[f["bout_id"]][0])
    assert np.allclose(aa[54:70],regional[f["bout_id"]][1])
    assert np.allclose(bb[38:54],regional[f["bout_id"]][1])
    assert np.allclose(bb[54:70],regional[f["bout_id"]][0])
    assert np.allclose(aa[70:89],recent[f["bout_id"]][0])
    assert np.allclose(aa[89:108],recent[f["bout_id"]][1])
    assert aa[108]==pytest.approx(.8*.5)
    assert bb[108]==pytest.approx(.1*.2)
    assert not np.array_equal(aa,bb)

def test_current_day_label_does_not_enter_features():
    f,r,n=fixture()
    f["feature_as_of_exclusive"]="2025-02-02"
    with pytest.raises(ValueError,match="Date leakage"):
        m.vectors(f,r,n)

def test_coefficient_candidates_dont_tune_to_target_year():
    assert m.C_GRID==(.005,.025,.10,.35)
    assert m.FOLDS[0][3]=="2023-01-01"
    assert m.FOLDS[1][3]=="2024-01-01"
    assert m.FOLDS[2][3]=="2025-01-01"
    assert all(m.DIMS[k]==len(range(m.DIMS[k])) for k in m.DIMS)
    assert m.DIMS["regional_self_54"]==54
    assert m.DIMS["recent_both_108_tuned"]==108
    assert m.DIMS["opponent_interactions_115_tuned"]==115

def test_method_probability_order_and_own_winner_exact_six_labels():
    class Dummy:
        classes_=np.array(["DEC","SUB","KO_TKO"])
        def predict_proba(self,X):
            return np.tile([.25,.15,.60],(len(X),1))
    x=m.methods_ordered(Dummy(),np.zeros((2,115)))
    assert x.shape==(2,3)
    assert np.allclose(x[0],[.60,.15,.25])
    from wshlx_ufc.finish_v1_research import coherent_six,score_six
    q=coherent_six(.7,x)
    assert score_six(q,0,"KO_TKO",p_a=.7)["exact"]==1
    assert score_six(q,0,"SUB",p_a=.7)["exact"]==0
    assert score_six(q,1,"KO_TKO",p_a=.7)["exact"]==0
