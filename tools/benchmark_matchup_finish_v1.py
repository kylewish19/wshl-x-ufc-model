"""Execute date-ordered Finish v1 research, compare originals on same bouts.

Predeclared windows:
  fit 2021-2023 -> evaluate 2024;
  fit 2021-2024 -> evaluate 2025;
  fit 2021-2025 -> retrospective (NOT pristine) evaluate 2026 through Nov7.
All four candidate methods share the *same* pre-fight historical-rate winner
head in each comparison. The runner scores candidate methods for BOTH fighter
sides, not the hindsight actual winner, and cannot modify live Stage A/B.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import random
import re
import unicodedata

import joblib
import numpy as np

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.finish_v1_research import (
    METHODS, aggregate, coherent_six, method_features, predict_family,
    prior_win_probability, score_six, train_candidate_family,
)

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"reports/model_health/2026-11-18_finish_v1_research"
WINDOWS=(
    ("2024","2024-01-01","2024-01-01","2025-01-01",511),
    ("2025","2025-01-01","2025-01-01","2026-01-01",513),
    ("2026_retrospective","2026-01-01","2026-01-01","2026-11-14",488),
)
ORIGINALS=(
    "ufc333_2026-10-24",
    "ufcvegas124_2026-11-07",
)
ALL_METHODS=("global_prior","hierarchical","multinomial","nonlinear")

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def namesafe(name):
    s=unicodedata.normalize("NFKD",str(name))
    return re.sub("[^a-z0-9]","",s.encode("ascii","ignore").decode("ascii").casefold())

def fight_key(date,a,b):
    names=(namesafe(a),namesafe(b))
    if not all(names) or names[0]==names[1]:
        raise ValueError("Invalid fighter identity")
    return (date,*sorted(names))

def result_score(label,forecast,p_a):
    if label["result_status"]!="DECISIVE":raise ValueError("Draw cannot receive six-class score")
    side=0 if int(label["label_a_win"])==1 else 1
    out=score_six(forecast,side,label["label_method"],p_a=p_a)
    out["sub_probability"]=float(forecast[1]+forecast[4])
    out["finish_probability"]=float(forecast[[0,1,3,4]].sum())
    out["actual_sub"]=int(label["label_method"]=="SUB")
    return out

def detailed(rows):
    metric=aggregate(rows)
    metric["expected_submissions"]=sum(x["sub_probability"] for x in rows)
    metric["actual_submissions"]=sum(x["actual_sub"] for x in rows)
    metric["sub_probability_brier"]=sum((x["sub_probability"]-x["actual_sub"])**2 for x in rows)/len(rows)
    metric["actual_decisions"]=sum(x["true_method"]=="DEC" for x in rows)
    metric["predicted_decisions"]=sum(x["pred_method"]=="DEC" for x in rows)
    return metric

def paired_event_bootstrap(rows_a,rows_b,metric,*,seed=19,resamples=1000):
    if len(rows_a)!=len(rows_b) or not rows_a:raise ValueError("Mismatched cohorts")
    groups=defaultdict(list)
    for a,b in zip(rows_a,rows_b):
        if a["event_date"]!=b["event_date"] or a["event"]!=b["event"] or a["bout_id"]!=b["bout_id"]:
            raise ValueError("Paired bootstrap must use exact same bouts")
        groups[(a["event_date"],a["event"])].append(a[metric]-b[metric])
    rng=random.Random(seed)
    events=sorted(groups)
    differences=[]
    for _ in range(resamples):
        drawn=[events[rng.randrange(len(events))] for _ in events]
        vals=[v for event in drawn for v in groups[event]]
        differences.append(sum(vals)/len(vals))
    differences.sort()
    return {
        "candidate_minus_comparator":True,
        "event_clusters":len(events),
        "observed_mean":sum(a[metric]-b[metric] for a,b in zip(rows_a,rows_b))/len(rows_a),
        "event_cluster_bootstrap_95pct":[
            differences[int(.025*(resamples-1))],
            differences[int(.975*(resamples-1))],
        ],
        "bootstrap_resamples":resamples,
        "seed":seed,
        "not_prospective_evidence":True,
    }

def evaluate_window(features,by_label,before,start,end,bundle,expected):
    subsets=[f for f in features if start<=f["event_date"]<end and by_label[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(subsets)!=expected:
        raise ValueError("Year population drift: "+start+" "+str(len(subsets)))
    scored=defaultdict(list)
    per_fight=[]
    for f in subsets:
        label=by_label[f["bout_id"]]
        p=prior_win_probability(f)
        forecasts=predict_family(f,bundle,p_a=p)
        for name,q in forecasts.items():
            s=result_score(label,q,p)
            scored[name].append({**s,"event_date":f["event_date"],"event":f["event"],"bout_id":f["bout_id"]})
            per_fight.append({
                "event_date":f["event_date"],"event":f["event"],"bout_id":f["bout_id"],
                "fighter_a":f["fighter_a"],"fighter_b":f["fighter_b"],
                "label_method":label["label_method"],"label_a_win":int(label["label_a_win"]),
                "model":name,"prob_a_win":p,
                "a_ko":q[0],"a_sub":q[1],"a_dec":q[2],
                "b_ko":q[3],"b_sub":q[4],"b_dec":q[5],
                "selected_fighter_exact":s["exact"],"predicted_method":s["pred_method"],
                "sub_probability":s["sub_probability"],
            })
    summary={m:detailed(scored[m]) for m in ALL_METHODS}
    compare={
       m:{
           "vs_global_prior_six_log_loss":paired_event_bootstrap(scored[m],scored["global_prior"],"six_log_loss"),
           "vs_global_prior_exact_accuracy":paired_event_bootstrap(scored[m],scored["global_prior"],"exact"),
       } for m in ("hierarchical","multinomial","nonlinear")
    }
    return summary,compare,per_fight

def compare_originals(features,by_label,bundle):
    index={}
    for f in features:
        key=fight_key(f["event_date"],f["fighter_a"],f["fighter_b"])
        if key in index:raise ValueError("Historical fighter-pair ambiguity")
        index[key]=f
    results=defaultdict(list)
    row_details=[]
    source_receipts=[]
    for slug in ORIGINALS:
        folder=ROOT/"data/locks"/slug
        rawpath=folder/"stage_a_model_raw_three_view.json"
        frozenpath=folder/"stage_a_final_selection.json"
        raw=json.loads(rawpath.read_text())
        final=json.loads(frozenpath.read_text())
        if (not final["stage_a_frozen"] or raw["odds_used"] or final["odds_used"]
            or final["raw_model_sha256"]!=sha(rawpath)):
            raise ValueError("Original Stage A provenance failed "+slug)
        if len(raw["fights"])!=len(final["fights"]):raise ValueError("Card counts differ")
        finalby={int(x["fight_no"]):x for x in final["fights"]}
        source_receipts.append({
            "event":slug,"original_raw_sha256":sha(rawpath),
            "original_final_sha256":sha(frozenpath),
            "frozen_at_utc":final["frozen_at_utc"],
        })
        for r in raw["fights"]:
            k=fight_key(raw["event_date"],r["a"],r["b"])
            f=index.get(k)
            if f is None:raise ValueError("Original bout missing historical features: "+str(k))
            label=by_label[f["bout_id"]]
            if label["result_status"]!="DECISIVE":
                raise ValueError("Unexpected original draw in 28-bout comparison")
            ff=finalby[int(r["fight_no"])]
            if (r["a"],r["b"])!=(ff["a"],ff["b"]):
                raise ValueError("Original raw and frozen fighter mismatch")
            p_original=float(r["historical_shadow"]["winner_p_a"])
            # Reorient original winner head to source archive fighter A.
            if namesafe(r["a"])==namesafe(f["fighter_a"]):
                p=p_original; swap=False
            elif namesafe(r["a"])==namesafe(f["fighter_b"]):
                p=1-p_original; swap=True
            else:raise ValueError("Original fighter order mismatch")
            qmap=predict_family(f,bundle,p_a=p)
            j=r["historical_shadow"]["joint_method"]
            native=np.array([j[k] for k in ("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")],float)
            if swap:native=native[[3,4,5,0,1,2]]
            norm=native.reshape(2,3)
            aligned=coherent_six(p,norm/norm.sum(axis=1,keepdims=True))
            qmap.update({"historical_original_native":native,
                         "historical_original_same_winner":aligned})
            for name,q in qmap.items():
                s=result_score(label,q,p)
                results[name].append({**s,"event_date":f["event_date"],"event":f["event"],"bout_id":f["bout_id"]})
                row_details.append({
                    "event_date":f["event_date"],"fighter_a":f["fighter_a"],
                    "fighter_b":f["fighter_b"],"variant":name,
                    "historical_original_p_a_after_orientation":p,
                    "predicted_method":s["pred_method"],"exact":s["exact"],
                    "six_log_loss":s["six_log_loss"],"six_brier":s["six_brier"],
                })
    if any(len(rows)!=28 for rows in results.values()):
        raise ValueError("Original common matchup count != 28")
    out={name:detailed(rows) for name,rows in results.items()}
    paired={
      name:paired_event_bootstrap(results[name],results["historical_original_same_winner"],"six_log_loss")
      for name in ALL_METHODS
    }
    return {
        "sample_type":"SAME_28_BOUTS_2_ALREADY_RESEARCHED_CARDS_NOT_GENUINELY_UNSEEN",
        "original_provenance":source_receipts,
        "winner_probability_always_original_frozen_historical":True,
        "two_original_comparators":"native six-state vs within-fighter conditional renormalized to original Historical winner head",
        "candidate_training_only_through":"2025-12-31",
        "scores":out,
        "paired_loss_difference_vs_original_historical_same_winner":paired,
        "model_promotion":False,
    },row_details

def main():
    if any((ROOT/"data/locks/ufcqatar_2026-11-21").glob("*.new")):
        raise RuntimeError("Do not rewrite or create new production Stage A")
    features,labels,manifest=load_matrix()
    by_label={l["bout_id"]:l for l in labels}
    if len(by_label)!=len(labels):raise ValueError("Duplicate source outcomes")
    all_years={}
    all_rows=[]
    bundles={}
    for title,before,start,end,expected in WINDOWS:
        bundle=train_candidate_family(features,labels,before)
        summaries,paired,rows=evaluate_window(features,by_label,before,start,end,bundle,expected)
        all_years[title]={
            "training_before_exclusive":before,"evaluated_from":start,
            "evaluated_before_exclusive":end,
            "training_n":bundle["train_n"],"training_method_counts":bundle["train_counts"],
            "winner_head":"PAST_ONLY_SMOOTHED_UFC_WIN_RATE_FIXED_ACROSS_METHOD_VARIANTS",
            "models":summaries,
            "paired_comparisons":paired,
        }
        all_rows.extend(rows)
        bundles[title]=bundle
    matched,original_rows=compare_originals(features,by_label,bundles["2026_retrospective"])
    OUTPUT.mkdir(parents=True,exist_ok=True)
    report={
        "schema":"WSHLX_INDEPENDENT_MATCHUP_FINISH_V1_CHRONOLOGICAL_RESEARCH",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "input_archive_sha256":manifest["source_stats_sha256"],
        "input_labels_separate_and_asof_date_only":True,
        "fit_method_conditional_on_past_actual_winners_but_predict_both_current_fighter_sides":True,
        "models":["global_prior","hierarchical","multinomial","nonlinear"],
        "no_age_reach_regional_data_or_direct_getups_fabricated":True,
        "prespecified_regularization_no_hyperparameter_search_this_run":True,
        "2026_already_inspected_not_pristine":True,
        "2024_2025_also_retrospective_research_not_prospective":True,
        "winner_head_fixed_for_method_family_comparison":True,
        "pre_event_qatar_stage_a_and_coherent_shadow_untouched":True,
        "no_model_wager_or_stage_b_promotion":True,
        "per_year":all_years,
        "same_28_original_historical":matched,
        "no_accepted_challenger":True,
    }
    report_path=OUTPUT/"evaluation.json"
    report_path.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    with (OUTPUT/"yearly_test_forecasts.csv").open("w",newline="",encoding="utf-8") as h:
        writer=csv.DictWriter(h,fieldnames=list(all_rows[0]))
        writer.writeheader();writer.writerows(all_rows)
    with (OUTPUT/"matched_28_original_predictions.csv").open("w",newline="",encoding="utf-8") as h:
        writer=csv.DictWriter(h,fieldnames=list(original_rows[0]))
        writer.writeheader();writer.writerows(original_rows)
    # Train-through-2025 artifact is research-only, not plugged into Stage A.
    joblib.dump({
        "schema":report["schema"],"fit_before":"2026-01-01",
        "input_archive_sha256":manifest["source_stats_sha256"],
        "models":bundles["2026_retrospective"],
        "approved_for_stage_a":False,"approved_for_fanduel":False,
    },OUTPUT/"finish_v1_train_through_2025_RESEARCH_ONLY.joblib")
    for f in OUTPUT.iterdir():
        report.setdefault("output_sha256",{})[f.name]=sha(f)
    report_path.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "status":"RESEARCH_TRAINED_EVALUATED_NO_PROMOTION",
        "year_summary":{y:{m:{k:d[k] for k in ("fights","exact_hits","six_log_loss")}
                            for m,d in v["models"].items()} for y,v in all_years.items()},
        "same_28":{m:{k:d[k] for k in ("fights","exact_hits","six_log_loss")}
                   for m,d in matched["scores"].items()},
        "output":str(OUTPUT),
        "nov21_original_lock_changed":False,
    },indent=2,sort_keys=True))

if __name__=="__main__":
    main()
