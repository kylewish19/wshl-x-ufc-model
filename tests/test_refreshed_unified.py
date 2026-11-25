"""Synthetic integration contract only: no real fight forecasts."""
import pytest
import numpy as np
from wshlx_ufc.refreshed_unified import compose
from wshlx_ufc.joint_coherence_shadow import JOINT_KEYS
def view(pa,q,h,n):
    return {"winner_p_a":pa,"joint_method":dict(zip(JOINT_KEYS,q)),"hazards_30s":[h]*n}
@pytest.mark.parametrize("seconds",[900,1500])
def test_refreshed_unified(seconds):
    r=view(.7,[.3,.1,.3,.1,.05,.15],.025,seconds//30)
    h=view(.4,[.1,.1,.2,.15,.1,.35],.035,seconds//30)
    out=compose(r,h,scheduled_seconds=seconds)
    assert out["weights_current"]=={"winner":.3,"method":.375,"timing":.75}
    assert out["reference"]["joint_method"]==r["joint_method"]
    assert out["historical"]["joint_method"]==h["joint_method"]
    for name in ("reference","historical","unified"):
        v=out[name]
        assert len(v["hazards_30s"])==seconds//30
        assert np.isclose(sum(v["joint_method"].values()),1)
        q=v["coherence"]["winner_and_timing_aligned"]
        assert np.isclose(sum(q[k] for k in JOINT_KEYS[:3]),v["winner_p_a"])
        assert np.isclose(q["A_DEC"]+q["B_DEC"],v["timing_direct"]["GTD_YES"])
        assert np.isclose(sum(v["timing_direct"][f"FINISH_ROUND_{i}"] for i in range(1,seconds//300+1))+v["timing_direct"]["GTD_YES"],1)
    assert .4<out["unified"]["winner_p_a"]<.7
    assert not out["bet_authorized"] and not out["model_promoted"]
def test_reject_incomplete_hazards():
    r=view(.6,[.2,.1,.3,.15,.05,.2],.02,30)
    h=view(.4,[.1,.1,.2,.15,.1,.35],.03,29)
    with pytest.raises(ValueError,match="hazard"):compose(r,h,scheduled_seconds=900)
def test_reject_invalid_probability():
    r=view(.6,[.2,.1,.3,.15,.05,.2],.02,30)
    h=view(.4,[.1,.1,.2,.15,.1,.35],.03,30)
    h["joint_method"]["A_KO"]=float("nan")
    with pytest.raises(ValueError,match="distribution"):compose(r,h,scheduled_seconds=900)
