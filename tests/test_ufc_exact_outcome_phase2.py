"""Critical phase-2 safeguards: source-feature groups, six exact states,
evidence-only selections, and no forced 'locks' on historical test cards.
"""
from __future__ import annotations
import math
import numpy as np
import pytest

from tools.research_exact_outcomes_phase2 import (
    ALL,CORE,GROUPS,VARIANTS,selection,scored,actual_state,
)

def one(index,model="factorized6",*,data=True,agree=True,hit=True):
    year="2025"; event="Synthetic Historical Event"
    r={
        "date":"2025-04-05","event":event,"bout_id":str(index),
        "model":model,
        "exact_probability":.42 if model=="factorized6" else .44,
        "global_exact_probability":.42 if model=="factorized6" else .44,
        "global_gap":.12,
        "picked_exact_state":0,
        "global_pick":0 if agree else 1,
        "min_prior_ufc":8 if data else 0,
        "min_stats_coverage":.9 if data else 0,
        "exact":int(hit),
        "a_ko":.44,"a_sub":.10,"a_dec":.13,
        "b_ko":.12,"b_sub":.07,"b_dec":.14,
    }
    return r

def test_groups_cover_all_38_and_ablation_removes_source_features():
    assert sorted(ALL)==list(range(38))
    assert set.union(*GROUPS.values())==ALL
    assert sum(map(len,GROUPS.values()))==38
    assert len(VARIANTS["all_features"])==38
    assert len(VARIANTS["no_grappling"])<38
    assert set(VARIANTS["experience_only"])==CORE
    assert 25 not in VARIANTS["no_grappling"]
    assert 6 not in VARIANTS["no_quality"]

def test_12_bout_card_selects_only_evidence_and_consensus_not_winner_rank():
    sample=[]
    for i in range(12):
        eligible=i<7
        for m in ("factorized6","direct6"):
            sample.append(one(i,m,data=eligible,agree=(i!=5),
                              hit=(i%2==0)))
    report=selection(sample)
    assert report["rule_predeclared_no_test_outcome_input"]
    top=report["groups"]["baseline_top3"]
    strict=report["groups"]["strict_agreement_evidence"]
    assert top["eligible_cards"]==1 and top["picked_fights"]==3
    # 0,1,2,3,4 eligible; i=5 disagreement; i>=7 no UFC history
    assert strict["picked_fights"]==5
    assert strict["all_exact_correct_for_2_to_5"]==0
    assert strict["perfect_card_rate_when_2_to_5"]==0
    assert strict["no_forced_2_to_5"] is True

def test_no_evidence_can_return_zero_picks():
    sample=[one(i,m,data=False) for i in range(11) for m in ("factorized6","direct6")]
    report=selection(sample)
    strict=report["groups"]["strict_agreement_evidence"]
    assert strict["zero_pick_cards"]==1
    assert strict["picked_fights"]==0
    assert strict["perfect_card_rate_when_2_to_5"] is None

def test_exact_scoring_requires_fighter_and_method_and_excludes_draws():
    f={"event_date":"2025-04-05","event":"Synthetic","bout_id":"xx",
       "a_prior_ufc_bouts":10,"b_prior_ufc_bouts":12,
       "a_stats_coverage":.9,"b_stats_coverage":.8}
    q=np.array([.30,.20,.15,.15,.10,.10])
    label={"result_status":"DECISIVE","label_a_win":1,"label_method":"KO_TKO"}
    a=scored(f,label,.65,q,"factorized6","all_features")
    assert a["exact"]==1 and a["global_exact"]==1 and a["winner_hit"]==1
    assert math.isclose(a["six_log_loss"],-math.log(.30))
    label["label_method"]="SUB"
    b=scored(f,label,.65,q,"factorized6","all_features")
    assert b["exact"]==0 and b["winner_hit"]==1
    label["label_method"]="DEC"
    label["label_a_win"]=0
    c=scored(f,label,.65,q,"factorized6","all_features")
    assert c["exact"]==0 and c["winner_hit"]==0
    assert actual_state(label)==5
    label["result_status"]="DRAW"
    with pytest.raises(ValueError):
        actual_state(label)
