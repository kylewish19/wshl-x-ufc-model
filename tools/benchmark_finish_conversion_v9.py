"""Compare verified UFC finishing-method features on identical historical fights.

Winner v3 logistic57 fixed in all arms; no odds. Same old historical years
previously investigated; strictly date-forward fitting, not an unseen test.
Only compare the UFC-only conditional head with new method mix/ conversion.
Does not claim to beat worldwide Method v5 or production champion.
"""
from collections import defaultdict
from datetime import date
from pathlib import Path
import hashlib,json,csv
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.prefight_finish_resistance import _load_records,ARCHIVE
from wshlx_ufc.winner_recent_form_v3 import supplement_current_feature_matrix
from wshlx_ufc.finish_v1_research import METHODS,coherent_six,score_six,aggregate
from wshlx_ufc.finish_conversion_v9 import build_conversion,enriched_features
from benchmark_winner_recent_form_v3 import matrices,event_paired_diff

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/model_health/2026-11-24_conversion_method_v9"
FOLDS=(("2024","2024-01-01","2025-01-01","2023-01-01",511),
       ("2025","2025-01-01","2026-01-01","2024-01-01",513),
       ("2026_retrospective","2026-01-01","2026-11-14","2025-01-01",488))
ARMS={"baseline_UFC38":38,"historical_method_mix54":54,"conversion94":94}
COEFF=(.005,.025,.20)

def classifier(x,y,c,intercept=True):
    return make_pipeline(StandardScaler(),LogisticRegression(
        C=c,fit_intercept=intercept,max_iter=2000)).fit(x,y)

def cond(model,x):
    p=model.predict_proba(x)
    return p[:,[list(model[-1].classes_).index(m) for m in METHODS]]

def main():
    feats,labs,manifest=load_matrix()
    forms,_=supplement_current_feature_matrix(feats)
    base=_load_records(ARCHIVE,date(2026,11,14))
    if len(base)!=8871:raise ValueError("Historical archive drift")
    conversion=build_conversion(base)
    labels={x["bout_id"]:x for x in labs}
    cases=[]
    for f in feats:
        y=labels[f["bout_id"]]
        if f["event_date"]<"2021-01-01" or y["result_status"]!="DECISIVE":continue
        va,vb=matrices(f,forms)
        a=enriched_features(f,"a",conversion);b=enriched_features(f,"b",conversion)
        cases.append((f,y,va-vb,np.stack((a,b))))
    if len(cases)!=3015:raise ValueError("Expected fixed historical cohort")
    output=[];results={}
    def method_training(rows,d):
        return (np.array([x[3][0 if int(x[1]["label_a_win"]) else 1,:d] for x in rows]),
                np.array([x[1]["label_method"] for x in rows]))
    for year,start,end,valstart,n in FOLDS:
        train=[r for r in cases if r[0]["event_date"]<start]
        inner=[r for r in train if r[0]["event_date"]<valstart]
        val=[r for r in train if valstart<=r[0]["event_date"]<start]
        testing=[r for r in cases if start<=r[0]["event_date"]<end]
        if len(testing)!=n:raise ValueError("Historical cohort changed")
        z=np.array([r[2] for r in train]);w=np.array([int(r[1]["label_a_win"]) for r in train])
        # Reuse the v3 symmetric, no-intercept winner architecture, identical across all arms.
        # Interleave A/B mirrors exactly like v3.
        z=np.stack((z,-z),axis=1).reshape(-1,57)
        w=np.stack((w,1-w),axis=1).reshape(-1)
        winner=classifier(z,w,.2,False)
        models={};tuning={}
        for name,d in ARMS.items():
            ix,iy=method_training(inner,d);vx,vy=method_training(val,d)
            ids=np.array([METHODS.index(m) for m in vy])
            losses={}
            for c in COEFF:
                q=cond(classifier(ix,iy,c),vx)
                losses[str(c)]=float(-np.log(np.maximum(1e-12,q[np.arange(len(vy)),ids])).mean())
            chosen=min(COEFF,key=lambda c:(losses[str(c)],c))
            tx,ty=method_training(train,d)
            models[name]=classifier(tx,ty,chosen)
            tuning[name]={"C":chosen,"conditional_logloss_by_C":losses,
                          "inner_train":len(inner),"prior_year_validation":len(val)}
        # Preserve the old fixed .20 control as a fourth comparator; do not confuse
        # improved regularization alone with new data.
        tx,ty=method_training(train,38)
        models["legacy_UFC38_C020"]=classifier(tx,ty,.2)
        by=defaultdict(list)
        for f,y,v,vec in testing:
            p=float(winner.predict_proba(v.reshape(1,-1))[0,1])
            reverse=float(winner.predict_proba((-v).reshape(1,-1))[0,1])
            p=(p+1-reverse)*.5
            for name,m in models.items():
                d=ARMS.get(name,38)
                q=coherent_six(p,cond(m,vec[:,:d]))
                scored=score_six(q,0 if int(y["label_a_win"]) else 1,y["label_method"],p_a=p)
                r={**scored,"event_date":f["event_date"],"event":f["event"],
                   "bout_id":f["bout_id"],"model":name,"p_a":p}
                by[name].append(r);output.append(r)
        stats={k:aggregate(v) for k,v in by.items()}
        assert len({v["winner_hits"] for v in stats.values()})==1
        pair={name:{metric:event_paired_diff(rows,by["baseline_UFC38"],metric)
                   for metric in ("exact","six_log_loss","method_class_correct")}
              for name,rows in by.items() if name!="baseline_UFC38"}
        results[year]={"test_n":n,"train_n":len(train),"coefficient_validation_year_start":valstart,
                       "tuning":tuning,"scores":stats,"paired_vs_tuned_UFC38":pair}
    OUT.mkdir(parents=True,exist_ok=True)
    csvfile=OUT/"conversion_v9_paired_forecasts.csv"
    with csvfile.open("w",newline="",encoding="utf-8") as h:
        wr=csv.DictWriter(h,fieldnames=list(output[0]));wr.writeheader();wr.writerows(output)
    report={"schema":"WSHLX_FINISH_CONVERSION_V9_PRIOR_OPPORTUNITY_RESEARCH",
            "source_sha256":manifest["source_stats_sha256"],"models":ARMS,
            "same_v3_winner_probabilities_for_all_arms":True,
            "earlier_year_only_tuning":True,"same_day_future_results_excluded":True,
            "not_causal_conversion_or_current_fight_observations":True,
            "previously_inspected_retrospective_years":True,"no_model_promotion":True,
            "forecast_sha256":hashlib.sha256(csvfile.read_bytes()).hexdigest(),"yearly":results}
    (OUT/"conversion_v9_results.json").write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({yr:{k:{"winner":v["winner_hits"],"exact":v["exact_hits"],
                  "ll":v["six_log_loss"],"sub_exact":v["methods"]["SUB"]["exact_hits"]}
                 for k,v in data["scores"].items()} for yr,data in results.items()},sort_keys=True))
if __name__=="__main__":main()
