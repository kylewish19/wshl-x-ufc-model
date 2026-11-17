"""Finish-resistance history: exact lag, missingness, coverage, and no get-up claims."""
from datetime import date
import json
from pathlib import Path
import pytest

from wshlx_ufc.prefight_finish_resistance import (
    build_from_records,load_and_build,
)

ROOT=Path(__file__).resolve().parents[1]


def _bout(day,a,b,ab,method,kd_a=0,kd_b=0,sub_a=0,sub_b=0,
          control_a=0,control_b=0,td_a=0,tda_a=0,td_b=0,tda_b=0):
    return {
        "date":date.fromisoformat(day),"event":day,
        "a":a,"b":b,"result":ab,"method":method,
        "elapsed_seconds":900 if method=="DEC" else 350,
        "stats_a":{"kd":kd_a,"td_landed":td_a,"td_attempted":tda_a,
                   "sub_att":sub_a,"ctrl_sec":control_a},
        "stats_b":{"kd":kd_b,"td_landed":td_b,"td_attempted":tda_b,
                   "sub_att":sub_b,"ctrl_sec":control_b},
    }


def test_previous_damage_and_defensive_survival_not_same_fight_result():
    previous=[
        _bout("2026-08-01","Alpha","Beta",("W","L"),"KO_TKO",kd_a=2),
        _bout("2026-08-08","Beta","Charlie",("W","L"),"DEC",
              kd_b=1,sub_b=2,control_b=75,td_b=1,tda_b=4),
        _bout("2026-08-08","Alpha","Delta",("L","W"),"SUB",sub_b=2),
    ]
    snaps,metrics=build_from_records(
        previous,as_of_exclusive="2026-08-15",
        query_bouts=[("Beta","Delta")],
    )
    assert metrics["fights"]==3
    assert metrics["query_bouts"]==1
    assert all(s["current_fight_result_not_a_feature"] for s in snaps)
    latest=snaps[-1]
    assert latest["query_only"]
    assert latest["event_date"]=="2026-08-15"
    B=latest["a_pre"]
    assert B["prior_ufc_bouts"]==2
    assert B["prior_knockdown_bouts"]==2
    assert B["prior_knockdowns_absorbed"]==3
    assert B["prior_submission_threat_bouts"]==0
    assert B["prior_ko_losses"] if "prior_ko_losses" in B else B["ko_loss_rate_shrunk"]>0.12
    assert B["prior_takedowns_faced"]==0
    assert B["getups_directly_measured"] is False
    assert latest["b_pre"]["prior_ufc_bouts"]==1
    assert latest["b_pre"]["prior_submission_threat_bouts"]==0
    assert latest["b_pre"]["stats_coverage"]==1.0


def test_different_same_day_results_cannot_change_prefight_state_for_day():
    old=[
        _bout("2026-08-01","A","B",("W","L"),"KO_TKO",kd_a=1),
        _bout("2026-08-08","B","C",("W","L"),"DEC",control_b=90),
        _bout("2026-08-08","A","D",("W","L"),"DEC"),
    ]
    baseline,_=build_from_records(old,as_of_exclusive="2026-08-15")
    changed=[dict(x) for x in old]
    changed[1]["result"]=("L","W")
    changed[1]["method"]="SUB"
    alternate,_=build_from_records(changed,as_of_exclusive="2026-08-15")
    assert baseline==alternate
    with pytest.raises(ValueError,match="Same-date/future"):
        build_from_records(old,as_of_exclusive="2026-08-08")


def test_future_card_query_cannot_contain_duplicate_fighters_or_invent_getups():
    old=[_bout("2026-08-01","A","B",("W","L"),"DEC")]
    with pytest.raises(ValueError,match="ambiguous fighter"):
        build_from_records(old,as_of_exclusive="2026-08-15",
                           query_bouts=[("A","C"),("A","D")])
    snapshots,_=build_from_records(old,as_of_exclusive="2026-08-15",
                                  query_bouts=[("A","New Fighter")])
    assert snapshots[-1]["b_pre"]["prior_ufc_bouts"]==0
    assert snapshots[-1]["b_pre"]["getups_directly_measured"] is False
    assert snapshots[-1]["b_pre"]["knockdowns_absorbed_per15"] is None


def test_real_pinned_archive_and_ufc334_card_is_only_query_not_train():
    f=json.loads((ROOT/"data/locks/ufc334_2026-11-14/stage_a_final_selection.json").read_text())
    pairs=[(x["a"],x["b"]) for x in f["fights"]]
    rows,meta=load_and_build(as_of_exclusive="2026-11-14",query_bouts=pairs)
    assert meta["fights"]>5000
    assert meta["query_bouts"]==13
    assert meta["complete_stat_bouts"]>1000
    assert meta["getups_directly_measured"] is False
    assert not meta["model_or_bet_promotion"]
    query=[x for x in rows if x.get("query_only")]
    assert len(query)==13
    assert {(x["a"],x["b"]) for x in query}==set(pairs)
    assert all(x["event_date"]=="2026-11-14" for x in query)
    assert all(x["a_pre"]["getups_directly_measured"] is False for x in query)
    assert all(x["a_pre"]["ko_loss_rate_shrunk"]>0 for x in query)
