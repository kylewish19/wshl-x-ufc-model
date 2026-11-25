"""All-roster source-backed fighter dossier audit; no forecasts or tape claims."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json
import pandas as pd
import audit_worldwide_mma_history_v4 as a
from audit_ufc_identity_overlay import DB,SHA
from audit_riyadh_refreshed_source_coverage import DRAFT,IDS
from run_combined_refreshed_research import PROFILE_IDS
from run_refreshed_three_view_card import source,resolve,prepare
from audit_low_sample_history import class_method
from wshlx_ufc.historical_data import normalize_events,bout,txt
import rebuild_v027 as rb

CUTOFF="2026-11-25"
def main():
    assert hashlib.sha256(DB.read_bytes()).hexdigest()==SHA
    d=json.loads(DRAFT.read_text());assert d["lineup_verified_by_caller"] is False
    names=[f[s] for f in d["fights"] for s in ("a","b")]
    roster=[{"name":n,"regional_id":i,"ufcstats_profile_id":p} for n,i,p in zip(names,IDS,PROFILE_IDS,strict=True)]
    bouts=[{"a":roster[i],"b":roster[i+1]} for i in range(0,len(roster),2)]
    t=source();_,static,reference_history,coverage=prepare(t)
    dates={txt(x.event):str(x.date.date()) for x in normalize_events(t["events"]).itertuples(index=False) if pd.notna(x.date)}
    raw=defaultdict(list)
    for x in t["results"].to_dict("records"):
        pair=bout(x["BOUT"]);day=dates.get(txt(x["EVENT"]))
        if not pair or not day or day>=CUTOFF:continue
        for n in pair:raw[n].append({k:txt(x.get(k)) for k in ("EVENT","BOUT","OUTCOME","METHOD","URL")}|{"date":day})
    saved=a.DATE_CUTOFF;a.DATE_CUTOFF=CUTOFF
    con=a.get_tables(DB)
    try:
        pairs=resolve(t,bouts,con);identities=[z for p in pairs for z in p]
        assert len(identities)==28
        histories=a.history_for_ids(con,IDS)
        all_rows=defaultdict(list)
        for fid in IDS:
            query="""SELECT e.date AS day,e.promotion,f.fight_id,f.bout_type,f.method,p.result,
                   o.fighter_id AS opponent_id,op.name AS opponent
                   FROM fight_participants p JOIN fights f ON f.fight_id=p.fight_id
                   JOIN events e ON e.event_id=f.event_id
                   LEFT JOIN fight_participants o ON o.fight_id=f.fight_id AND o.fighter_id<>p.fighter_id
                   LEFT JOIN fighters op ON op.fighter_id=o.fighter_id
                   WHERE p.fighter_id=? AND e.date IS NOT NULL AND e.date<?
                   ORDER BY e.date,f.fight_id"""
            all_rows[fid]=[dict(x) for x in con.execute(query,(fid,CUTOFF))]
        opp_ids={x["opponent_id"] for rows in all_rows.values() for x in rows if x["opponent_id"] is not None}
        oh=a.history_for_ids(con,opp_ids)
        dossiers=[]
        for z in identities:
            fid=z["regional_id"];n=z["source_name"];rows=all_rows[fid]
            counts=Counter(x["fight_id"] for x in rows)
            kept={x["fight_id"] for x in histories[fid]}
            for x in rows:
                x["included_in_frozen_history"]=x["fight_id"] in kept
                x["method_class_audit"]=class_method(x["method"])
                known=x["opponent_id"] is not None and counts[x["fight_id"]]==1
                h=[r for r in oh.get(x["opponent_id"],[]) if r["date"]<x["day"] and r["result"] in ("W","L","D")]
                x["opponent_known_prior_record_at_meeting"]={k:sum(r["result"]==k for r in h) for k in ("W","L","D")} if known else None
            ref=reference_history.get(rb.norm_name(n),[])
            st=static.get(rb.norm_name(n),{})
            counts_by_result=Counter(r["result"] for r in histories[fid])
            by_org=Counter(r["promotion"] for r in histories[fid])
            recent=sorted(raw[n],key=lambda x:x["date"],reverse=True)
            dossiers.append({**z,"known_record":dict(counts_by_result),"promotions":dict(by_org),"regional_model_prior":a.prior(histories[fid],d["event_date"]),"reference_decisive_prior":len(ref),"reference_paired_stats_prior":sum(x["paired_stats_available"] for x in ref),"archived_results":recent,"all_worldwide_rows":rows,"ambiguous_fight_ids":[k for k,v in counts.items() if v!=1],"missing_opponent_joins":sum(x["opponent_id"] is None for x in rows),"archived_height_present":bool(pd.notna(st.get("height_inches"))),"archived_reach_present":bool(pd.notna(st.get("reach_inches"))),"tape_reviewed":False})
    finally:a.DATE_CUTOFF=saved;con.close()
    result={"schema":"WSHLX_RIYADH_ROSTER_DOSSIER_AUDIT_V1","event_date":d["event_date"],"worldwide_sha256":SHA,"cutoff_exclusive":CUTOFF,"roster_attested":False,"opponent_records_as_of_each_meeting":True,"source_coverage":coverage,"fighters":dossiers,"odds_used":False,"actual_predictions":0,"model_inputs_changed":False}
    Path("riyadh_roster_dossiers.json").write_text(json.dumps(result,indent=2,allow_nan=False))
    summary=[{k:x[k] for k in ("display_name","regional_id","known_record","promotions","reference_decisive_prior","reference_paired_stats_prior","ambiguous_fight_ids","missing_opponent_joins")} for x in dossiers]
    print("ROSTER_DOSSIER_AUDIT",json.dumps({"fighters":len(dossiers),"reference_coverage":coverage,"dossiers":summary,"actual_predictions":0}))
if __name__=="__main__":main()
