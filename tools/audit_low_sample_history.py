"""Read-only evidence reconciliation: four low-sample fighters and their opponents.
No model changes, tape claims, live forecasts, or post-cutoff opponent records.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json
import pandas as pd
import audit_worldwide_mma_history_v4 as a
from audit_ufc_identity_overlay import DB,SHA
from wshlx_ufc.historical_data import load_source_files,normalize_events,bout,txt
from wshlx_ufc.prefight_finish_resistance import ARCHIVE

CUTOFF="2026-11-25"
DAY="2026-12-05"
IDS={138491:"Akbar Abdullaev",127793:"Mairon Santos",121393:"Ivan Gnizditskiy",136337:"Uran Satybaldiev",133556:"Mahammadali Osmanli",140692:"Pavel Andrusca",146940:"Modestino Rodrigues",133359:"Matthieu Duclos"}
# Expectations taken from the previously recorded written source register.
EXPECT=[
(138491,"2026-09-15","Ednilson Santos","W","KO","DWCS"),
(146940,"2026-09-01","Brandon Holmes","W","KO","DWCS"),
(133556,"2026-09-26","Ilimbek Akylbek","L","DQ","UFC"),
(121393,"2026-03-28","Tursunbek Sodikov","W","KO_OR_SUB","REGIONAL")]
def class_method(s):
    t=str(s or "").lower()
    if "disqualification" in t or "dq" in t:return "DQ"
    return a.victory_class(t)
def main():
    assert hashlib.sha256(DB.read_bytes()).hexdigest()==SHA
    t=load_source_files(ARCHIVE)
    dates={txt(x.event):str(x.date.date()) for x in normalize_events(t["events"]).itertuples(index=False) if pd.notna(x.date)}
    saved=a.DATE_CUTOFF;a.DATE_CUTOFF=CUTOFF
    con=a.get_tables(DB)
    try:
        aliases=a.aliases(con)
        for i,n in IDS.items():assert a.namekey(n) in aliases[i],(i,n)
        histories=a.history_for_ids(con,IDS)
        all_rows=defaultdict(list)
        for fid in IDS:
            q="""SELECT p.fighter_id,e.date AS day,e.promotion,f.fight_id,f.bout_type,f.method,p.result,
                  o.fighter_id AS opponent_id,op.name AS opponent
                FROM fight_participants p JOIN fights f ON f.fight_id=p.fight_id
                JOIN events e ON e.event_id=f.event_id
                LEFT JOIN fight_participants o ON o.fight_id=f.fight_id AND o.fighter_id<>p.fighter_id
                LEFT JOIN fighters op ON op.fighter_id=o.fighter_id
                WHERE p.fighter_id=? AND e.date IS NOT NULL AND e.date<?
                ORDER BY e.date,f.fight_id"""
            for row in con.execute(q,(fid,CUTOFF)):all_rows[fid].append(dict(row))
        opponent_ids={x["opponent_id"] for rows in all_rows.values() for x in rows if x["opponent_id"] is not None}
        opponent_history=a.history_for_ids(con,opponent_ids)
        result=[]
        for fid,name in IDS.items():
            rows=all_rows[fid];kept={x["fight_id"] for x in histories[fid]}
            counts=Counter(x["fight_id"] for x in rows)
            # No silent acceptance of ambiguous or missing opponent joins.
            ambiguous=[k for k,v in counts.items() if v!=1]
            for x in rows:
                x["included_in_frozen_history"]=x["fight_id"] in kept
                x["method_class_audit"]=class_method(x["method"])
                prior=[r for r in opponent_history.get(x["opponent_id"],[]) if r["date"]<x["day"] and r["result"] in ("W","L","D")]
                x["opponent_known_prior_record_at_meeting"]={k:sum(r["result"]==k for r in prior) for k in ("W","L","D")} if x["opponent_id"] is not None and x["fight_id"] not in ambiguous else None
            raw=[]
            for x in t["results"].to_dict("records"):
                pair=bout(x["BOUT"]);day=dates.get(txt(x["EVENT"]))
                if not pair or not day or day>=CUTOFF:continue
                if any(a.namekey(z) in aliases[fid] for z in pair):
                    raw.append({k:txt(x.get(k)) for k in ("EVENT","BOUT","OUTCOME","METHOD","URL")}|{"date":day})
            result.append({"fighter":name,"regional_id":fid,"database_rows":rows,"archive_matching_results":raw,"frozen_prior_features":a.prior(histories[fid],DAY),"duplicate_opponent_join_fight_ids":ambiguous,"promotions":dict(Counter(x["promotion"] for x in rows)),"bout_types":dict(Counter(str(x["bout_type"]) for x in rows))})
        checks=[]
        for fid,day,op,expected_result,expected_method,promotion_kind in EXPECT:
            rr=all_rows[fid]
            hits=[x for x in rr if x["day"]==day and (a.namekey(op)==a.namekey(x["opponent"]) or a.namekey(op) in aliases.get(x["opponent_id"],set()))]
            expected_classes={"KO","SUB"} if expected_method=="KO_OR_SUB" else {expected_method}
            match=len(hits)==1 and str(hits[0]["result"]).upper()==expected_result and hits[0]["method_class_audit"] in expected_classes
            checks.append({"fighter":IDS[fid],"expected_date":day,"expected_opponent":op,"expected_result":expected_result,"expected_method":expected_method,"expected_promotion_kind":promotion_kind,"status":"MATCHED_RESULT_AND_METHOD" if match else "REVIEW_REQUIRED","matches":hits,"same_date_other_rows":[x for x in rr if x["day"]==day and x not in hits]})
    finally:a.DATE_CUTOFF=saved;con.close()
    out={"schema":"WSHLX_LOW_SAMPLE_HISTORY_RECONCILIATION_V1","source_sha256":SHA,"cutoff_exclusive":CUTOFF,"query_date":DAY,"fighters":result,"expected_evidence_checks":checks,"no_future_opponent_records":True,"opponent_record_scope":"Known source W/L/D strictly before historical meeting, not verified complete record or skill rating","training_or_source_changed":False,"actual_predictions":0}
    Path("low_sample_history_reconciliation.json").write_text(json.dumps(out,indent=2))
    summary=[{"name":x["fighter"],"id":x["regional_id"],"source_rows":len(x["database_rows"]),"archive_rows":len(x["archive_matching_results"]),"promotions":x["promotions"],"bout_types":x["bout_types"],"prior":x["frozen_prior_features"],"recent_five":x["database_rows"][-5:],"ambiguous":x["duplicate_opponent_join_fight_ids"]} for x in result]
    print("LOW_SAMPLE_RECONCILIATION",json.dumps({"checks":checks,"fighters":summary,"actual_predictions":0}))
if __name__=="__main__":main()
