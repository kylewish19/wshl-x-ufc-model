"""Worldwide pro-MMA record -> UFC winner v4 historical research.

ALL regional results used solely before each UFC bout date. Fighter identities
accepted only after original UFC fight date AND both named fighters corroborate
FightCanon's source-linked fighter ID (not fuzzy name alone).

Chronological 2024/25/26 test:
- baseline Winner v3 pre-event UFC 57 features
- independent Winner v4, same UFC 57 features + actual regional pro record,
  KO/SUB/DEC tendencies, previous non-UFC 3/5 fights and age of activity.
- matchup-stable shared conditional MMA victory-method model held fixed.

Direct selection target and proper scores remain BOTH winner and exact
fighter+method. Retrospective research not a new prospectively untouched holdout.
Never overwrite Nov21 Stage A, original Coherent, or V3 prospective lock.
"""
from __future__ import annotations

from collections import defaultdict,Counter
from datetime import datetime,timezone
from pathlib import Path
import csv,hashlib,json,math,random
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.winner_recent_form_v3 import supplement_current_feature_matrix,N
from wshlx_ufc.finish_v1_research import (
    method_features,training_rows,MultinomialFinish,coherent_six,score_six,METHODS,
)
from wshlx_ufc.historical_baselines import _winner_probabilities

ROOT=Path(__file__).resolve().parents[1]
REGIONAL=ROOT/"reports/model_health/2026-11-19_worldwide_mma_identity_audit"
SOURCEROWS=REGIONAL/"verified_bout_prior_pro_history.json"
SOURCEMANIFEST=REGIONAL/"identity_and_regional_data_coverage.json"
OUT=ROOT/"reports/model_health/2026-11-19_worldwide_mma_winner_v4"
FOLDS=(("2024","2024-01-01","2025-01-01",511),
       ("2025","2025-01-01","2026-01-01",513),
       ("2026_retrospective","2026-01-01","2026-11-08",488))

EXTRA=(
    "nonUFC_pro_decisive_log_count",
    "nonUFC_bayes_win_rate",
    "nonUFC_recent3_winrate",
    "nonUFC_recent5_winrate",
    "nonUFC_KO_win_rate",
    "nonUFC_SUB_win_rate",
    "nonUFC_DEC_win_rate",
    "nonUFC_KO_loss_rate",
    "nonUFC_SUB_loss_rate",
    "nonUFC_DEC_loss_rate",
    "nonUFC_finish_share_of_wins",
    "nonUFC_bouts_last_365_log",
    "all_org_pro_bout_count_log",
    "regional_method_coverage",
    "externally_vetted_UFC_identity",
    "nonUFC_insufficient_sample_lt3",
)
FULL=57+len(EXTRA)
BASE=57
HEADS=("winner_v3_logit57","winner_v4_logit73",
       "winner_v3_boost57","winner_v4_boost73")
REGIONAL_SOURCE_SHA="8185a2163b5f97071dbc4ec68667cceb43f5e321fadc38c26b5069303af4d949"

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def features(p,*,verified):
    if not verified:
        # Neutral values, combined with an explicit missing-identity flag.
        v=[0.,.5,.5,.5,1/3,1/3,1/3,1/3,1/3,1/3,.5,0.,0.,0.,0.,1.]
    else:
        n=float(p["known_nonUFC_decisive_prior"])
        wins=float(p["known_nonUFC_wins_prior"])
        losses=float(p["known_nonUFC_losses_prior"])
        if abs(n-wins-losses)>1e-7:raise ValueError("Historical record total inconsistency")
        sn=max(wins,1.)
        ln=max(losses,1.)
        method_fights=float(p["known_nonUFC_method_recorded"])
        if method_fights>n:raise ValueError("Impossible method observation coverage")
        v=[
            math.log1p(n),
            (wins+2.)/(n+4.),
            (float(p["known_nonUFC_recent3_wins"])+1.)/(float(p["known_nonUFC_recent3_decisive"])+2.),
            (float(p["known_nonUFC_recent5_wins"])+2.)/(float(p["known_nonUFC_recent5_decisive"])+4.),
            (float(p["known_nonUFC_KO_wins_prior"])+1.)/(wins+3.),
            (float(p["known_nonUFC_SUB_wins_prior"])+1.)/(wins+3.),
            (float(p["known_nonUFC_DEC_wins_prior"])+1.)/(wins+3.),
            (float(p["known_nonUFC_KO_losses_prior"])+1.)/(losses+3.),
            (float(p["known_nonUFC_SUB_losses_prior"])+1.)/(losses+3.),
            (float(p["known_nonUFC_DEC_losses_prior"])+1.)/(losses+3.),
            (float(p["known_nonUFC_KO_wins_prior"])+float(p["known_nonUFC_SUB_wins_prior"])+2.)/(wins+4.),
            math.log1p(float(p["known_nonUFC_bouts_prior_365d"])),
            math.log1p(float(p["known_pro_mma_bouts_any_org_prior"])),
            method_fights/n if n else 0.,
            1.,
            float(n<3),
        ]
    out=np.asarray(v,dtype=float)
    if len(v)!=len(EXTRA) or not np.all(np.isfinite(out)):
        raise ValueError("Incorrect regional feature dimensions or invalid historical values")
    return out

