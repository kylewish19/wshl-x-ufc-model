"""Compare only input correction, not architecture or hyperparameter changes."""
from pathlib import Path
from datetime import date
from collections import defaultdict
import json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from wshlx_ufc.prefight_finish_resistance import ARCHIVE,_load_records
from wshlx_ufc.strict_history_inputs_v1 import strict_records,matrices_from_records
from wshlx_ufc.finish_v1_research import MultinomialFinish,training_rows,method_features,coherent_six,score_six,aggregate
from benchmark_winner_recent_form_v3 import matrices,event_paired_diff,FOLDS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/model_health/2026-11-24_strict_history_v1"
def train(features,labels,forms,cutoff):
    by={l["bout_id"]:l for l in labels}
    rows=[(f,by[f["bout_id"]]) for f in features if "2021-01-01"<=f["event_date"]<cutoff and by[f["bout_id"]]["result_status"]=="DECISIVE"]
    z=np.array([np.subtract(*matrices(f,forms)) for f,l in rows])
    y=np.array([int(l["label_a_win"]) for f,l in rows])
    winner=make_pipeline(StandardScaler(),LogisticRegression(C=.2,fit_intercept=False,max_iter=1800)).fit(np.stack((z,-z),axis=1).reshape(-1,57),np.stack((y,1-y),axis=1).reshape(-1))
    X,Y=training_rows(features,labels,cutoff)
    assert len(Y)==len(rows)
    return winner,MultinomialFinish().fit(X,Y),len(rows)

def predict(f,forms,model):
    w,m,_=model
    z=np.subtract(*matrices(f,forms)).reshape(1,-1)
    p=float((w.predict_proba(z)[0,1]+1-w.predict_proba(-z)[0,1])*.5)
    c=m.predict(np.vstack((method_features(f,"a"),method_features(f,"b"))))
    return p,c

def main():
    raw=_load_records(ARCHIVE,date(2026,11,14))
    clean,audit=strict_records(raw)
    assert len(raw)==len(clean)==8871
    old=matrices_from_records(raw,"2026-11-14")
    new=matrices_from_records(clean,"2026-11-14")
    assert old[1]==new[1]
    a,b=({f["bout_id"]:f for f in m[0]} for m in (old,new))
    changed=sum(any(a[k][x]!=b[k][x] for x in a[k] if x.startswith(("a_","b_"))) or not all(np.array_equal(u,v) for u,v in zip(old[2][k],new[2][k])) for k in old[2])
    report={}
    for year,start,end,n in FOLDS:
        fits=[train(*m,start) for m in (old,new)]
        rows=defaultdict(list)
        for l in old[1]:
            if not start<=l["event_date"]<end or l["result_status"]!="DECISIVE":continue
            k=l["bout_id"]
            p,c=predict(a[k],old[2],fits[0]);q,d=predict(b[k],new[2],fits[1])
            for name,pw,cm in (("legacy_both",p,c),("strict_method_only",p,d),("strict_winner_only",q,c),("strict_both",q,d)):
                s=score_six(coherent_six(pw,cm),0 if int(l["label_a_win"]) else 1,l["label_method"],p_a=pw)
                rows[name].append({**s,"bout_id":k,"event_date":l["event_date"],"event":a[k]["event"]})
        assert all(len(v)==n for v in rows.values())
        report[year]={"scores":{k:aggregate(v) for k,v in rows.items()},
          "paired_vs_legacy":{k:{m:event_paired_diff(v,rows["legacy_both"],m) for m in ("winner_correct","exact","six_log_loss")} for k,v in rows.items() if k!="legacy_both"}}
    OUT.mkdir(parents=True,exist_ok=True)
    d={"audit":audit,"modern_feature_rows_changed":changed,"same_labels":True,"yearly":report,"research_only":True}
    (OUT/"results.json").write_text(json.dumps(d,indent=2,allow_nan=False)+"\n")
    print("STRICT_AUDIT",json.dumps(audit),"changed",changed)
    for yr,v in report.items():print("STRICT_RESULT",yr,json.dumps({k:{x:s[x] for x in ("winner_hits","exact_hits","six_log_loss")} for k,s in v["scores"].items()}))
if __name__=="__main__":main()
