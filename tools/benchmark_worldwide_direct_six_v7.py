"""UFC fighter + METHOD v7, direct six-class worldwide-MMA training.

Each fight maps to six mutually exclusive labels:
A KO/TKO, A SUB, A DEC, B KO/TKO, B SUB, B DEC.
Source: the SAME matched UFC 2021–2026 event-time-lagged features, verified
third-party regional pro history, plus both sides' recent UFC stats.

Two new direct outcome input geometries:
 - difference (115 pre-fight relative features, mirrored)
 - paired (230 both-sides pre-fight features, mirrored).
Both train on two orientations PER PRIOR FIGHT, never future labels.
Small boosted difference nonlinear learner is a third independent architecture.

Logistic regularization is chosen using nested PRE-TEST validation:
train 2021-22 => validate 2023 for 2024 target;
train 2021-23 => validate 2024 for 2025 target;
train 2021-24 => validate 2025 for 2026 target.
Evaluate both global-six argmax and coherent winner-marginal + method
decision policies, plus explicit SAME-DATE conditional v5 benchmarks
with v3-logit and v4-boost winning heads. Proper six-state probability
scores and 2–5 subset successes are all separately recorded.

Research only: even 2026 has previously been investigated,
so no promotion, no odds, no change to frozen 11/21 research locks.
"""
from __future__ import annotations
from collections import defaultdict,Counter
from datetime import datetime,timezone
from pathlib import Path
import hashlib,csv,json,math,random
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.winner_recent_form_v3 import supplement_current_feature_matrix
from wshlx_ufc.finish_v1_research import (
    METHODS,coherent_six,score_six,method_features
)
from benchmark_worldwide_mma_winner_v4 import (
    load_external,train as winner_train,model_probas,
    REGIONAL_SOURCE_SHA
)
from benchmark_worldwide_method_v5 import (
    train_methods as method_train,conditional as method_cond
)
from benchmark_opponent_matchup_method_v6 import (
    training_matrix,vectors,reliable_picks,paired
)

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"reports/model_health/2026-11-19_direct_six_world_v7"
FOLDS=(("2024","2024-01-01","2025-01-01","2023-01-01",511),
       ("2025","2025-01-01","2026-01-01","2024-01-01",513),
       ("2026_retrospective","2026-01-01","2026-11-08","2025-01-01",488))
GLOBAL=("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")
C_GRID=(.005,.025,.10)
ARCHS=("direct_diff115","direct_paired230","direct_boost_diff115")
POLICIES=("global_best_cell","winner_marginal_method")
BASELINES=("factorized_v3plusv5","factorized_v4plusv5")
SWAP=np.array([3,4,5,0,1,2],dtype=int)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def outcome(label):
    if label["label_method"] not in METHODS or label["result_status"]!="DECISIVE":
        raise ValueError("Only six decisive outcomes can be trained")
    return (0 if int(label["label_a_win"]) else 3)+METHODS.index(label["label_method"])

def representation(row,kind,reverse=False):
    a,b=row["Xa"],row["Xb"]
    if a.shape!=(115,) or b.shape!=(115,):
        raise ValueError("Expected same 115-dimensional v6 enriched two-sided features")
    if reverse:a,b=b,a
    out=a-b if kind in ("direct_diff115","direct_boost_diff115") else np.r_[a,b]
    return np.asarray(out,dtype=float)

def create_training(rows,mode):
    X=[];y=[]
    for r in rows:
        state=int(r["truth"])
        X.append(representation(r,mode))
        X.append(representation(r,mode,reverse=True))
        y.extend([state,int(SWAP[state])])
    X=np.asarray(X,dtype=float)
    y=np.asarray(y,dtype=int)
    if X.shape!=(2*len(rows),(230 if mode=="direct_paired230" else 115)):
        raise ValueError("Mirrored six-label full historical training matrix mismatch")
    if any(z not in set(y) for z in range(6)):
        raise ValueError("Missing independent one-of-six winner-method training label")
    return X,y

def fit_model(rows,arch,C=None):
    X,y=create_training(rows,arch)
    if arch=="direct_boost_diff115":
        mdl=HistGradientBoostingClassifier(
            max_iter=120,learning_rate=.035,max_leaf_nodes=7,max_depth=3,
            min_samples_leaf=65,l2_regularization=25,
            early_stopping=False,random_state=19)
    else:
        mdl=make_pipeline(StandardScaler(),
            LogisticRegression(C=C,fit_intercept=True,max_iter=1900))
    mdl.fit(X,y)
    return mdl

def predict_six(model,row,arch):
    xy=np.vstack([representation(row,arch),representation(row,arch,reverse=True)])
    q=model.predict_proba(xy)
    classes=list(model[-1].classes_ if hasattr(model,"steps") else model.classes_)
    raw=np.asarray([[q[side,classes.index(i)] for i in range(6)] for side in (0,1)])
    # Prediction from reversing fighter order must reverse the six labels.
    out=.5*(raw[0]+raw[1][SWAP])
    if not np.all(np.isfinite(out)) or np.min(out)<0 or abs(out.sum()-1)>1e-8:
        raise ValueError("Broken symmetric direct-six marginal simplex")
    return out