def load_external(matrix):
    manifest=json.loads(SOURCEMANIFEST.read_text())
    if manifest["db_sha256"]!=REGIONAL_SOURCE_SHA:
        raise ValueError("World pro history source vintage changed")
    if not manifest["no_naive_name_only_identity_linkage"] or not manifest["no_current_bout_or_future_bouts_for_features"]:
        raise ValueError("Regional identity/point-in-time provenance invalid")
    source_rows=json.loads(SOURCEROWS.read_text())
    mapped={}
    for obj in source_rows:
        k=obj["bout_id"]
        if k in mapped:raise ValueError("Duplicate regional ID")
        mapped[k]=obj
    joined={}
    missing=[]
    for f in matrix:
        if not "2021-01-01"<=f["event_date"]<"2026-11-08":continue
        r=mapped.get(f["bout_id"])
        if r is None:
            joined[f["bout_id"]]=(features(None,verified=False),features(None,verified=False),False)
            missing.append(f["bout_id"])
            continue
        if (r["date"],r["fighter_a"],r["fighter_b"])!=(
              f["event_date"],f["fighter_a"],f["fighter_b"]):
            raise ValueError("FightCanon source and UFC fighter date/orientation mismatch")
        for side in ("a","b"):
            if int(r[f"{side}_prior_ufc_bouts"])!=int(f[f"{side}_ufc_prior_bouts"]):
                raise ValueError("UFC pre-bout history mismatch on external join")
        joined[f["bout_id"]]=(features(r["a"],verified=True),features(r["b"],verified=True),True)
    assert len(joined)==3036
    return joined,{
        "source_db_sha256":manifest["db_sha256"],
        "source_db_size_bytes":manifest["db_size_bytes"],
        "source_id_verification":"Original UFC date, both opponents and unique third-party source fighter IDs",
        "training_era_matchup_rows":len(joined),
        "both_fighters_verified":len(joined)-len(missing),
        "withheld_identity_mismatches":len(missing),
        "unresolved_identity_sample":missing[:8],
        "third_party_2026_vintage_not_prospective_historical_snapshot":True,
        "no_bet_odds_features":True,
        "source_sha256":sha(SOURCEROWS),
    }

def vector(f,ufc_forms,regional_forms):
    a,b=method_features(f,"a"),method_features(f,"b")
    recent=ufc_forms.get(f["bout_id"])
    region=regional_forms.get(f["bout_id"])
    if recent is None or region is None:
        raise ValueError("Missing as-of UFC or pre-UFC data")
    aa,bb=recent;ra,rb,verified=region
    aa=np.r_[a,aa,ra];bb=np.r_[b,bb,rb]
    if aa.shape!=(FULL,) or bb.shape!=(FULL,) or not np.all(np.isfinite(aa)) or not np.all(np.isfinite(bb)):
        raise ValueError("Feature vector dimension/integrity failed")
    return aa,bb,verified

def train(rows,ufc,regional,cutoff):
    Xbase=[];Xfull=[];y=[]
    for f,l in rows:
        if f["event_date"]>=cutoff:continue
        a,b,_=vector(f,ufc,regional)
        d=a-b
        Xbase.extend((d[:BASE],-d[:BASE]))
        Xfull.extend((d,-d))
        win=int(l["label_a_win"])
        y.extend((win,1-win))
    if len(Xfull)<2000:raise ValueError("Historical fold too small")
    Xbase=np.asarray(Xbase);Xfull=np.asarray(Xfull);y=np.asarray(y)
    def fit_log(X):return make_pipeline(
        StandardScaler(),LogisticRegression(
            C=.20,fit_intercept=False,max_iter=1800)).fit(X,y)
    def fit_boost(X):return HistGradientBoostingClassifier(
        max_iter=160,learning_rate=.04,max_leaf_nodes=7,max_depth=3,
        min_samples_leaf=75,l2_regularization=25.,early_stopping=False,
        random_state=19).fit(X,y)
    return {
        "winner_v3_logit57":fit_log(Xbase),
        "winner_v4_logit73":fit_log(Xfull),
        "winner_v3_boost57":fit_boost(Xbase),
        "winner_v4_boost73":fit_boost(Xfull),
        "n_training_fights":len(Xfull)//2,
    }

