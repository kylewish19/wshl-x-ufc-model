"""Observed prior finishing opportunities and conversion (research v9).

These are descriptive associations in already completed fights, not causal
measurements or predictions of future knockdowns/takedowns. The current bout
and all other same-date outcomes are excluded from every feature.
"""
from __future__ import annotations
from collections import defaultdict,Counter
from itertools import groupby
from math import log1p
import numpy as np

OPPORTUNITIES=("kd","no_kd","sub_attempt","grappling_access","grappling_access_dec")
TARGETS=("KO_TKO","KO_TKO","SUB","SUB","DEC")
PRIORS=(.50,.10,.24,.12,.32)
METHODS=("KO_TKO","SUB","DEC")
MIX=(.38,.18,.44)
MIX_N=8
CONVERSION_N=20

def state():
    return {"outcome":Counter(),"opportunities":Counter(),"conversions":Counter()}

def vectors(s):
    counts=s["outcome"]
    result=[]
    for side in ("W","L"):
        n=sum(counts[(side,m)] for m in METHODS)
        result.extend((counts[(side,m)]+6*p)/(n+6) for m,p in zip(METHODS,MIX))
        result.append(log1p(n))
    conversion=[]
    for role in ("offense","defense"):
        for opportunity,target,p in zip(OPPORTUNITIES,TARGETS,PRIORS):
            k=(role,opportunity)
            n=s["opportunities"][k];v=s["conversions"][k]
            if not 0<=v<=n:raise ValueError("Invalid prior conversion count")
            conversion.extend(((v+5*p)/(n+5),log1p(n)))
    return np.array(result,float),np.array(conversion,float)

def observe(s,own,rival,result,method):
    if result in ("W","L") and method in METHODS:
        s["outcome"][(result,method)]+=1
    if own is None or rival is None:return
    # Never impute a missing opportunity measurement as zero.
    for role,x,target_result in (("offense",own,"W"),("defense",rival,"L")):
        needed=("kd","sub_att","td_landed","ctrl_sec")
        if any(k not in x or not np.isfinite(x[k]) or x[k]<0 for k in needed):continue
        access=x["td_landed"]>0 or x["ctrl_sec"]>=60
        flags=(x["kd"]>0,x["kd"]==0,x["sub_att"]>0,access,access)
        for name,target,flag in zip(OPPORTUNITIES,TARGETS,flags):
            if not flag:continue
            key=(role,name)
            s["opportunities"][key]+=1
            s["conversions"][key]+=int(result==target_result and method==target)

def build_conversion(records,*,query_date=None,query_bouts=()):
    history=defaultdict(state);out={}
    data=sorted(records,key=lambda x:(x["date"],x["event"],x["a"],x["b"]))
    for day,batch in groupby(data,key=lambda r:r["date"]):
        rows=list(batch)
        for r in rows:
            key=(day.isoformat(),r["event"],*sorted((r["a"],r["b"])))
            if key in out:raise ValueError("Duplicate historical bout")
            out[key]=(r["a"],r["b"],vectors(history[r["a"]]),vectors(history[r["b"]]))
        for r in rows:
            a,b=r["a"],r["b"]
            observe(history[a],r["stats_a"],r["stats_b"],r["result"][0],r["method"])
            observe(history[b],r["stats_b"],r["stats_a"],r["result"][1],r["method"])
    if query_bouts:
        from datetime import date
        if query_date is None or any(r['date']>=date.fromisoformat(query_date) for r in records):raise ValueError('Conversion query must follow historical records')
        for a,b in query_bouts:
            key=(query_date,'__PREFIGHT_QUERY_NO_RESULTS__',*sorted((a,b)))
            if a==b or key in out:raise ValueError('Invalid conversion query identity')
            out[key]=(a,b,vectors(history[a]),vectors(history[b]))
    return out

def enriched_features(f,side,lookup):
    from .finish_v1_research import method_features
    if f["feature_as_of_exclusive"]!=f["event_date"]:raise ValueError("Not prefight")
    key=(f["event_date"],f["event"],*sorted((f["fighter_a"],f["fighter_b"])))
    a,b,va,vb=lookup[key]
    fighter=f["fighter_"+side]
    own,rival=(va,vb) if fighter==a else (vb,va) if fighter==b else (None,None)
    if own is None:raise ValueError("Source identity mismatch")
    v=np.r_[method_features(f,side),own[0],rival[0],own[1],rival[1]]
    if v.shape!=(94,) or not np.isfinite(v).all():raise ValueError("Invalid conversion feature vector")
    return v
