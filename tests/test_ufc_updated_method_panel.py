"""Real-data integration tests; never create a card prediction lock."""
from datetime import datetime,timezone
from pathlib import Path
import json,sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from run_future_updated_method_panel import build_panel,add_secondary_rounds
from wshlx_ufc.postevent_history_extension_v1 import load_extended_records
from wshlx_ufc.round_method_v10 import build_round_history,read_rounds
from wshlx_ufc.finish_conversion_v9 import build_conversion

def test_queries_cannot_use_same_day_records():
    from datetime import date
    r=[{"date":date(2026,11,21),"event":"x","a":"A","b":"B","result":("W","L"),"method":"DEC","stats_a":None,"stats_b":None,"elapsed_seconds":900}]
    with pytest.raises(ValueError,match="follow historical"):
        build_conversion(r,query_date="2026-11-21",query_bouts=[("A","B")])
    with pytest.raises(ValueError,match="follow historical"):
        build_round_history(r,{},query_date="2026-11-21",query_bouts=[("A","B")])

def test_draft_not_a_live_lock():
    d=json.loads((ROOT/"research/lineups/ufcriyadh_2026-12-05_draft_2026-11-24.json").read_text())
    assert len(d["fights"])==14
    assert not d["lineup_verified_by_caller"]
    with pytest.raises(ValueError,match="externally checked"):
        build_panel(d,now=datetime(2026,11,24,tzinfo=timezone.utc))

def test_round_and_regional_panel_with_actual_archive_hypothetical_fixture():
    # Fictional pairing, not a scheduled match or timestamped live forecast.
    fixture={"event_date":"2026-12-05","first_fight_utc":"2026-12-05T15:00:00+00:00",
        "lineup_verified_by_caller":True,"lineup_source_url":"https://example.invalid/test",
        "fights":[{"a":"Dan Hooker","b":"Jared Cannonier","provisional":True}]}
    panel=build_panel(fixture,now=datetime(2026,11,24,tzinfo=timezone.utc),secondary=True)
    assert panel["regional_v5_training"]==panel["round86_training"]["train_n"]==3039
    assert panel["regional_audit"]["regional_results_through"]=="2026-11-07"
    assert panel["round_source_audit"]["secondary_round_fighter_rows"]==64
    assert panel["regional_audit"]["new_historical_rows"]==25
    models=panel["fights"][0]["models"]
    assert set(models)=={"legacy_updated_v3","strict_updated_v3","round86_updated_UFC","regional_v5_updated_UFC_pinned_regional"}
    for key in ("round86_updated_UFC","regional_v5_updated_UFC_pinned_regional"):
        p=models[key]
        assert p["p_a"]==models["legacy_updated_v3"]["p_a"]
        assert sum(p["six_joint"].values())==pytest.approx(1.)
        assert sum(p["six_joint"][k] for k in ("A_KO","A_SUB","A_DEC"))==pytest.approx(p["p_a"])
    assert panel["new_approved_bets"]==0

def test_secondary_round_fields_not_fabricated():
    records,_=load_extended_records(as_of_exclusive="2026-12-05",allow_secondary_qatar_stats=True)
    raw={}
    assert add_secondary_rounds(records,raw)==64
    assert all(x["sub"] is None and x["ground"] is None for x in raw.values())
