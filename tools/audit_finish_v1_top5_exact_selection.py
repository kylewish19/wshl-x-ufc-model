"""Research-only event-by-event exact fighter+method pick selection audit.

This is not a bettor/promotion model. For each historically evaluated card,
sort existing date-out-of-fold model predictions without consulting outcomes;
grade top 1..5, including all-picked-correct frequency. Explicitly compare
ranking by exact-six probability to ranking by binary winner confidence.
Restrict main dashboard to original 11-14 fight-size cards.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

SOURCE = Path("reports/model_health/2026-11-18_finish_v1_research/yearly_test_forecasts.csv")
DEST = SOURCE.parent / "selection_top1_to5_diagnostic.json"
MODELS = ("global_prior", "hierarchical", "multinomial", "nonlinear")
SIX = ("a_ko", "a_sub", "a_dec", "b_ko", "b_sub", "b_dec")
METHODS = ("KO_TKO", "SUB", "DEC")


def parse(row):
    q = [float(row[k]) for k in SIX]
    if not all(0.0 <= p <= 1.0 for p in q) or abs(sum(q)-1) > 1e-7:
        raise ValueError("Invalid six-outcome distribution")
    p_a = float(row["prob_a_win"])
    if not 0 <= p_a <= 1 or abs(sum(q[:3])-p_a)>1e-7:
        raise ValueError("Winner marginal inconsistent with 6-state predictions")
    actual_side = 0 if row["label_a_win"] == "1" else 1
    if row["label_method"] not in METHODS:
        raise ValueError("Unsupported method")
    y = actual_side*3 + METHODS.index(row["label_method"])
    # Global max-six candidate: preferred when explicitly optimizing
    # probability of the exact fighter+method pair (may disagree with winner head).
    six_choice = max(range(6),key=lambda i:q[i])
    # Existing original selection style: winner head, then conditional method.
    side = 0 if p_a >= .5 else 1
    own = side*3 + max(range(3), key=lambda i:q[3*side+i])
    return {
        "event_date":row["event_date"],"event":row["event"],
        "bout_id":row["bout_id"],"year":row["event_date"][:4],
        "model":row["model"],
        "global_exact_probability":q[six_choice],
        "global_exact_hit":int(six_choice==y),
        "selected_fighter_exact_probability":q[own],
        "selected_fighter_exact_hit":int(own==y),
        "winner_confidence":max(p_a,1-p_a),
    }


def top_k(cards,rank_by,scored_by,k):
    subsets=[]
    for bout_rows in cards.values():
        if len(bout_rows) < k: continue
        ordered=sorted(bout_rows,key=lambda r:(-r[rank_by],r["bout_id"]))
        subsets.append(ordered[:k])
    if not subsets:raise ValueError("No eligible event groups")
    count=sum(len(x) for x in subsets)
    hits=sum(sum(r[scored_by] for r in x) for x in subsets)
    complete=sum(all(r[scored_by] for r in x) for x in subsets)
    return {
        "eligible_event_cards":len(subsets),"picks":count,
        "exact_hits":hits,"exact_pick_accuracy":hits/count,
        "all_exact_correct_cards":complete,
        "all_exact_correct_card_rate":complete/len(subsets),
        "mean_rank_probability":sum(r[rank_by] for subset in subsets for r in subset)/count,
    }


def report(rows):
    unique=set()
    groups=defaultdict(list)
    for r in rows:
        k=(r["model"],r["bout_id"])
        if k in unique:raise ValueError("Duplicate forecast: "+str(k))
        unique.add(k)
        groups[(r["year"],r["model"],r["event_date"],r["event"])].append(r)

    cohorts={}
    for year in ("2024","2025","2026","combined"):
        for model in MODELS:
            cards={
                (d,e):rs for (yr,m,d,e),rs in groups.items()
                if (yr==year or year=="combined") and m==model and 11<=len(rs)<=14
            }
            if not cards:raise ValueError("No 11–14 fight cards")
            allrows=[r for v in cards.values() for r in v]
            full_n=len(allrows)
            cohorts[year+"/"+model]={
                "event_cards":len(cards),"fights":full_n,
                "full_card_exact_selected_fighter_hits":sum(r["selected_fighter_exact_hit"] for r in allrows),
                "full_card_exact_global_six_hits":sum(r["global_exact_hit"] for r in allrows),
                "selection":{str(k):{
                    "top_six_probability":top_k(cards,"global_exact_probability","global_exact_hit",k),
                    "selected_fighter_exact_probability":top_k(cards,"selected_fighter_exact_probability","selected_fighter_exact_hit",k),
                    "highest_winner_probability":top_k(cards,"winner_confidence","selected_fighter_exact_hit",k),
                } for k in (1,2,3,4,5)},
            }
    original=[r for r in rows if r["model"]=="multinomial"]
    maxes=[r["global_exact_probability"] for r in original]
    thresholds={str(t):{
        "bouts":sum(p>t for p in maxes),
        "hits":sum(r["global_exact_hit"] for r in original if r["global_exact_probability"]>t),
    } for t in (.4,.45,.5,.55,.6,.7,.8,.9)}
    return {
        "schema":"WSHLX_CHRONOLOGICAL_CARD_SELECTION_TOP1_5_V1",
        "source":"previously generated year-out-of-fold research-only six-state probabilities",
        "primary_target":"EXACT_FIGHTER_AND_VICTORY_METHOD_NOT_WINNER_ONLY",
        "historical_2024_2026_not_unexamined_prospective":True,
        "per_card_eligibility":"11 <= count(decisive labeled bouts in event) <= 14",
        "rankings":"global six-cell maximum, selected-winner method six-cell, highest winner confidence",
        "top_k_pre_event_score_only_then_post_event_labels_for_grade":True,
        "no_topk_threshold_fitted_or_selection_rule_promoted":True,
        "picks_are_not_wagers":"Real FanDuel prices and bet approval separate",
        "sample_cohorts":cohorts,
        "multinomial_all_1512_prob_exact_thresholds":thresholds,
        "models_unmodified":True,
        "nov21_original_stage_a_and_coherent_lock_untouched":True,
    }


def main():
    with SOURCE.open(encoding="utf-8",newline="") as f:
        data=[parse(row) for row in csv.DictReader(f)]
    expected=1512*len(MODELS)
    if len(data)!=expected:raise ValueError(f"Expected {expected} source predictions; got {len(data)}")
    result=report(data)
    assert result["sample_cohorts"]["combined/multinomial"]["event_cards"]==117
    assert result["sample_cohorts"]["combined/multinomial"]["fights"]==1456
    DEST.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "research_only":True,
        "cards":result["sample_cohorts"]["combined/multinomial"]["event_cards"],
        "multinomial":result["sample_cohorts"]["combined/multinomial"]["selection"],
        "confidence_thresholds":result["multinomial_all_1512_prob_exact_thresholds"],
    },sort_keys=True))


if __name__=="__main__":
    main()
