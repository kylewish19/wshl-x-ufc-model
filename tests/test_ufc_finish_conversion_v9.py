"""Tests for past-only finishing-conversion features."""
from datetime import date
import numpy as np
import pytest
from wshlx_ufc.finish_conversion_v9 import state,observe,vectors,build_conversion,MIX_N,CONVERSION_N

def stats(kd=0,sub=0,td=0,ctrl=0):
    return {"kd":kd,"sub_att":sub,"td_landed":td,"ctrl_sec":ctrl}

def rec(day,a,b,res=("W","L"),method="KO_TKO",aa=None,bb=None):
    return {"date":date.fromisoformat(day),"event":"Test card","a":a,"b":b,
            "result":res,"method":method,"stats_a":aa,"stats_b":bb}

def test_offensive_conversion_and_sample_counts_respond_to_real_past_outcomes():
    s=state()
    observe(s,stats(kd=1),stats(),"W","KO_TKO")
    observe(s,stats(kd=1),stats(),"L","DEC")
    mix,con=vectors(s)
    assert mix.shape==(MIX_N,) and con.shape==(CONVERSION_N,)
    assert mix[:3].sum()==pytest.approx(1.)
    assert con[0]==pytest.approx((1+5*.5)/7)
    assert con[1]==pytest.approx(np.log1p(2))
    assert s["conversions"][("offense","kd")]==1

def test_missing_stats_does_not_count_as_no_knockdowns():
    s=state()
    observe(s,None,None,"W","SUB")
    mix,conv=vectors(s)
    assert s["outcome"][("W","SUB")]==1
    assert not s["opportunities"]
    assert np.all(conv[1::2]==0)

def test_current_and_same_day_results_are_never_features():
    rows=[
        rec("2025-01-01","A","B",aa=stats(kd=1),bb=stats()),
        rec("2025-01-01","A","C",("L","W"),"SUB",stats(),stats(sub=1)),
        rec("2025-01-02","A","D",aa=stats(kd=1),bb=stats()),
    ]
    out=build_conversion(rows)
    first=out[("2025-01-01","Test card","A","B")][2]
    second=out[("2025-01-01","Test card","A","C")][2]
    third=out[("2025-01-02","Test card","A","D")][2]
    assert all(np.array_equal(x,y) for x,y in zip(first,second))
    assert third[0][3]>0 and third[1][1]>0
    changed=[*rows[:2],{**rows[2],"result":("L","W"),"method":"DEC"}]
    assert all(np.array_equal(x,y) for x,y in zip(third,build_conversion(changed)[("2025-01-02","Test card","A","D")][2]))
