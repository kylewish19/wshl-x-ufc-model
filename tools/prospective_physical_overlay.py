"""Provenance-gated prospective physical field overlay.
No historical training edits. Only observed missing fields may be filled.
Default frozen model execution remains unchanged.
"""
from copy import deepcopy
from datetime import date
from urllib.parse import urlparse
import math
import pandas as pd
import numpy as np
import rebuild_v027 as rb
import audit_worldwide_mma_history_v4 as a

FIELDS={"height_in":"height","reach_in":"reach"}
def need(ok,msg):
    if not ok:raise ValueError(msg)
def build_overrides(observation,identities,day,static):
    need(observation["schema"]=="WSHLX_PHYSICAL_PROFILE_SOURCE_OBSERVATION_V1" and observation["status"]=="FIELD_VERIFIED_OBSERVATION_NOT_MODEL_INPUT" and observation["units"]=="inches","Wrong observation schema")
    need(date.fromisoformat(observation["observed_date"])<date.fromisoformat(day),"Physical source must precede event")
    ix={z["regional_id"]:z for pair in identities for z in pair}
    need(len(ix)==sum(len(p) for p in identities),"Repeated identity")
    seen=set();result={};ledger=[]
    for row in observation["fighters"]:
        fid=row["regional_id"]
        need(fid not in seen,"Duplicate observation");seen.add(fid)
        if fid not in ix:continue # withdrawn fighter not used
        z=ix[fid];n=z["source_name"]
        need(z["ufcstats_profile_id"]==row["ufcstats_profile_id"] and a.namekey(z["display_name"])==a.namekey(row["fighter"]),"Physical identity mismatch")
        need(row["applied_to_frozen_model_inputs"] is False,"Not original source observation")
        url=urlparse(row["source_url"])
        need(url.scheme=="https" and url.hostname=="www.ufc.com" and url.path.startswith("/athlete/") and not url.username and not url.password,"Official athlete URL required")
        for src,dst in FIELDS.items():
            val=row[src];status=row[dst+"_status"]
            if val is None:
                need(status=="UNCONFIRMED","Missing field inconsistent");continue
            need(status=="OFFICIAL_PUBLISHED" and type(val) in (int,float) and math.isfinite(val) and 50<=val<=90,"Unapproved or invalid measurement")
            old=static.get(rb.norm_name(n),{}).get(dst+"_inches",np.nan)
            # Never replace an existing measured value silently.
            need(pd.isna(old) or float(old)==float(val),"Existing physical measurement conflict: "+n+" "+dst)
            if pd.isna(old):
                result.setdefault(n,{})[dst]=float(val)
                ledger.append({"regional_id":fid,"ufcstats_profile_id":row["ufcstats_profile_id"],"source_name":n,"field":dst,"old":None,"new":float(val),"source_url":row["source_url"],"observed_date":observation["observed_date"]})
    return result,ledger

def patch_static(static,overrides):
    out=deepcopy(static)
    for name,fields in overrides.items():
        k=rb.norm_name(name);need(k in out,"Unknown Reference profile")
        for f,v in fields.items():
            need(f in ("height","reach") and pd.isna(out[k].get(f+"_inches")),"Refuse nonmissing Reference overwrite")
            out[k][f+"_inches"]=v
    return out

def patch_query_frame(frame,overrides,event,day):
    need(len(frame)>0 and frame["event"].eq(event).all() and pd.to_datetime(frame["date"]).dt.date.eq(pd.Timestamp(day).date()).all(),"Refuse historical or mixed-date frame")
    out=frame.copy(deep=True)
    for name,fields in overrides.items():
        own=out.fighter.eq(name);opp=out.opponent.eq(name)
        need(own.sum()==opp.sum()==1,"Missing/duplicate query identity")
        for field,val in fields.items():
            need(field in ("height","reach"),"Only physical fields allowed")
            need(out.loc[own,field].isna().all() and out.loc[opp,"opp_"+field].isna().all(),"Refuse nonmissing Historical overwrite")
            out.loc[own,field]=val;out.loc[opp,"opp_"+field]=val
    for field in ("height","reach"):out[field+"_diff"]=out[field]-out["opp_"+field]
    # All other target and feature values must be identical.
    changed={"height","reach","opp_height","opp_reach","height_diff","reach_diff"}
    pd.testing.assert_frame_equal(frame.drop(columns=list(changed)),out.drop(columns=list(changed)))
    return out
