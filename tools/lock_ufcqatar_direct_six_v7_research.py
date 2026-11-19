"""Independent PRE-EVENT UFC Qatar DIRECT 6 model v7 research shadow.

A single prespecified primary architecture: mirrored 230-feature bilateral
multinomial six-cell classifier; winner-marginal then top method policy.
Trained with 3015 older UFC decisive fights and historically dated global
regional MMA histories, with chosen regularization from 2025 validation.
11/21 Stage A, Coherent, v3, v4, v5 are never edited or backfilled.
No odds, betting approvals, winner locks, or arbitrary vote across models.
"""
from __future__ import annotations
from datetime import date,datetime,timezone
from pathlib import Path
import hashlib,json
import numpy as np
from wshlx_ufc.historical_feature_matrix import RESISTANCE,QUALITY,load_matrix
from wshlx_ufc.prefight_finish_resistance import ARCHIVE,_load_records,build_from_records
from wshlx_ufc.prefight_opponent_quality import build_historical_opponent_quality
from wshlx_ufc.winner_recent_form_v3 import (
    construct_record_history,supplement_current_feature_matrix
)
from audit_worldwide_mma_history_v4 import get_tables,history_for_ids,prior,DB
from benchmark_worldwide_mma_winner_v4 import (
    load_external,features as regional_features,REGIONAL_SOURCE_SHA
)
from benchmark_opponent_matchup_method_v6 import training_matrix,vectors
from benchmark_worldwide_direct_six_v7 import (
    fit_model,predict_six,select_prediction,validate_hyperparameters,outcome,
    METHODS,C_GRID,GLOBAL
)
from lock_ufcqatar_winner_v3_research import align_to_source