def model_probas(f,ufc,regional,fit):
    a,b,verified=vector(f,ufc,regional)
    d=a-b
    out={}
    for name in HEADS:
        x=d[:BASE] if name.endswith("57") else d
        model=fit[name]
        fwd=float(model.predict_proba(x.reshape(1,-1))[0,1])
        rev=float(model.predict_proba((-x).reshape(1,-1))[0,1])
        if name.startswith("winner_v3_logit") or name.startswith("winner_v4_logit"):
            if abs(fwd+rev-1)>1e-10:
                raise ValueError("Fighter role symmetry violated")
        out[name]=(fwd+1-rev)*.5
    return out,verified

def score_row(f,l,head,p,cond,verified):
    q=coherent_six(p,cond)
    truth=0 if int(l["label_a_win"])==1 else 1
    scored=score_six(q,truth,l["label_method"],p_a=p)
    return {
        "bout_id":f["bout_id"],"event_date":f["event_date"],"event":f["event"],
        "head":head,"p_a_win":p,
        "source_regional_verified":int(verified),
        "contains_UFC_debutant":int(min(int(f["a_ufc_prior_bouts"]),int(f["b_ufc_prior_bouts"]))==0),
        "winner_hit":int(scored["winner_correct"]),
        "exact_hit":int(scored["exact"]),
        "winner_brier":float(scored["winner_brier"]),
        "six_logloss":float(scored["six_log_loss"]),
        "six_brier":float(scored["six_brier"]),
        "actual_method":l["label_method"],
        "selected_method":scored["pred_method"],
        "p_selected_exact":max(q[:3] if p>=.5 else q[3:]),
        "a_ko":q[0],"a_sub":q[1],"a_dec":q[2],
        "b_ko":q[3],"b_sub":q[4],"b_dec":q[5],
    }

def aggregate(rows):
    n=len(rows)
    if not n:raise ValueError("Empty cohort")
    return {
        "bouts":n,"events":len({(r["event_date"],r["event"]) for r in rows}),
        "winner_hits":sum(r["winner_hit"] for r in rows),
        "winner_accuracy":sum(r["winner_hit"] for r in rows)/n,
        "exact_hits":sum(r["exact_hit"] for r in rows),
        "exact_accuracy":sum(r["exact_hit"] for r in rows)/n,
        "winner_brier":sum(r["winner_brier"] for r in rows)/n,
        "six_logloss":sum(r["six_logloss"] for r in rows)/n,
        "six_brier":sum(r["six_brier"] for r in rows)/n,
        "method_classes":{
            met:{
                "actual":sum(r["actual_method"]==met for r in rows),
                "called":sum(r["selected_method"]==met for r in rows),
                "correct_class":sum(r["actual_method"]==r["selected_method"]==met for r in rows),
            } for met in METHODS
        },
    }

def paired(a,b,metric,seed=19,reps=500):
    if len(a)!=len(b):raise ValueError("Unmatched year outcomes")
    diffs=defaultdict(list)
    for x,y in zip(a,b):
        if (x["bout_id"],x["event_date"])!=(y["bout_id"],y["event_date"]):
            raise ValueError("Wrong paired fight identity")
        diffs[(x["event_date"],x["event"])].append(float(x[metric])-float(y[metric]))
    events=sorted(diffs)
    rng=random.Random(seed)
    samples=[]
    for _ in range(reps):
        keys=[events[rng.randrange(len(events))] for _ in events]
        values=[z for k in keys for z in diffs[k]]
        samples.append(sum(values)/len(values))
    samples.sort()
    return {
        "candidate_minus_baseline":sum(x[metric]-y[metric] for x,y in zip(a,b))/len(a),
        "event_cluster_bootstrap95":[samples[int(.025*(reps-1))],samples[int(.975*(reps-1))]],
        "sampled_event_clusters":len(events),"research_not_pristine_test":True,
    }

def rank_topk(cards):
    grouped=defaultdict(list)
    for r in cards:
        grouped[(r["event_date"],r["event"])].append(r)
    eligible=[r for r in grouped.values() if 11<=len(r)<=14]
    output={"event_cards":len(eligible)}
    for k in (2,3,5):
        chosen=[sorted(r,key=lambda x:(-x["p_selected_exact"],x["bout_id"]))[:k] for r in eligible]
        output[f"top{k}"]={
            "picks":sum(map(len,chosen)),
            "exact_hits":sum(x["exact_hit"] for batch in chosen for x in batch),
            "perfect_selected_cards":sum(all(x["exact_hit"] for x in batch) for batch in chosen),
        }
    return output

