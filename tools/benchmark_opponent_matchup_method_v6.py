"""WSHL_X matchup conditional finish v6, chronologically nested tuning.

Correct fight+KO/SUB/DEC, not merely method class.
The existing 38 UFC method features ALREADY use opponent vulnerability.
New 70/108/115 architectures ADD previously missing regional opponent
finish vulnerability and both fighters' recent UFC striking/takedown
features, plus seven prespecified opponent-relative interactions.

Strict temporal guard: 2024 candidates' C tuned on 2023; 2025 on 2024;
2026 on 2025, fitting only dates EARLIER than validation years.
Each full-fitted model uses ONLY data before its target year. Target
year results are never used to choose C or coefficients. Hist 2024-26
already inspected in other research and NOT a pristine holdout.

Same two separately trained winner heads for all method candidates
(the unchanged 57-feature logit and unchanged 73-feature boosted models).
Original prospectively locked November21 Stage A and research sidecars
remain unmodified. NO betting permissions, no automatic model promotion.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from math import log
import csv,hashlib,json,random
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.winner_recent_form_v3 import supplement_current_feature_matrix,N
from wshlx_ufc.finish_v1_research import (
    METHODS, method_features,coherent_six,score_six,
)
from benchmark_worldwide_mma_winner_v4 import (
    load_external,train as fit_winner,model_probas,REGIONAL_SOURCE_SHA
)

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"reports/model_health/2026-11-19_matchup_method_v6"
FOLDS=(("2024","2024-01-01","2025-01-01","2023-01-01",511),
       ("2025","2025-01-01","2026-01-01","2024-01-01",513),
       ("2026_retrospective","2026-01-01","2026-11-08","2025-01-01",488))
PRIMARY_WINNERS=("winner_v3_logit57","winner_v4_boost73")
METHODS_MODELS=("ufc_only_38","regional_self_54",
    "regional_opp_70_tuned","recent_both_108_tuned",
    "opponent_interactions_115_tuned","opponent_boost_115")
TUNED=("regional_opp_70_tuned","recent_both_108_tuned",
    "opponent_interactions_115_tuned")
C_GRID=(.005,.025,.10,.35)
DIMS={"ufc_only_38":38,"regional_self_54":54,
      "regional_opp_70_tuned":70,"recent_both_108_tuned":108,
      "opponent_interactions_115_tuned":115,"opponent_boost_115":115}
assert 38+16+16+N+N+7==115

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def vectors(f,external,recent):
    if f["feature_as_of_exclusive"]!=f["event_date"]:
        raise ValueError("Date leakage in source fighter features")
    olda=method_features(f,"a")
    oldb=method_features(f,"b")
    ra,rb,verified=external[f["bout_id"]]
    ua,ub=recent[f["bout_id"]]
    if any(len(z)!=length for z,length in (
        (olda,38),(oldb,38),(ra,16),(rb,16),(ua,19),(ub,19))):
        raise ValueError("Missing dimensions of source-as-of prefight features")
    def interactions(attacker_ufc,defender_ufc,attacker_region,defender_region,
                     attacker_recent,defender_recent):
        # Regional KO/SUB tendencies x defender regional method losses;
        # date-lagged striking offensive x opponent defensive performance;
        # takedown + submission access in the 3 prior UFC fights.
        return np.array([
            attacker_region[4]*defender_region[7],
            attacker_region[5]*defender_region[8],
            attacker_region[6]*defender_region[9],
            attacker_recent[10]*defender_recent[11],
            attacker_recent[12]*defender_ufc[13],
            attacker_recent[13]*(1.-defender_recent[6]),
            attacker_recent[14]*defender_region[8],
        ],dtype=float)
    def make(own38,rival38,ownregion,oppregion,ownrecent,opprecent):
        cols=np.r_[own38,ownregion,oppregion,ownrecent,opprecent,
                   interactions(own38,rival38,ownregion,oppregion,ownrecent,opprecent)]
        if cols.shape!=(115,) or not np.all(np.isfinite(cols)):
            raise ValueError("Invalid opponent-relative historical fighter method features")
        return cols
    return make(olda,oldb,ra,rb,ua,ub),make(oldb,olda,rb,ra,ub,ua),verified

def training_matrix(cohort,external,recent):
    rows=[]
    for f,l in cohort:
        a,b,verified=vectors(f,external,recent)
        side=0 if int(l["label_a_win"]) else 1
        rows.append({
            "date":f["event_date"],"event":f["event"],"id":f["bout_id"],
            "Xwinner":a if side==0 else b,"Xa":a,"Xb":b,
            "method":l["label_method"],"win_a":int(l["label_a_win"]),
            "ufc_debutant":min(int(f["a_ufc_prior_bouts"]),int(f["b_ufc_prior_bouts"]))==0,
            "regional_verified":verified,
        })
    return rows

def fit_logit(X,y,c):
    model=make_pipeline(StandardScaler(),
        LogisticRegression(C=c,max_iter=1800))
    model.fit(X,y)
    return model

def fit_boost(X,y):
    model=HistGradientBoostingClassifier(
        max_iter=140,learning_rate=.035,max_leaf_nodes=7,max_depth=3,
        min_samples_leaf=65,l2_regularization=20,early_stopping=False,
        random_state=19)
    model.fit(X,y)
    return model

def methods_ordered(model,X):
    idx=[list(model[-1].classes_ if hasattr(model,"steps") else model.classes_).index(m)
          for m in METHODS]
    pred=model.predict_proba(X)
    q=np.asarray(pred[:,idx],dtype=float)
    if q.shape!=(len(X),3) or not np.all(np.isfinite(q)) or np.any(q<0) or np.max(abs(q.sum(axis=1)-1))>1e-9:
        raise ValueError("Invalid candidate conditional method probabilities")
    return q

def inner_tune_c(trainrows,foldstart,valstart,dim):
    earlier=[r for r in trainrows if r["date"]<valstart]
    val=[r for r in trainrows if valstart<=r["date"]<foldstart]
    if min(len(earlier),len(val))<100 or len({r["method"] for r in earlier})!=3:
        raise ValueError("Not enough strictly earlier independent validation data")
    x=np.array([r["Xwinner"][:dim] for r in earlier])
    y=np.array([r["method"] for r in earlier])
    vx=np.array([r["Xwinner"][:dim] for r in val])
    vy=[r["method"] for r in val]
    m2i={m:i for i,m in enumerate(METHODS)}
    vindex=np.array([m2i[m] for m in vy])
    losses={}
    for C in C_GRID:
        p=methods_ordered(fit_logit(x,y,C),vx)
        losses[str(C)]=float(-np.log(np.maximum(1e-12,p[np.arange(len(val)),vindex])).mean())
    winner=min(C_GRID,key=lambda c:(losses[str(c)],c))
    return {
        "chosen_C":winner,"validation_n":len(val),"train_n":len(earlier),
        "validation_loss_by_coefficient":losses,
        "validation_minimization_metric":"conditional method log loss, NOT target-year exact hit rate",
        "training_ends_strictly_before_validation_start":True,
        "test_year_excluded_from_tuning":True,
    }

def fit_models(rows,teststart,valstart):
    train=[r for r in rows if r["date"]<teststart]
    X=np.array([r["Xwinner"] for r in train],float)
    y=np.array([r["method"] for r in train])
    tuned={m:inner_tune_c(train,teststart,valstart,DIMS[m]) for m in TUNED}
    models={
        "ufc_only_38":fit_logit(X[:,:38],y,.2),
        "regional_self_54":fit_logit(X[:,:54],y,.2),
        "regional_opp_70_tuned":fit_logit(X[:,:70],y,tuned["regional_opp_70_tuned"]["chosen_C"]),
        "recent_both_108_tuned":fit_logit(X[:,:108],y,tuned["recent_both_108_tuned"]["chosen_C"]),
        "opponent_interactions_115_tuned":fit_logit(X,y,tuned["opponent_interactions_115_tuned"]["chosen_C"]),
        "opponent_boost_115":fit_boost(X,y),
    }
    if set(models)!=set(METHODS_MODELS):raise ValueError("Incomplete methodological challenger set")
    return models,tuned,len(train)

def evaluate(f,l,row,method_models,winheads):
    vals=np.vstack([row["Xa"],row["Xb"]])
    conditional={name:methods_ordered(model,vals[:,:DIMS[name]])
                 for name,model in method_models.items()}
    out=[]
    for winner in PRIMARY_WINNERS:
        p=winheads[winner]
        for name in METHODS_MODELS:
            q=coherent_six(p,conditional[name])
            scored=score_six(q,0 if int(l["label_a_win"]) else 1,l["label_method"],p_a=p)
            out.append({
                "event_date":f["event_date"],"event":f["event"],"bout_id":f["bout_id"],
                "winner_head":winner,"method_head":name,
                "winner_probability_a":float(p),
                "winner_hit":int(scored["winner_correct"]),
                "exact_hit":int(scored["exact"]),
                "method_hit":int(scored["method_class_correct"]),
                "actual_method":l["label_method"],"called_method":scored["pred_method"],
                "winner_correct_method_wrong":int(scored["winner_correct"] and not scored["exact"]),
                "p_own_exact":float(max(q[:3] if p>=.5 else q[3:])),
                "six_logloss":float(scored["six_log_loss"]),
                "six_brier":float(scored["six_brier"]),
                "min_prior_ufc_zero":int(row["ufc_debutant"]),
                "regional_both_verified":int(row["regional_verified"]),
                "a_ko":float(q[0]),"a_sub":float(q[1]),"a_dec":float(q[2]),
                "b_ko":float(q[3]),"b_sub":float(q[4]),"b_dec":float(q[5]),
            })
    return out

def summary(rows):
    n=len(rows)
    if not n:raise ValueError("Empty grade")
    return {
        "n":n,"events":len({(x["event_date"],x["event"]) for x in rows}),
        "winner_hits":sum(x["winner_hit"] for x in rows),
        "exact_hits":sum(x["exact_hit"] for x in rows),
        "exact_accuracy":sum(x["exact_hit"] for x in rows)/n,
        "method_hit_given_correct_winner":sum(x["exact_hit"] for x in rows)/sum(x["winner_hit"] for x in rows),
        "method_class_hits":sum(x["method_hit"] for x in rows),
        "correct_fighter_wrong_method":sum(x["winner_correct_method_wrong"] for x in rows),
        "six_logloss":sum(x["six_logloss"] for x in rows)/n,
        "six_brier":sum(x["six_brier"] for x in rows)/n,
        "submissions":{
            "actual":sum(x["actual_method"]=="SUB" for x in rows),
            "called":sum(x["called_method"]=="SUB" for x in rows),
            "correct_class":sum(x["called_method"]==x["actual_method"]=="SUB" for x in rows),
            "correct_exact":sum(x["exact_hit"] and x["actual_method"]=="SUB" for x in rows),
        },
    }

def paired(a,b,field,seed=19,reps=300):
    if len(a)!=len(b):raise ValueError("Paired sample mismatch")
    diffs=defaultdict(list)
    for x,y in zip(a,b):
        if (x["bout_id"],x["event_date"])!=(y["bout_id"],y["event_date"]):
            raise ValueError("Paired identity mismatch")
        diffs[(x["event_date"],x["event"])].append(x[field]-y[field])
    events=sorted(diffs);rng=random.Random(seed);samples=[]
    for _ in range(reps):
        selected=[events[rng.randrange(len(events))] for _ in events]
        vals=[n for key in selected for n in diffs[key]]
        samples.append(sum(vals)/len(vals))
    samples.sort()
    return {"candidate_minus_current_regional54":sum(x[field]-y[field] for x,y in zip(a,b))/len(a),
            "event_cluster_95pct":[samples[int(.025*(reps-1))],samples[int(.975*(reps-1))]],
            "clusters":len(events),"retrospective_studied_years":True}

def reliable_picks(rows):
    cards=defaultdict(list)
    for x in rows:cards[(x["event_date"],x["event"])].append(x)
    groups=[r for r in cards.values() if 11<=len(r)<=14]
    counts={}
    for k in (2,3,5):
        arr=[sorted(rs,key=lambda r:(-r["p_own_exact"],r["bout_id"]))[:k] for rs in groups]
        counts[str(k)]={"eligible_cards":len(groups),
            "selections":len(groups)*k,
            "exact_hits":sum(z["exact_hit"] for batch in arr for z in batch),
            "perfect_selection_groups":sum(all(z["exact_hit"] for z in batch) for batch in arr)}
    return counts

def main():
    features,labels,manifest=load_matrix()
    external,regionmeta=load_external(features)
    recent,recentmeta=supplement_current_feature_matrix(features)
    labelmap={x["bout_id"]:x for x in labels}
    cohort=[(f,labelmap[f["bout_id"]]) for f in features
            if "2021-01-01"<=f["event_date"]<"2026-11-08"
            and labelmap[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(cohort)!=3015:raise ValueError("3015 strict event-date decisive source cohort mismatch")
    rows=training_matrix(cohort,external,recent)
    lookup={r["id"]:r for r in rows}
    if len(lookup)!=3015:raise ValueError("Duplicate source fighter matchup features")
    results={};out=[]
    for year,start,end,valstart,n in FOLDS:
        models,tuning,ntrain=fit_models(rows,start,valstart)
        winmodels=fit_winner(cohort,recent,external,start)
        test=[(f,l) for f,l in cohort if start<=f["event_date"]<end]
        if len(test)!=n:raise ValueError("Changed independent test-year fight coverage")
        graded=defaultdict(list)
        for f,l in test:
            ps,_=model_probas(f,recent,external,winmodels)
            for q in evaluate(f,l,lookup[f["bout_id"]],models,ps):
                graded[q["winner_head"]+"__"+q["method_head"]].append(q)
                out.append(q)
        stats={key:summary(group) for key,group in graded.items()}
        delta={}
        for winner in PRIMARY_WINNERS:
            reference=graded[winner+"__regional_self_54"]
            delta[winner]={}
            for name in METHODS_MODELS:
                if name=="regional_self_54":continue
                candidate=graded[winner+"__"+name]
                delta[winner][name]={
                    field:paired(candidate,reference,field)
                    for field in ("exact_hit","six_logloss","method_hit")
                }
        results[year]={
            "train_before_exclusive":start,"inner_validation_start":valstart,
            "eval_before_exclusive":end,"eval_n":len(test),
            "training_method_n":ntrain,
            "chosen_coefficients_from_PREVIOUS_calendar_year_ONLY":tuning,
            "same_winner_heads_for_every_method_family":True,
            "scores":stats,"event_cluster_comparison":delta,
            "max2to5_exact_ranking":{
                key:reliable_picks(group) for key,group in graded.items()
            },
            "debutant_2026":{
                key:{
                    "has_debutant":summary([r for r in group if r["min_prior_ufc_zero"]]),
                    "no_debutant":summary([r for r in group if not r["min_prior_ufc_zero"]]),
                } for key,group in graded.items()
            } if year.startswith("2026") else None,
        }
    DEST.mkdir(parents=True,exist_ok=True)
    csvfile=DEST/"method_v6_2024_26_asof_bout_forecasts.csv"
    with csvfile.open("w",newline="",encoding="utf-8") as h:
        w=csv.DictWriter(h,fieldnames=list(out[0]))
        w.writeheader();w.writerows(out)
    report={
        "schema":"WSHLX_FIGHTER_VS_OPPONENT_MATCHUP_METHOD_V6_NESTED_COEFFICIENT_RESEARCH",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_ufc_archive_sha256":manifest["source_stats_sha256"],
        "source_FightCanon_database_SHA256":REGIONAL_SOURCE_SHA,
        "source_regional_audit":regionmeta,
        "source_recent_form_audit":recentmeta,
        "model_names":METHODS_MODELS,"winner_heads_fixed":PRIMARY_WINNERS,
        "model_feature_dimensionalities":DIMS,
        "coefficient_candidates_prespecified":C_GRID,
        "same_winner_head_within_all_method_comparisons":True,
        "all_inner_coefficient_tuning_uses_past_year_conditional_logloss_NOT_test_labels":True,
        "comparison_to_38_already_opponent_UFC_conditioned":True,
        "new_opp_region_and_prior_UFC_recent_stats_date_lagged":True,
        "historical_2024_2026_NOT_pristine_prospective":True,
        "nov21_original_and_v3_v4_v5_SHA_locked_artifacts_untouched":True,
        "model_promotion_or_betting_authority":False,
        "all_fights_on_same_test_year_identical":True,
        "yearly":results,"out_of_year_forecast_sha256":sha(csvfile),
    }
    (DEST/"method_v6_results.json").write_text(
        json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"status":"NESTED_MATCHUP_METHOD_V6_RESEARCH_ONLY",
       "yearly":{yr:{name:{
          "winner":d["winner_hits"],"exact":d["exact_hits"],
          "six_logloss":round(d["six_logloss"],5),
          "sub_correct":d["submissions"]["correct_class"]
       } for name,d in vals["scores"].items()}
       for yr,vals in results.items()},"model_promoted":False},sort_keys=True))

if __name__=="__main__":main()
