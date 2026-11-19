"""Worldwide pro-MMA conditional METHOD v5 — independent finish classifier.

Addresses the project bottleneck: correct WINNER but wrong KO/SUB/DEC.
Fighter-specific finishing model is refit using 16 truly prior non-UFC
professional fight history features: KO/SUB/DEC wins and losses, past MMA
form, source coverage, identity missingness; compares to old 38-feature
conditional method model under the SAME frozen fitted v4 winner heads.

Conditional models are trained on winners of PAST fight dates ONLY.
For future/test bouts, probabilities are computed for BOTH candidate
winners, without using the true winner. The SIX joint probabilities
are proper and coherent. Scores primary EXACT fighter+method; separately
method recall and proper six-state log-loss/Brier, no forced SUB quotas.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import csv,json,hashlib,math,random
import numpy as np

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.winner_recent_form_v3 import supplement_current_feature_matrix
from wshlx_ufc.finish_v1_research import (
    method_features,training_rows,MultinomialFinish,HierarchicalFinish,
    coherent_six,score_six,METHODS,
)
from benchmark_worldwide_mma_winner_v4 import (
    load_external,train as train_winners,model_probas,HEADS,REGIONAL,
    REGIONAL_SOURCE_SHA,
)

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"reports/model_health/2026-11-19_worldwide_method_v5"
FOLDS=(("2024","2024-01-01","2025-01-01",511),
       ("2025","2025-01-01","2026-01-01",513),
       ("2026_retrospective","2026-01-01","2026-11-08",488))
MODEL_TYPES=("prior_UFC_only_multinomial38",
             "worldwide_MMA_multinomial54",
             "worldwide_MMA_hierarchical54")
WINNERS=("winner_v4_boost73","winner_v3_logit57")
FIGHT_STATUS="DECISIVE"

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def train_methods(eligible,external,prior_exclusive):
    oldX=[];addX=[];targets=[]
    for f,l in eligible:
        if not "2021-01-01"<=f["event_date"]<prior_exclusive:continue
        if f["feature_as_of_exclusive"]!=f["event_date"]:raise ValueError("Invalid time-safe fighter stat")
        a,b,verified=external[f["bout_id"]]
        side=0 if int(l["label_a_win"])==1 else 1
        orig=method_features(f,"a" if side==0 else "b")
        region=a if side==0 else b
        v=np.r_[orig,region]
        if v.shape!=(54,) or not np.all(np.isfinite(v)):
            raise ValueError("Winner conditional method+region feature shape")
        oldX.append(orig);addX.append(v)
        targets.append(l["label_method"])
    if len(addX)<1000 or set(targets)!=set(METHODS):
        raise ValueError("Insufficient correctly dated method training")
    base=np.asarray(oldX,float);new=np.asarray(addX,float)
    y=np.asarray(targets)
    models={
        "prior_UFC_only_multinomial38":MultinomialFinish().fit(base,y),
        "worldwide_MMA_multinomial54":MultinomialFinish().fit(new,y),
        "worldwide_MMA_hierarchical54":HierarchicalFinish().fit(new,y),
    }
    return models,len(y)

def conditional(f,external,models):
    a,b,_=external[f["bout_id"]]
    original=np.vstack((method_features(f,"a"),method_features(f,"b")))
    expanded=np.vstack((np.r_[original[0],a],np.r_[original[1],b]))
    if expanded.shape!=(2,54):raise ValueError("Both winners require regional matchup vectors")
    return {
      "prior_UFC_only_multinomial38":models["prior_UFC_only_multinomial38"].predict(original),
      "worldwide_MMA_multinomial54":models["worldwide_MMA_multinomial54"].predict(expanded),
      "worldwide_MMA_hierarchical54":models["worldwide_MMA_hierarchical54"].predict(expanded),
    }

def grade(f,l,winner_head,method_head,p,cond):
    q=coherent_six(p,cond)
    true_side=0 if int(l["label_a_win"]) else 1
    s=score_six(q,true_side,l["label_method"],p_a=p)
    return {
        "date":f["event_date"],"event":f["event"],"bout_id":f["bout_id"],
        "winner_head":winner_head,"method_head":method_head,
        "p_a":p,
        "winner_hit":s["winner_correct"],
        "method_class_hit":s["method_class_correct"],
        "exact_hit":s["exact"],
        "winner_correct_method_wrong":int(s["winner_correct"] and not s["exact"]),
        "actual_method":l["label_method"],"predicted_method":s["pred_method"],
        "winner_brier":s["winner_brier"],"six_brier":s["six_brier"],
        "six_logloss":s["six_log_loss"],
        "a_ko":q[0],"a_sub":q[1],"a_dec":q[2],
        "b_ko":q[3],"b_sub":q[4],"b_dec":q[5],
    }

def summary(rows):
    if not rows:raise ValueError("Empty method test set")
    n=len(rows);right=sum(x["winner_hit"] for x in rows)
    return {
        "n":n,"events":len({(x["date"],x["event"]) for x in rows}),
        "winner_hits":right,"exact_hits":sum(x["exact_hit"] for x in rows),
        "method_correct_given_winner_hit":sum(x["exact_hit"] for x in rows)/right if right else None,
        "method_class_hits":sum(x["method_class_hit"] for x in rows),
        "six_logloss":sum(x["six_logloss"] for x in rows)/n,
        "six_brier":sum(x["six_brier"] for x in rows)/n,
        "winner_brier":sum(x["winner_brier"] for x in rows)/n,
        "actual_class":{
            met:sum(r["actual_method"]==met for r in rows) for met in METHODS
        },
        "predicted_class":{
            met:sum(r["predicted_method"]==met for r in rows) for met in METHODS
        },
        "correct_method_class":{
            met:sum(r["actual_method"]==r["predicted_method"]==met for r in rows)
            for met in METHODS
        },
        "correct_exact_by_method":{
            met:sum(r["actual_method"]==r["predicted_method"]==met and r["exact_hit"]
                    for r in rows) for met in METHODS
        },
    }

def event_paired(candidate,benchmark,metric,seed=19,reps=500):
    if len(candidate)!=len(benchmark):raise ValueError("Different fight cohort")
    clusters=defaultdict(list)
    for a,b in zip(candidate,benchmark):
        if a["bout_id"]!=b["bout_id"] or a["date"]!=b["date"]:
            raise ValueError("Unmatched paired event")
        clusters[(a["date"],a["event"])].append(a[metric]-b[metric])
    eventkeys=sorted(clusters);rng=random.Random(seed);samples=[]
    for _ in range(reps):
        drawn=[eventkeys[rng.randrange(len(eventkeys))] for _ in eventkeys]
        vals=[v for key in drawn for v in clusters[key]]
        samples.append(sum(vals)/len(vals))
    samples.sort()
    return {"candidate_minus_UFC_only":sum(a[metric]-b[metric] for a,b in zip(candidate,benchmark))/len(candidate),
            "bootstrap95":[samples[int(.025*(reps-1))],samples[int(.975*(reps-1))]],
            "events":len(eventkeys),"retrospective_development_only":True}

def main():
    feats,labels,ufcmanifest=load_matrix()
    region,report=load_external(feats)
    recent,formsource=supplement_current_feature_matrix(feats)
    labelled={x["bout_id"]:x for x in labels}
    if len(labelled)!=len(labels):raise ValueError("Duplicate source outcomes")
    eligible=[(f,labelled[f["bout_id"]]) for f in feats if
              "2021-01-01"<=f["event_date"]<"2026-11-08" and
              labelled[f["bout_id"]]["result_status"]==FIGHT_STATUS]
    if len(eligible)!=3015:raise ValueError("Historical decisive cohort changed")
    allrows=[];annual={}
    for year,start,end,expected in FOLDS:
        trained_win=train_winners(eligible,recent,region,start)
        trained_methods,ntrain=train_methods(eligible,region,start)
        testing=[(f,l) for f,l in eligible if start<=f["event_date"]<end]
        if len(testing)!=expected:raise ValueError("Year's precise fight sample changed")
        scored=defaultdict(list)
        for f,l in testing:
            ph,_=model_probas(f,recent,region,trained_win)
            methods=conditional(f,region,trained_methods)
            for winner_head in WINNERS:
                for method_head in MODEL_TYPES:
                    r=grade(f,l,winner_head,method_head,ph[winner_head],methods[method_head])
                    scored[winner_head+"__"+method_head].append(r)
                    allrows.append(r)
        model_scores={key:summary(r) for key,r in scored.items()}
        comparisons={
            win:{
               challenger:{
                   metric:event_paired(
                        scored[win+"__"+challenger],
                        scored[win+"__prior_UFC_only_multinomial38"],
                        metric)
                   for metric in ("exact_hit","six_logloss","method_class_hit")
               }
               for challenger in MODEL_TYPES[1:]
            } for win in WINNERS
        }
        annual[year]={
            "evaluation_fights":len(testing),"training_method_fights":ntrain,
            "training_winner_fights":trained_win["n_training_fights"],
            "same_winner_head_within_method_comparison":True,
            "models":model_scores,
            "paired_method_family_changes":comparisons,
        }
    DEST.mkdir(parents=True,exist_ok=True)
    csvfile=DEST/"worldwide_mma_method_v5_datefold_forecasts.csv"
    with csvfile.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(allrows[0]))
        w.writeheader();w.writerows(allrows)
    result={
        "schema":"WSHLX_FIGHTER_SPECIFIC_WORLD_MMA_METHOD_V5_RESEARCH",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "source_ufc_stats_sha256":ufcmanifest["source_stats_sha256"],
        "regional_history_source_sha256":report["source_db_sha256"],
        "regional_feature_missingness_explicit":True,
        "two_potential_winner_methods_forecast_before_result":True,
        "new_method_head_trained_on_past_winners_only":True,
        "winner_head_FIXED_within_each_method_comparison":True,
        "win_method_exact_primary_metric":True,
        "no_fighter_prediction_or_method_global_quota":True,
        "all_original_nov21_reference_historical_unified_coherent_v3_v4_frozen_untouched":True,
        "2024_2026_already_inspected_NOT_NEW_PROSPECTIVE":True,
        "no_model_or_bet_promotion":True,
        "winner_head_variants":WINNERS,
        "method_head_variants":MODEL_TYPES,
        "yearly":annual,
        "predictions_csv_sha256":sha(csvfile),
    }
    (DEST/"worldwide_method_v5_results.json").write_text(
        json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "STATUS":"RESEARCH_ONLY_METHOD_V5_NO_PROMOTION",
        "source_sha":report["source_db_sha256"],
        "year_scores":{year:{name:{
            "winner_hits":m["winner_hits"],"exact_hits":m["exact_hits"],
            "six_logloss":round(m["six_logloss"],5),
            "SUB_correct":m["correct_method_class"]["SUB"],
            "SUB_called":m["predicted_class"]["SUB"],
        } for name,m in v["models"].items()} for year,v in annual.items()},
    },sort_keys=True))

if __name__=="__main__":main()