def main():
    features,labels,source=load_matrix()
    regional,regional_source=load_external(features)
    forms,formmeta=supplement_current_feature_matrix(features)
    lab={x["bout_id"]:x for x in labels}
    if len(lab)!=len(labels):raise ValueError("Duplicate historical target")
    cohort=[(f,lab[f["bout_id"]]) for f in features
            if "2021-01-01"<=f["event_date"]<"2026-11-08"
            and lab[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(cohort)!=3015:raise ValueError("True historical total changed")
    yearly={};allrows=[]
    for year,start,end,size in FOLDS:
        trained=train(cohort,forms,regional,start)
        train_features=[f for f,l in cohort if f["event_date"]<start]
        train_labels=[l for f,l in cohort if f["event_date"]<start]
        X,y=training_rows(train_features,train_labels,start)
        method=MultinomialFinish().fit(X,y)
        testing=[(f,l) for f,l in cohort if start<=f["event_date"]<end]
        if len(testing)!=size:raise ValueError("Out-of-time year count mismatch")
        v=defaultdict(list)
        for f,l in testing:
            prob,verified=model_probas(f,forms,regional,trained)
            cond=method.predict(np.vstack((method_features(f,"a"),method_features(f,"b"))))
            for head in HEADS:
                r=score_row(f,l,head,prob[head],cond,verified)
                v[head].append(r);allrows.append(r)
        scores={name:aggregate(rows) for name,rows in v.items()}
        splits={
          name:{
             "any_UFC_debutant":aggregate([r for r in rows if r["contains_UFC_debutant"]]),
             "neither_UFC_debutant":aggregate([r for r in rows if not r["contains_UFC_debutant"]]),
             "verified_regional_id":aggregate([r for r in rows if r["source_regional_verified"]]),
          } for name,rows in v.items()
        }
        paired_scores={
          variant:{
              metric:paired(v[variant],v[base],metric)
              for metric in ("winner_hit","exact_hit","winner_brier","six_logloss")
          } for variant,base in (
              ("winner_v4_logit73","winner_v3_logit57"),
              ("winner_v4_boost73","winner_v3_boost57"))
        }
        yearly[year]={
           "training_fights":trained["n_training_fights"],
           "evaluation_fights":size,"same_method_head_across_all_winner_variants":True,
           "models":scores,"debutant_splits":splits,
           "paired_v4_minus_v3":paired_scores,
           "reliable_exact_top_2_to_5":{
              name:rank_topk(v[name]) for name in HEADS
           },
        }
    OUT.mkdir(parents=True,exist_ok=True)
    probabilities=OUT/"worldwide_mma_winner_v4_chronological_forecasts.csv"
    with probabilities.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(allrows[0]))
        w.writeheader();w.writerows(allrows)
    report={
        "schema":"WSHLX_UFC_WINNER_V4_OPEN_MMA_REGIONAL_HISTORY_TEST",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "feature_source_sha256":source["source_stats_sha256"],
        "external_source":regional_source,
        "recent_ufc_source":formmeta,
        "regional_feature_columns":EXTRA,
        "all_feature_column_count":FULL,
        "same_existing_KO_SUB_DEC_method_head_across_winner_arms":True,
        "chronological_train_earlier_years_only":True,
        "external_dataset_reconstructed_2026_vintage":True,
        "no_new_pristine_2026_or_pre_event_grade_claim":True,
        "nov21_all_previously_frozen_picks_unchanged":True,
        "no_betting_odds_used_or_bets_authorized":True,
        "no_model_promoted":True,
        "yearly":yearly,
        "source_predictions_sha256":sha(probabilities),
    }
    (OUT/"winner_v4_results.json").write_text(
        json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "STATUS":"RESEARCH_ONLY_REGIONAL_PRO_HISTORY_NO_MODEL_PROMOTION",
        "regional_verified":regional_source["both_fighters_verified"],
        "years":{year:{name:{
               "winner_hits":m["winner_hits"],"exact_hits":m["exact_hits"],
               "winner_brier":round(m["winner_brier"],5),
               "six_logloss":round(m["six_logloss"],5)}
          for name,m in rep["models"].items()} for year,rep in yearly.items()},
    },sort_keys=True))

if __name__=="__main__":main()
