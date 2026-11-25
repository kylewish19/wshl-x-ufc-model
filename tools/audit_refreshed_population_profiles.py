"""Compare exact training populations and extract provisional physical profile candidates.
No source edits, no model fitting, no live card predictions.
"""
from pathlib import Path
import json,tempfile
from collections import Counter
import pandas as pd
import rebuild_v027 as rb
from refit_reference_identity_corrected import source,FILES
from audit_riyadh_refreshed_source_coverage import DRAFT,IDS
from audit_ufc_identity_overlay import DB
import audit_worldwide_mma_history_v4 as a
from wshlx_ufc.historical_data import build_prefight_perspective_rows,normalize_events,bout,txt,outcome,method
def key(day,event,x,y):return (str(day)[:10],txt(event),*sorted([txt(x),txt(y)]))
def main():
    t=source()
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)
        for k,v in FILES.items():t[k].to_csv(p/v,index=False)
        rb.TRAINING_CUTOFF=pd.Timestamp("2026-11-22",tz="UTC")
        r,_,_=rb.load_fights(p)
    h=build_prefight_perspective_rows(t["events"],t["results"],t["stats"],t["fighters"])
    h=h[h.fight_method.isin(["KO_TKO","SUB","DEC"])]
    ri={key(x.event_date,x.event,x.fighter_a,x.fighter_b):{"winner":x.winner,"method":x.method} for x in r.itertuples(index=False)}
    hi={key(x.date,x.event,x.fighter,x.opponent):{"winner":x.fighter,"method":"KO" if x.fight_method=="KO_TKO" else x.fight_method} for x in h[h.win==1].itertuples(index=False)}
    assert len(ri)==len(r)==8831 and len(hi)==len(h)//2==8832
    dates={x.event:str(x.date.date()) for x in normalize_events(t["events"]).itertuples(index=False) if pd.notna(x.date)}
    raw={}
    for x in t["results"].to_dict("records"):
        pair=bout(x["BOUT"]);day=dates.get(txt(x["EVENT"]))
        if pair and day:
            k=key(day,x["EVENT"],*pair)
            raw.setdefault(k,[]).append({n:txt(x.get(n)) for n in ("OUTCOME","METHOD","ROUND","TIME","TIME FORMAT","URL")})
    diffs={}
    for label,keys in (("reference_only",ri.keys()-hi.keys()),("historical_only",hi.keys()-ri.keys())):
        diffs[label]=[{"key":k,"raw":raw.get(k,[]),"reference_known_nonperformance":bool(rb.is_known_nonperformance_bout(k[1],k[2]+" vs. "+k[3]) or rb.is_known_nonperformance_bout(k[1],k[3]+" vs. "+k[2]))} for k in sorted(keys)]
    mismatch=[{"key":k,"reference":ri[k],"historical":hi[k]} for k in sorted(ri.keys()&hi.keys()) if ri[k]!=hi[k]]
    d=json.loads(DRAFT.read_text())
    assert d["lineup_verified_by_caller"] is False
    listed=[f[s] for f in d["fights"] for s in ("a","b")]
    missing={"Yaroslav Amosov","Akbar Abdullaev","Magomed Tuchalov","Luke Riley","Ivan Gnizditskiy","Pavel Andrusca","Mahammadali Osmanli","Modestino Rodrigues","Abdul Hussein"}
    con=a.get_tables(DB)
    candidates=[]
    try:
        aliases=a.aliases(con)
        for n,fid in zip(listed,IDS,strict=True):
            if n not in missing:continue
            assert a.namekey(n) in aliases[fid]
            row=con.execute("SELECT name,dob,height_in,reach_in FROM fighters WHERE fighter_id=?",(fid,)).fetchone()
            assert row is not None
            name,dob,height,reach=row
            ids=[dict(z) for z in con.execute("SELECT source,source_id,name FROM fighter_aliases WHERE fighter_id=? AND source IN ('ufcstats','sherdog') ORDER BY source,source_id",(fid,))]
            candidates.append({"listed_name":n,"provisional_id":fid,"canonical_name":name,"height_in":height,"reach_in":reach,"dob":dob,"source_aliases":ids,"independent_field_verification":False,"approved_for_input":False})
    finally:con.close()
    assert len(candidates)==9
    result={"reference_count":len(ri),"historical_count":len(hi),"shared":len(ri.keys()&hi.keys()),"differences":diffs,"shared_label_mismatches":mismatch,"profile_candidates":candidates,"source_changed":False,"predictions_generated":0,"production_migrated":False}
    Path("refreshed_population_profile_audit.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=="__main__":main()
