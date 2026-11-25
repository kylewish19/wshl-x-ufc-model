"""Draft roster source coverage audit, never a live lineup attestation."""
from pathlib import Path
import json,tempfile
from collections import defaultdict
import pandas as pd
import rebuild_v027 as rb
import audit_worldwide_mma_history_v4 as a
from audit_ufc_identity_overlay import DB,NAMES
from refit_reference_identity_corrected import source,rebuild,FILES
from wshlx_ufc.historical_data import col,txt,normalize_fighters
ROOT=Path(__file__).resolve().parents[1]
DRAFT=ROOT/"research/lineups/ufcriyadh_2026-12-05_draft_2026-11-24.json"
# Previously reviewed provisional regional crosswalk; never auto-promote.
IDS=[64102,117117,126956,66342,101614,132393,87879,144863,127793,138491,166491,64455,144783,87596,55096,67025,136337,121393,112513,81159,140692,133556,146940,133359,107541,136096,83722,102396]
def main():
    d=json.loads(DRAFT.read_text())
    assert d["lineup_verified_by_caller"] is False
    listed=[f[s] for f in d["fights"] for s in ("a","b")]
    assert len(listed)==len(IDS)==28 and len(set(IDS))==28
    tables=source()
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)
        for k,v in FILES.items():tables[k].to_csv(p/v,index=False)
        rb.TRAINING_CUTOFF=pd.Timestamp("2026-11-22",tz="UTC")
        fights,stats,static=rb.load_fights(p)
    _,history,coverage=rebuild(fights,rb.aggregate_fight_stats(fights,stats),static)
    raw=tables["fighters"];namecol,urlcol=col(raw,"FIGHTER"),col(raw,"URL")
    profiles=defaultdict(set)
    for row in raw.to_dict("records"):
        sid=txt(row[urlcol]).rstrip("/").split("/")[-1]
        if sid:profiles[sid].add(txt(row[namecol]))
    con=a.get_tables(DB)
    rows=[]
    try:
        aliases=a.aliases(con)
        for name,fid in zip(listed,IDS,strict=True):
            assert a.namekey(name) in aliases[fid]
            ids={r[0] for r in con.execute("SELECT source_id FROM fighter_aliases WHERE fighter_id=? AND source='ufcstats'",(fid,))}
            prof=sorted({n for sid in ids for n in profiles[sid]})
            key=rb.norm_name(prof[0]) if len(prof)==1 else None
            if fid==55096:assert prof==[NAMES[fid]]
            h=history.get(key,[]) if key else []
            st=static.get(key,{}) if key else {}
            candidates=sorted(k for k in history if k==rb.norm_name(name))
            rows.append({"listed_name":name,"provisional_regional_id":fid,"ufcstats_profile_ids":sorted(ids),
                "profile_id_matched_source_names":prof,"unverified_normalized_history_candidates":candidates,
                "reference_decisive_prior_if_profile_matched":len(h) if key else None,
                "reference_paired_stats_prior_if_profile_matched":sum(x["paired_stats_available"] for x in h) if key else None,
                "height_present":bool(pd.notna(st.get("height_inches"))) if key else False,
                "reach_present":bool(pd.notna(st.get("reach_inches"))) if key else False,
                "dob_present":bool(pd.notna(st.get("dob"))) if key else False,
                "live_identity_attested":False})
    finally:con.close()
    result={"event_date":d["event_date"],"listed_fights":len(d["fights"]),"fighters":rows,
        "matched_unique_raw_profile_by_id":sum(len(x["profile_id_matched_source_names"])==1 for x in rows),
        "no_unique_raw_profile":sum(len(x["profile_id_matched_source_names"])!=1 for x in rows),
        "matched_with_prior_reference_bouts":sum((x["reference_decisive_prior_if_profile_matched"] or 0)>0 for x in rows),
        "lineup_verified":False,"predictions_generated":0,"production_migrated":False}
    Path("riyadh_refreshed_source_coverage.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=="__main__":main()
