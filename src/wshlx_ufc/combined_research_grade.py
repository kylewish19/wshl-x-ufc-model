"""Score frozen combined research outputs; not a lock or betting decision.
External pre-event publication must be independently verified by the caller.
The pure scorer checks a supplied digest and timestamp, not their authenticity.
"""
from datetime import datetime,timezone
from collections import defaultdict
from math import isfinite,log
import hashlib,json
import numpy as np
from .finish_v1_research import score_six,aggregate
from .joint_coherence_shadow import JOINT_KEYS

CORE=("reference","historical","unified")
VARIANTS=("raw","winner_aligned","winner_and_timing_aligned")
CHALLENGERS=("legacy_updated_v3_identity_corrected","strict_updated_v3_identity_corrected","round86_identity_corrected","regional_v5_refreshed_identity_corrected")
NONDECISIVE={"DRAW","NC","DQ","CANCELLED","NONPERFORMANCE"}

def require(ok,msg):
    if not ok:raise ValueError(msg)
def stamp(s):
    d=datetime.fromisoformat(s.replace("Z","+00:00"))
    require(d.tzinfo is not None,"Timezone required")
    return d.astimezone(timezone.utc)
def prob(p):
    p=float(p);require(isfinite(p) and 0<=p<=1,"Invalid probability");return p
def distributions(row):
    require(set(row["models"])==set(CORE),"Missing core model")
    for name in CORE:
        v=row["models"][name];p=prob(v["winner_p_a"])
        require(set(v["coherence"])==set(VARIANTS),"Missing coherence variant")
        for variant in VARIANTS:
            yield name+":"+variant,p,v["coherence"][variant]
    ch=row["challengers"]
    require(set(CHALLENGERS[:3])<=set(ch)<=set(CHALLENGERS),"Missing or unregistered challenger")
    require((CHALLENGERS[-1] in ch)==(row["regional_status"]=="ELIGIBLE"),"Regional eligibility mismatch")
    for name,v in ch.items():yield name,prob(v["p_a"]),v["six_joint"]
def grade(lock_bytes,actual,evidence):
    lock=json.loads(lock_bytes)
    require(lock["schema"]=="WSHLX_REFRESHED_COMBINED_RESEARCH_V1" and lock["research_only"] is True and lock["odds_used"] is False and lock["bet_authorized"] is False,"Not an odds-blind research lock")
    digest=hashlib.sha256(lock_bytes).hexdigest()
    require(evidence["sha256"]==digest and evidence["externally_verified_by_caller"] is True and evidence["evidence_url"].startswith("https://"),"External lock proof required")
    first=stamp(lock["first_fight_utc"]);created=stamp(lock["generated_at_utc"]);published=stamp(evidence["published_at_utc"])
    require(created<=published<first,"Pre-event publication required")
    require(actual["event_date"]==lock["event_date"] and actual["event"]==lock["event"] and stamp(actual["verified_at_utc"])>=first and actual["results_verified_by_caller"] is True,"Verified post-event result register required")
    rows=lock["fights"];truth=actual["fights"]
    byno={r["fight_no"]:r for r in truth}
    require(len(byno)==len(truth)==len(rows) and set(byno)=={r["fight_no"] for r in rows} and len({r["fight_no"] for r in rows})==len(rows),"Incomplete or duplicate results")
    groups=defaultdict(dict);excluded=[];seen=set();eligible=set();timing=defaultdict(list)
    for r in rows:
        ids=[z["regional_id"] for z in r["identities"]]
        require(len(ids)==2 and len(set(ids))==2,"Invalid locked identities")
        key=tuple(sorted(ids));require(key not in seen,"Duplicate bout");seen.add(key)
        t=byno[r["fight_no"]]
        require(set(t["regional_ids"])==set(ids) and len(t["regional_ids"])==2,"Outcome identity mismatch")
        status=t["status"]
        views=list(distributions(r))
        # Validate all forecasts even for excluded bouts.
        for name,p,j in views:
            require(set(j)==set(JOINT_KEYS),"Incomplete six states")
            q=[prob(j[k]) for k in JOINT_KEYS]
            require(abs(sum(q)-1)<1e-8,"Invalid joint mass")
        if status in NONDECISIVE:
            excluded.append({"fight_no":r["fight_no"],"regional_ids":ids,"status":status});continue
        require(status=="DECISIVE" and t["winner_id"] in ids and t["method"] in ("KO_TKO","SUB","DEC"),"Invalid result label")
        eligible.add(key);side=ids.index(t["winner_id"])
        for name,p,j in views:
            q=[float(j[k]) for k in JOINT_KEYS]
            groups[name][key]=score_six(q,side,t["method"],p_a=p)
        # Direct GTD separate from joint method; only standard decisive labels
        # with explicit verified timing eligibility enter this score.
        if t.get("timing_eligible") is True:
            require(type(t.get("went_distance")) is bool,"Verified GTD truth required")
            y=int(t["went_distance"])
            for name in CORE:
                p=prob(r["models"][name]["timing_direct"]["GTD_YES"])
                timing[name].append({"gtd_brier":(p-y)**2,"gtd_log_loss":-log(max(1e-12,p if y else 1-p)),"gtd_correct":int((p>=.5)==bool(y))})
    metrics={n:aggregate(list(s.values())) for n,s in groups.items()}
    paired={}
    base=groups["reference:raw"]
    for name,s in groups.items():
        keys=sorted(set(base)&set(s))
        if not keys:continue
        paired[name]={"paired_fights":len(keys),"six_log_loss_delta":sum(s[k]["six_log_loss"]-base[k]["six_log_loss"] for k in keys)/len(keys),"six_brier_delta":sum(s[k]["six_brier"]-base[k]["six_brier"] for k in keys)/len(keys),"exact_hit_delta":sum(s[k]["exact"]-base[k]["exact"] for k in keys)}
    # Keep own-native comparison separate from Reference baseline.
    own={}
    for n in CORE:
        base=groups[n+":raw"]
        for v in VARIANTS[1:]:
            s=groups[n+":"+v];require(set(s)==set(base),"Unpaired core variants")
            if base:own[n+":"+v]={"paired_fights":len(base),"six_log_loss_delta":sum(s[k]["six_log_loss"]-base[k]["six_log_loss"] for k in base)/len(base),"six_brier_delta":sum(s[k]["six_brier"]-base[k]["six_brier"] for k in base)/len(base),"exact_hit_delta":sum(s[k]["exact"]-base[k]["exact"] for k in base)}
    return {"schema":"WSHLX_COMBINED_RESEARCH_EVENT_GRADE_V1","event":lock["event"],"event_date":lock["event_date"],"lock_sha256":digest,"publication_evidence":evidence,"external_evidence_authenticity_checked_by_caller_not_code":True,"unique_decisive_bouts":len(eligible),"decisive_bout_keys":[list(k) for k in sorted(eligible)],"per_bout_scores":{n:[{"regional_ids":list(k),**v} for k,v in sorted(s.items())] for n,s in groups.items()},"non_gradeable":excluded,"models":metrics,"paired_vs_reference_raw":paired,"paired_vs_own_raw":own,"timing_gtd":{n:{"n":len(s),**{k:sum(x[k] for x in s)/len(s) for k in s[0]}} for n,s in timing.items()},"prospective_promotion_authorized":False,"research_only":True}
