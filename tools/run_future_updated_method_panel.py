"""Updated-data method panel for future research, not Stage A/B.
v3, v5, Round86 use identical updated UFC winner probabilities.
Regional database deliberately retains its audited Nov7 cutoff. No new
regional identity inferred from a name alone. Unknown identities abstain
from the v5 arm. No actual future card lock until caller verifies lineup.
"""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import argparse,json,hashlib,csv
import numpy as np
from run_future_updated_history_research import build as base_build,query
from benchmark_strict_history_v1 import train,predict
from benchmark_round_method_v10 import classifier,cond,COEFF
from benchmark_worldwide_mma_winner_v4 import load_external,features as encode_region,REGIONAL_SOURCE_SHA
from benchmark_worldwide_method_v5 import train_methods,conditional
from audit_worldwide_mma_history_v4 import DB,get_tables,history_for_ids,prior,namekey
from lock_ufcqatar_worldwide_winner_v4_research import historic_verified_id_map
from wshlx_ufc.postevent_history_extension_v1 import load_extended_records,verify_qatar_round_totals,pinned,KEYS
from wshlx_ufc.strict_history_inputs_v1 import matrices_from_records
from wshlx_ufc.round_method_v10 import read_rounds,build_round_history,features as round_features
from wshlx_ufc.finish_conversion_v9 import build_conversion,enriched_features
from wshlx_ufc.finish_v1_research import coherent_six,METHODS

SIX=("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")
CUTOFF="2026-11-08"
QUERY="__PREFIGHT_QUERY_NO_RESULTS__"

def add_secondary_rounds(records,rounds):
    totals=json.loads(pinned(KEYS[3]));res=json.loads(pinned(KEYS[2]))
    raw=list(csv.DictReader(pinned(KEYS[4]).decode().splitlines()))
    verify_qatar_round_totals(totals,raw,res)
    # Map the archived display names to the source-verified extension pair,
    # using the same normalized name and date+pair, never a new fuzzy match.
    lookup={}
    for r in records:
        if r["date"].isoformat()!="2026-11-21":continue
        k=tuple(sorted(namekey(r[z]) for z in ("a","b")))
        if k in lookup:raise ValueError("ambiguous extension identity")
        lookup[k]=r
    byno={x["fight_no"]:x for x in res["fights"]}
    count=0
    for x in raw:
        r=byno[int(x["fight_no"])]
        pair=tuple(sorted(namekey(r[z]) for z in ("winner","loser")))
        record=lookup[pair]
        names=[record[z] for z in ("a","b") if namekey(record[z])==namekey(x["fighter"])]
        if len(names)!=1:raise ValueError("secondary round name mismatch")
        key=((record["event"],*sorted((record["a"],record["b"]))),names[0],int(x["round"]))
        if key in rounds:raise ValueError("duplicate supplemental round")
        # These two fields are unavailable in the round mirror. Do not
        # synthesize round-specific submission counts or ground strikes.
        rounds[key]={"sig":(int(x["sig_landed"]),int(x["sig_attempted"])),
          "td":(int(x["td_landed"]),int(x["td_attempted"])),
          "ctrl":int(x["control_seconds"]),"sub":None,"ground":None}
        count+=1
    if count!=64:raise ValueError("incomplete round supplement")
    return count

def regional_inputs(features,queries):
    if hashlib.sha256(DB.read_bytes()).hexdigest()!=REGIONAL_SOURCE_SHA:raise ValueError("regional DB hash mismatch")
    # Existing matched training cohort stays exactly as audited.
    ext,audit=load_external(features)
    ids=historic_verified_id_map()
    # Historical ID crosswalk based on previously corroborated UFC date+opponent
    # matches. Never use a new fighter's same-name database candidate.
    with get_tables(DB) as con:
        history=history_for_ids(con,ids.values())
    appended=0;missing=0;eligible_queries=0
    for f in [x for x in features if x["event_date"]>=CUTOFF]+queries:
        isquery=f["event"]==QUERY
        aa,bb=(ids.get(namekey(f["fighter_"+s])) for s in ("a","b"))
        valid=aa is not None and bb is not None and aa!=bb
        if valid:
            # history_for_ids itself excludes Nov8 and later, even for
            # December queries. This is an explicitly stale-source variant.
            a,b=(encode_region(prior(history[z],f["event_date"]),verified=True) for z in (aa,bb))
        else:
            a=b=encode_region(None,verified=False)
        ext[f["bout_id"]]=(a,b,valid)
        if isquery:eligible_queries+=int(valid)
        else:appended+=1;missing+=int(not valid)
    return ext,{**audit,"regional_results_through":"2026-11-07",
      "updated_UFC_outcomes_but_not_refreshed_worldwide_records":True,
      "new_historical_rows":appended,"new_rows_without_both_prior_verified_ids":missing,
      "query_rows_with_both_prior_verified_ids":eligible_queries}

def method_vector(f,side,conversion,rounds):
    return np.r_[enriched_features(f,side,conversion)[:54],round_features(f,side,rounds)]

