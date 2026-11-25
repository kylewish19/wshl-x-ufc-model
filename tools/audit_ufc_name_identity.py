"""Read-only audit of name-key identity collisions in pinned UFC source."""
from pathlib import Path
from collections import defaultdict,Counter
import json
import pandas as pd
import audit_worldwide_mma_history_v4 as a
from wshlx_ufc.prefight_finish_resistance import ARCHIVE
from wshlx_ufc.historical_data import normalize_events,col,bout,txt

def main():
    events=pd.read_csv(ARCHIVE/"ufc_event_details.csv",low_memory=False)
    results=pd.read_csv(ARCHIVE/"ufc_fight_results.csv",low_memory=False)
    profiles=pd.read_csv(ARCHIVE/"ufc_fighter_tott.csv",low_memory=False)
    days={x.event:x.date.date().isoformat() for x in normalize_events(events).itertuples(index=False) if pd.notna(x.date)}
    con=a.get_tables(Path(".research_cache/fightcanon/new.db"))
    aliases=a.aliases(con)
    index,_=a.source_matched_fights(con,aliases)
    # Compare only dates covered by the existing pinned UFC archive.
    source=a.load_source_pairs()
    ids=defaultdict(set)
    for r in source:
        candidates=index.get(r["key"],set())
        if len(candidates)!=1:continue
        _,i,j=next(iter(candidates))
        ka,kb=a.namekey(r["a"]),a.namekey(r["b"])
        for x,y in ((i,j),(j,i)):
            if ka in aliases[x] and kb in aliases[y]:
                ids[ka].add(x);ids[kb].add(y)
    disputed={k:sorted(v) for k,v in ids.items() if len(v)>1}
    ec,bc,wc=(col(results,k) for k in ("EVENT","BOUT","WEIGHTCLASS"))
    bruno=[]
    for row in results.to_dict("records"):
        p=bout(row[bc])
        if p and "brunosilva" in [a.namekey(x) for x in p]:
            event=txt(row[ec]);day=days.get(event)
            bruno.append({"date":day,"event":event,"pair":p,"weight_class":txt(row[wc]) if wc else None})
    fc=col(profiles,"FIGHTER")
    pr=profiles[profiles[fc].map(a.namekey)=="brunosilva"].fillna("").to_dict("records")
    result={"modern_dated_name_collisions":disputed,"bruno_raw_fights":bruno,
       "bruno_weight_classes":dict(Counter(x["weight_class"] for x in bruno)),
       "bruno_physical_profile_rows":pr,"raw_profile_count":len(pr),
       "name_key_features_require_identity_review":True,
       "historical_source_changed":False,"predictions_generated":0}
    con.close()
    Path("bruno_identity_audit.json").write_text(json.dumps(result,indent=2,default=str))
    print(json.dumps(result,default=str))
if __name__=="__main__":main()
