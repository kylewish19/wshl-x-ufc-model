"""Join independently evaluated core and challenger views, never create a vote.
CI uses rotated fictional matchups, no saved forecasts or live attestation.
Real mode uses the exact existing caller verification gate and source ID joins.
"""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import numpy as np
import audit_worldwide_mma_history_v4 as a
from audit_ufc_identity_overlay import DB,SHA,NAMES,mapping,overlay
from wshlx_ufc.postevent_history_extension_v1 import load_extended_records
from wshlx_ufc.models import fighter_double_chance
from wshlx_ufc.simulation import simulate_joint_outcomes
from run_refreshed_three_view_card import gate,require,prepare,resolve,evaluate,ROOT,CUTOFF,BASE_SEED,checked_load,REFERENCE,OFFSETS,HISTORICAL,source
from refreshed_identity_challenger_panel import panel

PROFILE_IDS=[
"1338e2c7480bdf9e","06734ca9d88dec3a","442c9011034ae1fd","f139d6836efd43dd",
"a69a7120cf26669d","e803242fb2e41112","e2f6b2769aaedd6c","39d309957c5c210d",
"480779d7f9a424d3","24cb8f04de1310cb","bc5a51159ec2fdf2","cd13728ae1151f46",
"b1de86d835638319","f2f140ce7532e327","294aa73dbf37d281","65adf3856c4d9256",
"02f484417a6fa69d",None,"9384e71bca6c409d","285ae0b4a68221f4",
"93f9c19ae41d2a97","2bbdbc925f4323ac","48e43b65f7838878","ec322adbabbfa6e7",
"0e6bc8d1d6c0ad90","ec3bd30378d63dd1","849c5d9979df5357","48a9a128784d53d1"]

def bridge(pairs,day,con):
    original,_=load_extended_records(as_of_exclusive=day)
    records,_=overlay(original,mapping())
    names={r[s] for r in records for s in ("a","b")}
    aliases=a.aliases(con)
    mapped=[];query_ids={};details=[];used=set()
    for pair in pairs:
        result=[];info=[]
        for z in pair:
            fid=z["regional_id"];n=z["source_name"]
            if fid in NAMES:
                require(n==NAMES[fid] and n in names,"Corrected same-name identity lost")
                name=n
            else:
                keys=aliases.get(fid,set())
                require(a.namekey(n) in keys,"Source alias conflict")
                choices={x for x in names if a.namekey(x) in keys}
                require(len(choices)<=1,"Multiple challenger history aliases require explicit reconciliation: "+n)
                name=next(iter(choices)) if choices else n
            require(name not in used,"Duplicate challenger source identity")
            used.add(name);query_ids[name]=fid;result.append(name)
            info.append({"core_source_name":n,"challenger_source_name":name,"regional_id":fid,"matching_challenger_prior_history":name in names})
        mapped.append(tuple(result));details.append(info)
    return mapped,query_ids,details

def attach(core,challenger,details):
    require(len(core)==len(challenger)==len(details),"Model output cardinality mismatch")
    for x,y,d in zip(core,challenger,details,strict=True):
        require(x["source_names"]==[z["core_source_name"] for z in d],"Core orientation mismatch")
        require(y["source_names"]==[z["challenger_source_name"] for z in d],"Challenger orientation mismatch")
        v={}
        for k,m in y["models"].items():
            j=m["six_joint"];require(np.isclose(sum(j.values()),1),"Challenger probability mass")
            require(np.isclose(sum(j["A_"+z] for z in ("KO","SUB","DEC")),m["p_a"]),"Challenger winner marginal")
            v[k]={**m,"double_chance":fighter_double_chance(j),
                "joint_simulation_10000":simulate_joint_outcomes(j,trials=10000,seed=BASE_SEED+x["fight_no"]),
                "timing_direct":None,"timing_status":"NOT_MODELED_BY_THIS_CHALLENGER"}
        x["challengers"]=v;x["challenger_identity_bridge"]=d
        x["regional_status"]="ELIGIBLE" if y["regional_eligible"] else "ABSTAIN_UNRESOLVED"
        x["bet_authorized"]=False
    return core

