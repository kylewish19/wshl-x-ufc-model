"""Round-level prior form: submission opportunities, pace and opponent resistance.
All features are from earlier completed UFC fights, never the target fight.
Only standard first two full five-minute rounds are compared for pace.
Survivor selection means these are conditional historical measures, not fatigue proof.
"""
from collections import defaultdict
from itertools import groupby
from math import log1p
import re
import numpy as np
import pandas as pd
from .historical_data import col,txt,bout
from .prefight_finish_resistance import ARCHIVE

FIELDS=("round_coverage_count","rounds_observed","early_sub_access",
 "late_sub_access","early_opponent_sub_access","late_opponent_sub_access",
 "ground_share","opponent_ground_share","paired_round_bouts",
 "round2_strike_change","round2_absorbed_change","round2_control_change",
 "round2_td_change","round2_sub_change","round2_opponent_control_change",
 "round2_opponent_sub_change")
N=len(FIELDS)

def strict_count(v):
    s=txt(v)
    return int(float(s)) if re.fullmatch(r"\d+(?:\.0+)?",s) else None

def strict_pair(v):
    m=re.fullmatch(r"(\d+)\s+of\s+(\d+)",txt(v),re.I)
    if not m:return None
    a,b=map(int,m.groups())
    return (a,b) if a<=b else None

def strict_time(v):
    m=re.fullmatch(r"(\d+):([0-5]\d)",txt(v))
    return int(m[1])*60+int(m[2]) if m else None

def read_rounds(root=ARCHIVE):
    df=pd.read_csv(root/"ufc_fight_stats.csv",low_memory=False)
    fields={k:col(df,*aliases) for k,aliases in {
        "event":("EVENT",),"bout":("BOUT",),"fighter":("FIGHTER",),
        "round":("ROUND",),"sig":("SIG.STR.",),"td":("TD",),
        "sub":("SUB ATT","SUB.ATT"),"control":("CTRL",),"ground":("GROUND",)}.items()}
    if any(v is None for v in fields.values()):raise ValueError("Required round source column missing: "+str(fields))
    out={};bad=set()
    for x in df.to_dict("records"):
        pair=bout(x[fields["bout"]])
        n=re.fullmatch(r"(?:Round\s*)?(\d+)",txt(x[fields["round"]]),re.I)
        fighter=txt(x[fields["fighter"]])
        if not pair or not n or fighter not in pair:continue
        key=(txt(x[fields["event"]]),*sorted(pair))
        k=(key,fighter,int(n[1]))
        if k in out:bad.add(k);continue
        out[k]={
            "sig":strict_pair(x[fields["sig"]]),"td":strict_pair(x[fields["td"]]),
            "sub":strict_count(x[fields["sub"]]),"ctrl":strict_time(x[fields["control"]]),
            "ground":strict_pair(x[fields["ground"]])}
    for k in bad:out.pop(k,None)
    return out,{"parsed_round_fighter_rows":len(out),"duplicate_rows_excluded":len(bad)}

def snapshot(seq):
    early=[];late=[];pairs=[];ground=[]
    for own,opp in seq:
        for n in sorted(set(own)&set(opp)):
            a,b=own[n],opp[n]
            (early if n==1 else late).append((a,b))
            if a["ground"] is not None and b["ground"] is not None and a["sig"] is not None and b["sig"] is not None:
                if a["ground"][0]<=a["sig"][0] and b["ground"][0]<=b["sig"][0]:
                    ground.append((a["ground"][0],a["sig"][0],b["ground"][0],b["sig"][0]))
        if 1 in own and 2 in own and 1 in opp and 2 in opp:
            a,b,c,d=own[1],own[2],opp[1],opp[2]
            if all(all(x[k] is not None for k in ("sig","td","sub","ctrl")) for x in (a,b,c,d)):
                pairs.append([(b["sig"][0]-a["sig"][0])/50,(d["sig"][0]-c["sig"][0])/50,
                  (b["ctrl"]-a["ctrl"])/300,(b["td"][0]-a["td"][0])/5,
                  (b["sub"]-a["sub"])/3,(d["ctrl"]-c["ctrl"])/300,(d["sub"]-c["sub"])/3])
    def access(rows,side):
        v=[x[side]["sub"] for x in rows if x[side]["sub"] is not None]
        return (sum(z>0 for z in v)+1)/(len(v)+5)
    g=np.array(ground).reshape(-1,4).sum(axis=0)
    # Shrink small samples; explicit coverage and paired-round counts.
    p=np.array(pairs).reshape(-1,7).sum(axis=0)/(len(pairs)+4)
    return np.r_[log1p(len(seq)),log1p(len(early)+len(late)),access(early,0),access(late,0),
        access(early,1),access(late,1),(g[0]+5)/(g[1]+25),(g[2]+5)/(g[3]+25),
        log1p(len(pairs)),p]

def build_round_history(records,rounds,*,query_date=None,query_bouts=()):
    hist=defaultdict(list);out={};covered=0;paired=0
    for day,batch in groupby(sorted(records,key=lambda r:(r["date"],r["event"],r["a"],r["b"])),key=lambda r:r["date"]):
        rows=list(batch)
        for r in rows:
            a,b=r["a"],r["b"];key=(r["event"],*sorted((a,b)))
            k=(day.isoformat(),*key)
            if k in out:raise ValueError("duplicate bout")
            out[k]=(a,b,snapshot(hist[a]),snapshot(hist[b]))
        for r in rows:
            a,b=r["a"],r["b"];key=(r["event"],*sorted((a,b)))
            # Only fully elapsed rounds for pace and opportunity rates.
            # Exclude pre-modern formats and reported format mismatch.
            if day.year<2001 or r.get("round_format_mismatch"):continue
            n=min(5,int(r["elapsed_seconds"]//300))
            aa={i:rounds[(key,a,i)] for i in range(1,n+1) if (key,a,i) in rounds}
            bb={i:rounds[(key,b,i)] for i in range(1,n+1) if (key,b,i) in rounds}
            valid={i for i in aa.keys()&bb.keys() if all(x["ctrl"] is None or x["ctrl"]<=300 for x in (aa[i],bb[i]))}
            if not valid:continue
            aa={i:aa[i] for i in valid};bb={i:bb[i] for i in valid}
            hist[a].append((aa,bb));hist[b].append((bb,aa))
            covered+=1;paired+=int({1,2}<=valid)
    if query_bouts:
        from datetime import date
        if query_date is None or any(r['date']>=date.fromisoformat(query_date) for r in records):raise ValueError('Round query must follow historical records')
        for a,b in query_bouts:
            key=(query_date,'__PREFIGHT_QUERY_NO_RESULTS__',*sorted((a,b)))
            if a==b or key in out:raise ValueError('Invalid round query identity')
            out[key]=(a,b,snapshot(hist[a]),snapshot(hist[b]))
    return out,{"bouts_with_paired_full_round_data":covered,"bouts_with_first_two_full_rounds":paired}

def features(f,side,lookup):
    key=(f["event_date"],f["event"],*sorted((f["fighter_a"],f["fighter_b"])))
    if f["feature_as_of_exclusive"]!=f["event_date"]:raise ValueError("not as of")
    a,b,va,vb=lookup[key]
    if f["fighter_"+side]==a:out=np.r_[va,vb]
    elif f["fighter_"+side]==b:out=np.r_[vb,va]
    else:raise ValueError("identity mismatch")
    if out.shape!=(2*N,) or not np.isfinite(out).all():raise ValueError("invalid round vector")
    return out
