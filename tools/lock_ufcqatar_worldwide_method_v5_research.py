"""New November 21 research-only KO/SUB/DEC future shadow, zero winner flips.

Locks independently trained method-v5 conditional finishing forecasts on
the EXACT same pre-event winner probabilities already locked for Winner v3
on November 19. Method comparison changes ONLY the method probabilities:
old 38 UFC-only vs worldwide 54 and hierarchical worldwide 54.

All histories for both sides stop on 2026-11-07; no synthetic match outcomes,
no odds and no modification to 11/21 original Reference/Historical/Unified,
Coherent, Winner v3 or Winner v4 SHA-protected files. No bets.
"""
from __future__ import annotations
from datetime import date,datetime,timezone
from pathlib import Path
import hashlib,json
import numpy as np

from wshlx_ufc.historical_feature_matrix import RESISTANCE,QUALITY,load_matrix
from wshlx_ufc.prefight_finish_resistance import ARCHIVE,_load_records,build_from_records
from wshlx_ufc.prefight_opponent_quality import build_historical_opponent_quality
from wshlx_ufc.finish_v1_research import method_features,coherent_six,METHODS
from benchmark_worldwide_method_v5 import train_methods,conditional
from benchmark_worldwide_mma_winner_v4 import load_external,features as region_features,REGIONAL_SOURCE_SHA
from audit_worldwide_mma_history_v4 import get_tables,history_for_ids,prior,DB
from lock_ufcqatar_winner_v3_research import align_to_source

