"""Locked 14-bout Nov 7 2026: reproducible grading and no fake placed bets."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.grade_ufcvegas124_all_locked_picks import compute, _timing_spec
from tools.summarize_ufc_top5_research_units import aggregate_research_grades
from wshlx_ufc.research_top5_ledger import candidate_id
from wshlx_ufc.two_tier_card import LONGSHOTS, BEST_BETS
from wshlx_ufc.market_compatibility import _wins as market_wins

LOCK=ROOT/"data/locks/ufcvegas124_2026-11-07"
RESULTS=ROOT/"data/results"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_14_fight_source_outcomes_and_frozen_snapshots_untouched():
    o=read(RESULTS/"ufcvegas124_2026-11-07_verified_outcomes.json")
    a=read(LOCK/"stage_a_final_selection.json")
    t=read(LOCK/"stage_b_one_timing_forecast_per_fight.json")
    w=read(LOCK/"stage_b_top5_ranked_research_review_compatible_cross_tier.json")
    assert len(o["fights"])==len(a["fights"])==len(t["fights"])==14
    assert a["stage_a_frozen"] is True and a["odds_used"] is False
    assert t["original_stage_a_sha256"]==w["stage_a_original_sha256"]==sha(LOCK/"stage_a_final_selection.json")
    assert t["post_price_research_selection"] and not t["stage_a_historically_locked_timing_pick"]
    assert [(x["winner"],x["method"],x["round"],x["time"]) for x in o["fights"]]==[
        ("Jose Souza","KO",1,"4:16"),("Seokhyeon Ko","DEC",3,"5:00"),
        ("Andre Petroski","KO",2,"4:39"),("Austin Bashi","SUB",1,"1:07"),
        ("Murtazali Magomedov","DEC",3,"5:00"),("Karine Silva","DEC",3,"5:00"),
        ("Thomas Petersen","KO",3,"4:47"),("Ollie Schmid","DEC",3,"5:00"),
        ("Mitch Raposo","DEC",3,"5:00"),("Nina Milosevic","KO",2,"3:40"),
        ("Lucas Fernando","DEC",3,"5:00"),("Elijah Smith","KO",1,"1:00"),
        ("Tatiana Suarez","DEC",3,"5:00"),("Johnny Walker","KO",3,"2:27")
    ]


def test_grade_ref_vs_challengers_own_fighter_and_conditional_method_not_mixed():
    g=read(RESULTS/"ufcvegas124_2026-11-07_all_models_grading.json")
    assert g["original_stage_a_sha256"]==sha(LOCK/"stage_a_final_selection.json")
    assert g["raw_model_sha256"]==sha(LOCK/"stage_a_model_raw_three_view.json")
    assert g["timing_research_sha256"]==sha(LOCK/"stage_b_one_timing_forecast_per_fight.json")
    assert [g["scoreboards"][name]["winner_W"] for name in ("reference","historical","unified")]==[9,11,11]
    assert [g["scoreboards"][name]["own_fighter_and_method_W"] for name in ("reference","historical","unified")]==[5,7,8]
    assert [g["scoreboards"][name]["reference_side_method_class_only_matches"] for name in ("reference","historical","unified")]==[9,10,10]
    assert [g["scoreboards"][name]["method_given_correct_winner_W"] for name in ("reference","historical","unified")]==[5,7,8]
    assert g["observed_finish_distribution"]=={"KO":6,"SUB":1,"DEC":7}
    # Historic winner Petersen but method DEC missed; unified winner Petersen KO hit.
    p=g["fights"][6]["model_views"]
    assert p["reference"]["pick"]=="Gabriel Lorenco"
    assert not p["reference"]["own_fighter_and_method_correct"]
    assert p["historical"]["pick"]=="Thomas Petersen"
    assert p["historical"]["own_selected_fighter_conditional_method"]=="DEC"
    assert not p["historical"]["own_fighter_and_method_correct"]
    assert p["unified"]["pick"]=="Thomas Petersen"
    assert p["unified"]["own_selected_fighter_conditional_method"]=="KO"
    assert p["unified"]["own_fighter_and_method_correct"]
    # All three wrongly expected Magomedov submission; actual decision.
    m=g["fights"][4]
    assert m["method"]=="DEC"
    assert all(m["model_views"][view]["own_selected_fighter_conditional_method"]=="SUB"
               for view in ("reference","historical","unified"))
    # Actual one submission: current KO missed; both challengers picked SUB.
    b=g["fights"][3]["model_views"]
    assert b["reference"]["own_selected_fighter_conditional_method"]=="KO"
    assert b["historical"]["own_selected_fighter_conditional_method"]=="SUB"
    assert b["unified"]["own_selected_fighter_conditional_method"]=="SUB"


def test_timing_one_outcome_per_fight_10_4_research_not_official():
    g=read(RESULTS/"ufcvegas124_2026-11-07_all_models_grading.json")
    assert g["single_primary_timing_research"]["W"]==10
    assert g["single_primary_timing_research"]["L"]==4
    actual={x["fight_no"]:x for x in read(RESULTS/"ufcvegas124_2026-11-07_verified_outcomes.json")["fights"]}
    frozen={x["fight_no"]:x for x in read(LOCK/"stage_a_final_selection.json")["fights"]}
    assert len({r["fight_no"] for r in g["fights"]})==14
    for r in g["fights"]:
        t=r["timing_research"]
        o=actual[r["fight_no"]]
        side="a" if o["winner"]==frozen[r["fight_no"]]["a"] else "b"
        spec=_timing_spec(t["metric"])
        win=market_wins(spec,side,o["method"],o["elapsed_seconds"],o["scheduled_rounds"]*300)
        assert t["correct"]==win
        assert t["result"]==("W" if win else "L")
        assert t["status"]=="RESEARCH_TIMING_FORECAST_NO_APPROVED_STAKE"


def test_top5_original_price_correct_units_and_explicit_zero_approved():
    g=read(RESULTS/"ufcvegas124_2026-11-07_all_models_grading.json")
    research=read(RESULTS/"ufcvegas124_2026-11-07_top5_research_unit_grade.json")
    assert research["frozen_research_watchlist_sha256"]==sha(LOCK/"stage_b_top5_ranked_research_review_compatible_cross_tier.json")
    assert research["status"]=="VERIFIED_EVENT_RESEARCH_RESULTS"
    assert research["combined"]["record"]=={"W":2,"L":8,"PUSH":0,"VOID":0,"PENDING":0}
    assert research["combined"]["hypothetical_net_units"]==pytest.approx(-5.12)
    assert research["combined"]["hypothetical_roi"]==pytest.approx(-.512)
    assert g["official_approved_betting_record"]["total_bets"]==0
    assert g["official_approved_betting_record"]["pnl_units"]==0
    assert g["official_approved_betting_record"]["roi"] is None
    assert research["categories"][LONGSHOTS]["record"]=={"W":0,"L":5,"PUSH":0,"VOID":0,"PENDING":0}
    assert research["categories"][LONGSHOTS]["hypothetical_net_units"]==-5
    assert research["categories"][BEST_BETS]["record"]=={"W":2,"L":3,"PUSH":0,"VOID":0,"PENDING":0}
    assert research["categories"][BEST_BETS]["hypothetical_net_units"]==pytest.approx(-.12)
    assert [x["american_odds"] for x in research["categories"][LONGSHOTS]["selections"]]==[240,230,400,360,460]
    assert [x["american_odds"] for x in research["categories"][BEST_BETS]["selections"]]==[100,188,188,-110,132]
    assert [x["hypothetical_profit_units"] for x in research["categories"][LONGSHOTS]["selections"]]==[-1]*5
    assert [x["hypothetical_profit_units"] for x in research["categories"][BEST_BETS]["selections"]]==[1,-1,1.88,-1,-1]
    assert all(not x["is_actual_bet"] for tier in (LONGSHOTS,BEST_BETS)
               for x in research["categories"][tier]["selections"])
    totals=aggregate_research_grades([research])
    assert totals["events"]==1
    assert totals["categories"][LONGSHOTS]["net_hypothetical_units"]==-5
    assert totals["categories"][BEST_BETS]["net_hypothetical_units"]==pytest.approx(-.12)
    assert totals["combined"]["net_hypothetical_units"]==pytest.approx(-5.12)


def test_old_official_139_rows_preserved_153_exact_cumulative():
    with (RESULTS/"clean_ufc_139_2026-10-24.csv").open(newline="") as f:
        old=list(csv.reader(f))
    with (RESULTS/"clean_ufc_153_2026-11-07.csv").open(newline="") as f:
        new=list(csv.reader(f))
    assert len(old)==140
    assert len(new)==154
    assert new[:140]==old
    assert all(line[0]=="2026-11-07" for line in new[140:])
    assert [sum(int(x[i]) for x in new[1:]) for i in (6,7,8)]==[92,79,48]
    g=read(RESULTS/"ufcvegas124_2026-11-07_all_models_grading.json")
    assert g["reference_cumulative_153"]=={
        "count":153,"winner_W":92,"displayed_method_class_match_W":79,"joint_W":48
    }


def test_recomputation_from_frozen_files_agrees_graded_artifact():
    recomputed,settled,watch,ledger=compute()
    stored=read(RESULTS/"ufcvegas124_2026-11-07_all_models_grading.json")
    assert recomputed["scoreboards"]==stored["scoreboards"]
    assert recomputed["single_primary_timing_research"]==stored["single_primary_timing_research"]
    assert recomputed["reference_cumulative_153"]==stored["reference_cumulative_153"]
    assert settled["results"]==read(RESULTS/"ufcvegas124_2026-11-07_top5_verified_settlements.json")["results"]
    assert watch["combined"]==read(RESULTS/"ufcvegas124_2026-11-07_top5_research_unit_grade.json")["combined"]
    assert ledger==(RESULTS/"clean_ufc_153_2026-11-07.csv").read_text()
