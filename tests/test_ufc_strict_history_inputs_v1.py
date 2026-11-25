from datetime import date,datetime,timezone
import sys
from pathlib import Path
import pytest
from wshlx_ufc.strict_history_inputs_v1 import strict_records,matrices_from_records
from wshlx_ufc.prefight_finish_resistance import build_from_records
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from run_future_updated_history_research import build

def test_missing_source_retains_outcome_and_excludes_stat_exposure(tmp_path):
    (tmp_path/"ufc_fight_stats.csv").write_text(
        "EVENT,BOUT,FIGHTER,ROUND,KD,SUB ATT,TD,CTRL,SIG.STR.\n"
        "test,A vs. B,A,Round 1,0,--,1 of 2,0:30,2 of 5\n"
        "test,A vs. B,B,Round 1,0,0,0 of 1,0:00,2 of 5\n")
    r={"date":date(2025,1,1),"event":"test","a":"A","b":"B","result":("W","L"),"method":"KO_TKO","elapsed_seconds":280.}
    out,qa=strict_records([r],tmp_path)
    assert out[0]["stats_a"] is None and out[0]["stats_b"]["kd"]==0
    assert out[0]["result"]==r["result"]
    s,_=build_from_records(out,as_of_exclusive="2025-01-02",query_bouts=[("A","B")])
    assert s[-1]["a_pre"]["prior_ufc_bouts"]==1
    assert s[-1]["a_pre"]["prior_stats_bouts"]==0
    assert s[-1]["a_pre"]["own_sub_attempts_per15"] is None

def test_no_backdating():
    with pytest.raises(ValueError,match="future event"):
        build({"event_date":"2026-11-21","first_fight_utc":"2026-11-21T15:00:00+00:00"},
              now=datetime(2026,11,24,tzinfo=timezone.utc))

def test_future_runner_real_data_integration_not_a_real_card():
    # Intentionally hypothetical matchup, in-memory integration test only.
    # No lock file, market or actual scheduled event is claimed.
    from wshlx_ufc.postevent_history_extension_v1 import load_extended_records
    from run_future_updated_history_research import query
    records,a=load_extended_records(as_of_exclusive="2026-11-25")
    q=[(records[-1]["a"],records[-1]["b"])]
    prior=[r for r in records if r["date"]<date(2026,11,14)]
    f,_=query(records,"2026-11-25",q);old,_=query(prior,"2026-11-25",q)
    assert f[0]["a_prior_ufc_bouts"]==old[0]["a_prior_ufc_bouts"]+1
    assert f[0]["b_prior_ufc_bouts"]==old[0]["b_prior_ufc_bouts"]+1
    # Exercise full fitting + query code using an explicitly marked fixture.
    result=build({"event_date":"2026-11-25","first_fight_utc":"2026-11-25T20:00:00+00:00",
            "lineup_source_url":"https://example.invalid/test-fixture",
            "lineup_verified_by_caller":True,"fights":[{"a":q[0][0],"b":q[0][1],"provisional":True}]},
            now=datetime(2026,11,24,12,tzinfo=timezone.utc))
    assert set(result["training_counts"].values())=={3039}
    assert result["new_approved_bets"]==0
    for model in result["fights"][0]["models"].values():
        assert sum(model["six_joint"].values())==pytest.approx(1.)
        assert sum(model["six_joint"][k] for k in ("A_KO","A_SUB","A_DEC"))==pytest.approx(model["p_a"])
