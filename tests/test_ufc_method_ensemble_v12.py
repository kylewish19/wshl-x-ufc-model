import numpy as np
import pytest
from wshlx_ufc.method_ensemble_v12 import fit,predict,blend,group,temper
from wshlx_ufc.finish_v1_research import coherent_six

def test_weight_and_winner_invariance():
    p=np.array([[[.6,.2,.2],[.1,.2,.7]],[[.2,.6,.2],[.7,.2,.1]]])
    rows=[{"p":p,"side":0,"method":0,"group":"g"} for i in range(100)]
    w,groups,t=fit(rows)
    assert w[0]>w[1]
    assert abs(w.sum()-1)<1e-8
    for q in predict(p,"unseen",(w,groups,t)).values():
        assert np.allclose(q.sum(axis=1),1)
        assert coherent_six(.63,q)[:3].sum()==pytest.approx(.63)
    assert np.allclose(predict(p,"unseen",(w,groups,t))["learned_group"],blend(p,w))
    assert np.allclose(temper(p,1),p)

def test_invalid_input_rejected():
    with pytest.raises(ValueError):blend(np.zeros((2,2,3)),[.5,.5])
    with pytest.raises(ValueError):blend(np.ones((2,2,3))/3,[1,1])

def test_group_limited_or_unknown():
    f={"a_prior_ufc_bouts":2,"b_prior_ufc_bouts":10}
    assert group(f)=="limited_UFC_history"
    f["a_prior_ufc_bouts"]=3
    assert group(f)=="unknown_activity"
