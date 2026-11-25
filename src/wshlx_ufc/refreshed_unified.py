"""Pure research-only Unified composition using unchanged October17 weights.

This module does not fit models, generate a live lock, or select wagers.
It compares independently supplied refreshed model views, preserving raw
method pooling alongside previously defined coherence projections.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from wshlx_ufc.unified_ensemble import binary_logit_pool,multiclass_log_pool,blend_hazards,markets_from_hazards
from wshlx_ufc.joint_coherence_shadow import JOINT_KEYS,project
ROOT=Path(__file__).resolve().parents[1]
WEIGHTS_PATH=ROOT/"data/unified/oof_global_unified_shadow.json"
WEIGHTS_BLOB="c22c068ace74d0ad9b5e09ecbe232556b76ba89f"
def pinned_weights():
    b=WEIGHTS_PATH.read_bytes()
    assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==WEIGHTS_BLOB
    x=json.loads(b)
    assert x["source_cutoff"]=="2026-10-17"
    w={k:float(x[k]["weight_current"]) for k in ("winner","method","timing")}
    assert w=={"winner":.3,"method":.375,"timing":.75}
    return w

def validate(view,scheduled):
    pa=float(view["winner_p_a"])
    j=view["joint_method"]
    h=np.asarray(view["hazards_30s"],float)
    if not np.isfinite(pa) or not 0<pa<1:raise ValueError("Invalid winner probability")
    if set(j)!=set(JOINT_KEYS) or any(not np.isfinite(v) or v<=0 for v in j.values()) or not np.isclose(sum(j.values()),1,atol=1e-8,rtol=0):
        raise ValueError("Invalid six-state distribution")
    if h.shape!=(scheduled//30,) or not np.isfinite(h).all() or not ((h>0)&(h<1)).all():
        raise ValueError("Incomplete or invalid 30-second hazard sequence")
    return pa,np.array([j[k] for k in JOINT_KEYS]),h

def package(pa,j,h,scheduled):
    q=dict(zip(JOINT_KEYS,map(float,j)))
    timing=markets_from_hazards(h,scheduled,bin_seconds=30)
    return {"winner_p_a":float(pa),"joint_method":q,"timing_direct":timing,
        "coherence":{"raw":q,"winner_aligned":project(q,winner_p_a=pa),
            "winner_and_timing_aligned":project(q,winner_p_a=pa,finish_p=timing["GTD_NO"])},
        "hazards_30s":list(map(float,h))}

def compose(reference,historical,*,scheduled_seconds):
    if scheduled_seconds not in (900,1500):raise ValueError("Unsupported scheduled duration")
    w=pinned_weights()
    p,q,h=validate(reference,scheduled_seconds)
    r,s,g=validate(historical,scheduled_seconds)
    pa=float(binary_logit_pool([p],[r],w["winner"])[0])
    joint=multiclass_log_pool(q.reshape(1,-1),s.reshape(1,-1),w["method"])[0]
    hazards=blend_hazards(h,g,w["timing"],current_bin_seconds=30,historical_bin_seconds=30,output_bin_seconds=30)
    return {"reference":package(p,q,h,scheduled_seconds),"historical":package(r,s,g,scheduled_seconds),
        "unified":package(pa,joint,hazards,scheduled_seconds),"weights_current":w,
        "weight_source_blob":WEIGHTS_BLOB,"weights_refitted":False,
        "research_only":True,"bet_authorized":False,"model_promoted":False}
