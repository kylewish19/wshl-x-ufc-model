"""Research-only identity overlay; preserve source rows and historical locks."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json
import numpy as np
import pandas as pd
import audit_worldwide_mma_history_v4 as a
from wshlx_ufc.postevent_history_extension_v1 import load_extended_records
from wshlx_ufc.strict_history_inputs_v1 import matrices_from_records
from wshlx_ufc.prefight_finish_resistance import ARCHIVE,build_from_records
from wshlx_ufc.historical_feature_matrix import RESISTANCE,QUALITY
from wshlx_ufc.historical_data import normalize_events,col,bout,txt
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/".research_cache/fightcanon/new.db"
SHA="e7e0a53ff47d336ed961b228e31a1ef98c77129fa9104e82496637e69f3ade29"
NAMES={55096:"Bruno Silva [Bulldog]",50558:"Bruno Silva [Blindado]"}
PROFILE_IDS={55096:"294aa73dbf37d281",50558:"12ebd7d157e91701"}

def mapping():
    if hashlib.sha256(DB.read_bytes()).hexdigest()!=SHA:raise ValueError("Source SHA mismatch")
    con=a.get_tables(DB)
    try:
        aliases=a.aliases(con)
        for fid,sid in PROFILE_IDS.items():
            matches={r[0] for r in con.execute("SELECT fighter_id FROM fighter_aliases WHERE source='ufcstats' AND source_id=?",(sid,))}
            if matches!={fid}:raise ValueError("UFCStats profile ID mismatch")
        lookup=defaultdict(set)
        for day,fid,opp,mid in con.execute("""SELECT e.date,p.fighter_id,q.fighter_id,f.fight_id
         FROM fight_participants p JOIN fight_participants q ON q.fight_id=p.fight_id AND q.corner<>p.corner
         JOIN fights f ON f.fight_id=p.fight_id JOIN events e ON e.event_id=f.event_id
         WHERE p.fighter_id IN (55096,50558) AND e.date<'2026-11-25'
         AND EXISTS(SELECT 1 FROM fight_aliases fa WHERE fa.fight_id=f.fight_id AND fa.source='ufcstats')"""):
            for name in aliases[opp]:lookup[(day,name)].add((fid,mid))
        events=pd.read_csv(ARCHIVE/"ufc_event_details.csv",low_memory=False)
        results=pd.read_csv(ARCHIVE/"ufc_fight_results.csv",low_memory=False)
        days={x.event:x.date.date().isoformat() for x in normalize_events(events).itertuples(index=False) if pd.notna(x.date)}
        ec,bc=col(results,"EVENT"),col(results,"BOUT")
        matched={}
        for row in results.to_dict("records"):
            p=bout(row[bc])
            if not p or "brunosilva" not in [a.namekey(z) for z in p]:continue
            day=days[txt(row[ec])]
            other=next(z for z in p if a.namekey(z)!="brunosilva")
            hits=lookup[(day,a.namekey(other))]
            if len(hits)!=1:raise ValueError("Unresolved dated UFC identity "+str((day,p,hits)))
            fid,mid=next(iter(hits))
            matched[(day,a.namekey(other))]=(fid,mid)
        assert len(matched)==23
        return matched
    finally:con.close()

def overlay(records,matched):
    corrected=[];counts=Counter()
    for orig in records:
        r=dict(orig)
        for s,other in (("a","b"),("b","a")):
            if a.namekey(r[s])!="brunosilva":continue
            fid,_=matched[(r["date"].isoformat(),a.namekey(r[other]))]
            r[s]=NAMES[fid];counts[fid]+=1
        corrected.append(r)
    return corrected,dict(counts)

def canonical(n):return "Bruno Silva" if n in NAMES.values() else n
def pairkey(f):return (f["event_date"],f["event"],canonical(f["fighter_a"]),canonical(f["fighter_b"]))
def main():
    day="2026-12-05"
    matched=mapping()
    records,_=load_extended_records(as_of_exclusive=day)
    fixed,counts=overlay(records,matched)
    assert len(records)==len(fixed)==8896
    assert all(all(x[k]==y[k] for k in x if k not in ("a","b")) for x,y in zip(records,fixed))
    oldf,oldl,oldform=matrices_from_records(records,day)
    newf,newl,newform=matrices_from_records(fixed,day)
    old={pairkey(x):x for x in oldf};new={pairkey(x):x for x in newf}
    assert len(old)==len(oldf)==len(new)==len(newf) and old.keys()==new.keys()
    ol={x["bout_id"]:x for x in oldl};nl={x["bout_id"]:x for x in newl}
    changed=Counter();dec=Counter();form_changed=0
    fields=[s+"_"+k for s in ("a","b") for k in set(RESISTANCE)|set(QUALITY)]
    for k,x in old.items():
        y=new[k];l,m=ol[x["bout_id"]],nl[y["bout_id"]]
        for label in ("result_status","label_a_win","label_method"):
            assert l[label]==m[label]
        diff=any(x[z]!=y[z] for z in fields)
        formdiff=False
        if k[0]>="2021-01-01":
            formdiff=any(not np.array_equal(np.asarray(u),np.asarray(v),equal_nan=True) for u,v in zip(oldform[x["bout_id"]],newform[y["bout_id"]],strict=True))
        else:
            assert x["bout_id"] not in oldform and y["bout_id"] not in newform
        if formdiff:form_changed+=1
        if diff or formdiff:
            changed["all"]+=1
            if "Bruno Silva" in k[2:]:changed["direct"]+=1
            else:changed["other"]+=1
            if l["result_status"]=="DECISIVE" and k[0]>="2021-01-01":dec["modern_decisive"]+=1
    # Query-only counts; no scheduled matchup predictions.
    o,_=build_from_records(records,as_of_exclusive=day,query_bouts=[("Bruno Silva","Identity Audit Control")])
    n,_=build_from_records(fixed,as_of_exclusive=day,query_bouts=[(NAMES[55096],NAMES[50558])])
    before=o[-1]["a_pre"];after=n[-1]
    result={"matched_raw_rows":len(matched),"raw_rows_by_id":dict(Counter(x[0] for x in matched.values())),"eligible_records_by_id":counts,"original_combined_eligible_bouts":before["prior_ufc_bouts"],"separated_eligible_bouts":{"bulldog":after["a_pre"]["prior_ufc_bouts"],"blindado":after["b_pre"]["prior_ufc_bouts"]},"changed_feature_rows":dict(changed),"changed_modern_decisive_rows":dec["modern_decisive"],"changed_recent_form_rows_2021_onward":form_changed,"same_result_labels":True,"source_unchanged":True,"production_migrated":False,"predictions_generated":0,"profile_ids_verified":PROFILE_IDS}
    Path("ufc_identity_overlay_audit.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=="__main__":main()