def fit_round(rows,conversion,rounds):
    X=np.array([method_vector(f,"a" if int(l["label_a_win"]) else "b",conversion,rounds) for f,l in rows])
    y=np.array([l["label_method"] for f,l in rows])
    dates=np.array([f["event_date"] for f,l in rows])
    # Keep tuning on the completed 2025 calendar validation year, as in
    # the most recent v10 retrospective protocol, not on the new card.
    inner=dates<"2025-01-01";val=(dates>="2025-01-01")&(dates<"2026-01-01")
    labels=np.array([METHODS.index(m) for m in y[val]])
    losses={}
    for c in COEFF:
        q=cond(classifier(X[inner],y[inner],c),X[val])
        losses[c]=float(-np.log(np.maximum(1e-12,q[np.arange(len(labels)),labels])).mean())
    chosen=min(COEFF,key=lambda c:(losses[c],c))
    return classifier(X,y,chosen),{"C":chosen,"prior_year_validation":int(val.sum()),"train_n":len(y)}

def project(p,c,a,b):
    q=coherent_six(p,c)
    side=0 if p>=.5-1e-12 else 1
    i=3*side+int(np.argmax(q[3*side:3*side+3]))
    return {"p_a":p,"winner":a if side==0 else b,"method":METHODS[i%3],
      "p_exact":float(q[i]),"six_joint":dict(zip(SIX,map(float,q))),
      "research_only":True,"not_an_approved_wager":True}

def build_panel(lineup,*,now,secondary=False):
    base=base_build(lineup,now=now,secondary=secondary)
    cutoff=base["event_date"]
    records,audit=load_extended_records(as_of_exclusive=cutoff,allow_secondary_qatar_stats=secondary)
    pairs=[(x["identity_a"]["source_name"],x["identity_b"]["source_name"]) for x in base["fights"]]
    features,labels,forms=matrices_from_records(records,cutoff)
    ff,queryforms=query(records,cutoff,pairs)
    for f in ff:f["event"]=QUERY
    labs={x["bout_id"]:x for x in labels}
    rows=[(f,labs[f["bout_id"]]) for f in features if "2021-01-01"<=f["event_date"]<cutoff and labs[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(rows)!=3039:raise ValueError("training cohort changed")
    conv=build_conversion(records,query_date=cutoff,query_bouts=pairs)
    raw,rawaudit=read_rounds()
    n=add_secondary_rounds(records,raw) if secondary else 0
    rounds,roundaudit=build_round_history(records,raw,query_date=cutoff,query_bouts=pairs)
    round_model,tuning=fit_round(rows,conv,rounds)
    regional,regaudit=regional_inputs(features,ff)
    v5,train_n=train_methods(rows,regional,cutoff)
    assert train_n==3039
    for f,row in zip(ff,base["fights"],strict=True):
        p=row["models"]["legacy_updated_v3"]["p_a"]
        c=cond(round_model,np.vstack([method_vector(f,s,conv,rounds) for s in ("a","b")]))
        row["models"]["round86_updated_UFC"]=project(p,c,row["a"],row["b"])
        if regional[f["bout_id"]][2]:
            c=conditional(f,regional,v5)["worldwide_MMA_multinomial54"]
            row["models"]["regional_v5_updated_UFC_pinned_regional"]=project(p,c,row["a"],row["b"])
            row["regional_status"]="PRIOR_CROSSWALK_MATCH_REQUIRES_FIGHT_WEEK_ID_CONFIRMATION"
        else:
            row["regional_status"]="PASS_UNRESOLVED_REGIONAL_IDENTITY"
        row["research_only"]=True
    base.update({"schema":"WSHLX_UPDATED_METHOD_RESEARCH_PANEL_V1",
      "round86_training":tuning,"round_source_audit":{**rawaudit,**roundaudit,"secondary_round_fighter_rows":n},
      "regional_v5_training":train_n,"regional_audit":regaudit,
      "method_only_comparisons_keep_legacy_updated_v3_winner_probability":True,
      "production_stage_a_or_coherent_not_migrated":True})
    return base

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--lineup",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--allow-secondary-qatar-stats",action="store_true")
    a=ap.parse_args()
    if a.output.exists():raise FileExistsError("No overwrite")
    raw=a.lineup.read_bytes()
    lineup=json.loads(raw)
    # Caller must verify no missing completed UFC event between archive and
    # requested date; future archival refresh is not automatic.
    if lineup.get("UFC_history_current_through_last_completed_event_verified") is not True:
        raise ValueError("Recheck historical freshness before running a live research card")
    result=build_panel(lineup,now=datetime.now(timezone.utc),secondary=a.allow_secondary_qatar_stats)
    if datetime.now(timezone.utc)>=datetime.fromisoformat(result["first_fight_utc"]):raise ValueError("Event began")
    result["lineup_sha256"]=hashlib.sha256(raw).hexdigest()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x") as f:json.dump(result,f,indent=2,allow_nan=False)
if __name__=="__main__":main()
