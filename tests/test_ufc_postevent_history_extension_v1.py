from datetime import date
from copy import deepcopy
import csv,json
import pytest
from wshlx_ufc.postevent_history_extension_v1 import (
    KEYS,pinned,verify_qatar_round_totals,load_extended_records,
    future_research_matrix,future_research_snapshots
)

def inputs():
    return (json.loads(pinned(KEYS[3])),
            list(csv.DictReader(pinned(KEYS[4]).decode().splitlines())),
            json.loads(pinned(KEYS[2])))

def test_all_64_rounds_match_24_totals():
    t,r,y=inputs()
    assert verify_qatar_round_totals(t,r,y)["matched_round_fighter_rows"]==64
    r[0]["sig_landed"]=str(int(r[0]["sig_landed"])+1)
    with pytest.raises(ValueError):verify_qatar_round_totals(t,r,y)

def test_extension_cannot_be_backdated():
    with pytest.raises(ValueError,match="future dates"):
        load_extended_records(as_of_exclusive="2026-11-21")
    with pytest.raises(ValueError,match="future dates"):
        load_extended_records(as_of_exclusive="2026-11-24")

def test_real_extended_history_and_future_matrix():
    f,l,a=future_research_matrix(as_of_exclusive="2026-11-25")
    assert a["added_decisive"]==24 and a["added_draws"]==1
    assert len(f)==len(l)==8896
    new=[x for x in f if x["event_date"]>="2026-11-14"]
    assert len(new)==25
    assert all(x["data_partition"]=="postevent_extension_research" for x in new)
    assert sum(x["result_status"]=="DECISIVE" and x["event_date"]>="2026-11-14" for x in l)==24
    assert not a["Qatar_secondary_stats_enabled"]

def test_explicit_stats_opt_in_changes_future_snapshot_only():
    r,a=load_extended_records(as_of_exclusive="2026-11-25",allow_secondary_qatar_stats=True)
    added=[x for x in r if x["date"]>=date(2026,11,14)]
    assert len(added)==25
    assert all(x["stats_a"] is None and x["stats_b"] is None for x in added if x["date"]==date(2026,11,14))
    assert all(x["stats_a"] is not None and x["stats_b"] is not None for x in added if x["date"]==date(2026,11,21))
    q,form,a=future_research_snapshots(as_of_exclusive="2026-11-25",
          query_bouts=[("Navajo Stirling","Diyar Nurgozhay")],allow_secondary_qatar_stats=True)
    assert len(q)==len(form)==1
    assert q[0]["a_pre"]["prior_ufc_bouts"]>=1
    assert q[0]["a_pre"]["prior_stats_bouts"]>=1
    assert a["Qatar_stats_crosscheck"]["matched_fighter_totals"]==24
