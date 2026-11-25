"""Paired retrospective identity correction benchmark, not a new holdout."""
from pathlib import Path
from collections import defaultdict
import json
from audit_ufc_identity_overlay import mapping,overlay,pairkey
from wshlx_ufc.postevent_history_extension_v1 import load_extended_records
from wshlx_ufc.strict_history_inputs_v1 import matrices_from_records
from wshlx_ufc.finish_v1_research import coherent_six,score_six,aggregate
from benchmark_strict_history_v1 import train,predict
from benchmark_winner_recent_form_v3 import event_paired_diff,FOLDS

def main():
    day="2026-12-05"
    records,_=load_extended_records(as_of_exclusive=day)
    fixed,_=overlay(records,mapping())
    old=matrices_from_records(records,day)
    new=matrices_from_records(fixed,day)
    a,b=({pairkey(x):x for x in m[0]} for m in (old,new))
    assert a.keys()==b.keys()
    oldlabels={x["bout_id"]:x for x in old[1]}
    newlabels={x["bout_id"]:x for x in new[1]}
    for k in a:
        x,y=oldlabels[a[k]["bout_id"]],newlabels[b[k]["bout_id"]]
        assert all(x[z]==y[z] for z in ("result_status","label_a_win","label_method","label_elapsed_seconds"))
    report={}
    # Same historical folds as previous benchmarks; last 24 additions are not a fresh test.
    for year,start,end,n in FOLDS:
        fits=[train(*m,start) for m in (old,new)]
        assert fits[0][2]==fits[1][2]
        scored=defaultdict(list)
        for k,x in a.items():
            l=oldlabels[x["bout_id"]]
            if not start<=k[0]<end or l["result_status"]!="DECISIVE":continue
            p,c=predict(x,old[2],fits[0])
            q,d=predict(b[k],new[2],fits[1])
            for name,pw,cm in (("legacy",p,c),("corrected_winner_only",q,c),("corrected_method_only",p,d),("corrected_both",q,d)):
                s=score_six(coherent_six(pw,cm),0 if l["label_a_win"] else 1,l["label_method"],p_a=pw)
                scored[name].append({**s,"bout_id":x["bout_id"],"event_date":k[0],"event":k[1]})
        assert all(len(v)==n for v in scored.values()) and len(scored)==4
        report[year]={"n":n,"training_n":fits[0][2],"scores":{k:aggregate(v) for k,v in scored.items()},"paired_vs_legacy":{k:{m:event_paired_diff(v,scored["legacy"],m) for m in ("winner_correct","exact","six_log_loss")} for k,v in scored.items() if k!="legacy"}}
        print("IDENTITY_FOLD",year,json.dumps({k:{x:s[x] for x in ("winner_hits","exact_hits","six_log_loss")} for k,s in report[year]["scores"].items()}))
    result={"yearly":report,"same_labels":True,"same_architecture":True,"retrospective_reused_cohort":True,"new_prospective_observations":0,"no_model_promotion":True,"production_migrated":False}
    Path("identity_corrected_benchmark.json").write_text(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__":main()
