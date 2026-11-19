"""Worldwide opponent-quality Elo Winner v8 vs verified Winner v4 baseline.

Uses actual prior pro fight opponents' chronological strength, NOT merely
counting fighter's W/L over unknown regional quality. Same undefeated
fighter vs 0–10s can be rated differently from one beating elite opponents.

Four winner heads share the SAME independently trained conditional method
head, held fixed within exact fighter+KO/SUB/DEC comparisons:
  v4 logistic73 vs v8 logistic77,
  v4 boosted73 vs v8 boosted77.

No odds, no new production models, no Nov21 Stage A/Coherent/v3-v5
retroactively rewritten. Historical 2024/25/26 years already researched.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import csv,hashlib,json,random
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.winner_recent_form_v3 import supplement_current_feature_matrix
from wshlx_ufc.worldwide_opponent_elo_v8 import build as build_world_elo,FIELDS
from wshlx_ufc.finish_v1_research import (
    method_features,coherent_six,score_six,METHODS
)
from benchmark_worldwide_mma_winner_v4 import (
    load_external,vector as v4_vector,
    REGIONAL_SOURCE_SHA,REGIONAL,SOURCEROWS
)
from benchmark_worldwide_method_v5 import train_methods,conditional
from audit_worldwide_mma_history_v4 import get_tables,DB

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/model_health/2026-11-19_global_elo_winner_v8"
FOLDS=(("2024","2024-01-01","2025-01-01",511),
       ("2025","2025-01-01","2026-01-01",513),
       ("2026_retrospective","2026-01-01","2026-11-08",488))
HEADS=("v4_logit73","v8_worldelo_logit77",
       "v4_boost73","v8_worldelo_boost77")
DIMS={k:(77 if "77" in k else 73) for k in HEADS}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def enrich(features,external,recent):
    if sha(DB)!=REGIONAL_SOURCE_SHA:raise ValueError("Global MMA source vintage mismatch")
    prior_raw=json.loads(SOURCEROWS.read_text())
    verified={r["bout_id"]:r for r in prior_raw}
    if len(verified)!=len(prior_raw):raise ValueError("Repeated verified UFC source fight")
    requested=defaultdict(set)
    for f in features:
        if not "2021-01-01"<=f["event_date"]<"2026-11-08":continue
        raw=verified.get(f["bout_id"])
        if raw is None:continue
        if (raw["date"],raw["fighter_a"],raw["fighter_b"])!=(
            f["event_date"],f["fighter_a"],f["fighter_b"]):
            raise ValueError("Opponent Elo joined to wrong UFC fighter")
        requested[f["event_date"]].update(
            (int(raw["a_verified_id"]),int(raw["b_verified_id"])))
    conn=get_tables(DB)
    indexed,manifest=build_world_elo(requested,conn)
    summary={"missing_UFC_source_pairs":0,"verified_UFC_source_pairs":0,
             "any_UFC_debutant_matched":0,"any_UFC_debutant_unmatched":0}
    values={}
    for f in features:
        if not "2021-01-01"<=f["event_date"]<"2026-11-08":continue
        record=verified.get(f["bout_id"])
        if record is None:
            q=np.zeros(4,float);values[f["bout_id"]]=(q,q.copy(),False)
            summary["missing_UFC_source_pairs"]+=1
            if min(f["a_ufc_prior_bouts"],f["b_ufc_prior_bouts"])==0:
                summary["any_UFC_debutant_unmatched"]+=1
        else:
            ar=indexed.get((f["event_date"],int(record["a_verified_id"])))
            br=indexed.get((f["event_date"],int(record["b_verified_id"])))
            if ar is None or br is None:raise ValueError("Missing pre-day professional opponent strength")
            values[f["bout_id"]]=(np.asarray(ar,float),np.asarray(br,float),True)
            summary["verified_UFC_source_pairs"]+=1
            if min(f["a_ufc_prior_bouts"],f["b_ufc_prior_bouts"])==0:
                summary["any_UFC_debutant_matched"]+=1
    if len(values)!=3036 or summary["verified_UFC_source_pairs"]!=3016:
        raise ValueError("Global MMA opponent strength cohort/identity drift")
    if any(x[0].shape!=(4,) or x[1].shape!=(4,) for x in values.values()):
        raise ValueError("Invalid professional MMA Elo features")
    return values,{**manifest,**summary,
            "feature_list":FIELDS,
            "external_fight_history_source_sha256":REGIONAL_SOURCE_SHA,
            "UFC_fight_2012_2026_not_transferred_to_unverified_name":True}

def vector(f,recent,region,world):
    a,b,verified=v4_vector(f,recent,region)
    c,d,ok=world[f["bout_id"]]
    if verified!=ok:raise ValueError("Past professional and UFC fighter identity provenance differs")
    result=(np.r_[a,c],np.r_[b,d])
    if any(v.shape!=(77,) or not np.all(np.isfinite(v)) for v in result):
        raise ValueError("Incorrect historical 77-feature opponent-strength vector")
    return *result,verified

def train(cohort,recent,region,world,test_before):
    X73=[];X77=[];y=[]
    for f,l in cohort:
        if f["event_date"]>=test_before:continue
        a,b,_=vector(f,recent,region,world)
        d=a-b
        X73.extend((d[:73],-d[:73]))
        X77.extend((d,-d))
        w=int(l["label_a_win"])
        y.extend((w,1-w))
    if len(y)<2000:raise ValueError("Historical train size inconsistent")
    x=np.asarray(X73);xx=np.asarray(X77);target=np.asarray(y)
    def logistic(t):return make_pipeline(
        StandardScaler(),LogisticRegression(C=.20,fit_intercept=False,max_iter=1800)
    ).fit(t,target)
    def nonlinear(t):return HistGradientBoostingClassifier(
        max_iter=160,learning_rate=.04,max_leaf_nodes=7,max_depth=3,
        min_samples_leaf=75,l2_regularization=25,early_stopping=False,
        random_state=19).fit(t,target)
    return {
        "v4_logit73":logistic(x),"v8_worldelo_logit77":logistic(xx),
        "v4_boost73":nonlinear(x),"v8_worldelo_boost77":nonlinear(xx),
        "training_decisive_fights":len(y)//2,
    }

def winner_proba(f,recent,region,world,models):
    a,b,_=vector(f,recent,region,world)
    difference=a-b
    out={}
    for model in HEADS:
        v=difference[:DIMS[model]]
        clf=models[model]
        forward=float(clf.predict_proba(v.reshape(1,-1))[0,1])
        backward=float(clf.predict_proba((-v).reshape(1,-1))[0,1])
        if model.startswith(("v4_logit","v8_worldelo_logit")):
            if abs(forward+backward-1)>1e-10:raise ValueError("Winner symmetry guard")
        out[model]=(forward+1-backward)*.5
    return out

def grade(f,l,head,p,condition):
    q=coherent_six(p,condition)
    s=score_six(q,0 if l["label_a_win"] else 1,l["label_method"],p_a=p)
    return {
        "bout_id":f["bout_id"],"date":f["event_date"],"event":f["event"],
        "head":head,"p_a":float(p),
        "winner_hit":s["winner_correct"],"exact_hit":s["exact"],
        "method_class_hit":s["method_class_correct"],
        "actual_method":l["label_method"],"selected_method":s["pred_method"],
        "six_logloss":s["six_log_loss"],"six_brier":s["six_brier"],
        "winner_brier":s["winner_brier"],
        "p_own_exact":float(max(q[:3] if p>=.5 else q[3:])),
        "a_ko":q[0],"a_sub":q[1],"a_dec":q[2],
        "b_ko":q[3],"b_sub":q[4],"b_dec":q[5],
    }

def aggregate(rows):
    n=len(rows)
    return {
        "n":n,"events":len({(r["date"],r["event"]) for r in rows}),
        "winner_hits":sum(r["winner_hit"] for r in rows),
        "winner_accuracy":sum(r["winner_hit"] for r in rows)/n,
        "exact_hits":sum(r["exact_hit"] for r in rows),
        "exact_accuracy":sum(r["exact_hit"] for r in rows)/n,
        "method_class_hits":sum(r["method_class_hit"] for r in rows),
        "winner_brier":sum(r["winner_brier"] for r in rows)/n,
        "six_logloss":sum(r["six_logloss"] for r in rows)/n,
        "six_brier":sum(r["six_brier"] for r in rows)/n,
        "submissions_correct":sum(
            r["actual_method"]==r["selected_method"]=="SUB" for r in rows),
        "submissions_actual":sum(r["actual_method"]=="SUB" for r in rows),
    }

def paired(a,b,field,seed=19,n=300):
    clusters=defaultdict(list)
    for x,y in zip(a,b):
        if (x["bout_id"],x["date"])!=(y["bout_id"],y["date"]):
            raise ValueError("Mismatch same fight evaluation pair")
        clusters[(x["date"],x["event"])].append(x[field]-y[field])
    rng=random.Random(seed);keys=sorted(clusters);s=[]
    for _ in range(n):
        chosen=[keys[rng.randrange(len(keys))] for _ in keys]
        vals=[v for k in chosen for v in clusters[k]]
        s.append(sum(vals)/len(vals))
    s.sort()
    return {"candidate_minus_original_v4":sum(x[field]-y[field] for x,y in zip(a,b))/len(a),
        "bootstrap95":(s[int(.025*(n-1))],s[int(.975*(n-1))]),
        "already_inspected_2024_26":True}

def select_topk(rows):
    grouped=defaultdict(list)
    for r in rows:grouped[(r["date"],r["event"])].append(r)
    cards=[r for r in grouped.values() if 11<=len(r)<=14]
    return {str(n):{
       "cards":len(cards),"picks":len(cards)*n,
       "exact_hits":sum(x["exact_hit"] for r in cards for x in sorted(r,key=lambda z:(-z["p_own_exact"],z["bout_id"]))[:n]),
       "perfect_cards":sum(all(x["exact_hit"] for x in sorted(r,key=lambda z:(-z["p_own_exact"],z["bout_id"]))[:n]) for r in cards)
    } for n in (2,3,5)}

def main():
    feats,labs,ufc=load_matrix()
    region,regmeta=load_external(feats)
    recent,recmeta=supplement_current_feature_matrix(feats)
    world,worldmeta=enrich(feats,region,recent)
    label={x["bout_id"]:x for x in labs}
    cohort=[(f,label[f["bout_id"]]) for f in feats if
            "2021-01-01"<=f["event_date"]<"2026-11-08" and
            label[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(cohort)!=3015:raise ValueError("Exact date/labeled UFC source universe changed")
    results={};outputs=[]
    for year,start,end,expected in FOLDS:
        models=train(cohort,recent,region,world,start)
        methods,_=train_methods(cohort,region,start)
        testing=[(f,l) for f,l in cohort if start<=f["event_date"]<end]
        if len(testing)!=expected:raise ValueError("Changed independent source year cohort")
        bymodel=defaultdict(list)
        for f,l in testing:
            probs=winner_proba(f,recent,region,world,models)
            method=conditional(f,region,methods)["worldwide_MMA_multinomial54"]
            for head,p in probs.items():
                r=grade(f,l,head,p,method);outputs.append(r);bymodel[head].append(r)
        scores={head:aggregate(r) for head,r in bymodel.items()}
        comparisons={
            new:{
                metric:paired(bymodel[new],bymodel[old],metric)
                for metric in ("winner_hit","exact_hit","winner_brier","six_logloss")
            } for new,old in (
                ("v8_worldelo_logit77","v4_logit73"),
                ("v8_worldelo_boost77","v4_boost73"))
        }
        results[year]={
            "evaluation_fights":len(testing),
            "training_decisive_fights":models["training_decisive_fights"],
            "same_method_model_across_all_winner_arms":True,
            "scores":scores,"paired_elo_vs_unweighted_professional_record":comparisons,
            "top_two_through_five":{h:select_topk(r) for h,r in bymodel.items()},
        }
    OUT.mkdir(parents=True,exist_ok=True)
    predictions=OUT/"global_professional_opponent_quality_elo_v8_forecasts.csv"
    with predictions.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(outputs[0]))
        w.writeheader();w.writerows(outputs)
    report={
        "schema":"WSHLX_GLOBAL_PRO_MMA_ASOF_OPPONENT_ELO_WINNER_V8",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "ufc_source_SHA256":ufc["source_stats_sha256"],
        "fightcanon_external_source_SHA256":REGIONAL_SOURCE_SHA,
        "source_verification":worldmeta,
        "prior_regional_coverage":regmeta,
        "prior_UFC_recent_coverage":recmeta,
        "same_KO_SUB_DEC_method_predictions_across_winner_arms":True,
        "only_pre_fight_opponent_strength_extracted":True,
        "no_future_sameday_fight_results_used_to_train_elo_snapshot":True,
        "historical_2024_26_retrospective_not_pristine":True,
        "nov21_original_and_all_other_SHA_protected_shadows_unchanged":True,
        "no_model_promoted_or_betting_picks_issued":True,
        "feature_dimensions":DIMS,
        "yearly":results,
        "forecast_sha256":sha(predictions),
    }
    (OUT/"global_elo_winner_v8_results.json").write_text(
        json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "status":"GLOBAL_PRO_MMA_ELO_SOURCE_VERIFIED_NO_PROMOTION",
        "n_global_hist_pro_bouts":worldmeta["raw_pro_bouts_used"],
        "models":{year:{k:{"winner":v["winner_hits"],"exact":v["exact_hits"],
                      "six_logloss":round(v["six_logloss"],5)}
                 for k,v in x["scores"].items()}
                 for year,x in results.items()},
    },sort_keys=True))

if __name__=="__main__":main()