def validate_hyperparameters(earlier,val,arch):
    if len(earlier)<700 or len(val)<100:
        raise ValueError("Not enough independent previous-era outcome labels")
    truth=np.array([r["truth"] for r in val],dtype=int)
    costs={}
    for C in C_GRID:
        fit=fit_model(earlier,arch,C)
        preds=np.asarray([predict_six(fit,r,arch) for r in val])
        costs[str(C)]=float(-np.log(np.maximum(1e-12,preds[np.arange(len(val)),truth])).mean())
    chosen=min(C_GRID,key=lambda c:(costs[str(c)],c))
    return {"chosen_C":chosen,"validation_cases":len(val),"train_cases":len(earlier),
            "six_logloss_by_C":costs,
            "past_years_only":True,"no_test_target_used_to_tune":True}

def select_prediction(q,policy):
    if policy=="global_best_cell":
        idx=int(np.argmax(q))
    elif policy=="winner_marginal_method":
        first=float(q[:3].sum())
        side=0 if first>=.5 else 1
        idx=side*3+int(np.argmax(q[side*3:side*3+3]))
    else:raise ValueError("Unregistered selection rule")
    return idx

def grade_direct(f,l,arch,policy,q):
    truth=outcome(l)
    idx=select_prediction(q,policy)
    win_actual=0 if truth<3 else 1
    marginal_a=float(q[:3].sum())
    return {
        "date":f["event_date"],"event":f["event"],"bout_id":f["bout_id"],
        "model":arch+"__"+policy,
        "selected_state":idx,"true_state":truth,
        "winner_hit":int((idx<3)==(truth<3)),
        "exact_hit":int(idx==truth),
        "method_class_hit":int((idx%3)==(truth%3)),
        "winner_brier":float((marginal_a-(1 if win_actual==0 else 0))**2),
        "six_logloss":float(-math.log(max(1e-12,q[truth]))),
        "six_brier":float(np.sum((q-np.eye(6)[truth])**2)),
        "p_a_win":marginal_a,"p_selected_exact":float(q[idx]),
        "actual_method":METHODS[truth%3],"selected_method":METHODS[idx%3],
        "a_ko":float(q[0]),"a_sub":float(q[1]),"a_dec":float(q[2]),
        "b_ko":float(q[3]),"b_sub":float(q[4]),"b_dec":float(q[5]),
    }

def grade_base(f,l,model,p,cond):
    q=coherent_six(p,cond)
    # Choose side by winner head; identical to old coherent-same-head method.
    idx=select_prediction(q,"winner_marginal_method")
    scored=grade_direct(f,l,model,"winner_marginal_method",q)
    scored["model"]=model
    return scored

def metric(rows):
    if not rows:raise ValueError("Empty same-date cohort")
    n=len(rows)
    return {
        "n":n,
        "event_clusters":len({(r["date"],r["event"]) for r in rows}),
        "winner_hits":sum(r["winner_hit"] for r in rows),
        "winner_accuracy":sum(r["winner_hit"] for r in rows)/n,
        "exact_hits":sum(r["exact_hit"] for r in rows),
        "exact_accuracy":sum(r["exact_hit"] for r in rows)/n,
        "method_class_hits":sum(r["method_class_hit"] for r in rows),
        "winner_brier":sum(r["winner_brier"] for r in rows)/n,
        "six_logloss":sum(r["six_logloss"] for r in rows)/n,
        "six_brier":sum(r["six_brier"] for r in rows)/n,
        "submission":{
            "actual":sum(r["actual_method"]=="SUB" for r in rows),
            "selected":sum(r["selected_method"]=="SUB" for r in rows),
            "correct_class":sum(r["actual_method"]==r["selected_method"]=="SUB" for r in rows),
            "exact_hits":sum(r["exact_hit"] and r["actual_method"]=="SUB" for r in rows),
        },
    }

def card_selection(rows):
    d=defaultdict(list)
    for r in rows:d[(r["date"],r["event"])].append(r)
    valid=[a for a in d.values() if 11<=len(a)<=14]
    out={}
    for k in (2,3,5):
        picks=[sorted(x,key=lambda r:(-r["p_selected_exact"],r["bout_id"]))[:k] for x in valid]
        out[str(k)]={
            "cards":len(valid),"predictions":len(valid)*k,
            "exact_hits":sum(r["exact_hit"] for p in picks for r in p),
            "perfect_groups":sum(all(r["exact_hit"] for r in p) for p in picks),
        }
    return out

