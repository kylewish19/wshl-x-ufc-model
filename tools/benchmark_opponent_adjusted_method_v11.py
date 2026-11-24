"""V11 opponent-adjusted method comparison, fixed v3 winner.
Compare strong prior regional v5 and round86 on same retrospective folds.
No production or prospective claims."""
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
from wshlx_ufc.round_method_v10 import read_rounds,build_round_history,features as round_features
from wshlx_ufc.opponent_adjusted_method_v11 import build as build_adjusted,features as adjusted_features
from benchmark_worldwide_mma_winner_v4 import load_external

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/model_health/2026-11-24_opponent_method_v11"
FOLDS=(("2024","2024-01-01","2025-01-01","2023-01-01",511),
       ("2025","2025-01-01","2026-01-01","2024-01-01",513),
       ("2026_retrospective","2026-01-01","2026-11-14","2025-01-01",488))
ARMS={
 "regional54_tuned":list(range(54)),
 "regional_bilateral70":list(range(70)),
 "round86":list(range(38))+list(range(70,118)),
 "regional_round118":list(range(118)),
 "adjusted_UFC83":list(range(38))+list(range(118,163)),
 "adjusted_full163":list(range(163)),
 "hierarchical_adjusted163":list(range(163)),
}
COEFF=(.005,.025,.20)

def classifier(x,y,c,intercept=True):
    return make_pipeline(StandardScaler(),LogisticRegression(
        C=c,fit_intercept=intercept,max_iter=2000)).fit(x,y)

class Hierarchical:
    def fit(self,x,y,c):
        finish=(y!="DEC")
        self.finish=classifier(x,finish,c)
        self.sub=classifier(x[finish],y[finish]=="SUB",c)
        return self
    def predict(self,x):
        f=self.finish.predict_proba(x)[:,1]
        s=self.sub.predict_proba(x)[:,1]
        return np.c_[f*(1-s),f*s,1-f]

def fit_method(name,x,y,c):
    return Hierarchical().fit(x,y,c) if name.startswith("hierarchical") else classifier(x,y,c)

def cond(model,x):
    if isinstance(model,Hierarchical):return model.predict(x)
    p=model.predict_proba(x)
    return p[:,[list(model[-1].classes_).index(m) for m in METHODS]]