ROOT=Path(__file__).resolve().parents[1]
DATE="2026-11-21"
START=datetime.fromisoformat("2026-11-21T15:00:00+00:00")
DIR=ROOT/"data/shadow_locks/ufcqatar_2026-11-21"
STAGEA=ROOT/"data/locks/ufcqatar_2026-11-21/stage_a_final_selection.json"
COHERENT=DIR/"coherent_joint_pre_event_shadow.json"
V3=DIR/"winner_v3_prospective_shadow.json"
V4=DIR/"worldwide_winner_v4_prospective_shadow.json"
DEST=DIR/"worldwide_method_v5_prospective_shadow.json"
SIX=("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")
HEADS=("prior_UFC_only_multinomial38","worldwide_MMA_multinomial54","worldwide_MMA_hierarchical54")
PRIMARY="worldwide_MMA_multinomial54"

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    now=datetime.now(timezone.utc)
    if now>=START:raise RuntimeError("Cannot assign a future-only method lock after first fight")
    if DEST.exists():raise FileExistsError("Method v5 research shadow already exists, never overwrite")
    sources=(STAGEA,COHERENT,V3,V4)
    if any(not x.exists() for x in sources):raise FileNotFoundError("All prior original locks must exist and remain frozen")
    if sha(DB)!=REGIONAL_SOURCE_SHA:raise ValueError("Third party professional source must be same pinned SHA as v4")

    origin=json.loads(STAGEA.read_text())
    v3=json.loads(V3.read_text());v4=json.loads(V4.read_text())
    if (not origin["stage_a_frozen"] or origin["odds_used"] or
        v3["original_stage_a_sha256"]!=sha(STAGEA) or
        v4["original_stage_a_sha256"]!=sha(STAGEA) or
        v3["original_coherent_shadow_sha256"]!=sha(COHERENT) or
        v4["original_coherent_shadow_sha256"]!=sha(COHERENT) or
        v4["original_independent_v3_shadow_sha256"]!=sha(V3)):
        raise ValueError("Stored independent source locks have been changed")
    if len(origin["fights"])!=len(v3["fights"])!=len(v4["fights"]):
        raise ValueError("Research and original cohort sizes disagree")
    if len(origin["fights"])!=12:raise ValueError("Twelve original full-card fights required")
    if v4["external_source_SHA256"]!=REGIONAL_SOURCE_SHA:
        raise ValueError("V4 regional history source vintage mismatch")

    feats,labels,ufcmanifest=load_matrix()
    regional,regionaudit=load_external(feats)
    byid={x["bout_id"]:x for x in labels}
    eligible=[(f,byid[f["bout_id"]]) for f in feats if
              "2021-01-01"<=f["event_date"]<DATE and
              byid[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(eligible)!=3015:raise ValueError("Historic training fight labels changed")
    methods,ntrain=train_methods(eligible,regional,DATE)

    archive=_load_records(ARCHIVE,date.fromisoformat(DATE))
    if len(archive)!=8871:raise ValueError("Pinned UFC source altered unexpectedly")
    names=[z for fight in origin["fights"] for z in (fight["a"],fight["b"])]
    mapped,aliases=align_to_source(names,archive)
    pairs=[tuple(mapped[2*i:2*i+2]) for i in range(12)]
    past,_=build_from_records(archive,as_of_exclusive=DATE,query_bouts=pairs)
    resistance=[p for p in past if p.get("query_only")]
    history=[{"date":r["date"].isoformat(),"event":r["event"],
              "a":r["a"],"b":r["b"],"outcome":"/".join(r["result"])} for r in archive]
    ratings=build_historical_opponent_quality(history,query_date=DATE,query_bouts=pairs)
    qualities=[p for p in ratings if p.get("query_only")]
    if len(resistance)!=12 or len(qualities)!=12:raise ValueError("Missing up-to-date source fighter features")

    ids=[]
    for item in v4["fights"]:
        ids.extend((item["external_source_fighter_ids"]["a"],
                    item["external_source_fighter_ids"]["b"]))
    conn=get_tables(DB)
    region_history=history_for_ids(conn,[i for i in ids if i is not None])
    results=[]
    for i,(original,pair) in enumerate(zip(origin["fights"],pairs),1):
        a,b=pair
        oldv3=v3["fights"][i-1]
        oldv4=v4["fights"][i-1]
        if (oldv3["a"],oldv3["b"])!=(original["a"],original["b"]) or (
                oldv4["a"],oldv4["b"])!=(original["a"],original["b"]):
            raise ValueError("Original fighter ordering changed")
        p=float(oldv3["research_models"]["logit_recent_57"]["p_a"])
        p_other=float(oldv4["research_variants"]["winner_v3_logit57"]["p_a_win"])
        if abs(p-p_other)>1e-8:
            raise ValueError("Cannot score changed v3 winner probabilities, true method-only pair required")
        r=resistance[i-1];q=qualities[i-1]
        if (r["a"],r["b"])!=pair or (q["a"],q["b"])!=pair:
            raise ValueError("UFC time-safe history source fighter identities differ")
        fid=f"WSHLX_QATAR_WORLD_METHOD_V5_{i:02d}"
        f={"bout_id":fid,"event_date":DATE,
           "feature_as_of_exclusive":DATE,"event":"UFC Fight Night: Prochazka vs Stirling",
           "fighter_a":a,"fighter_b":b}
        for fields,x,y in ((RESISTANCE,r["a_pre"],r["b_pre"]),
                            (QUALITY,q["a_pre"],q["b_pre"])):
            for key in fields:
                if key not in x or key not in y:
                    raise ValueError("Incomplete historical as-of method feature "+key)
                f["a_"+key]=x[key];f["b_"+key]=y[key]
        if any(f[side+"_prior_ufc_bouts"]!=f[side+"_ufc_prior_bouts"] for side in ("a","b")):
            raise ValueError("Two independent UFC histories disagree")
        ida,idb=ids[2*(i-1):2*i]
        for side,k in (("a",ida),("b",idb)):
            if k is None and f[side+"_prior_ufc_bouts"]>0:
                raise ValueError("Established UFC fighter with no previously verified regional identity")
        rega=region_features(prior(region_history[ida],DATE),verified=True) if ida is not None else region_features(None,verified=False)
        regb=region_features(prior(region_history[idb],DATE),verified=True) if idb is not None else region_features(None,verified=False)
        regional[fid]=(rega,regb,ida is not None and idb is not None)
        probabilities=conditional(f,regional,methods)
        methodvariants={}
        for head,c in probabilities.items():
            q6=coherent_six(p,c)
            side=0 if p>=.5 else 1
            n=int(np.argmax(q6[3*side:3*side+3]))
            methodvariants[head]={
                "winner":original["a"] if side==0 else original["b"],
                "method":METHODS[n],
                "p_a_from_original_frozen_v3":p,
                "p_exact_fighter_method":float(q6[3*side+n]),
                "six_joint":{key:float(q6[k]) for k,key in enumerate(SIX)},
                "method_model_only_changed_from_baseline":head!=HEADS[0],
                "not_official_betting_pick":True,
            }
        sparse=min(f["a_prior_ufc_bouts"],f["b_prior_ufc_bouts"])<5
        results.append({
            "fight_no":i,"a":original["a"],"b":original["b"],
            "original_reference_betting_posture_UNCHANGED":original["stage_a_posture"],
            "original_frozen_v3_winner_probability_a":p,
            "source_fighter_identity_verified_both":ida is not None and idb is not None,
            "sample_quality":"UNVERIFIED_NONUFC_IDENTITY_PASS" if ida is None or idb is None else
                "SPARSE_UFC_SAMPLE" if sparse else "NORMAL_RESEARCH",
            "reported_provisional_addition":bool(i==12),
            "no_method_bets_approved":True,
            "method_model_variants":methodvariants,
        })
    if not results[-1]["reported_provisional_addition"] or results[-1]["original_reference_betting_posture_UNCHANGED"]!="PASS":
        raise ValueError("The late novice bout must remain PASS without a bet")
    result={
        "schema":"WSHLX_QATAR_WORLD_MMA_INDEPENDENT_METHOD_V5_PROSPECTIVE",
        "locked_at_utc":now.isoformat(),
        "first_bout_at_utc":START.isoformat(),
        "event_date":DATE,
        "original_stage_a_sha256":sha(STAGEA),
        "original_coherent_sha256":sha(COHERENT),
        "independent_v3_sha256":sha(V3),
        "independent_v4_sha256":sha(V4),
        "historic_ufc_stats_source_sha256":ufcmanifest["source_stats_sha256"],
        "regional_histories_through_2026_11_07_only":True,
        "regional_source_release":"db-2026-11-19-1934",
        "regional_source_SHA256":REGIONAL_SOURCE_SHA,
        "train_method_n_decisive_bouts":ntrain,
        "primary_registered_method_model":PRIMARY,
        "winner_head_fixed_to_independent_v3_prospectively_frozen":True,
        "new_model_modifies_ONLY_method_given_winner":True,
        "all_12_test_prospectively_no_results_used":True,
        "original_reference_historical_unified_coherent_v3_v4_UNTOUCHED":True,
        "no_FanDuel_prices_or_approved_wagers":True,
        "all_candidates_research_only":True,
        "n_fights":len(results),
        "source_cross_promotion_audit":regionaudit,
        "research_predictions":results,
    }
    DEST.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
       "status":"INDEPENDENT_METHOD_V5_PRE_EVENT_SHADOW_LOCKED_RESEARCH_ONLY",
       "locked":now.isoformat(),"primary":PRIMARY,
       "fights":[{"n":r["fight_no"],"a":r["a"],"b":r["b"],
                 "winner":r["method_model_variants"][PRIMARY]["winner"],
                 "method":r["method_model_variants"][PRIMARY]["method"],
                 "p_exact":round(r["method_model_variants"][PRIMARY]["p_exact_fighter_method"],4),
                 "quality":r["sample_quality"]} for r in results],
    },sort_keys=True))

if __name__=="__main__":main()
