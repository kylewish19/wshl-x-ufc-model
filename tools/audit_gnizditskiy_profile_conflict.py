"""Read-only diagnostic of the rejected supplemental profile crosswalk."""
from pathlib import Path
import json,hashlib
from audit_ufc_identity_overlay import DB,SHA
import audit_worldwide_mma_history_v4 as a
from wshlx_ufc.historical_data import load_source_files,txt,bout,normalize_events
from wshlx_ufc.prefight_finish_resistance import ARCHIVE
import pandas as pd

FID=121393
SID="057a241e4ba90c4d"
def main():
    assert hashlib.sha256(DB.read_bytes()).hexdigest()==SHA
    t=load_source_files(ARCHIVE)
    con=a.get_tables(DB)
    try:
        mapped=[dict(x) for x in con.execute("SELECT fighter_id,source,source_id,name FROM fighter_aliases WHERE fighter_id=? ORDER BY source,source_id",(FID,))]
        owners=[dict(x) for x in con.execute("SELECT fighter_id,source,source_id,name FROM fighter_aliases WHERE source='ufcstats' AND source_id=?",(SID,))]
        related={FID}|{x["fighter_id"] for x in owners}
        people=[dict(con.execute("SELECT fighter_id,name,dob,height_in,reach_in FROM fighters WHERE fighter_id=?",(i,)).fetchone()) for i in sorted(related)]
        keys=set().union(*(a.aliases(con).get(i,set()) for i in related))
        profiles=[{k:txt(v) for k,v in x.items()} for x in t["fighters"].to_dict("records") if txt(x["URL"]).rstrip("/").endswith("/"+SID) or a.namekey(x["FIGHTER"]) in keys]
        bouts=[{k:txt(x.get(k)) for k in ("EVENT","BOUT","OUTCOME","METHOD","URL")} for x in t["results"].to_dict("records") if any(a.namekey(n) in keys for n in (bout(x["BOUT"]) or ()))]
        prior=[dict(x) for x in con.execute("""SELECT e.date,e.promotion,f.fight_id,p.fighter_id,p.result,fa.source_id FROM fight_participants p JOIN fights f ON f.fight_id=p.fight_id JOIN events e ON e.event_id=f.event_id LEFT JOIN fight_aliases fa ON fa.fight_id=f.fight_id AND fa.source='ufcstats' WHERE p.fighter_id IN (%s) ORDER BY e.date""" % ",".join("?"*len(related)),tuple(sorted(related)))]
    finally:con.close()
    result={"target_id":FID,"archive_profile_id":SID,"database_target_aliases":mapped,"database_profile_owners":owners,"database_person_rows":people,"archive_matching_profiles":profiles,"archive_matching_bouts":bouts,"database_history":prior,"identity_promoted":False,"predictions_generated":0}
    print("PROFILE_CONFLICT_AUDIT",json.dumps(result))
    Path("gnizditskiy_profile_conflict_audit.json").write_text(json.dumps(result,indent=2))
if __name__=="__main__":main()
