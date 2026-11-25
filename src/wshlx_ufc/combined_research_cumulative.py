"""Aggregate event-graded, externally evidenced research forecasts.
Use event clusters, not individual prop or model outputs as independent trials.
No automatic promotion. Input evidence authenticity remains caller responsibility.
"""
from collections import defaultdict
import numpy as np
from .combined_research_grade import require,CORE,VARIANTS,CHALLENGERS
from .finish_v1_research import aggregate
PRIMARY="six_log_loss"
SECONDARY="six_brier"
MIN_FIGHTS=300
MIN_EVENTS_FOR_INTERVAL=10
BOOTSTRAP_REPS=10000
BOOTSTRAP_SEED=112526
REGISTERED=tuple(n+":"+v for n in CORE for v in VARIANTS)+CHALLENGERS

def comparison(events,model,base):
    # Each event contributes all paired fight deltas, preserving within-event dependence.
    clusters=[]
    for e in events:
        m=e["per_bout_scores"]
        left={tuple(x["regional_ids"]):x for x in m.get(model,[])}
        right={tuple(x["regional_ids"]):x for x in m.get(base,[])}
        common=sorted(left.keys()&right.keys())
        if common:
            clusters.append([len(common),*[sum(left[k][z]-right[k][z] for k in common) for z in (PRIMARY,SECONDARY,"exact")]])
    if not clusters:return None
    z=np.asarray(clusters,float);n=int(z[:,0].sum())
    d=z[:,1:].sum(axis=0)/n
    interval=None
    if len(z)>=MIN_EVENTS_FOR_INTERVAL:
        rng=np.random.default_rng(BOOTSTRAP_SEED)
        sampled=z[rng.integers(0,len(z),size=(BOOTSTRAP_REPS,len(z)))].sum(axis=1)
        v=sampled[:,1:]/sampled[:,0,None]
        interval={k:[float(q) for q in np.quantile(v[:,i],[.025,.975])] for i,k in enumerate((PRIMARY,SECONDARY,"exact"))}
    return {"paired_fights":n,"paired_events":len(z),"six_log_loss_delta":float(d[0]),"six_brier_delta":float(d[1]),"exact_accuracy_delta":float(d[2]),"event_cluster_percentile_95":interval,"interval_status":"EXPLORATORY" if interval else "INSUFFICIENT_EVENT_CLUSTERS"}

def summarize(grades,*,synthetic=False):
    kind="SYNTHETIC_CONTRACT_TEST" if synthetic else "PROSPECTIVE_RESEARCH"
    # One grade per calendar event and one unordered fighter pair per date.
    event_keys=set();digests=set();all_bouts=set();by=defaultdict(list)
    for e in grades:
        require(e["schema"]=="WSHLX_COMBINED_RESEARCH_EVENT_GRADE_V1" and e["research_only"] is True and e["prospective_promotion_authorized"] is False,"Wrong grade schema or authorization")
        require(e.get("run_kind")==kind,"Wrong run kind; fictional grades cannot enter prospective cohort")
        require(e["publication_evidence"]["externally_verified_by_caller"] is True and e["publication_evidence"]["sha256"]==e["lock_sha256"],"Unverified publication evidence")
        key=(e["event_date"],e["event"]);digest=e["lock_sha256"]
        require(key not in event_keys and digest not in digests,"Duplicate event grade or lock")
        event_keys.add(key);digests.add(digest)
        bouts={tuple(k) for k in e["decisive_bout_keys"]}
        require(len(bouts)==len(e["decisive_bout_keys"])==e["unique_decisive_bouts"],"Duplicate or inconsistent decisive counts")
        require(all(len(k)==2 and k[0]<k[1] for k in bouts),"Unordered or invalid bout keys")
        dates={(e["event_date"],*k) for k in bouts}
        require(not dates&all_bouts,"Repeated prospective fight")
        all_bouts|=dates
        s=e["per_bout_scores"]
        require(set(s)<=set(REGISTERED),"Unknown model")
        for m in REGISTERED:
            rows=s.get(m,[])
            ids={tuple(x["regional_ids"]) for x in rows}
            require(len(ids)==len(rows) and ids<=bouts,"Duplicate or unmatched score row")
            if m!=CHALLENGERS[-1]:require(ids==bouts,"Incomplete mandatory model coverage")
            by[m].extend(rows)
    ordered=sorted(grades,key=lambda x:(x["event_date"],x["event"]))
    metrics={m:aggregate(by[m]) for m in REGISTERED if by[m]}
    paired={m:v for m in REGISTERED if m!="reference:raw" and (v:=comparison(ordered,m,"reference:raw")) is not None}
    own={n+":"+v:x for n in CORE for v in VARIANTS[1:] if (x:=comparison(ordered,n+":"+v,n+":raw")) is not None}
    return {"schema":"WSHLX_COMBINED_RESEARCH_CUMULATIVE_V1","run_kind":kind,"unique_decisive_bouts":len(all_bouts),"graded_events":len(event_keys),"minimum_prospective_fights":MIN_FIGHTS,"minimum_fight_count_met":len(all_bouts)>=MIN_FIGHTS,"model_metrics":metrics,"paired_vs_reference_raw":paired,"paired_vs_own_raw":own,"minimum_events_for_exploratory_interval":MIN_EVENTS_FOR_INTERVAL,"bootstrap_reps":BOOTSTRAP_REPS,"prospective_promotion_authorized":False,"research_only":True,"notes":"Caller verifies external pre-event evidence; count threshold alone never authorizes promotion. Event-cluster intervals exploratory and not multiplicity-adjusted."}
