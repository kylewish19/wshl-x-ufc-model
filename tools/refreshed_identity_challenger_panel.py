"""Research-only challenger panel on corrected identities and refreshed data.
Existing v3/strict v3/round86/regional v5 architectures, no promotion.
"""
import json,tempfile,hashlib
from pathlib import Path
import numpy as np
import audit_worldwide_mma_history_v4 as a
from audit_ufc_identity_overlay import mapping,overlay,NAMES,DB,SHA,canonical
from audit_identity_safe_csv import corrected_tables,FILES
from wshlx_ufc.prefight_finish_resistance import ARCHIVE
from wshlx_ufc.historical_data import load_source_files
from wshlx_ufc.postevent_history_extension_v1 import load_extended_records
from wshlx_ufc.strict_history_inputs_v1 import matrices_from_records,strict_records
from wshlx_ufc.finish_conversion_v9 import build_conversion
from wshlx_ufc.round_method_v10 import read_rounds,build_round_history
from wshlx_ufc.finish_v1_research import coherent_six
from run_future_updated_history_research import query
from run_future_updated_method_panel import fit_round,method_vector,cond,project,QUERY
from benchmark_strict_history_v1 import train,predict
from benchmark_worldwide_mma_winner_v4 import features as encode
from benchmark_worldwide_method_v5 import train_methods,conditional
from lock_ufcqatar_worldwide_winner_v4_research import historic_verified_id_map
from regional_v5_refreshed_inputs import FLAGGED
CUTOFF="2026-11-25"

def regional(features,queries,original,query_ids):
    if hashlib.sha256(DB.read_bytes()).hexdigest()!=SHA:raise ValueError("DB SHA mismatch")
    saved=a.DATE_CUTOFF;con=a.get_tables(DB)
    try:
        a.DATE_CUTOFF="2026-11-08"
        source=a.load_source_pairs()
        for r in original:
            day=r["date"].isoformat()
            if "2026-11-08"<=day<CUTOFF:
                source.append({"date":day,"event":r["event"],"a":r["a"],"b":r["b"],"key":(day,*sorted(a.namekey(r[s]) for s in ("a","b")))})
        a.DATE_CUTOFF=CUTOFF
        aliases=a.aliases(con);idx,_=a.source_matched_fights(con,aliases)
        ids,m,miss,amb,_=a.build_verified_map(source,idx,aliases)
        assert (len(source),len(m),len(miss),len(amb))==(3096,3096,0,0)
        # Dated exact pair supplies orientation. Same-name rows never share a regional ID.
        dated={}
        for r in m:
            day=r["date"];pair={a.namekey(r[s]):r[s+"_id"] for s in ("a","b")}
            k=(day,*sorted(pair))
            if k in dated:raise ValueError("Duplicate source matchup")
            dated[k]=pair
        for name,fid in query_ids.items():
            if name in NAMES.values():
                if NAMES.get(fid)!=name:raise ValueError("Wrong Bruno Silva identity")
            elif fid not in (ids.get(a.namekey(name)),FLAGGED.get(a.namekey(name))) or a.namekey(name) not in aliases.get(fid,set()):
                raise ValueError("Unverified query regional identity")
        hist=a.history_for_ids(con,set(ids.values())|set(NAMES)|set(query_ids.values()))
        ext={};valid_queries=0;valid_training=0
        for f in features+queries:
            day=f["event_date"]
            if day<"2021-01-01":continue
            na,nb=(f["fighter_"+s] for s in ("a","b"))
            ka,kb=map(lambda n:a.namekey(canonical(n)),(na,nb))
            q=f["bout_id"].startswith("future_")
            if q:
                x,y=query_ids.get(na),query_ids.get(nb)
            else:
                pair=dated.get((day,*sorted((ka,kb))),{})
                # Retain prior globally vetted IDs except the explicitly repaired identity.
                x,y=(pair.get(k) if n in NAMES.values() else ids.get(k) for n,k in ((na,ka),(nb,kb)))
                if not pair or pair.get(ka)!=x or pair.get(kb)!=y:x=y=None
                for n,i in ((na,x),(nb,y)):
                    if n in NAMES.values() and i is not None and NAMES.get(i)!=n:raise ValueError("Dated Bruno crosswalk conflict")
            valid=x is not None and y is not None and x!=y
            v,w=(encode(a.prior(hist[z],day),verified=True) for z in (x,y)) if valid else (encode(None,verified=False),encode(None,verified=False))
            ext[f["bout_id"]]=(v,w,valid)
            if q:valid_queries+=int(valid)
            else:valid_training+=int(valid)
        return ext,{"matched_source_pairs":len(m),"eligible_query_bouts":valid_queries,"eligible_historical_rows":valid_training,"cutoff_exclusive":CUTOFF,"source_sha":SHA}
    finally:
        a.DATE_CUTOFF=saved;con.close()

