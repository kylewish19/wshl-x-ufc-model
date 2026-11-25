"""Fictional rotated roster only: compare baseline vs verified physical inputs."""
from pathlib import Path
import argparse,hashlib,json
import pandas as pd
import numpy as np
import audit_worldwide_mma_history_v4 as a
from audit_ufc_identity_overlay import DB
from audit_riyadh_refreshed_source_coverage import DRAFT,IDS
from run_combined_refreshed_research import PROFILE_IDS
from run_refreshed_three_view_card import source,prepare,resolve,evaluate,checked_load,REFERENCE,OFFSETS,HISTORICAL,ROOT
from prospective_physical_overlay import build_overrides,patch_static
from wshlx_ufc.prefight_finish_resistance import ARCHIVE
from audit_identity_safe_csv import FILES
import rebuild_v027 as rb
def main():
    ap=argparse.ArgumentParser()
    for n in ("reference","offsets","historical"):ap.add_argument("--"+n,type=Path,required=True)
    args=ap.parse_args()
    ref={**{n:checked_load(args.reference,n,s) for n,s in REFERENCE.items()},**{n:checked_load(args.offsets,n,s) for n,s in OFFSETS.items()}}
    hist={n:checked_load(args.historical,"historical_"+n,s) for n,s in HISTORICAL.items()}
    source_hash={k:hashlib.sha256((ARCHIVE/v).read_bytes()).hexdigest() for k,v in FILES.items()}
    d=json.loads(DRAFT.read_text());day=d["event_date"];stamp=pd.Timestamp(day,tz="UTC")
    flat=[f[s] for f in d["fights"] for s in ("a","b")]
    roster=[{"name":n,"regional_id":i,"ufcstats_profile_id":p} for n,i,p in zip(flat,IDS,PROFILE_IDS,strict=True)]
    bouts=[{"a":roster[2*i],"b":roster[2*((i+1)%14)+1],"scheduled_rounds":5 if i==0 else 3,"weight_class":"Middleweight Bout"} for i in range(14)]
    t=source();_,static,history,coverage=prepare(t)
    original_tables={k:v.copy(deep=True) for k,v in t.items()}
    con=a.get_tables(DB)
    try:identities=resolve(t,bouts,con)
    finally:con.close()
    p=ROOT/"research/lineups/ufcriyadh_2026-12-05_physical_observed_2026-11-25.json"
    obs=json.loads(p.read_text());override,ledger=build_overrides(obs,identities,day,static)
    assert len(ledger)==12 and len(override)==7
    after=patch_static(static,override)
    for z in ledger:
        k=rb.norm_name(z["source_name"]);f=z["field"]+"_inches"
        assert pd.isna(static[k][f]) and after[k][f]==z["new"]
    rows=[{"names":tuple(z["source_name"] for z in pair),"rounds":f["scheduled_rounds"],"weight_class":f["weight_class"]} for f,pair in zip(bouts,identities,strict=True)]
    base=evaluate(t,rows,stamp,static,history,ref,hist)
    filled=evaluate(t,rows,stamp,static,history,ref,hist,physical_overrides=override)
    old=sum(not z["height_known"] or not z["reach_known"] for x in base for z in x["source_coverage"])
    new=sum(not z["height_known"] or not z["reach_known"] for x in filled for z in x["source_coverage"])
    assert (old,new)==(9,4)
    diffs={k:{"winner_max_abs_delta":0.,"six_joint_max_abs_delta":0.,"gtd_max_abs_delta":0.,"changed_fixtures":0} for k in ("reference","historical","unified")}
    for x,y in zip(base,filled,strict=True):
        assert x["source_names"]==y["source_names"]
        affected=any(n in override for n in x["source_names"])
        for k in diffs:
            u,v=x["models"][k],y["models"][k]
            delta=[abs(u["winner_p_a"]-v["winner_p_a"]),max(abs(u["joint_method"][j]-v["joint_method"][j]) for j in u["joint_method"]),abs(u["timing_direct"]["GTD_YES"]-v["timing_direct"]["GTD_YES"])]
            if not affected:assert u==v
            for label,z in zip(("winner_max_abs_delta","six_joint_max_abs_delta","gtd_max_abs_delta"),delta):diffs[k][label]=max(diffs[k][label],z)
            diffs[k]["changed_fixtures"]+=int(max(delta)>1e-12)
    for k in t:pd.testing.assert_frame_equal(t[k],original_tables[k])
    assert source_hash=={k:hashlib.sha256((ARCHIVE/v).read_bytes()).hexdigest() for k,v in FILES.items()}
    print("PHYSICAL_OVERLAY_AUDIT",json.dumps({"hypothetical_fights":14,"verified_fields_applied":len(ledger),"fighters_with_new_fields":len(override),"incomplete_before":old,"incomplete_after":new,"six_fields_unconfirmed":True,"unaffected_fixture_outputs_identical":True,"source_tables_unchanged":True,"archive_hashes_unchanged":True,"model_deltas_aggregate_only":diffs,"observation_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"actual_forecasts":0,"production_migrated":False}))
if __name__=="__main__":main()
