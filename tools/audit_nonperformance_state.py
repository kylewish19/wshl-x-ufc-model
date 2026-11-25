"""Read-only sensitivity audit of the documented Reference nonperformance exclusion.
This is a feature audit, not an accuracy benchmark or a model refit.
Preserve official result, immutable source and previously locked predictions.
"""
from pathlib import Path
from collections import Counter
import hashlib,json
import numpy as np
import pandas as pd
from refit_reference_identity_corrected import source
from wshlx_ufc.historical_data import build_prefight_perspective_rows,normalize_events,bout,txt,METRICS
from wshlx_ufc.prefight_finish_resistance import ARCHIVE
from audit_identity_safe_csv import FILES

PAIR={"Alexandre Pantoja","Joshua Van"}
DAY="2025-12-06"
def matches(x,dates):
    return dates.get(txt(x["EVENT"]))==DAY and set(bout(x["BOUT"]) or ())==PAIR
def make(t):
    return build_prefight_perspective_rows(t["events"],t["results"],t["stats"],t["fighters"])
def main():
    source_hashes={k:hashlib.sha256((ARCHIVE/v).read_bytes()).hexdigest() for k,v in FILES.items()}
    t=source()
    dates={r.event:str(r.date.date()) for r in normalize_events(t["events"]).itertuples(index=False) if pd.notna(r.date)}
    m=t["results"].apply(lambda x:matches(x,dates),axis=1)
    assert int(m.sum())==1
    target=t["results"].loc[m].iloc[0]
    assert txt(target["OUTCOME"]) in ("W/L","L/W") and "KO" in txt(target["METHOD"])
    # Outcome remains in original input; only the alternate isolated frame
    # excludes it from both label and subsequent historical state updates.
    alt={k:v.copy(deep=True) for k,v in t.items()}
    alt["results"]=alt["results"].loc[~m].reset_index(drop=True)
    raw=make(t);clean=make(alt)
    ids=["fight_id","fighter","opponent"]
    old=raw.set_index(ids,verify_integrity=True);new=clean.set_index(ids,verify_integrity=True)
    removed=old.index.difference(new.index)
    assert len(removed)==2 and len(new.index.difference(old.index))==0
    assert set(removed.get_level_values("fighter"))==PAIR
    assert all(str(old.loc[k,"date"].date())==DAY for k in removed)
    old=old.loc[new.index]
    for label in ("win","fight_method","scheduled_rounds","weight_class","date"):
        pd.testing.assert_series_equal(old[label],new[label])
    fields=[k for m in METRICS for k in (m,"opp_"+m,m+"_diff")]+["previous_meeting_result","rematch_number","finish_profile_matchup","debut_status","sig_str_diff","sig_str_diff_diff","five_round_exp_status","title_exp_status"]
    different=pd.DataFrame({k:~((old[k]==new[k])|(old[k].isna()&new[k].isna())) for k in fields},index=new.index)
    changed=different.any(axis=1)
    assert not (changed & (new["date"]<=pd.Timestamp(DAY))).any()
    affected=[]
    for key in changed[changed].index:
        o,n=old.loc[key],new.loc[key]
        # Historical states are fighter-local; unrelated fighters should not change.
        assert bool(set(key[1:])&PAIR)
        affected.append({"fight_id":key[0],"fighter":key[1],"opponent":key[2],"date":str(n["date"].date()),"changed_fields":[k for k in fields if different.loc[key,k]],"own_prior_fights_before":float(o["ufc_fights"]),"own_prior_fights_after":float(n["ufc_fights"]),"opponent_prior_fights_before":float(o["opp_ufc_fights"]),"opponent_prior_fights_after":float(n["opp_ufc_fights"])})
    assert all(hashlib.sha256((ARCHIVE/v).read_bytes()).hexdigest()==source_hashes[k] for k,v in FILES.items())
    result={"official_outcome_preserved":True,"target":{"date":DAY,"names":sorted(PAIR),"raw_outcome":txt(target["OUTCOME"]),"raw_method":txt(target["METHOD"])},"native_perspectives":len(raw),"alternate_perspectives":len(clean),"removed_target_perspectives":2,"changed_later_perspectives":int(changed.sum()),"changed_later_fights":len({x["fight_id"] for x in affected}),"affected":affected,"all_shared_labels_unchanged":True,"source_hashes_unchanged":True,"predictive_accuracy_measured":False,"production_migrated":False}
    Path("nonperformance_state_sensitivity.json").write_text(json.dumps(result,indent=2))
    print("NONPERFORMANCE_STATE_AUDIT",json.dumps(result))
if __name__=="__main__":main()