def panel(day,pairs,query_ids):
    original,audit=load_extended_records(as_of_exclusive=day)
    matches=mapping();records,_=overlay(original,matches)
    strict,qa=strict_records(records)
    f,l,forms=matrices_from_records(records,day)
    ff,qforms=query(records,day,pairs)
    sf,sl,sforms=matrices_from_records(strict,day)
    sq,sqforms=query(strict,day,pairs)
    fits=[train(*m,day) for m in ((f,l,forms),(sf,sl,sforms))]
    assert all(x[2]==3039 for x in fits)
    for x in ff:x["event"]=QUERY
    labels={x["bout_id"]:x for x in l}
    rows=[(x,labels[x["bout_id"]]) for x in f if "2021-01-01"<=x["event_date"]<day and labels[x["bout_id"]]["result_status"]=="DECISIVE"]
    assert len(rows)==3039
    # Re-key both records and round statistics from the same verified map.
    t,_=corrected_tables(load_source_files(ARCHIVE),matches)
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp);t["stats"].to_csv(p/FILES["stats"],index=False)
        raw,ra=read_rounds(p)
    assert ra=={"parsed_round_fighter_rows":42310,"duplicate_rows_excluded":2}
    rounds,roundaudit=build_round_history(records,raw,query_date=day,query_bouts=pairs)
    conv=build_conversion(records,query_date=day,query_bouts=pairs)
    rm,rt=fit_round(rows,conv,rounds)
    ext,regaudit=regional(f,ff,original,query_ids)
    reg,n=train_methods(rows,ext,day);assert n==3039
    out=[]
    for x,y,(aa,bb) in zip(ff,sq,pairs,strict=True):
        p,c=predict(x,qforms,fits[0]);ps,cs=predict(y,sqforms,fits[1])
        rc=cond(rm,np.vstack([method_vector(x,s,conv,rounds) for s in ("a","b")]))
        models={"legacy_updated_v3_identity_corrected":project(p,c,aa,bb),"strict_updated_v3_identity_corrected":project(ps,cs,aa,bb),"round86_identity_corrected":project(p,rc,aa,bb)}
        if ext[x["bout_id"]][2]:
            cc=conditional(x,ext,reg)["worldwide_MMA_multinomial54"]
            models["regional_v5_refreshed_identity_corrected"]=project(p,cc,aa,bb)
        for k,v in models.items():
            assert np.isclose(sum(v["six_joint"].values()),1)
            assert np.isclose(sum(v["six_joint"]["A_"+m] for m in ("KO","SUB","DEC")),v["p_a"])
            if "strict" not in k:assert v["p_a"]==p
        out.append({"source_names":[aa,bb],"models":models,"regional_eligible":bool(ext[x["bout_id"]][2]),"bet_authorized":False})
    return out,{"training_fights":3039,"regional":regaudit,"round":{**ra,**roundaudit,**rt},"source_outcomes_through":"2026-11-21","secondary_qatar_rounds_used":False,"research_only":True}

def main():
    # Hypothetical pairs only; test corrected identity + newcomer + abstention.
    ids=historic_verified_id_map()
    pairs=[(NAMES[55096],"Dan Hooker"),("Akbar Abdullaev","Amir Albazi"),("Identity Test Unknown","Mateusz Gamrot")]
    qids={NAMES[55096]:55096,"Dan Hooker":ids["danhooker"],"Akbar Abdullaev":138491,"Amir Albazi":ids["amiralbazi"],"Mateusz Gamrot":ids["mateuszgamrot"]}
    result,audit=panel("2026-12-05",pairs,qids)
    assert [x["regional_eligible"] for x in result]==[True,True,False]
    print(json.dumps({**audit,"hypothetical_matchups":len(result),"models_checked":sum(len(x["models"]) for x in result),"new_live_forecasts":0,"production_migrated":False}))
if __name__=="__main__":main()
