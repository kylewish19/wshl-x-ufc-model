"""Submission discrimination audit for Finish v1; no new picks or thresholds.

Reads already generated OUT-OF-YEAR forecasts; sorting by pre-event model
P(selected fighter wins by submission) is independent of future labels.
Labels are only revealed afterward to compute ranking precision/recall.
Global top-decile research analysis, NOT a UFC-card wagering strategy.
"""
from __future__ import annotations
import csv,json,math
from pathlib import Path
from collections import defaultdict
from sklearn.metrics import average_precision_score,roc_auc_score

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"reports/model_health/2026-11-18_finish_v1_research"
SOURCE=DIR/"yearly_test_forecasts.csv"
OUTPUT=DIR/"submission_ranking.json"
MODELS=("global_prior","hierarchical","multinomial","nonlinear")
YEARS=("2024","2025","2026")

def audit(rows):
    if not rows:raise ValueError("Empty cohort")
    ids=set()
    scored=[]
    for row in rows:
        bout_id=row["bout_id"]
        if bout_id in ids:raise ValueError("Duplicate scored bout")
        ids.add(bout_id)
        p_a=float(row["prob_a_win"])
        if not 0<=p_a<=1:raise ValueError("Invalid winner probability")
        picked_a=p_a>=.5
        p=float(row["a_sub"] if picked_a else row["b_sub"])
        total=float(row["a_sub"])+float(row["b_sub"])
        actual=int(row["label_method"]=="SUB" and picked_a == (int(row["label_a_win"])==1))
        any_sub=int(row["label_method"]=="SUB")
        if not 0<=p<=1 or not 0<=total<=1:
            raise ValueError("Invalid submission mass")
        scored.append({
            "id":bout_id,"date":row["event_date"],
            "p_selected_fighter_sub":p,"p_any_sub":total,
            "exact_submission":actual,"any_submission":any_sub,
        })
    n=len(scored)
    # The threshold is a fixed percentile for ranking evaluation, not a
    # bet signal. No target-derived top-K selection is permitted.
    topn=max(1,int(n*.10+.5))
    ranked=sorted(scored,key=lambda r:(-r["p_selected_fighter_sub"],r["id"]))
    subset=ranked[:topn]
    total_exact=sum(x["exact_submission"] for x in scored)
    precision=sum(x["exact_submission"] for x in subset)/topn
    anylabels=[x["any_submission"] for x in scored]
    exactlabels=[x["exact_submission"] for x in scored]
    pselected=[x["p_selected_fighter_sub"] for x in scored]
    pany=[x["p_any_sub"] for x in scored]
    if len(set(anylabels))<2 or len(set(exactlabels))<2:
        raise ValueError("Need both outcomes for ranking calibration")
    return {
        "fights":n,
        "total_exact_submission_opportunities":total_exact,
        "exact_submission_base_rate":total_exact/n,
        "top_decile_count":topn,
        "top_decile_exact_hits":sum(x["exact_submission"] for x in subset),
        "top_decile_exact_precision":precision,
        "top_decile_exact_recall":sum(x["exact_submission"] for x in subset)/total_exact,
        "top_decile_average_model_probability":sum(x["p_selected_fighter_sub"] for x in subset)/topn,
        "exact_selected_fighter_sub_average_precision":average_precision_score(exactlabels,pselected),
        "exact_selected_fighter_sub_roc_auc":roc_auc_score(exactlabels,pselected),
        "fight_has_any_sub_base_rate":sum(anylabels)/n,
        "fight_any_sub_average_precision":average_precision_score(anylabels,pany),
        "fight_any_sub_roc_auc":roc_auc_score(anylabels,pany),
        "only_historical_rank_assessment_no_bet_signals":True,
    }

def main():
    records=list(csv.DictReader(SOURCE.open(encoding="utf-8",newline="")))
    grouped=defaultdict(list)
    for row in records:
        year=row["event_date"][:4]
        name=row["model"]
        if year not in YEARS or name not in MODELS:raise ValueError("Unknown source fold/model")
        grouped[(year,name)].append(row)
    if set(grouped)!={(year,name) for year in YEARS for name in MODELS}:
        raise ValueError("Missing evaluation folds or methods")
    report={
        "schema":"WSHLX_FINISH_V1_SUBMISSION_RANKING_DIAGNOSTIC",
        "origin":"Already-generated date-out-of-fold finish v1 probabilities",
        "top_decile_rule":"Sort each evaluation-year cohort by pre-event p(selected fighter by SUB), descending, tie-break bout ID; take round(0.1*n)",
        "never_decide_sub_method_or_bet_from_hindsight":True,
        "no_method_production_promotion":True,
        "2026_is_prior_inspected_retrospective_not_clean_holdout":True,
        "folds":{},
    }
    for year in YEARS:
        report["folds"][year]={name:audit(grouped[(year,name)]) for name in MODELS}
        n={x["fights"] for x in report["folds"][year].values()}
        if n!={511 if year=="2024" else 513 if year=="2025" else 488}:
            raise ValueError("Unexpected fold count")
    OUTPUT.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({year:{m:{k:round(s[k],4) if isinstance(s[k],float) else s[k] for k in
                                ("fights","top_decile_exact_hits","top_decile_exact_precision",
                                 "exact_submission_base_rate","exact_selected_fighter_sub_average_precision")}
                             for m,s in results.items()}
                      for year,results in report["folds"].items()},sort_keys=True))

if __name__=="__main__":
    main()
