"""Pre-bout profile and recency provenance guards, including same-day freeze."""
from datetime import date
from wshlx_ufc.prefight_profile_context import (
    inches_height,inches_reach,date_dob,construct_metadata,
)

def record(when,a,b,weight):
    return {"date":when,"event":"Synthetic UFC",
            "a":a,"b":b,"weightclass":weight,
            "key":(when.isoformat(),"Synthetic UFC",*sorted((a,b)))}

def test_height_reach_dob_with_true_missing_not_fake_zero():
    assert inches_height("5' 11\"")==71.
    assert inches_height("--") is None
    assert inches_height("6' 2\"")==74.
    assert inches_reach('73"')==73.
    assert inches_reach("--") is None
    assert date_dob("Jul 03, 1983")==date(1983,7,3)
    assert date_dob("--") is None

def test_prior_weightclass_and_layoff_are_frozen_before_all_same_date_results():
    d=date(2024,1,1);end=date(2024,2,1)
    first=record(d,"Alice","Bob","Lightweight")
    second=record(d,"Alice","Charlie","Featherweight")
    third=record(end,"Alice","Dave","Lightweight")
    profiles={"alice":{"dob":date(1995,1,1),"height_inches":65.,"reach_inches":69.},
              "bob":{"dob":date(1990,1,1),"height_inches":73.,"reach_inches":76.}}
    indexed=construct_metadata([first,second,third],profiles)
    x=indexed[first["key"]]
    y=indexed[second["key"]]
    future=indexed[third["key"]]
    assert x["a"]["prior_same_weightclass_bouts"]==0
    assert y["a"]["prior_same_weightclass_bouts"]==0
    assert x["a"]["days_since_last_ufc_bout"] is None
    assert y["a"]["days_since_last_ufc_bout"] is None
    assert future["a"]["prior_same_weightclass_bouts"]==1
    assert future["a"]["days_since_last_ufc_bout"]==31
    assert future["a"]["prior_ufc_bouts_last365"]==2
    assert future["b"]["profile_found"] is False
    assert future["b"]["age_on_event_day"] is None
    assert future["b"]["reach_inches"] is None
    assert x["a"]["age_on_event_day"]==29.0 or abs(x["a"]["age_on_event_day"]-29)<.02
