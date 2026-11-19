"""WSHL_X phase-2 research: data audit, method-feature ablation, direct-six
fighter+method learning, and abstention-aware 2-5 outcome selection.

All features are strict pre-event UFC history from the pinned SECONDARY archive.
This is historical MODEL DEVELOPMENT, never a prospective performance claim.
No production/Stage A/B code, source records, odds, or locks may be modified.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import csv,hashlib,json,math,random
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.finish_v1_research import method_features, METHODS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/model_health/2026-11-19_exact_outcome_phase2"
DATES=(("2024","2024-01-01","2025-01-01",511),
       ("2025","2025-01-01","2026-01-01",513),
       ("2026_retrospective","2026-01-01","2026-11-14",488))
# 38 source-derived features, indices from method_features. ALL groups are
# predeclared before seeing outcome labels for this experiment.
CORE={0,1,2,3,4,5,30,31,32,33,34,35,36,37}
QUALITY={6,7,8}
STRIKING={12,13,17,19,28}
GRAPPLING={9,10,11,14,15,16,18,22,23,24,25,26,27,29}
SURVIVAL={20,21}
GROUPS={"core":CORE,"quality":QUALITY,"striking":STRIKING,
        "grappling":GRAPPLING,"survival":SURVIVAL}
ALL=set(range(38))
assert set.union(*GROUPS.values())==ALL
assert sum(len(s) for s in GROUPS.values())==38
VARIANTS={
 "all_features":sorted(ALL),
 "no_quality":sorted(ALL-QUALITY),
 "no_striking":sorted(ALL-STRIKING),
 "no_grappling":sorted(ALL-GRAPPLING),
 "no_survival":sorted(ALL-SURVIVAL),
 "experience_only":sorted(CORE),
}
CLASS_ORDER=("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")
OUTCOMES=METHODS
K=6

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def encoded(f):
    if f["feature_as_of_exclusive"]!=f["event_date"]:
        raise ValueError("Source was not event-time-lagged")
    a,b=method_features(f,"a"),method_features(f,"b")
    if a.shape!=(38,) or b.shape!=(38,):
        raise ValueError("38 predeclared source feature slots expected")
    return a,b

def actual_state(l):
    if l["result_status"]!="DECISIVE":raise ValueError("Exclude draws")
    return (0 if int(l["label_a_win"])==1 else 3)+OUTCOMES.index(l["label_method"])

def prepared(features,labels):
    label_by={l["bout_id"]:l for l in labels}
    if len(label_by)!=len(labels):raise ValueError("Duplicate labels")
    training=[]
    for f in features:
        if not "2021-01-01"<=f["event_date"]<"2026-11-14":continue
        label=label_by[f["bout_id"]]
        if label["result_status"]!="DECISIVE":continue
        a,b=encoded(f)
        training.append((f,label,a,b,actual_state(label)))
    return training

def classifier(c=.2):
    return make_pipeline(StandardScaler(),
                         LogisticRegression(C=c,max_iter=1600))

def fit_train(training,cutoff,cols):
    x_w=[];y_w=[];x_m=[];y_m=[];x_s=[];y_s=[]
    for f,l,a,b,state in training:
        if f["event_date"]>=cutoff:continue
        av,bv=a[cols],b[cols]
        win_a=state<3
        difference=av-bv
        x_w.extend((difference,-difference))
        y_w.extend((int(win_a),int(not win_a)))
        x_m.append(av if win_a else bv)
        y_m.append(OUTCOMES[state%3])
        x_s.extend((np.r_[av,bv],np.r_[bv,av]))
        y_s.extend((state,(state+3)%6))
    if len(x_m)<1000:raise ValueError("Training size unexpectedly small")
    wm=make_pipeline(StandardScaler(),
        LogisticRegression(C=.2,fit_intercept=False,max_iter=1600))
    wm.fit(np.asarray(x_w),np.asarray(y_w))
    mm=classifier().fit(np.asarray(x_m),np.asarray(y_m))
    sm=classifier().fit(np.asarray(x_s),np.asarray(y_s))
    if set(sm[-1].classes_)!=set(range(6)):
        raise ValueError("All six outcomes must be trained")
    if set(mm[-1].classes_)!=set(OUTCOMES):
        raise ValueError("All three method outcomes must be trained")
    return wm,mm,sm,len(x_m)

def probabilities(models,a,b,cols):
    wm,mm,sm,_=models
    av,bv=a[cols],b[cols]
    p=float(wm.predict_proba((av-bv).reshape(1,-1))[0,1])
    p_reverse=float(wm.predict_proba((bv-av).reshape(1,-1))[0,1])
    if abs(p+p_reverse-1)>1e-10:raise ValueError("Fighter symmetry failed")
    both=np.vstack((av,bv))
    cond=mm.predict_proba(both)
    ix=[list(mm[-1].classes_).index(x) for x in OUTCOMES]
    cond=cond[:,ix]
    factor=np.r_[p*cond[0],(1-p)*cond[1]]
    forward=sm.predict_proba(np.r_[av,bv].reshape(1,-1))[0]
    backward=sm.predict_proba(np.r_[bv,av].reshape(1,-1))[0]
    ci=list(sm[-1].classes_)
    first=np.asarray([forward[ci.index(i)] for i in range(6)])
    second=np.asarray([backward[ci.index((i+3)%6)] for i in range(6)])
    direct=(first+second)*.5
    direct/=direct.sum()
    for q in (factor,direct):
        if not np.all(np.isfinite(q)) or np.min(q)<0 or abs(q.sum()-1)>1e-9:
            raise ValueError("Broken six-cell simplex")
    if abs(factor[:3].sum()-p)>1e-9:raise ValueError("Factor winner marginal inconsistent")
    return p,factor,direct

def scored(f,label,p,q,mode,variant):
    y=actual_state(label)
    owner=0 if p>=.5 else 1
    pick=3*owner+int(np.argmax(q[3*owner:3*owner+3]))
    global_pick=int(np.argmax(q))
    winner_actual=int(y<3)
    v={
        "year":f["event_date"][:4],"event":f["event"],"date":f["event_date"],
        "bout_id":f["bout_id"],"model":mode,"variant":variant,
        "prob_a":float(p),"exact_probability":float(q[pick]),
        "global_exact_probability":float(q[global_pick]),
        "second_probability":float(np.partition(q,-2)[-2]),
        "global_gap":float(q[global_pick]-np.partition(q,-2)[-2]),
        "own_gap":float(np.max(q[3*owner:3*owner+3])-
                         np.partition(q[3*owner:3*owner+3],-2)[-2]),
        "picked_exact_state":pick,"global_pick":global_pick,
        "truth":y,"exact":int(pick==y),"global_exact":int(global_pick==y),
        "winner_hit":int(owner==int(y>=3)),
        "winner_brier":float((p-winner_actual)**2),
        "six_log_loss":float(-np.log(max(1e-12,q[y]))),
        "six_brier":float(np.sum((q-np.eye(6)[y])**2)),
        "methods_pred":OUTCOMES[pick%3],"method_true":OUTCOMES[y%3],
        "a_ko":float(q[0]),"a_sub":float(q[1]),"a_dec":float(q[2]),
        "b_ko":float(q[3]),"b_sub":float(q[4]),"b_dec":float(q[5]),
        "min_prior_ufc":min(float(f["a_prior_ufc_bouts"]),float(f["b_prior_ufc_bouts"])),
        "min_stats_coverage":min(float(f["a_stats_coverage"]),float(f["b_stats_coverage"])),
    }
    return v

def aggregate(rows):
    if not rows:raise ValueError("No scored rows")
    n=len(rows)
    return {
       "n":n,"events":len({(r["date"],r["event"]) for r in rows}),
       "winner_hits":sum(r["winner_hit"] for r in rows),
       "winner_accuracy":sum(r["winner_hit"] for r in rows)/n,
       "exact_hits":sum(r["exact"] for r in rows),
       "exact_accuracy":sum(r["exact"] for r in rows)/n,
       "global_six_hits":sum(r["global_exact"] for r in rows),
       "global_six_accuracy":sum(r["global_exact"] for r in rows)/n,
       "six_log_loss":sum(r["six_log_loss"] for r in rows)/n,
       "six_brier":sum(r["six_brier"] for r in rows)/n,
       "winner_brier":sum(r["winner_brier"] for r in rows)/n,
       "actual_sub":sum(r["method_true"]=="SUB" for r in rows),
       "called_sub":sum(r["methods_pred"]=="SUB" for r in rows),
       "correct_sub_method":sum(r["methods_pred"]==r["method_true"]=="SUB" for r in rows),
       "max_exact_probability":max(r["exact_probability"] for r in rows),
    }

def quality_audit(training,features):
    a=[f for f in features if "2021-01-01"<=f["event_date"]<"2026-11-14"]
    cohorts={}
    for year in ("2021","2022","2023","2024","2025","2026"):
        yy=[f for f in a if f["event_date"].startswith(year)]
        if not yy:continue
        n=len(yy)
        null=lambda key:sum(f[key] is None for f in yy)
        debut=sum(min(float(f["a_prior_ufc_bouts"]),float(f["b_prior_ufc_bouts"]))==0 for f in yy)
        under5=sum(min(float(f["a_prior_ufc_bouts"]),float(f["b_prior_ufc_bouts"]))<5 for f in yy)
        missing_control=sum(f["a_own_control_generated_sec_per15"] is None or f["b_own_control_generated_sec_per15"] is None for f in yy)
        cohorts[year]={
            "bouts":n,"any_debutant":debut,"any_under5_prior_ufc":under5,
            "any_unavailable_prior_control_rate":missing_control,
            "avg_min_stats_coverage":sum(min(float(f["a_stats_coverage"]),float(f["b_stats_coverage"])) for f in yy)/n,
        }
    keys={k for f in a[:50] for k in f}
    unavailable=["age_at_fight","reach_at_fight","height_at_fight","weightclass_prior_bouts",
                 "regional_record_quality","actual_getup_count","injury_status","prior_layoff_days"]
    return {
        "entire_source_matrix_rows":len(features),
        "modern_source_bouts":len(a),"modern_decisive_bouts":len(training),
        "years":cohorts,
        "unavailable_asof_source_variables":unavailable,
        "unavailable_variable_presence":{x:any(x in k for k in keys) for x in unavailable},
        "do_not_guess_missing_as_zero":True,
        "no_region_or_getup_fields_invented":True,
        "missingness_leakage_guard":"Only prior-event history, no current-fight labels or future opponent results",
        "source_classification":"pinned secondary UFCStats-compatible; NOT direct first-party UFCStats"
    }

def event_bootstrap(a,b,metric,*,seed=19,reps=500):
    if len(a)!=len(b):raise ValueError("paired cohort")
    group=defaultdict(list)
    for x,y in zip(a,b):
        if x["bout_id"]!=y["bout_id"] or x["date"]!=y["date"]:
            raise ValueError("Paired identity drift")
        group[(x["date"],x["event"])].append(float(x[metric])-float(y[metric]))
    rng=random.Random(seed); keys=list(sorted(group)); samples=[]
    for _ in range(reps):
        chosen=[keys[rng.randrange(len(keys))] for _ in keys]
        vals=[d for key in chosen for d in group[key]]
        samples.append(sum(vals)/len(vals))
    samples.sort()
    return {
        "candidate_minus_full_features":sum(float(x[metric])-float(y[metric]) for x,y in zip(a,b))/len(a),
        "event_bootstrap_95pct":[samples[int(.025*(reps-1))],samples[int(.975*(reps-1))]],
        "event_clusters":len(keys),"reps":reps,
        "research_not_prospective":True,
    }

def selection(card_records):
    # Each card can have 11-14 DECiSIVE fights, and each row is from existing
    # OOF predictions, never newly fitted on same-day/target events.
    groups=defaultdict(list)
    for r in card_records:
        groups[(r["date"],r["event"])].append(r)
    cards={k:v for k,v in groups.items() if 11<=len(v)<=14}
    stats=defaultdict(list)
    evidence=[]
    for (date,event),rs in sorted(cards.items()):
        by_bout=defaultdict(dict)
        for r in rs:by_bout[r["bout_id"]][r["model"]]=r
        if any(set(b)!={"direct6","factorized6"} for b in by_bout.values()):
            raise ValueError("Both six-way systems must cover same card")
        pairs=list(by_bout.values())
        own=[x["factorized6"] for x in pairs]
        # Transparent baseline: top 3 exact probability, any fights.
        baseline=sorted(own,key=lambda x:(-x["exact_probability"],x["bout_id"]))[:3]
        stats["baseline_top3"].append(baseline)
        # Predeclared strict selection: BOTH independent six-way models pick
        # the SAME EXACT fighter+method, not merely the winner.
        # Minimum 5 prior UFC bouts each, >=80% recorded past-stat coverage,
        # conservative exact P >=.30, and 5pp min between highest exact cells.
        qualified=[]
        for pair in pairs:
            f,d=pair["factorized6"],pair["direct6"]
            if (f["picked_exact_state"]!=d["global_pick"] or
                f["min_prior_ufc"]<5 or f["min_stats_coverage"]<.8 or
                min(f["exact_probability"],
                    (d["a_ko"],d["a_sub"],d["a_dec"],d["b_ko"],d["b_sub"],d["b_dec"])[f["picked_exact_state"]])<.30 or
                d["global_gap"]<.05):
                continue
            qualified.append((min(f["exact_probability"],d["global_exact_probability"]),f))
        qualified.sort(key=lambda x:(-x[0],x[1]["bout_id"]))
        picks=[r for _,r in qualified[:5]]
        stats["strict_agreement_evidence"].append(picks)
        evidence.append({"date":date,"event":event,"all_fights":len(pairs),
                         "strict_qualified_count":len(qualified),
                         "strict_selected_count":len(picks)})
    output={}
    for method,selected in stats.items():
        lengths=Counter(len(p) for p in selected)
        flat=[r for rs in selected for r in rs]
        eligible=[rs for rs in selected if 2<=len(rs)<=5]
        output[method]={
            "eligible_cards":len(cards),"picked_fights":len(flat),
            "correct_exact":sum(r["exact"] for r in flat),
            "exact_hit_rate":sum(r["exact"] for r in flat)/len(flat) if flat else None,
            "selection_counts":dict(lengths),
            "cards_with_2_to_5_picks":len(eligible),
            "all_exact_correct_for_2_to_5":sum(all(r["exact"] for r in rs) for rs in eligible),
            "perfect_card_rate_when_2_to_5":sum(all(r["exact"] for r in rs) for rs in eligible)/len(eligible) if eligible else None,
            "zero_pick_cards":lengths[0],
            "no_forced_2_to_5":True,
        }
    return {"groups":output,"card_evidence_counts":evidence,
            "rule_predeclared_no_test_outcome_input":True,
            "bet_approvals":0}

def run():
    features,labels,manifest=load_matrix()
    prepared_rows=prepared(features,labels)
    audit=quality_audit(prepared_rows,features)
    by_year={}
    allrows=[]
    folds_out={}
    for year,before,end,count in DATES:
        target=[r for r in prepared_rows if before<=r[0]["event_date"]<end]
        if len(target)!=count:raise ValueError("Decisive annual count mismatch: "+year)
        benchmark=defaultdict(list)
        for variant,cols in VARIANTS.items():
            models=fit_train(prepared_rows,before,cols)
            predictions=defaultdict(list)
            for f,l,a,b,_ in target:
                p,q_factor,q_direct=probabilities(models,a,b,cols)
                for mode,q in (("factorized6",q_factor),("direct6",q_direct)):
                    o=scored(f,l,(p if mode=="factorized6" else float(q[:3].sum())),q,mode,variant)
                    predictions[mode].append(o)
                    allrows.append(o)
            for mode,rows in predictions.items():
                benchmark[mode+"__"+variant]=rows
        expected=set(m+"__"+v for m in ("factorized6","direct6") for v in VARIANTS)
        if set(benchmark)!=expected:raise ValueError("Missing ablations or direct six")
        summary={key:aggregate(rs) for key,rs in benchmark.items()}
        compare={}
        for mode in ("factorized6","direct6"):
            base=benchmark[mode+"__all_features"]
            compare[mode]={name:{
                "exact":event_bootstrap(benchmark[mode+"__"+name],base,"exact"),
                "six_log_loss":event_bootstrap(benchmark[mode+"__"+name],base,"six_log_loss"),
                "winner_hit":event_bootstrap(benchmark[mode+"__"+name],base,"winner_hit")
            } for name in VARIANTS if name!="all_features"}
        # Same-year exact direct6 versus factorized6 under the same features.
        direct=benchmark["direct6__all_features"]
        factor=benchmark["factorized6__all_features"]
        pair={"exact":event_bootstrap(direct,factor,"exact"),
              "global_exact":event_bootstrap(direct,factor,"global_exact"),
              "six_log_loss":event_bootstrap(direct,factor,"six_log_loss")}
        selection_rows=direct+factor
        folds_out[year]={
            "train_before":before,"test_before":end,
            "evaluation_fights":len(target),
            "models":summary,"feature_ablation_paired":compare,
            "direct6_vs_factorized6":pair,
            "abstention_selection":selection(selection_rows),
        }
    quality_pass=all(not any(audit["unavailable_variable_presence"].values()) for _ in range(1))
    if not quality_pass:raise ValueError("Unsupported features unexpectedly in source!")
    OUT.mkdir(parents=True,exist_ok=True)
    fmt={k:v for k,v in folds_out.items()}
    report={
        "schema":"WSHLX_PHASE2_EXACT_SIX_FEATURE_ABLATION_AND_ABSTENTION_V1",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "source_sha256":manifest["source_stats_sha256"],
        "original_ufcqatar_original_stage_a_and_coherent_lock_unchanged":True,
        "no_code_connected_to_fanduel_bets_or_reference_model":True,
        "all_evaluations_retro_not_300_prospective":True,
        "data_quality":audit,
        "predeclared_feature_families":{k:sorted(v) for k,v in GROUPS.items()},
        "ablations":VARIANTS,
        "folds":fmt,
        "no_model_promoted":True,
    }
    outfile=OUT/"phase2_results.json"
    outfile.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    with (OUT/"out_of_year_six_predictions.csv").open("w",newline="",encoding="utf-8") as h:
        cols=list(allrows[0])
        wr=csv.DictWriter(h,fieldnames=cols)
        wr.writeheader();wr.writerows(allrows)
    (OUT/"run_manifest.json").write_text(json.dumps({
        "source_sha256":manifest["source_stats_sha256"],
        "prediction_sha256":sha(OUT/"out_of_year_six_predictions.csv"),
        "report_sha256":sha(outfile),
        "frozen_originals_mutated":False,
        "evaluation_years":list(folds_out),
        "no_promotion":True,
    },indent=2)+"\n")
    print(json.dumps({"status":"RESEARCH_FINISHED_NOT_PROMOTED",
        "years":{year:{
            "full_factorized":r["models"]["factorized6__all_features"],
            "full_direct6":r["models"]["direct6__all_features"],
            "experience_only_factor":r["models"]["factorized6__experience_only"],
            "selection":r["abstention_selection"]["groups"],
        } for year,r in folds_out.items()},"output":str(OUT)},sort_keys=True,allow_nan=False))
if __name__=="__main__":run()
