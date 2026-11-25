"""Before-lock controls: future-date UFC matchups cannot read same-day labels."""
from datetime import date
import pytest

from wshlx_ufc.prefight_opponent_quality import build_historical_opponent_quality
from wshlx_ufc.winner_recent_form_v3 import construct_record_history

def historical():
    return [{
        "date":date(2026,11,7),"event":"Synthetic earlier UFC",
        "a":"Athlete A","b":"Athlete B",
        "result":("W","L"),"elapsed_seconds":600.,
        "stats_a":{"sig_landed":30.,"sig_attempted":60.,"td_landed":1.,"td_attempted":2.,"kd":1.,"sub_att":0.},
        "stats_b":{"sig_landed":10.,"sig_attempted":30.,"td_landed":0.,"td_attempted":2.,"kd":0.,"sub_att":1.},
    }]

def test_pre_event_query_elo_uses_only_prior_date_and_no_synthetic_result():
    past=[{
        "date":"2026-11-07","event":"Synthetic earlier UFC",
        "a":"Athlete A","b":"Athlete B","outcome":"W/L",
    }]
    rows=build_historical_opponent_quality(past,query_date="2026-11-21",
                query_bouts=[("Athlete A","Athlete X")])
    assert len(rows)==2
    q=rows[-1]
    assert q["query_only"]
    assert q["source_status"]=="QUERY_ONLY_NO_RESULTS_OR_FUTURE_FEATURES"
    assert q["a_pre"]["ufc_prior_bouts"]==1
    assert q["b_pre"]["ufc_prior_bouts"]==0
    assert q["a_pre"]["ufc_elo_pre"]>1500.
    assert q["b_pre"]["ufc_elo_pre"]==1500.
    assert rows[0]["a_pre"]["ufc_prior_bouts"]==0
    with pytest.raises(ValueError,match="after all"):
        build_historical_opponent_quality(past,query_date="2026-11-07",
                   query_bouts=[("Athlete A","Athlete X")])
    with pytest.raises(ValueError,match="Duplicate"):
        build_historical_opponent_quality(past,query_date="2026-11-21",
                   query_bouts=[("Athlete A","Athlete X"),("Athlete A","Athlete B")])

def test_recent_form_future_queries_are_explicitly_result_free():
    source=historical()
    snaps=construct_record_history(source,cutoff="2026-11-21",
            query_date="2026-11-21",
            query_bouts=(("Athlete A","Athlete X"),))
    assert len(snaps)==2
    q=snaps[("2026-11-21","__PREFIGHT_QUERY_NO_RESULTS__","Athlete A","Athlete X")]
    assert q["query_only"] and q["a"][17]==0 and q["b"][17]==1
    assert q["a_name"]=="Athlete A"
    assert q["a"][0]>0 and q["b"][0]==0
    assert q["a"][9]>0 and q["b"][9]==0
    with pytest.raises(ValueError,match="Future query"):
        construct_record_history(source,cutoff="2026-11-21",
            query_date="2026-11-07",
            query_bouts=(("Athlete A","Athlete X"),))
