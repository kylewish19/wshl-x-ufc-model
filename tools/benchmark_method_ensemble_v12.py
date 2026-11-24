"""V12 uses immutable V11 out-of-year forecasts, not in-sample predictions.
2024 fits meta-model for 2025; 2024+2025 fit it for 2026. No 2024
meta-test, no target-year coefficient selection, no official picks.
"""
from collections import defaultdict
from pathlib import Path
import csv,json,hashlib
import numpy as np
from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.finish_v1_research import METHODS,coherent_six,score_six,aggregate
from wshlx_ufc.method_ensemble_v12 import group,fit,predict,validate
from benchmark_winner_recent_form_v3 import event_paired_diff

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"reports/model_health/2026-11-24_opponent_method_v11"
OUT=ROOT/"reports/model_health/2026-11-24_method_ensemble_v12"
NAMES=("regional_v5_fixed54","regional_bilateral70","round86",
       "regional_round118","adjusted_full163","hierarchical_adjusted163")
KEYS=("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")
COUNTS={"2024":511,"2025":513,"2026":488}

def topk(rows):
    cards=defaultdict(list)
    for r in rows:cards[(r["event_date"],r["event"])].append(r)
    eligible=[x for x in cards.values() if 11<=len(x)<=14]
    out={"cards":len(eligible)}
    for k in (2,3,4,5):
        picks=[sorted(c,key=lambda r:(-r["p_selected_exact"],r["bout_id"]))[:k] for c in eligible]
        out[str(k)]={"n":sum(map(len,picks)),"hits":sum(r["exact"] for c in picks for r in c),
            "perfect_cards":sum(all(r["exact"] for r in c) for c in picks)}
    return out

def main():
    meta=json.loads((SRC/"opponent_v11_results.json").read_text())
    file=SRC/"opponent_v11_paired_forecasts.csv"
    if hashlib.sha256(file.read_bytes()).hexdigest()!=meta["forecast_sha256"]:raise ValueError("V11 artifact changed")
    if not meta["adjustment_audit"]["raw_missing_values_not_filled"]:raise ValueError("Wrong pre-correction V11 source")
    features,labels,manifest=load_matrix()
    if manifest["source_stats_sha256"]!=meta["source_sha256"]:raise ValueError("UFC source drift")
    f={x["bout_id"]:x for x in features}; y={x["bout_id"]:x for x in labels}
    rows=defaultdict(dict)
    with file.open() as h:
        for r in csv.DictReader(h):
            if r["model"] not in NAMES:continue
            b=r["bout_id"];m=r["model"]
            if m in rows[b]:raise ValueError("duplicate model")
            rows[b][m]=r
    cohort=defaultdict(list)
    for b,rs in rows.items():
        if set(rs)!=set(NAMES):raise ValueError("incomplete model coverage")
        ff=f[b];yy=y[b];date=ff["event_date"]
        if yy["result_status"]!="DECISIVE":raise ValueError("nondecisive")
        side=0 if int(yy["label_a_win"]) else 1
        method=METHODS.index(yy["label_method"])
        p=float(rs[NAMES[0]]["p_a"])
        cond=[]
        for name in NAMES:
            r=rs[name]
            if r["event_date"]!=date or r["event"]!=ff["event"] or abs(float(r["p_a"])-p)>1e-12 or r["true_method"]!=yy["label_method"]:
                raise ValueError("model or label misalignment")
            q=np.array([float(r[k]) for k in KEYS]).reshape(2,3)
            if not 0<p<1 or not np.allclose(q.sum(1),[p,1-p],atol=1e-8,rtol=0):
                raise ValueError("winner marginal mismatch")
            cond.append(q/np.array([[p],[1-p]]))
        cohort[date[:4]].append({"bout_id":b,"event_date":date,"event":ff["event"],
            "side":side,"method":method,"group":group(ff),"p":validate(cond),"p_a":p})
    for yr,n in COUNTS.items():
        if len(cohort[yr])!=n:raise ValueError("cohort mismatch")
        cohort[yr].sort(key=lambda r:(r["event_date"],r["event"],r["bout_id"]))
    report={};allrows=[]
    for yr in ("2025","2026"):
        earlier=[r for k,v in cohort.items() if k<yr for r in v]
        if max(r["event_date"] for r in earlier)>=min(r["event_date"] for r in cohort[yr]):raise ValueError("meta leakage")
        fitted=fit(earlier)
        scored=defaultdict(list)
        for r in cohort[yr]:
            pp=predict(r["p"],r["group"],fitted)
            pp.update(dict(zip(NAMES,r["p"])))
            for name,c in pp.items():
                q=coherent_six(r["p_a"],c)
                side=0 if r["p_a"]>=.5 else 1
                s=score_six(q,r["side"],METHODS[r["method"]],p_a=r["p_a"])
                row={**s,"event_date":r["event_date"],"event":r["event"],"bout_id":r["bout_id"],
                     "group":r["group"],"model":name,"p_a":r["p_a"],
                     "p_selected_exact":float(max(q[3*side:3*side+3])),
                     **dict(zip(KEYS,map(float,q)))}
                scored[name].append(row);allrows.append(row)
        scores={name:aggregate(v) for name,v in scored.items()}
        if len({v["winner_hits"] for v in scores.values()})!=1:raise ValueError("winner changed")
        report[yr]={"meta_train_n":len(earlier),"test_n":len(cohort[yr]),
          "weights":dict(zip(NAMES,map(float,fitted[0]))),
          "group_weights":{g:dict(zip(NAMES,map(float,w))) for g,w in fitted[1].items()},
          "temperature":fitted[2],"scores":scores,
          "topk":{k:topk(v) for k,v in scored.items()},
          "subgroups":{k:{g:aggregate([r for r in v if r["group"]==g])
                   for g in sorted({r["group"] for r in v})} for k,v in scored.items()},
          "paired_vs_v5":{k:{m:event_paired_diff(v,scored[NAMES[0]],m)
               for m in ("exact","six_log_loss")} for k,v in scored.items() if k!=NAMES[0]}}
    OUT.mkdir(parents=True,exist_ok=True)
    out=OUT/"ensemble_v12_forecasts.csv"
    with out.open("w",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
    result={"schema":"WSHLX_METHOD_ENSEMBLE_V12","source_run":45494717295,
       "source_forecast_sha256":meta["forecast_sha256"],"out_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
       "winner_fixed":True,"no_promotion":True,"retrospective_only":True,"yearly":report}
    (OUT/"ensemble_v12_results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    for yr,d in report.items():
        print("V12_RESULT",yr,json.dumps({"weights":d["weights"],"temperature":d["temperature"],
            "group_weights":d["group_weights"],
            "scores":{k:{"winner":v["winner_hits"],"exact":v["exact_hits"],
                 "ll":round(v["six_log_loss"],6),"sub":v["methods"]["SUB"]["exact_hits"],
                 "topk":d["topk"][k]} for k,v in d["scores"].items()}}))
if __name__=="__main__":main()
