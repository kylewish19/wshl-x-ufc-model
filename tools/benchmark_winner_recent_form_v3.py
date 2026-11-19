"""Winner v3: strictly chronological testing of historical recent-form models.

Every winner candidate uses the EXACT SAME fitted multinomial fighter-method
head. Thus exact fighter+method difference isolates improvement in the winner
selection, not a simultaneous change of target, method or odds. Both fighters
are independently evaluated for conditional KO/SUB/DEC.

Research only. All 2024/2025/2026 fights have already been researched; NO
model promotion from retrospective scores, no rewritten UFC Qatar lock.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import csv,hashlib,json,math,random
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.historical_baselines import _winner_probabilities
from wshlx_ufc.finish_v1_research import (
    method_features, training_rows, MultinomialFinish,
    coherent_six, score_six, METHODS,
)
from wshlx_ufc.winner_recent_form_v3 import supplement_current_feature_matrix,N

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/model_health/2026-11-19_winner_v3_recent_form"
FOLDS=(
    ("2024","2024-01-01","2025-01-01",511),
    ("2025","2025-01-01","2026-01-01",513),
    ("2026_retrospective","2026-01-01","2026-11-14",488),
)
HEADS=("ufc_winrate","past_only_elo","logit_original_38",
       "logit_recent_57","boost_original_38","boost_recent_57")
TOTAL=38+N

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def matrices(feature,forms):
    base_a,base_b=method_features(feature,"a"),method_features(feature,"b")
    recent=forms.get(feature["bout_id"])
    if recent is None:raise ValueError("One UFC pre-event form row missing for "+feature["bout_id"])
    a,b=recent
    if len(a)!=N or len(b)!=N:raise ValueError("Form dimension mismatch")
    vectors=(np.r_[base_a,a],np.r_[base_b,b])
    if any(v.shape!=(TOTAL,) or not np.all(np.isfinite(v)) for v in vectors):
        raise ValueError("Invalid combined UFC winner features")
    return vectors

def fit_candidates(rows,forms,cutoff):
    X38=[]; X57=[]; y=[]
    for feature,label in rows:
        if feature["event_date"]>=cutoff:continue
        a,b=matrices(feature,forms)
        z38=a[:38]-b[:38]
        z57=a-b
        actual=int(label["label_a_win"])
        X38.extend((z38,-z38));X57.extend((z57,-z57))
        y.extend((actual,1-actual))
    if len(y)<2000:raise ValueError("Not enough past-only source winner examples")
    X38=np.asarray(X38,float);X57=np.asarray(X57,float)
    y=np.asarray(y,int)
    fit_logistic=lambda x:make_pipeline(
        StandardScaler(),LogisticRegression(C=.20,fit_intercept=False,max_iter=1800)
    ).fit(x,y)
    boost=lambda x:HistGradientBoostingClassifier(
        max_iter=160,learning_rate=.04,max_leaf_nodes=7,max_depth=3,
        min_samples_leaf=75,l2_regularization=25.,early_stopping=False,
        random_state=19,
    ).fit(x,y)
    return {
        "logit_original_38":fit_logistic(X38),
        "logit_recent_57":fit_logistic(X57),
        "boost_original_38":boost(X38),
        "boost_recent_57":boost(X57),
        "training_decisive_fights":len(y)//2,
    }

def heads(f,forms,models):
    a,b=matrices(f,forms)
    diff=a-b
    p=_winner_probabilities(f)
    results={"ufc_winrate":p["prior_ufc_win_rate"],
             "past_only_elo":p["past_only_ufc_elo"]}
    for key in HEADS[2:]:
        z=diff[:38] if key.endswith("_38") else diff
        classifier=models[key]
        pa=float(classifier.predict_proba(z.reshape(1,-1))[0,1])
        pb=float(classifier.predict_proba(-z.reshape(1,-1))[0,1])
        if key.startswith("logit_") and abs(pa+pb-1)>1e-10:
            raise ValueError("Linear winner symmetry broken")
        results[key]=(pa+1-pb)*.5
    if set(results)!=set(HEADS) or any(not 0<=x<=1 for x in results.values()):
        raise ValueError("Incomplete winner model family")
    return results

def scored(f,l,name,p,method):
    a,b=method_features(f,"a"),method_features(f,"b")
    cond=method.predict(np.vstack((a,b)))
    q=coherent_six(p,cond)
    truth=0 if int(l["label_a_win"])==1 else 1
    s=score_six(q,truth,l["label_method"],p_a=p)
    return {
        "event_date":f["event_date"],"event":f["event"],"bout_id":f["bout_id"],
        "fighter_a":f["fighter_a"],"fighter_b":f["fighter_b"],"head":name,
        "p_a":p,"winner_correct":s["winner_correct"],
        "exact":s["exact"],"pred_method":s["pred_method"],"actual_method":l["label_method"],
        "winner_brier":s["winner_brier"],
        "winner_logloss":-math.log(max(1e-12,p if int(l["label_a_win"]) else 1-p)),
        "six_logloss":s["six_log_loss"],"six_brier":s["six_brier"],
        "p_selected_exact":float(max(q[0:3] if p>=.5 else q[3:6])),
        "observed_min_ufc":int(min(f["a_prior_ufc_bouts"],f["b_prior_ufc_bouts"])),
        "observed_min_stats_cov":float(min(f["a_stats_coverage"],f["b_stats_coverage"])),
        "a_ko":float(q[0]),"a_sub":float(q[1]),"a_dec":float(q[2]),
        "b_ko":float(q[3]),"b_sub":float(q[4]),"b_dec":float(q[5]),
    }

def aggregate(rows):
    n=len(rows)
    if n<1:raise ValueError("No evaluation rows")
    return {
        "fights":n,"events":len({(x["event_date"],x["event"]) for x in rows}),
        "winner_hits":sum(x["winner_correct"] for x in rows),
        "winner_accuracy":sum(x["winner_correct"] for x in rows)/n,
        "exact_hits":sum(x["exact"] for x in rows),
        "exact_accuracy":sum(x["exact"] for x in rows)/n,
        "winner_brier":sum(x["winner_brier"] for x in rows)/n,
        "winner_logloss":sum(x["winner_logloss"] for x in rows)/n,
        "six_logloss":sum(x["six_logloss"] for x in rows)/n,
        "six_brier":sum(x["six_brier"] for x in rows)/n,
        "methods":{k:{
            "actual":sum(x["actual_method"]==k for x in rows),
            "predicted":sum(x["pred_method"]==k for x in rows),
            "correct_method":sum(x["pred_method"]==x["actual_method"]==k for x in rows),
        } for k in METHODS},
        "winner_confidence_over70_exact":{
            "fights":sum(max(x["p_a"],1-x["p_a"])>=.7 for x in rows),
            "exact_hits":sum(x["exact"] for x in rows if max(x["p_a"],1-x["p_a"])>=.7),
        },
    }

def event_paired_diff(candidates,benchmark,field,*,seed=19,n=500):
    if len(candidates)!=len(benchmark):raise ValueError("Paired sample size drift")
    groups=defaultdict(list)
    for a,b in zip(candidates,benchmark):
        if (a["bout_id"],a["event_date"])!=(b["bout_id"],b["event_date"]):
            raise ValueError("Non-identical bout alignment")
        groups[(a["event_date"],a["event"])].append(a[field]-b[field])
    events=sorted(groups)
    rng=random.Random(seed)
    diffs=[]
    for _ in range(n):
        draw=[events[rng.randrange(len(events))] for _ in events]
        values=[x for e in draw for x in groups[e]]
        diffs.append(sum(values)/len(values))
    diffs.sort()
    return {
        "candidate_minus_baseline":sum(a[field]-b[field] for a,b in zip(candidates,benchmark))/len(candidates),
        "cluster_event_bootstrap_95pct":[diffs[int(.025*(n-1))],diffs[int(.975*(n-1))]],
        "event_clusters":len(events),"resamples":n,
        "not_an_unseen_prospective_holdout":True,
    }

def main():
    features,labels,source=load_matrix()
    forms,form_source=supplement_current_feature_matrix(features)
    bylabels={l["bout_id"]:l for l in labels}
    if len(bylabels)!=len(labels) or form_source["modern_rows_unmatched"]:
        raise ValueError("Missing UFC forms or duplicate source labels")
    eligible=[(f,bylabels[f["bout_id"]]) for f in features if
              "2021-01-01"<=f["event_date"]<"2026-11-14" and
              bylabels[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(eligible)!=3015:raise ValueError("Historical population mismatch")
    results={};rows=[]
    for year,start,end,count in FOLDS:
        fit=fit_candidates(eligible,forms,start)
        tr_features=[f for f,l in eligible if f["event_date"]<start]
        tr_labels=[l for f,l in eligible if f["event_date"]<start]
        # Conditional method head fixed for every winner family on this fold.
        Xtrain,ytrain=training_rows(tr_features,tr_labels,start)
        method=MultinomialFinish().fit(Xtrain,ytrain)
        testing=[(f,l) for f,l in eligible if start<=f["event_date"]<end]
        if len(testing)!=count:raise ValueError("Unexpected chronological fold size")
        scored_by=defaultdict(list)
        for f,l in testing:
            probabilities=heads(f,forms,fit)
            a,b=method_features(f,"a"),method_features(f,"b")
            cond=method.predict(np.vstack((a,b)))
            for name,p in probabilities.items():
                q=coherent_six(p,cond)
                winner=0 if int(l["label_a_win"])==1 else 1
                s=score_six(q,winner,l["label_method"],p_a=p)
                observed={
                    "event_date":f["event_date"],"event":f["event"],"bout_id":f["bout_id"],
                    "fighter_a":f["fighter_a"],"fighter_b":f["fighter_b"],
                    "head":name,"p_a":p,"winner_correct":s["winner_correct"],
                    "exact":s["exact"],"pred_method":s["pred_method"],
                    "actual_method":l["label_method"],
                    "winner_brier":s["winner_brier"],
                    "winner_logloss":-math.log(max(1e-12,p if int(l["label_a_win"]) else 1-p)),
                    "six_logloss":s["six_log_loss"],"six_brier":s["six_brier"],
                    "p_selected_exact":float(max(q[:3] if p>=.5 else q[3:])),
                    "observed_min_ufc":int(min(f["a_prior_ufc_bouts"],f["b_prior_ufc_bouts"])),
                    "observed_min_stats_cov":float(min(f["a_stats_coverage"],f["b_stats_coverage"])),
                    "a_ko":float(q[0]),"a_sub":float(q[1]),"a_dec":float(q[2]),
                    "b_ko":float(q[3]),"b_sub":float(q[4]),"b_dec":float(q[5]),
                }
                scored_by[name].append(observed)
                rows.append(observed)
        scores={name:aggregate(v) for name,v in scored_by.items()}
        paired={}
        for name in HEADS[2:]:
            paired[name]={
                comparator:{
                    metric:event_paired_diff(scored_by[name],scored_by[comparator],metric)
                    for metric in ("winner_correct","exact","winner_brier","six_logloss")
                } for comparator in ("ufc_winrate","logit_original_38")
                if name!=comparator
            }
        results[year]={
            "train_before_exclusive":start,"tested_before_exclusive":end,
            "training_decisive_bouts":fit["training_decisive_fights"],
            "test_decisive_bouts":len(testing),
            "all_same_pretrained_method_head":True,
            "winner_models":scores,"event_cluster_paired":paired,
        }
    OUT.mkdir(parents=True,exist_ok=True)
    csvfile=OUT/"year_fold_winner_v3_six_exact.csv"
    with csvfile.open("w",newline="",encoding="utf-8") as h:
        writer=csv.DictWriter(h,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    report={
        "schema":"WSHLX_WINNER_V3_DATE_ASOF_STRIKING_FORM_RESEARCH",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "source_archive_stats_sha256":source["source_stats_sha256"],
        "source_recent_forms":form_source,
        "winner_heads":HEADS,
        "same_conditional_method_model_for_all_winner_heads":True,
        "method_model_trained_strictly_before_test_year":True,
        "no_bookmaker_odds_or_wager_promotion":True,
        "nov21_original_stage_a_and_coherent_shadow_not_modified":True,
        "chronological_years_previous_research_inspected_NOT_UNSEEN":True,
        "out_of_year_tests":results,"no_model_promoted":True,
        "prediction_csv_sha256":sha(csvfile),
    }
    (OUT/"winner_v3_results.json").write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "status":"RESEARCH_ONLY_NO_MODEL_PROMOTED",
        "asof_form_joins":form_source["modern_rows_joined"],
        "cohorts":{year:{name:{
            "winner_hits":d["winner_hits"],"exact_hits":d["exact_hits"],
            "winner_brier":round(d["winner_brier"],5),
            "six_logloss":round(d["six_logloss"],5)}
        for name,d in y["winner_models"].items()}
        for year,y in results.items()},
    },sort_keys=True))

if __name__=="__main__":main()
