"""Strict complete-case adapter for legacy resistance and recent-form builders.
An incomplete fighter-bout is not a zero-stat bout. Outcomes are always retained.
This is a new research input, not a change to historical locks or legacy parser.
"""
from collections import Counter
from math import ceil,isfinite
import re
import pandas as pd
from .historical_data import col,txt,bout
from .round_method_v10 import strict_count,strict_pair,strict_time
from .prefight_finish_resistance import ARCHIVE

REQUIRED=("kd","sub_att","td_landed","td_attempted","ctrl_sec",
          "sig_landed","sig_attempted")
def complete(s,elapsed):
    if s is None:return False
    if any(k not in s or s[k] is None or not isfinite(s[k]) or s[k]<0 or int(s[k])!=s[k] for k in REQUIRED):return False
    return s["td_landed"]<=s["td_attempted"] and s["sig_landed"]<=s["sig_attempted"] and s["ctrl_sec"]<=elapsed

def strict_records(records,root=ARCHIVE):
    df=pd.read_csv(root/"ufc_fight_stats.csv",low_memory=False)
    columns={k:col(df,*v) for k,v in {
       "event":("EVENT",),"bout":("BOUT",),"fighter":("FIGHTER",),"round":("ROUND",),
       "kd":("KD",),"sub":("SUB ATT","SUB.ATT"),"td":("TD",),
       "ctrl":("CTRL",),"sig":("SIG.STR.",)}.items()}
    if any(v is None for v in columns.values()):raise ValueError("Missing required raw column")
    raw={};dupes=set()
    for row in df.to_dict("records"):
        pair=bout(row[columns["bout"]]);name=txt(row[columns["fighter"]])
        rnd=re.fullmatch(r"(?:Round\s*)?(\d+)",txt(row[columns["round"]]),re.I)
        if not pair or name not in pair or not rnd:continue
        k=(txt(row[columns["event"]]),*sorted(pair),name,int(rnd[1]))
        if k in raw:dupes.add(k);continue
        td=strict_pair(row[columns["td"]]);sig=strict_pair(row[columns["sig"]])
        raw[k]={"kd":strict_count(row[columns["kd"]]),"sub_att":strict_count(row[columns["sub"]]),
            "td_landed":td[0] if td else None,"td_attempted":td[1] if td else None,
            "sig_landed":sig[0] if sig else None,"sig_attempted":sig[1] if sig else None,
            "ctrl_sec":strict_time(row[columns["ctrl"]])}
    for k in dupes:raw.pop(k,None)
    out=[];audit=Counter();fields=Counter()
    for r in records:
        item=dict(r)
        if r["date"].isoformat()>"2026-11-07":
            # Only caller's verified extension totals, never an invented raw
            # match. Preserve its results-only default and opt-in provenance.
            for side in ("a","b"):
                s=r.get("stats_"+side)
                item["stats_"+side]=s if complete(s,r["elapsed_seconds"]) else None
            audit["extension_bouts"]+=1
        else:
            n=max(1,int(ceil(r["elapsed_seconds"]/300)))
            for side in ("a","b"):
                key=(r["event"],*sorted((r["a"],r["b"])),r[side])
                rr=[raw.get((*key,i)) for i in range(1,n+1)] if n<=5 and not r.get("round_format_mismatch") else []
                sums={}
                for k in REQUIRED:
                    values=[x[k] for x in rr if x is not None]
                    ok=bool(rr) and len(values)==len(rr) and all(v is not None for v in values)
                    if k=="ctrl_sec" and ok:
                        ok=all(v<=min(300,r["elapsed_seconds"]-300*i) for i,v in enumerate(values))
                    sums[k]=sum(values) if ok else None
                    if not ok:fields[k]+=1
                item["stats_"+side]=sums if complete(sums,r["elapsed_seconds"]) else None
        old=all(r.get("stats_"+s) is not None for s in ("a","b"))
        new=all(item.get("stats_"+s) is not None for s in ("a","b"))
        audit["bouts"]+=1;audit["legacy_complete"]+=old;audit["strict_complete"]+=new
        audit["legacy_complete_now_quarantined"]+=old and not new
        if old and new:
            audit["both_complete_changed_values"]+=any(float(r["stats_"+s].get(k,0))!=item["stats_"+s][k] for s in ("a","b") for k in REQUIRED)
        out.append(item)
    return out,dict(audit)|{"missing_field_totals":dict(fields),"duplicate_raw_round_keys":len(dupes),
          "complete_case_policy":True,"all_outcome_labels_retained":True}

def matrices_from_records(records,cutoff):
    from .prefight_finish_resistance import build_from_records
    from .historical_feature_matrix import build_matrix
    from .winner_recent_form_v3 import construct_record_history
    snaps,_=build_from_records(records,as_of_exclusive=cutoff)
    features,labels=build_matrix(records,snaps)
    form=construct_record_history(records,cutoff=cutoff)
    forms={}
    for f in features:
        if f["event_date"]<"2021-01-01":continue
        s=form[(f["event_date"],f["event"],*sorted((f["fighter_a"],f["fighter_b"])))]
        if (s["a_name"],s["b_name"])!=(f["fighter_a"],f["fighter_b"]):raise ValueError("form identity mismatch")
        forms[f["bout_id"]]=(s["a"],s["b"])
    return features,labels,forms
