"""Compare pinned regional DB vintages, no forecasts or production changes."""
from pathlib import Path
import hashlib,json
import audit_worldwide_mma_history_v4 as a
from wshlx_ufc.postevent_history_extension_v1 import load_extended_records
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/".research_cache/fightcanon"
PINS=[("old.db","8185a2163b5f97071dbc4ec68667cceb43f5e321fadc38c26b5069303af4d949","2026-11-08"),("new.db","e7e0a53ff47d336ed961b228e31a1ef98c77129fa9104e82496637e69f3ade29","2026-11-25")]
COMMON="2026-11-08"
def inspect(pin,rows,extra,names):
    filename,sha,cutoff=pin
    path=CACHE/filename
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
    con=a.get_tables(path)
    saved=a.DATE_CUTOFF
    try:
        assert [r[0] for r in con.execute("PRAGMA quick_check")]==["ok"]
        alias=a.aliases(con)
        a.DATE_CUTOFF=COMMON
        idx,_=a.source_matched_fights(con,alias)
        ids,m,miss,amb,_=a.build_verified_map(rows,idx,alias)
        a.DATE_CUTOFF=cutoff
        idx,_=a.source_matched_fights(con,alias)
        ext,matched,missing,ambiguous,_=a.build_verified_map(rows+extra,idx,alias)
        histories=a.history_for_ids(con,set(ids.values())|set(ext.values()))
        common={k:a.prior(histories[v],COMMON) for k,v in ids.items()}
        draft=[]
        for name in names:
            k=a.namekey(name)
            fid=ext.get(k) if k!="brunosilva" else None
            draft.append({"name":name,"alias_candidates":sorted(i for i,keys in alias.items() if k in keys),"dated_crosswalk_candidate":fid,"prior_counts_if_identity_correct":a.prior(histories[fid],cutoff) if fid is not None else None,"identity_verified":False})
        latest=con.execute("SELECT MAX(e.date) FROM events e JOIN fights f ON f.event_id=e.event_id JOIN fight_participants p ON p.fight_id=f.fight_id WHERE e.date < ? AND UPPER(p.result) IN ('W','L','D') AND LOWER(COALESCE(f.bout_type,'')) NOT IN ('amateur','exhibition')",(cutoff,)).fetchone()[0]
        return {"sha":sha,"cutoff_exclusive":cutoff,"latest_recorded_result_date":latest,"common_matched":len(m),"common_missing":len(miss),"common_ambiguous":len(amb),"common_vetted_names":len(ids),"extended_matched":len(matched),"extended_missing":len(missing),"extended_ambiguous":len(ambiguous),"nov14_21_matched":sum(x["date"]>=COMMON for x in matched),"draft":draft},common,ids
    finally:
        a.DATE_CUTOFF=saved
        con.close()
def main():
    rows=a.load_source_pairs()
    rec,_=load_extended_records(as_of_exclusive="2026-11-25")
    extra=[]
    for r in rec:
        day=r["date"].isoformat()
        if COMMON<=day<"2026-11-25":
            extra.append({"date":day,"event":r["event"],"a":r["a"],"b":r["b"],"key":(day,*sorted(a.namekey(r[s]) for s in ("a","b")))})
    assert len(extra)==25
    d=json.loads((ROOT/"research/lineups/ufcriyadh_2026-12-05_draft_2026-11-24.json").read_text())
    assert not d["lineup_verified_by_caller"]
    names=[f[s] for f in d["fights"] for s in ("a","b")]
    old,x,ix=inspect(PINS[0],rows,extra,names)
    new,y,iy=inspect(PINS[1],rows,extra,names)
    shared=sorted(x.keys()&y.keys())
    changed=[k for k in shared if x[k]!=y[k]]
    result={"old":old,"new":new,"common_source_pairs":len(rows),"extra_source_pairs":len(extra),"shared_crosswalk_names":len(shared),"changed_prior_features":len(changed),"changed_examples":[{"name":k,"old":x[k],"new":y[k]} for k in changed[:20]],"changed_source_ids":sum(ix[k]!=iy[k] for k in shared),"gained_names":sorted(y.keys()-x.keys()),"lost_names":sorted(x.keys()-y.keys()),"limitations":"Retrospective backfills possible; date cutoff is not vintage proof. Alias candidates are not verified identities. Unknown bout types may be present. Coverage date is not completeness.","predictions_generated":0,"model_promotion":False}
    out=ROOT/"reports/model_health/2026-11-25_worldwide_refresh"
    out.mkdir(parents=True,exist_ok=True)
    (out/"refresh_audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("changed_examples",)}))
if __name__=="__main__":main()
