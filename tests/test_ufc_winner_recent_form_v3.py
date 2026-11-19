"""Research-only UFC winner-v3 feature snapshot and antisymmetry tests."""
from datetime import date
import numpy as np
import pytest

from wshlx_ufc.winner_recent_form_v3 import (
    FIELDS,N,fighter_snapshot,construct_record_history,
)

def fake(when,a,b,result=("W","L"),a_sig=20.,b_sig=10.):
    def s(landed):
        return {"sig_landed":landed,"sig_attempted":landed*2.,
                "td_landed":2.,"td_attempted":4.,"kd":0.,"sub_att":0.}
    return {
        "date":when,"event":"Synthetic UFC Day","a":a,"b":b,
        "result":result,"elapsed_seconds":600.,"stats_a":s(a_sig),"stats_b":s(b_sig),
    }

def key(row):
    return (row["date"].isoformat(),row["event"],*sorted((row["a"],row["b"])))

def test_19_observed_features_with_debutants_and_missing_history():
    assert N==19 and len(FIELDS)==19
    empty=fighter_snapshot([],date(2026,6,1))
    assert empty.shape==(19,) and np.all(np.isfinite(empty))
    assert empty[17]==1. and empty[18]==1.
    assert empty[7]==.5 and empty[8]==.5
    record={
        "date":date(2025,3,1),"result":"W",
        "stat_available":True,"fight_minutes":10.,
        "sig_landed":30.,"sig_attempted":60.,"sig_absorbed":12.,"sig_faced":40.,
        "td_landed":2.,"td_attempted":4.,"td_absorbed":0.,"td_faced":1.,
        "kd":1.,"sub_att":2.,
    }
    existing=fighter_snapshot([record],date(2025,6,1))
    assert existing[17]==0. and existing[18]==0.
    assert existing[7]==pytest.approx((1+1)/(1+2))
    assert existing[9]>0
    assert existing[15]==np.log1p(1)
    with pytest.raises(ValueError,match="same-date or future"):
        fighter_snapshot([record],date(2025,3,1))

def test_all_same_calendar_date_fights_frozen_prior_to_result():
    day=date(2025,1,1)
    following=date(2025,2,1)
    rows=[
        fake(day,"Alice","Bob"),
        fake(day,"Alice","Charlie",result=("L","W")),
        fake(following,"Alice","Dave"),
    ]
    s=construct_record_history(rows,cutoff="2026-01-01")
    assert len(s)==3
    first=s[key(rows[0])]
    second=s[key(rows[1])]
    third=s[key(rows[2])]
    assert np.array_equal(first["a"],second["a"])  # no same-day updates
    assert first["a"][17]==1
    assert second["a"][17]==1
    assert third["a"][17]==0
    assert third["a"][0]==np.log1p(2)
    assert third["a"][7]==pytest.approx((1+1)/(2+2))
    assert third["a"][15]==pytest.approx(np.log1p(2))

def test_source_fighter_role_orientation_preserved_and_duplicate_guarded():
    row=fake(date(2025,1,2),"Zulu","Alpha")
    state=construct_record_history([row],cutoff="2026-01-01")
    assert state[key(row)]["a_name"]=="Zulu"
    assert state[key(row)]["b_name"]=="Alpha"
    with pytest.raises(ValueError,match="Ambiguous"):
        construct_record_history([row,row],cutoff="2026-01-01")
    with pytest.raises(ValueError,match="Future"):
        construct_record_history([row],cutoff="2024-01-01")
