from datetime import date
import numpy as np
import pytest
from wshlx_ufc.round_method_v10 import (
    snapshot,build_round_history,strict_count,strict_pair,strict_time,N
)

def row(sig,sub=0,ctrl=0,td=0):
    return {"sig":(sig,50),"td":(td,5),"sub":sub,"ctrl":ctrl,"ground":(0,1)}

def bout(day, a,b,elapsed=900):
    return {"date":date.fromisoformat(day),"event":"test "+day,
            "a":a,"b":b,"elapsed_seconds":float(elapsed)}

def test_round_history_only_from_completed_prior_dates():
    r=[bout("2025-01-01","A","B"),bout("2025-01-01","A","C"),bout("2025-01-02","A","D")]
    key=("test 2025-01-01","A","B")
    stats={(key,"A",1):row(10,1,120,1),(key,"B",1):row(8),
           (key,"A",2):row(30,0,60),(key,"B",2):row(9)}
    out,audit=build_round_history(r,stats)
    a=out[("2025-01-01",*key)][2]
    b=out[("2025-01-01","test 2025-01-01","A","C")][2]
    c=out[("2025-01-02","test 2025-01-02","A","D")][2]
    assert np.array_equal(a,b)
    assert len(c)==N
    assert c[9]==pytest.approx(.4/5)
    assert c[2]>a[2]
    assert audit["bouts_with_first_two_full_rounds"]==1
    # Current fight rows can't change their own features.
    stats[(("test 2025-01-02","A","D"),"A",1)]=row(49,2)
    assert np.array_equal(c,build_round_history(r,stats)[0][("2025-01-02","test 2025-01-02","A","D")][2])

def test_partial_second_round_not_used_for_pace():
    r=[bout("2025-01-01","A","B",elapsed=400),bout("2025-01-02","A","D")]
    key=("test 2025-01-01","A","B")
    stats={(key,"A",1):row(10,1),(key,"B",1):row(8),
           (key,"A",2):row(30,0),(key,"B",2):row(9)}
    out,audit=build_round_history(r,stats)
    c=out[("2025-01-02","test 2025-01-02","A","D")][2]
    assert c[8]==0 and c[9]==0
    assert audit["bouts_with_first_two_full_rounds"]==0

def test_missing_counts_are_not_observed_zeros():
    assert strict_count("0.0")==0
    assert strict_count("--") is None
    assert strict_pair("4 of 2") is None
    assert strict_pair("0 of 0")== (0,0)
    assert strict_time("0:00")==0
    assert strict_time("--") is None
    z=row(1);z["sub"]=None
    assert snapshot([({1:z},{1:row(1)})])[2]==pytest.approx(.2)