ROOT=Path(__file__).resolve().parents[1]
DAY="2026-11-21"
FIRST=datetime.fromisoformat("2026-11-21T15:00:00+00:00")
DIR=ROOT/"data/shadow_locks/ufcqatar_2026-11-21"
STAGE=ROOT/"data/locks/ufcqatar_2026-11-21/stage_a_final_selection.json"
AUDIT=ROOT/"data/locks/ufcqatar_2026-11-21/stage_a_final_audit.json"
COHERENT=DIR/"coherent_joint_pre_event_shadow.json"
V3=DIR/"winner_v3_prospective_shadow.json"
V4=DIR/"worldwide_winner_v4_prospective_shadow.json"
V5=DIR/"worldwide_method_v5_prospective_shadow.json"
DEST=DIR/"worldwide_direct_six_v7_prospective_shadow.json"
ARCH="direct_paired230"
POLICY="winner_marginal_method"

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    now=datetime.now(timezone.utc)
    if now>=FIRST:raise RuntimeError("Nov21 prospective window closed")
    if DEST.exists():raise FileExistsError("Cannot overwrite initial pre-event V7 research lock")
    originals=(STAGE,AUDIT,COHERENT,V3,V4,V5)
    if any(not p.is_file() for p in originals):raise FileNotFoundError("Missing earlier immutable locks")
    original=json.loads(STAGE.read_text())
    oldaudit=json.loads(AUDIT.read_text())
    v3=json.loads(V3.read_text())
    v4=json.loads(V4.read_text())
    v5=json.loads(V5.read_text())
    if (not original["stage_a_frozen"] or original["odds_used"] or
        original["event_date"]!=DAY or oldaudit["final_sha256"]!=sha(STAGE) or
        v3["original_stage_a_sha256"]!=sha(STAGE) or
        v4["original_stage_a_sha256"]!=sha(STAGE) or
        v5["original_stage_a_sha256"]!=sha(STAGE) or
        v4["original_independent_v3_shadow_sha256"]!=sha(V3) or
        v5["independent_v3_sha256"]!=sha(V3) or
        v5["independent_v4_sha256"]!=sha(V4) or
        v3["original_coherent_shadow_sha256"]!=sha(COHERENT)):
        raise ValueError("Earlier prospective/official picks source SHA mismatch")
    if sha(DB)!=REGIONAL_SOURCE_SHA or v4["external_source_SHA256"]!=REGIONAL_SOURCE_SHA:
        raise ValueError("Wrong external regional pro history archive")
    if any(len(x)!=12 for x in (original["fights"],v3["fights"],v4["fights"],v5["research_predictions"])):
        raise ValueError("Must compare exactly 12 previously registered card positions")

    feats,labels,ufcsource=load_matrix()
    regional,regionmeta=load_external(feats)
    recent,recentmeta=supplement_current_feature_matrix(feats)
    byid={r["bout_id"]:r for r in labels}
    rows=[(f,byid[f["bout_id"]]) for f in feats
          if "2021-01-01"<=f["event_date"]<DAY and
          byid[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(rows)!=3015:raise ValueError("Source historical training decisive bout count changed")
    historical=training_matrix(rows,regional,recent)
    for record,(f,l) in zip(historical,rows):
        if record["id"]!=f["bout_id"]:raise ValueError("Incorrect history label correspondence")
        record["truth"]=outcome(l)
    inner_train=[r for r in historical if r["date"]<"2025-01-01"]
    inner_val=[r for r in historical if "2025-01-01"<=r["date"]<"2026-01-01"]
    tuning=validate_hyperparameters(inner_train,inner_val,ARCH)
    assert tuning["chosen_C"] in C_GRID
    model=fit_model(historical,ARCH,tuning["chosen_C"])

    archive=_load_records(ARCHIVE,date.fromisoformat(DAY))
    if len(archive)!=8871:raise ValueError("Historical UFC source pin no longer matches")
    lineup=[name for f in original["fights"] for name in (f["a"],f["b"])]
    names,_=align_to_source(lineup,archive)
    pairs=[tuple(names[2*i:2*i+2]) for i in range(12)]
    if len(set(names))!=24:raise ValueError("12 separate matchup identities required")
    resisting,_=build_from_records(archive,as_of_exclusive=DAY,query_bouts=pairs)
    rr=[r for r in resisting if r.get("query_only")]
    earlier=[{"date":r["date"].isoformat(),"event":r["event"],
             "a":r["a"],"b":r["b"],"outcome":"/".join(r["result"])} for r in archive]
    quality=build_historical_opponent_quality(
        earlier,query_date=DAY,query_bouts=pairs)
    qq=[r for r in quality if r.get("query_only")]
    forms=construct_record_history(
        archive,cutoff=DAY,query_date=DAY,query_bouts=tuple(pairs))
    if len(rr)!=12 or len(qq)!=12:raise ValueError("All original future matchup snapshots required")

    fighterids=[]
    for f in v4["fights"]:
        fighterids.extend((f["external_source_fighter_ids"]["a"],f["external_source_fighter_ids"]["b"]))
    con=get_tables(DB)
    histories=history_for_ids(con,[k for k in fighterids if k is not None])

    outputs=[]
    for i,(bout,pair) in enumerate(zip(original["fights"],pairs),1):
        a,b=pair
        other=v4["fights"][i-1]
        if (other["a"],other["b"])!=(bout["a"],bout["b"]):
            raise ValueError("V4 verified source identity does not match frozen card")
        r=rr[i-1];q=qq[i-1]
        if (r["a"],r["b"])!=pair or (q["a"],q["b"])!=pair:
            raise ValueError("As-of independent UFC histories wrongly aligned")
        fid=f"QATAR_DIRECT_SIX_V7_{i:02d}"
        feat={"bout_id":fid,"event_date":DAY,
              "feature_as_of_exclusive":DAY,
              "event":"UFC Fight Night: Prochazka vs Stirling",
              "fighter_a":a,"fighter_b":b}
        for fields,lhs,rhs in ((RESISTANCE,r["a_pre"],r["b_pre"]),
                               (QUALITY,q["a_pre"],q["b_pre"])):
            for key in fields:
                if key not in lhs or key not in rhs:
                    raise ValueError("Missing dated source UFC feature "+key)
                feat["a_"+key]=lhs[key];feat["b_"+key]=rhs[key]
        if any(feat[x+"_prior_ufc_bouts"]!=feat[x+"_ufc_prior_bouts"] for x in ("a","b")):
            raise ValueError("Source UFC history models disagree on prior bouts")
        form=forms.get((DAY,"__PREFIGHT_QUERY_NO_RESULTS__",*sorted(pair)))
        if not form or not form.get("query_only") or (form["a_name"],form["b_name"])!=pair:
            raise ValueError("Missing genuine future-only recent fighter context")
        recent[fid]=(form["a"],form["b"])
        ida,idb=fighterids[2*(i-1):2*i]
        if (ida is None and feat["a_prior_ufc_bouts"]>0) or (
            idb is None and feat["b_prior_ufc_bouts"]>0):
            raise ValueError("Previously known UFC veteran loses verified external ID")
        ra=regional_features(prior(histories[ida],DAY),verified=True) if ida is not None else regional_features(None,verified=False)
        rb=regional_features(prior(histories[idb],DAY),verified=True) if idb is not None else regional_features(None,verified=False)
        regional[fid]=(ra,rb,ida is not None and idb is not None)
        va,vb,verified=vectors(feat,regional,recent)
        newrow={"Xa":va,"Xb":vb}
        q6=predict_six(model,newrow,ARCH)
        state=select_prediction(q6,POLICY)
        win_a=float(q6[:3].sum())
        side=state//3
        exact=float(q6[state])
        if not .0<=exact<=win_a+1e-8 if side==0 else not .0<=exact<=1-win_a+1e-8:
            raise ValueError("Bad six-cell winner/method joint probability")
        warning=other["cross_promotion_identity_or_UFC_data_warning"]
        outputs.append({
            "fight_no":i,"a":bout["a"],"b":bout["b"],
            "source_a":a,"source_b":b,
            "original_Stage_A_posture_unchanged":bout["stage_a_posture"],
            "original_provisional_12th":i==12,
            "a_prior_ufc_bouts":feat["a_prior_ufc_bouts"],
            "b_prior_ufc_bouts":feat["b_prior_ufc_bouts"],
            "independent_external_source_ids_both_verified":bool(verified),
            "data_quality":warning,
            "winner":bout["a"] if side==0 else bout["b"],
            "method":METHODS[state%3],
            "p_winner":float(win_a if side==0 else 1-win_a),
            "p_a":win_a,
            "p_exact_winner_method":exact,
            "selected_state":GLOBAL[state],
            "six_joint":{key:float(q6[j]) for j,key in enumerate(GLOBAL)},
            "not_an_approved_wager":True,
            "prospective_research_only":True,
        })
    if (not outputs[-1]["original_provisional_12th"] or
        outputs[-1]["original_Stage_A_posture_unchanged"]!="PASS"):
        raise ValueError("Provisional Mitchell-Yousaf stays research-only PASS")
    result={
        "schema":"WSHLX_UFC_QATAR_INDEPENDENT_DIRECT_SIX_V7_PROSPECTIVE_RESEARCH",
        "created_and_locked_utc":now.isoformat(),
        "earliest_fight_utc":FIRST.isoformat(),
        "event_date":DAY,"fights_predicted":12,
        "primary_architecture_locked_before_results":ARCH,
        "primary_selection_policy_locked_before_results":POLICY,
        "nested_C_chosen_using_2021_to_2024_training_and_2025_validation":tuning,
        "date_before_event_training_decisive_fights":len(historical),
        "source_UFC_SHA256":ufcsource["source_stats_sha256"],
        "world_MMA_source_SHA256":REGIONAL_SOURCE_SHA,
        "training_source_through":"2026-11-07",
        "independent_UFC_fight_stats_and_world_MMA_histories_past_date_only":True,
        "original_frozen_sha256":{x.name:sha(x) for x in originals},
        "all_prior_official_research_predictions_UNCHANGED":True,
        "FanDuel_odds_used":False,
        "betting_picks_approved":0,
        "provisional_fight_12_research_PASS":True,
        "six_classes":GLOBAL,
        "winner_and_method_joint_forecast_for_each_bout":True,
        "regional_data_source_audit":regionmeta,
        "recent_UFC_source_audit":recentmeta,
        "research_fights":outputs,
    }
    DEST.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
       "STATUS":"DIRECT_SIX_V7_NOV21_SEPARATE_SHA_LOCKED_RESEARCH_ONLY",
       "lock_utc":now.isoformat(),"primary_C":tuning["chosen_C"],
       "forecasts":[{"n":f["fight_no"],"a":f["a"],"b":f["b"],
          "winner":f["winner"],"method":f["method"],
          "p_win":round(f["p_winner"],4),
          "p_exact":round(f["p_exact_winner_method"],4),
          "warning":f["data_quality"]} for f in outputs],
    },sort_keys=True))

if __name__=="__main__":main()