def main():
    ap=argparse.ArgumentParser()
    for n in ("reference","offsets","historical"):ap.add_argument("--"+n,type=Path,required=True)
    ap.add_argument("--lineup",type=Path);ap.add_argument("--output",type=Path);ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args();now=datetime.now(timezone.utc)
    if args.self_test:
        require(args.lineup is None and args.output is None,"Fixture cannot publish")
        from audit_riyadh_refreshed_source_coverage import DRAFT,IDS
        d=json.loads(DRAFT.read_text())
        try:gate(d,now)
        except ValueError:pass
        else:raise AssertionError("Draft passed actual gate")
        flat=[f[s] for f in d["fights"] for s in ("a","b")]
        roster=[{"name":n,"regional_id":i,"ufcstats_profile_id":p} for n,i,p in zip(flat,IDS,PROFILE_IDS,strict=True)]
        # All original pairings changed. Synthetic division fields exercise schemas only.
        bouts=[{"a":roster[2*i],"b":roster[2*((i+1)%14)+1],"scheduled_rounds":5 if i==0 else 3,"weight_class":"Middleweight Bout"} for i in range(14)]
        day="2026-12-05"
    else:
        require(args.lineup is not None and args.output is not None and not args.output.exists(),"Verified lineup and exclusive output required")
        raw=args.lineup.read_bytes();d=json.loads(raw);first=gate(d,now)
        bouts=d["fights"];day=d["event_date"]
    ref={**{n:checked_load(args.reference,n,s) for n,s in REFERENCE.items()},**{n:checked_load(args.offsets,n,s) for n,s in OFFSETS.items()}}
    hist={n:checked_load(args.historical,"historical_"+n,s) for n,s in HISTORICAL.items()}
    t=source();_,static,history,coverage=prepare(t)
    con=a.get_tables(DB)
    try:
        identities=resolve(t,bouts,con)
        cp,ids,details=bridge(identities,day,con)
    finally:con.close()
    rows=[{"names":tuple(z["source_name"] for z in pair),"rounds":f["scheduled_rounds"],"weight_class":f["weight_class"]} for f,pair in zip(bouts,identities,strict=True)]
    core=evaluate(t,rows,pd.Timestamp(day,tz="UTC"),static,history,ref,hist)
    ch,audit=panel(day,cp,ids)
    result=attach(core,ch,details)
    for row,pair in zip(result,identities,strict=True):row["identities"]=pair
    json.dumps(result,allow_nan=False)
    if args.self_test:
        print(json.dumps({"fictional_fights":len(result),"core_views":len(result)*3,"core_coherence_variants":len(result)*9,"challenger_outputs":sum(len(x["challengers"]) for x in result),"regional_eligible":sum(x["regional_status"]=="ELIGIBLE" for x in result),"missing_physical_profiles_retained":sum(not z["height_known"] or not z["reach_known"] for x in result for z in x["source_coverage"]),"draft_rejected":True,"actual_forecasts":0,"production_migrated":False}))
        return
    require(datetime.now(timezone.utc)<first,"Event already started")
    report={"schema":"WSHLX_REFRESHED_COMBINED_RESEARCH_V1","event":d["event"],"event_date":day,"first_fight_utc":first.isoformat(),"generated_at_utc":datetime.now(timezone.utc).isoformat(),"lineup_sha256":hashlib.sha256(raw).hexdigest(),"lineup_source_url":d["lineup_source_url"],"history_through":CUTOFF,"worldwide_source_sha256":SHA,"artifact_hashes":{"reference":REFERENCE,"offsets":OFFSETS,"historical":HISTORICAL},"source_coverage":coverage,"challenger_audit":audit,"research_only":True,"odds_used":False,"model_vote_created":False,"bet_authorized":False,"production_migrated":False,"fights":result}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x") as f:json.dump(report,f,indent=2,allow_nan=False)
if __name__=="__main__":main()
