"""Build isolated identity-safe UFC CSV tables; do not edit original archive."""
from pathlib import Path
from collections import Counter
import hashlib,json,tempfile
import pandas as pd
import numpy as np
from audit_ufc_identity_overlay import mapping,NAMES,PROFILE_IDS,canonical
from wshlx_ufc.historical_data import load_source_files,normalize_events,normalize_fighters,build_prefight_perspective_rows,col,bout,txt,METRICS
from wshlx_ufc.prefight_finish_resistance import ARCHIVE
from wshlx_ufc.round_method_v10 import read_rounds
from audit_worldwide_mma_history_v4 import namekey

FILES={"events":"ufc_event_details.csv","results":"ufc_fight_results.csv","stats":"ufc_fight_stats.csv","fighters":"ufc_fighter_tott.csv"}
def corrected_tables(tables,matched):
    t={k:v.copy(deep=True) for k,v in tables.items()}
    days={x.event:x.date.date().isoformat() for x in normalize_events(t["events"]).itertuples(index=False) if pd.notna(x.date)}
    counts=Counter()
    for typ in ("results","stats"):
        df=t[typ];ec,bc=col(df,"EVENT"),col(df,"BOUT")
        fc=col(df,"FIGHTER") if typ=="stats" else None
        if typ=="stats" and fc is None:raise ValueError("No fighter column")
        for i,x in df.iterrows():
            p=bout(x[bc])
            if not p or "brunosilva" not in [namekey(z) for z in p]:continue
            side=next(z for z in p if namekey(z)=="brunosilva")
            other=next(z for z in p if namekey(z)!="brunosilva")
            fid,_=matched[(days[txt(x[ec])],namekey(other))]
            assert str(x[bc]).count(side)==1
            df.at[i,bc]=str(x[bc]).replace(side,NAMES[fid],1)
            if fc and namekey(x[fc])=="brunosilva":df.at[i,fc]=NAMES[fid]
            counts[typ]+=1
        cols=[k for k in df.columns if k not in (bc,fc)]
        pd.testing.assert_frame_equal(df[cols],tables[typ][cols])
    df=t["fighters"];fc,uc=col(df,"FIGHTER"),col(df,"URL")
    if not fc or not uc:raise ValueError("Physical profile identity fields absent")
    for i,x in df.iterrows():
        if namekey(x[fc])!="brunosilva":continue
        sid=txt(x[uc]).rstrip("/").split("/")[-1]
        ids=[k for k,v in PROFILE_IDS.items() if v==sid]
        if len(ids)!=1:raise ValueError("Unverified physical profile")
        df.at[i,fc]=NAMES[ids[0]];counts["fighters"]+=1
    pd.testing.assert_frame_equal(df.drop(columns=[fc]),tables["fighters"].drop(columns=[fc]))
    assert counts["results"]==23 and counts["fighters"]==2
    return t,dict(counts)
def frame(t):
    return build_prefight_perspective_rows(t["events"],t["results"],t["stats"],t["fighters"])
def index_frame(df):
    return {(str(r["date"]),r["event"],canonical(r["fighter"]),canonical(r["opponent"])):r for r in df.to_dict("records")}
def main():
    original={k:hashlib.sha256((ARCHIVE/v).read_bytes()).hexdigest() for k,v in FILES.items()}
    old=load_source_files(ARCHIVE)
    new,counts=corrected_tables(old,mapping())
    assert all(len(old[k])==len(new[k]) for k in FILES)
    prof=normalize_fighters(new["fighters"]).set_index("fighter")
    assert tuple(prof.loc[NAMES[55096],["height","reach"]])==(64.,65.)
    assert tuple(prof.loc[NAMES[50558],["height","reach"]])==(72.,74.)
    assert str(prof.loc[NAMES[55096],"dob"].date())=="1990-03-16"
    assert str(prof.loc[NAMES[50558],"dob"].date())=="1989-07-13"
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)
        new["stats"].to_csv(path/FILES["stats"],index=False)
        r0,a0=read_rounds(ARCHIVE)
        r1,a1=read_rounds(path)
        def revert(k):
            pair,fighter,n=k
            return ((pair[0],*sorted(canonical(z) for z in pair[1:])),canonical(fighter),n)
        restored={revert(k):v for k,v in r1.items()}
        assert len(restored)==len(r1)==len(r0) and restored==r0
    f0,f1=frame(old),frame(new)
    a,b=index_frame(f0),index_frame(f1)
    assert len(a)==len(f0)==len(b)==len(f1) and a.keys()==b.keys()
    for k,x in a.items():
        y=b[k]
        assert all(x[z]==y[z] for z in ("win","fight_method","scheduled_rounds","weight_class"))
    fields=[p+m for m in METRICS for p in ("","opp_")]
    def differs(x,y):
        return any(not ((pd.isna(x[z]) and pd.isna(y[z])) or x[z]==y[z]) for z in fields)
    affected=[k for k,x in a.items() if differs(x,b[k])]
    assert all(hashlib.sha256((ARCHIVE/v).read_bytes()).hexdigest()==original[k] for k,v in FILES.items())
    result={"corrected_raw_rows":counts,"round_rows_preserved":len(r0),"round_audit_before":a0,"round_audit_after":a1,"perspective_rows":len(a),"changed_perspective_feature_rows":len(affected),"changed_modern_perspectives":sum(k[0]>="2021-01-01" for k in affected),"physical_profiles_separated":True,"all_outcome_labels_preserved":True,"source_hashes_unchanged":True,"production_migrated":False,"predictions_generated":0}
    Path("identity_safe_csv_audit.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=="__main__":main()
