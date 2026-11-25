"""Refreshed data comparison for existing Regional v5; research only."""
from pathlib import Path
import hashlib,json
import numpy as np
import audit_worldwide_mma_history_v4 as a
from benchmark_worldwide_mma_winner_v4 import features as encode
from benchmark_worldwide_method_v5 import train_methods,conditional
from run_future_updated_method_panel import regional_inputs
from run_future_updated_history_research import query
from wshlx_ufc.postevent_history_extension_v1 import load_extended_records
from wshlx_ufc.strict_history_inputs_v1 import matrices_from_records
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/".research_cache/fightcanon/new.db"
SHA="e7e0a53ff47d336ed961b228e31a1ef98c77129fa9104e82496637e69f3ade29"
CUTOFF="2026-11-25"
FLAGGED={"akbarabdullaev":138491,"ivangnizditskiy":121393,"mahammadaliosmanli":133556,"modestinorodrigues":146940}
def refreshed_inputs(features,queries,records,query_ids):
    if hashlib.sha256(DB.read_bytes()).hexdigest()!=SHA:raise ValueError("DB SHA mismatch")
    saved=a.DATE_CUTOFF
    con=a.get_tables(DB)
    try:
        a.DATE_CUTOFF="2026-11-08"
        source=a.load_source_pairs()
        for r in records:
            day=r["date"].isoformat()
            if "2026-11-08"<=day<CUTOFF:
                source.append({"date":day,"event":r["event"],"a":r["a"],"b":r["b"],"key":(day,*sorted(a.namekey(r[s]) for s in ("a","b")))})
        a.DATE_CUTOFF=CUTOFF
        aliases=a.aliases(con)
        index,_=a.source_matched_fights(con,aliases)
        ids,m,miss,amb,_=a.build_verified_map(source,index,aliases)
        assert (len(source),len(m),len(miss),len(amb))==(3096,3096,0,0)
        for k,v in query_ids.items():
            if k=="brunosilva":raise ValueError("Original UFC identity audit required")
            if v not in (ids.get(k),FLAGGED.get(k)) or k not in aliases.get(v,set()):raise ValueError("Unverified query ID")
        hist=a.history_for_ids(con,set(ids.values())|set(query_ids.values()))
        pairs={(r["date"],*sorted(a.namekey(r[s]) for s in ("a","b"))) for r in m}
        ext={}
        for f in features+queries:
            day=f["event_date"]
            if day<"2021-01-01":continue
            ka,kb=(a.namekey(f["fighter_"+s]) for s in ("a","b"))
            q=f["bout_id"].startswith("future_")
            lookup=query_ids if q else ids
            x,y=lookup.get(ka),lookup.get(kb)
            valid=x is not None and y is not None and x!=y and (q or (day,*sorted((ka,kb))) in pairs)
            ra,rb=(encode(a.prior(hist[z],day),verified=True) for z in (x,y)) if valid else (encode(None,verified=False),encode(None,verified=False))
            ext[f["bout_id"]]=(ra,rb,valid)
        return ext
    finally:
        a.DATE_CUTOFF=saved
        con.close()
def main():
    day="2026-12-05"
    records,_=load_extended_records(as_of_exclusive=day)
    f,l,_=matrices_from_records(records,day)
    labels={x["bout_id"]:x for x in l}
    rows=[(x,labels[x["bout_id"]]) for x in f if "2021-01-01"<=x["event_date"]<day and labels[x["bout_id"]]["result_status"]=="DECISIVE"]
    assert len(rows)==3039
    # Fictional matchup, not a live prediction.
    q,_=query(records,day,[("Akbar Abdullaev","Dan Hooker")])
    for x in q:x["event"]="__PREFIGHT_QUERY_NO_RESULTS__"
    from lock_ufcqatar_worldwide_winner_v4_research import historic_verified_id_map
    ids=historic_verified_id_map()
    new=refreshed_inputs(f,q,records,{"akbarabdullaev":138491,"danhooker":ids["danhooker"]})
    old,_=regional_inputs(f,q)
    assert new[q[0]["bout_id"]][2] and not old[q[0]["bout_id"]][2]
    _,nold=train_methods(rows,old,day)
    fit,nnew=train_methods(rows,new,day)
    assert nold==nnew==3039
    c=conditional(q[0],new,fit)["worldwide_MMA_multinomial54"]
    assert c.shape==(2,3) and np.allclose(c.sum(axis=1),1)
    from wshlx_ufc.finish_v1_research import coherent_six
    assert np.isclose(sum(coherent_six(.61,c)[:3]),.61)
    changed=sum(any(not np.array_equal(old[x["bout_id"]][i],new[x["bout_id"]][i]) for i in (0,1)) for x,_ in rows)
    result={"training_n_each":nnew,"changed_training_feature_rows":changed,"old_fixture_eligible":False,"new_fixture_eligible":True,"source_sha":SHA,"cutoff_exclusive":CUTOFF,"live_forecasts_generated":0,"production_changed":False}
    Path("regional_v5_refresh_integration.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=="__main__":main()