def main():
    features,labels,ufcsource=load_matrix()
    external,extmeta=load_external(features)
    recent,recmeta=supplement_current_feature_matrix(features)
    byid={l["bout_id"]:l for l in labels}
    cohort=[(f,byid[f["bout_id"]]) for f in features
            if "2021-01-01"<=f["event_date"]<"2026-11-08" and
               byid[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(cohort)!=3015:
        raise ValueError("Identical 3015 modern dated UFC outcome labels required")
    base=training_matrix(cohort,external,recent)
    for r,(f,l) in zip(base,cohort):
        if (r["id"],r["date"])!=(f["bout_id"],f["event_date"]):
            raise ValueError("Prior as-of feature and actual independent label alignment failure")
        r["truth"]=outcome(l)
    byf={x["id"]:x for x in base}
    all_rows=[];fold_data={}
    for year,start,end,valstart,expected in FOLDS:
        earlier=[r for r in base if r["date"]<start]
        inner_train=[r for r in base if r["date"]<valstart]
        inner_val=[r for r in earlier if valstart<=r["date"]<start]
        tuning={arch:validate_hyperparameters(inner_train,inner_val,arch)
                for arch in ARCHS if not arch.startswith("direct_boost")}
        trained={arch:fit_model(earlier,arch,tuning[arch]["chosen_C"]
                    if arch in tuning else None) for arch in ARCHS}
        winner=winner_train(cohort,recent,external,start)
        methodbundle,trainedmethodn=method_train(cohort,external,start)
        target=[(f,l) for f,l in cohort if start<=f["event_date"]<end]
        if len(target)!=expected:
            raise ValueError("Wrong year fold or detached matchups")
        scores=defaultdict(list)
        for f,l in target:
            x=byf[f["bout_id"]]
            for arch in ARCHS:
                q=predict_six(trained[arch],x,arch)
                for policy in POLICIES:
                    r=grade_direct(f,l,arch,policy,q)
                    scores[r["model"]].append(r)
                    all_rows.append(r)
            probabilities,_=model_probas(f,recent,external,winner)
            condition=method_cond(f,external,methodbundle)
            for name,winnerhead in (("factorized_v3plusv5","winner_v3_logit57"),
                                    ("factorized_v4plusv5","winner_v4_boost73")):
                r=grade_base(f,l,name,probabilities[winnerhead],
                             condition["worldwide_MMA_multinomial54"])
                scores[name].append(r);all_rows.append(r)
        stats={k:metric(v) for k,v in scores.items()}
        paired_vs={}
        for arch in ARCHS:
            for policy in POLICIES:
                key=arch+"__"+policy
                paired_vs[key]={
                    baseline:{
                        field:paired([{**r,"bout_id":r["bout_id"],"event_date":r["date"]} for r in scores[key]],
                            [{**r,"bout_id":r["bout_id"],"event_date":r["date"]} for r in scores[baseline]],field)
                        for field in ("exact_hit","winner_hit","six_logloss")
                    } for baseline in BASELINES
                }
        fold_data[year]={
            "training_fights":len(earlier),"inner_validation_fights":len(inner_val),
            "evaluation_fights":len(target),
            "winner_models_fit_strictly_before_target_year":True,
            "independent_previous_year_6_state_C_tuning":tuning,
            "scores":stats,
            "paired_vs_previously_tested_factorized":paired_vs,
            "full_card_exact_selection":{k:card_selection(v) for k,v in scores.items()},
        }
    DEST.mkdir(parents=True,exist_ok=True)
    csvfile=DEST/"worldwide_direct_six_2024_26_forecasts.csv"
    with csvfile.open("w",newline="",encoding="utf-8") as h:
        w=csv.DictWriter(h,fieldnames=list(all_rows[0]))
        w.writeheader();w.writerows(all_rows)
    report={
        "schema":"WSHLX_INDEPENDENT_DIRECT_SIX_WORLD_MMA_V7_CHRONOLOGICAL",
        "source_UFC_SHA256":ufcsource["source_stats_sha256"],
        "source_professional_MMA_SHA256":REGIONAL_SOURCE_SHA,
        "source_regional_audit":extmeta,
        "source_ufc_recent_audit":recmeta,
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "training_symmetry":"Each historical fight mirrored A/B; predictions explicitly averaged with relabeling",
        "direct_six_only_prior_known_outcomes":True,
        "prior_year_nested_C_test_year_never_used":True,
        "no_fighter_method_or_betting_model_promotion":True,
        "Nov21_all_original_and_research_sidecars_frozen_unchanged":True,
        "2024_2026_previously_inspected_not_pristine":True,
        "models":ARCHS,
        "six_selection_policies":POLICIES,
        "factorized_matchup_baselines":BASELINES,
        "years":fold_data,
        "outcome_csv_sha256":sha(csvfile),
    }
    (DEST/"worldwide_direct_six_v7_results.json").write_text(
        json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "status":"RESEARCH_ONLY_NO_DIRECT6_PROMOTION",
        "years":{k:{name:{
            "winner":v["winner_hits"],"exact":v["exact_hits"],
            "logloss":round(v["six_logloss"],5),
            "sub_right":v["submission"]["correct_class"]
        } for name,v in y["scores"].items()} for k,y in fold_data.items()},
    },sort_keys=True))

if __name__=="__main__":main()
