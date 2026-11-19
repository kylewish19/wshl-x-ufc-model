"""Diagnose winner-vs-method errors and sparse UFC fighter history (research only).

Reads exactly dated independent joint v2 forecasts; pre-event coverage values
are reconstructed exclusively from the pinned prior-only source matrix.
No model weights/thresholds are fit; no Stage A/B files are touched.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from pathlib import Path
import csv,json,math

from wshlx_ufc.historical_feature_matrix import load_matrix

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"reports/model_health/2026-11-18_joint_winner_finish_v2"
SOURCE=DIR/"all_date_fold_forecasts.csv"
OUT=DIR/"winner_method_failure_decomposition.json"
VARIANTS=("prior_ufc_winrate__multinomial","new_symmetric_logistic__multinomial")

def avg(rows,field):
    return sum(float(x[field]) for x in rows)/len(rows) if rows else None

def summarize(rows):
    counts=Counter()
    method=defaultdict(Counter)
    for x in rows:
        w=int(x["winner_correct"])
        exact=int(x["selected_fighter_exact"])
        if exact and not w:raise ValueError("Impossible winner+method exact without winning fighter")
        counts["fights"]+=1
        counts["winner_right"]+=w
        counts["winner_wrong"]+=1-w
        counts["winner_right_method_wrong"]+=w-exact
        counts["exact"]+=exact
        method[x["actual_method"]][x["method_prediction"]]+=1
        method[x["actual_method"]]["actual"]+=1
        method[x["method_prediction"]]["predicted"]+=1
    return {
        **dict(counts),
        "winner_accuracy":counts["winner_right"]/counts["fights"],
        "exact_accuracy":counts["exact"]/counts["fights"],
        "method_accuracy_given_correct_winner":counts["exact"]/counts["winner_right"] if counts["winner_right"] else None,
        "six_class_log_loss":avg(rows,"six_log_loss"),
        "method_confusion":{k:dict(v) for k,v in sorted(method.items())},
    }

def main():
    features,labels,source=load_matrix()
    byid={x["bout_id"]:x for x in features}
    if len(byid)!=len(features):raise ValueError("Duplicate feature identities")
    rows=defaultdict(list)
    with SOURCE.open(newline="",encoding="utf-8") as io:
        for r in csv.DictReader(io):
            if r["event_date"].startswith("2026") and r["variant"] in VARIANTS:
                f=byid.get(r["bout_id"])
                if f is None or f["event_date"]!=r["event_date"]:
                    raise ValueError("Source matchup identity mismatch")
                if f["feature_as_of_exclusive"]!=r["event_date"]:
                    raise ValueError("Feature date leakage")
                prior=min(int(f["a_ufc_prior_bouts"]),int(f["b_ufc_prior_bouts"]))
                coverage=min(float(f["a_stats_coverage"]),float(f["b_stats_coverage"]))
                p=float(r["p_a_win"])
                r["group_debut"]=prior==0
                r["group_under5"]=prior<5
                r["group_5plus"]=prior>=5
                r["group_10plus"]=prior>=10
                r["group_eighty_percent_stats"]=coverage>=.8
                r["winner_confidence"]=max(p,1-p)
                rows[r["variant"]].append(r)
    if set(rows)!=set(VARIANTS) or any(len(g)!=488 for g in rows.values()):
        raise ValueError("2026 decisive cohort mismatch")
    report={
        "schema":"WSHLX_INDEPENDENT_WINNER_V2_FAILURE_DECOMPOSITION",
        "source":"same 488 as-of 2026 decisive historical bouts from date-out-of-fold joint v2",
        "source_stats_sha256":source["source_stats_sha256"],
        "2026_was_previously_studied":True,
        "no_new_coefficients_calibration_or_betting_predictions":True,
        "variants":{},
    }
    for name,rr in rows.items():
        groups={"all":rr,
                "any_ufc_debutant":[x for x in rr if x["group_debut"]],
                "any_under_5_ufc_bouts":[x for x in rr if x["group_under5"]],
                "both_5plus_ufc_bouts":[x for x in rr if x["group_5plus"]],
                "both_10plus_ufc_bouts":[x for x in rr if x["group_10plus"]],
                "both_at_least_80pct_stats_coverage":[x for x in rr if x["group_eighty_percent_stats"]],
                "winner_confidence_at_least_70pct":[x for x in rr if x["winner_confidence"]>=.70]}
        report["variants"][name]={k:summarize(v) for k,v in groups.items()}
    OUT.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({v:{g:{k:m[k] for k in ("fights","winner_right","exact","winner_right_method_wrong")}
                         for g,m in x.items()}
                      for v,x in report["variants"].items()},sort_keys=True))

if __name__=="__main__":
    main()
