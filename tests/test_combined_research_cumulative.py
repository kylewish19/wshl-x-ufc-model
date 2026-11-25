import copy
import pytest
from test_combined_research_grade import fixture
from wshlx_ufc.combined_research_grade import grade,CHALLENGERS
from wshlx_ufc.combined_research_cumulative import summarize

def base():
    b,a,e=fixture();return grade(b,a,e)
def test_empty_and_single_event():
    assert summarize([])["unique_decisive_bouts"]==0
    g=summarize([base()])
    assert g["unique_decisive_bouts"]==2 and g["graded_events"]==1
    assert g["model_metrics"]["reference:raw"]["fights"]==2
    assert g["paired_vs_reference_raw"][CHALLENGERS[-1]]["paired_fights"]==1
    assert g["paired_vs_reference_raw"][CHALLENGERS[-1]]["event_cluster_percentile_95"] is None
    assert not g["prospective_promotion_authorized"]
def test_duplicate_or_missing_rejected():
    x=base()
    with pytest.raises(ValueError,match="Duplicate"):summarize([x,x])
    y=copy.deepcopy(x);y["per_bout_scores"]["reference:raw"].pop()
    with pytest.raises(ValueError,match="coverage"):summarize([y])
def test_event_cluster_intervals_and_unique_counts():
    # Pure synthetic aggregation test, never live prospective evidence.
    events=[]
    for i in range(10):
        e=base();e["event_date"]=f"2026-12-{i+1:02}"
        e["lock_sha256"]=f"{i:064x}";e["publication_evidence"]["sha256"]=e["lock_sha256"]
        events.append(e)
    s=summarize(events);p=s["paired_vs_own_raw"]["reference:winner_aligned"]
    assert s["unique_decisive_bouts"]==20 and p["paired_events"]==10
    assert p["event_cluster_percentile_95"]["six_log_loss"]==[0.,0.]
    assert not s["minimum_fight_count_met"]