def main():
    feats,labs,manifest=load_matrix()
    forms,_=supplement_current_feature_matrix(feats)
    region,region_audit=load_external(feats)
    base=_load_records(ARCHIVE,date(2026,11,14))
    if len(base)!=8871:raise ValueError("Historical archive drift")
    conversion=build_conversion(base)
    adjusted,adjusted_audit=build_adjusted(base)
    assert adjusted_audit['historical_bouts']==8871
    rounds,round_audit=read_rounds()
    round_lookup,coverage=build_round_history(base,rounds)
    if coverage['bouts_with_first_two_full_rounds']<1000:raise ValueError('Insufficient real paired rounds: '+str(coverage))
    labels={x["bout_id"]:x for x in labs}
    cases=[]
    for f in feats:
        y=labels[f["bout_id"]]
        if f["event_date"]<"2021-01-01" or y["result_status"]!="DECISIVE":continue
        va,vb=matrices(f,forms)
        def vector(side):
            v=enriched_features(f,side,conversion)
            ra,rb,_=region[f["bout_id"]]
            own,rival=(ra,rb) if side=="a" else (rb,ra)
            out=np.r_[v[:38],own,rival,v[38:54],round_features(f,side,round_lookup),adjusted_features(f,side,adjusted)]
            if out.shape!=(163,) or not np.isfinite(out).all():raise ValueError("Invalid V11 matchup")
            return out
        a,b=vector("a"),vector("b")
        cases.append((f,y,va-vb,np.stack((a,b))))
    if len(cases)!=3015:raise ValueError("Expected fixed historical cohort")
    output=[];results={}
    def method_training(rows,indices):
        return (np.array([x[3][0 if int(x[1]["label_a_win"]) else 1,indices] for x in rows]),
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
                q=cond(fit_method(name,ix,iy,c),vx)
                losses[str(c)]=float(-np.log(np.maximum(1e-12,q[np.arange(len(vy)),ids])).mean())
            chosen=min(COEFF,key=lambda c:(losses[str(c)],c))
            tx,ty=method_training(train,d)
            models[name]=fit_method(name,tx,ty,chosen)
            tuning[name]={"C":chosen,"conditional_logloss_by_C":losses,
                          "inner_train":len(inner),"prior_year_validation":len(val)}
        # Preserve the old fixed .20 control as a fourth comparator; do not confuse
        # improved regularization alone with new data.
        tx,ty=method_training(train,list(range(54)))
        models["regional_v5_fixed54"]=classifier(tx,ty,.2)
        by=defaultdict(list)
        for f,y,v,vec in testing:
            p=float(winner.predict_proba(v.reshape(1,-1))[0,1])
            reverse=float(winner.predict_proba((-v).reshape(1,-1))[0,1])
            p=(p+1-reverse)*.5
            for name,m in models.items():
                d=ARMS.get(name,list(range(54)))
                q=coherent_six(p,cond(m,vec[:,d]))
                scored=score_six(q,0 if int(y["label_a_win"]) else 1,y["label_method"],p_a=p)
                r={**scored,"event_date":f["event_date"],"event":f["event"],
                   "bout_id":f["bout_id"],"model":name,"p_a":p,
                   **dict(zip(("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC"),map(float,q)))}
                by[name].append(r);output.append(r)
        stats={k:aggregate(v) for k,v in by.items()}
        assert len({v["winner_hits"] for v in stats.values()})==1
        pair={name:{metric:event_paired_diff(rows,by["regional_v5_fixed54"],metric)
                   for metric in ("exact","six_log_loss","method_class_correct")}
              for name,rows in by.items() if name!="regional_v5_fixed54"}
        results[year]={"test_n":n,"train_n":len(train),"coefficient_validation_year_start":valstart,
                       "tuning":tuning,"scores":stats,"paired_vs_v5":pair}
    OUT.mkdir(parents=True,exist_ok=True)
    csvfile=OUT/"opponent_v11_paired_forecasts.csv"
    with csvfile.open("w",newline="",encoding="utf-8") as h:
        wr=csv.DictWriter(h,fieldnames=list(output[0]));wr.writeheader();wr.writerows(output)
    report={"schema":"WSHLX_OPPONENT_ADJUSTED_METHOD_V11_RESEARCH",
            "source_sha256":manifest["source_stats_sha256"],"models":{k:len(v) for k,v in ARMS.items()},
            "regional_source":region_audit,"adjustment_audit":adjusted_audit,
            "round_source_audit":{**round_audit,**coverage},
            "same_v3_winner_probabilities_for_all_arms":True,
            "earlier_year_only_tuning":True,"same_day_future_results_excluded":True,
            "not_causal_conversion_or_current_fight_observations":True,
            "previously_inspected_retrospective_years":True,"no_model_promotion":True,
            "forecast_sha256":hashlib.sha256(csvfile.read_bytes()).hexdigest(),"yearly":results}
    (OUT/"opponent_v11_results.json").write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("ADJUSTED_COVERAGE",json.dumps(adjusted_audit,sort_keys=True))
    print("ROUND_COVERAGE",json.dumps({**round_audit,**coverage},sort_keys=True))
    print(json.dumps({yr:{k:{"winner":v["winner_hits"],"exact":v["exact_hits"],
                  "ll":v["six_log_loss"],"sub_exact":v["methods"]["SUB"]["exact_hits"]}
                 for k,v in data["scores"].items()} for yr,data in results.items()},sort_keys=True))
if __name__=="__main__":main()
