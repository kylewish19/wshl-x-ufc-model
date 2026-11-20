"""Reproducible winner+method JOINT independent candidate research.

This addresses the blind spot of Finish v1: the historical winrate head was
fixed, preventing independent winner improvement. Separate winner models now
use date-lagged matchup contrasts. A jointly evaluated six-class forecast
joins each candidate winner P to *both* fighter-conditional method heads.
Chronological freeze years and exact selected fighter+method are primary.

All results are retrospective research, not unseen original Stage A locks.
No direct wagering, no FanDuel market odds, no promotion.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import re
import unicodedata
import numpy as np

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.finish_v1_research import (
    METHODS,train_candidate_family,method_features,score_six,aggregate,
)
from wshlx_ufc.independent_winner_v2 import (
    fit_winner_logistic,predict_winner,joint_from_conditional,
)

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/model_health/2026-11-18_joint_winner_finish_v2"
WINDOWS=(
    ("2024","2024-01-01","2025-01-01",511),
    ("2025","2025-01-01","2026-01-01",513),
    ("2026_retrospective","2026-01-01","2026-11-14",488),
)
METHOD_HEADS=("global_prior","hierarchical","multinomial")
WINNER_HEADS=("prior_ufc_winrate","past_only_elo","new_symmetric_logistic")
ORIGINAL_SLUGS=("ufc333_2026-10-24","ufcvegas124_2026-11-07")

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def join(labels):
    byid={x["bout_id"]:x for x in labels}
    if len(byid)!=len(labels):raise ValueError("Duplicate labels")
    return byid

def score(q,f,label,p_a):
    side=0 if int(label["label_a_win"])==1 else 1
    s=score_six(q,side,label["label_method"],p_a=p_a)
    return {**s,"date":f["event_date"],"event":f["event"],
            "bout_id":f["bout_id"],"fighter_a":f["fighter_a"],"fighter_b":f["fighter_b"],
            "p_a_win":p_a,"p_any_sub":float(q[1]+q[4]),
            "p_selected_exact":float(q[3*int(p_a<.5)+np.argmax(q[3*int(p_a<.5):3*int(p_a<.5)+3])]),
            "p_global_exact":float(np.max(q)),
            "actual_a_win":int(label["label_a_win"]),
            "actual_method":label["label_method"],
            "winner_log_loss":-math.log(max(1e-12,p_a if int(label["label_a_win"]) else 1-p_a))}

def summary(scored):
    agg=aggregate(scored)
    agg.update({
        "winner_log_loss":sum(x["winner_log_loss"] for x in scored)/len(scored),
        "expected_submissions":sum(x["p_any_sub"] for x in scored),
        "actual_submissions":sum(x["actual_method"]=="SUB" for x in scored),
        "events":len({(x["date"],x["event"]) for x in scored}),
        "selected_exact_prob_mean":sum(x["p_selected_exact"] for x in scored)/len(scored),
        "max_selected_exact_prob":max(x["p_selected_exact"] for x in scored),
    })
    return agg

def event_bootstrap(candidate,comparator,metric,*,seed=19,resamples=1000):
    if not candidate or len(candidate)!=len(comparator):raise ValueError("Unmatched cohort")
    d={}
    groups=defaultdict(list)
    for a,b in zip(candidate,comparator):
        k=(a["date"],a["event"],a["bout_id"])
        if k!=(b["date"],b["event"],b["bout_id"]):
            raise ValueError("Comparison must be identical fight-day identity")
        groups[k[:2]].append(a[metric]-b[metric])
    rng=random.Random(seed)
    events=sorted(groups)
    draws=[]
    for _ in range(resamples):
        picked=[events[rng.randrange(len(events))] for _ in events]
        all_vals=[v for e in picked for v in groups[e]]
        draws.append(sum(all_vals)/len(all_vals))
    draws.sort()
    return {
        "sample_fights":len(candidate),"event_clusters":len(events),
        "candidate_minus_comparator":sum(a[metric]-b[metric] for a,b in zip(candidate,comparator))/len(candidate),
        "event_bootstrap_95pct":[draws[int(.025*(resamples-1))],draws[int(.975*(resamples-1))]],
        "seed":seed,"resamples":resamples,
    }

def forecast_bundle(f,methods,winner):
    X=np.vstack((method_features(f,"a"),method_features(f,"b")))
    conditional={
        "global_prior":np.array([methods["prior"],methods["prior"]]),
        "hierarchical":methods["hierarchical"].predict(X),
        "multinomial":methods["multinomial"].predict(X),
    }
    wp=predict_winner(f,winner)
    return {
        w+"__"+m:(float(p),joint_from_conditional(float(p),cm))
        for w,p in wp.items() for m,cm in conditional.items()
    }

def build_fold(features,labels,before,end,expected):
    bl=join(labels)
    methods=train_candidate_family(features,labels,before)
    winner=fit_winner_logistic(features,labels,before=before)
    candidates=[f for f in features if before<=f["event_date"]<end
                and bl[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(candidates)!=expected:raise ValueError("Historical period count drift")
    predictions=defaultdict(list)
    rows=[]
    for f in candidates:
        label=bl[f["bout_id"]]
        for name,(p,q) in forecast_bundle(f,methods,winner).items():
            scored=score(q,f,label,p)
            predictions[name].append(scored)
            rows.append({
                "event_date":f["event_date"],"event":f["event"],
                "bout_id":f["bout_id"],"fighter_a":f["fighter_a"],
                "fighter_b":f["fighter_b"],"variant":name,
                "p_a_win":p,"a_ko":float(q[0]),"a_sub":float(q[1]),
                "a_dec":float(q[2]),"b_ko":float(q[3]),"b_sub":float(q[4]),
                "b_dec":float(q[5]),"actual_a_win":label["label_a_win"],
                "actual_method":label["label_method"],
                "selected_fighter_exact":scored["exact"],
                "winner_correct":scored["winner_correct"],
                "winner_brier":scored["winner_brier"],
                "six_log_loss":scored["six_log_loss"],
                "six_brier":scored["six_brier"],
                "method_prediction":scored["pred_method"],
            })
    out={
        "fit_before_exclusive":before,
        "method_training_n":methods["train_n"],
        "winner_training_n":winner["training_decisive_bouts"],
        "eval_count":len(candidates),
        "candidates":{k:summary(predictions[k]) for k in predictions},
        "paired_tests":{
            m:{
                "winner_brier":event_bootstrap(
                    predictions["new_symmetric_logistic__"+m],
                    predictions["prior_ufc_winrate__"+m],
                    "winner_brier"),
                "six_log_loss":event_bootstrap(
                    predictions["new_symmetric_logistic__"+m],
                    predictions["prior_ufc_winrate__"+m],
                    "six_log_loss"),
                "exact":event_bootstrap(
                    predictions["new_symmetric_logistic__"+m],
                    predictions["prior_ufc_winrate__"+m],
                    "exact"),
            } for m in METHOD_HEADS
        },
    }
    return out,rows,methods,winner

def normalize_name(n):
    s=unicodedata.normalize("NFKD",str(n)).encode("ascii","ignore").decode("ascii").casefold()
    return re.sub("[^a-z0-9]","",s)

def fight_key(date,a,b):
    return (date,*sorted([normalize_name(a),normalize_name(b)]))

def frozen_comparison(features,labels,methods,winner):
    index={}
    bl=join(labels)
    for f in features:
        k=fight_key(f["event_date"],f["fighter_a"],f["fighter_b"])
        if k in index:raise ValueError("Duplicate canonical date-pair")
        index[k]=f
    score_sets=defaultdict(list)
    evidence=[]
    for slug in ORIGINAL_SLUGS:
        root=ROOT/"data/locks"/slug
        finalpath=root/"stage_a_final_selection.json"
        original=root/"stage_a_model_raw_three_view.json"
        fz=json.loads(finalpath.read_text())
        raw=json.loads(original.read_text())
        if not fz["stage_a_frozen"] or fz["odds_used"] or raw["odds_used"] or sha(original)!=fz["raw_model_sha256"]:
            raise ValueError("Original lock tampered/missing")
        evidence.append({"source":str(original.relative_to(ROOT)),
                         "sha256":sha(original),"frozen":fz["frozen_at_utc"]})
        for entry in raw["fights"]:
            f=index.get(fight_key(raw["event_date"],entry["a"],entry["b"]))
            if f is None:raise ValueError("Unknown original bout")
            label=bl[f["bout_id"]]
            if label["result_status"]!="DECISIVE":raise ValueError("Original sample includes draw")
            reversed_order=normalize_name(entry["a"])==normalize_name(f["fighter_b"])
            if not reversed_order and normalize_name(entry["a"])!=normalize_name(f["fighter_a"]):
                raise ValueError("Identity mismatch")
            pmodels={
                "original_reference":(entry["winner_reference_p_a"],entry["joint_calibrated"]),
                "original_historical":(entry["historical_shadow"]["winner_p_a"],entry["historical_shadow"]["joint_method"]),
                "original_unified":(entry["oof_unified_shadow"]["winner_p_a"],entry["oof_unified_shadow"]["joint_method"]),
            }
            for name,(p,d) in pmodels.items():
                p=float(1-p if reversed_order else p)
                q=np.array([d[k] for k in ("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")],float)
                if reversed_order:q=q[[3,4,5,0,1,2]]
                # Original native six-way probability retained unadjusted;
                # independent winner head may differ from joint marginal.
                score_sets[name].append(score(q,f,label,p))
            new=forecast_bundle(f,methods,winner)
            for name,(p,q) in new.items():
                score_sets[name].append(score(q,f,label,p))
    if len(score_sets)!=12 or any(len(x)!=28 for x in score_sets.values()):
        raise ValueError("28-fight original model join drift")
    return {"origins":evidence,
            "method_and_winner_new_heads_train_to":"2025-12-31",
            "cohort_28":{"models":{m:summary(s) for m,s in score_sets.items()},
                         "paired_vs_original_historical":{
                            name:{
                                "exact":event_bootstrap(score_sets[name],score_sets["original_historical"],"exact"),
                                "six_log_loss":event_bootstrap(score_sets[name],score_sets["original_historical"],"six_log_loss"),
                            }
                            for name in score_sets if name.startswith("new_")
                         }},
            "original_native_six_may_disagree_with_native_winner_head":True,
            "no_training_or_candidate_selection_using_these_28_outcomes":True}

def main():
    features,labels,manifest=load_matrix()
    all_reports,all_rows={},[]
    latest=None
    for year,before,end,expected in WINDOWS:
        report,rows,methods,winner=build_fold(features,labels,before,end,expected)
        all_reports[year]=report
        all_rows.extend(rows)
        if year=="2026_retrospective":latest=(methods,winner)
    matched=frozen_comparison(features,labels,*latest)
    OUTPUT=OUT
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with (OUTPUT/"all_date_fold_forecasts.csv").open("w",newline="",encoding="utf-8") as h:
        writer=csv.DictWriter(h,fieldnames=list(all_rows[0]))
        writer.writeheader();writer.writerows(all_rows)
    result={
        "schema":"WSHLX_INDEPENDENT_WINNER_AND_METHOD_V2_2026_11_18",
        "research_not_production":True,
        "data_source_sha256":manifest["source_stats_sha256"],
        "method_training_actual_winners_only_pre_cutoff_but_both_prediction_sides_scored":True,
        "winner_training_mirrors_both_roles_and_excludes_actual_method":True,
        "date_asof_exclusive_and_year_chronological":True,
        "already_studied_2026_not_pristine":True,
        "method_models_compared_on_same_winner_heads":True,
        "frozen_nov21_and_all_fanduel_original_picks_unchanged":True,
        "no_promotion":True,
        "dates":{"prepared_at_utc":datetime.now(timezone.utc).isoformat()},
        "folds":all_reports,
        "matched_two_frozen_cards":matched,
        "source_forecast_csv_sha256":sha(OUTPUT/"all_date_fold_forecasts.csv"),
    }
    (OUTPUT/"joint_v2_evaluation.json").write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "status":"RESEARCH_ONLY_WINNER_AND_METHOD_NO_PROMOTION",
        "per_year":{year:{
            "prior_rate_plus_multinomial":r["candidates"]["prior_ufc_winrate__multinomial"],
            "new_winner_plus_multinomial":r["candidates"]["new_symmetric_logistic__multinomial"],
            "new_winner_plus_hierarchical":r["candidates"]["new_symmetric_logistic__hierarchical"],
        } for year,r in all_reports.items()},
        "matched_28":{k:v for k,v in matched["cohort_28"]["models"].items()
                      if k in ("original_reference","original_historical","original_unified",
                               "new_symmetric_logistic__multinomial",
                               "new_symmetric_logistic__hierarchical")},
    },sort_keys=True,allow_nan=False))

if __name__=="__main__":
    main()
