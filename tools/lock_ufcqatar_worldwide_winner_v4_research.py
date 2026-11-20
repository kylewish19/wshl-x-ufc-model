"""Pre-event independently locked WORLDWIDE-MMA Winner v4 Qatar research.

Requires existing SHA-frozen November 21 original Stage A, Coherent shadow
and already independent Winner v3 prospective shadow; NONE may be modified.
Trains 2021-Nov7 UFC results plus only external pro bouts preceding each
historical matchup. New Nov21 feature queries use prior UFC info, and only
verified cross-promotion fighter IDs from PAST UFC fight date+opponent pairs.
The three unseen fighter identities without UFC history are UNVERIFIED, not
fuzzy matched or assigned unverified regional stats.

Primary challenger registered BEFORE any bout: winner_v4_boost73 paired with
the same independent time-safe conditional method model for both winners.
No wager signals, no stage B, no 100% locks, no source invented stats.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date,datetime,timezone
from pathlib import Path
import hashlib,json
import numpy as np

from wshlx_ufc.historical_feature_matrix import (
    RESISTANCE,QUALITY,load_matrix,
)
from wshlx_ufc.prefight_finish_resistance import (
    ARCHIVE,_load_records,build_from_records,
)
from wshlx_ufc.prefight_opponent_quality import build_historical_opponent_quality
from wshlx_ufc.winner_recent_form_v3 import (
    construct_record_history,supplement_current_feature_matrix,
)
from wshlx_ufc.finish_v1_research import (
    method_features,training_rows,MultinomialFinish,coherent_six,METHODS,
)
from audit_worldwide_mma_history_v4 import (
    get_tables,history_for_ids,prior,namekey,DB,
)
from benchmark_worldwide_mma_winner_v4 import (
    load_external,features as encode_region,train,model_probas,
    REGIONAL,REGIONAL_SOURCE_SHA,HEADS,
)
from lock_ufcqatar_winner_v3_research import align_to_source

ROOT=Path(__file__).resolve().parents[1]
START_UTC=datetime.fromisoformat("2026-11-21T15:00:00+00:00")
DAY="2026-11-21"
FROZEN=ROOT/"data/locks/ufcqatar_2026-11-21/stage_a_final_selection.json"
FROZEN_AUDIT=ROOT/"data/locks/ufcqatar_2026-11-21/stage_a_final_audit.json"
COHERENT=ROOT/"data/shadow_locks/ufcqatar_2026-11-21/coherent_joint_pre_event_shadow.json"
V3=ROOT/"data/shadow_locks/ufcqatar_2026-11-21/winner_v3_prospective_shadow.json"
DEST=ROOT/"data/shadow_locks/ufcqatar_2026-11-21/worldwide_winner_v4_prospective_shadow.json"
JOINT=("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def historic_verified_id_map():
    source=json.loads((REGIONAL/"verified_bout_prior_pro_history.json").read_text())
    m=defaultdict(set)
    for r in source:
        for side in ("a","b"):
            m[namekey(r[f"fighter_{side}"])].add(int(r[f"{side}_verified_id"]))
    # No guesses if 2 pro-fighters share the same textual name.
    return {key:next(iter(ids)) for key,ids in m.items() if len(ids)==1}

def main():
    stamp=datetime.now(timezone.utc)
    if stamp>=START_UTC:raise RuntimeError("Post-event shadow cannot claim pre-event freeze")
    if DEST.exists():raise FileExistsError("Never overwrite original v4 future-only research forecast")
    originals=[FROZEN,FROZEN_AUDIT,COHERENT,V3]
    if any(not p.exists() for p in originals):
        raise FileNotFoundError("All original independent pre-event research/Stage A locks required")
    old=json.loads(FROZEN.read_text())
    audit=json.loads(FROZEN_AUDIT.read_text())
    v3=json.loads(V3.read_text())
    if (not old["stage_a_frozen"] or old["event_date"]!=DAY or old["odds_used"] or
        audit["final_sha256"]!=sha(FROZEN) or
        v3["original_stage_a_sha256"]!=sha(FROZEN) or
        v3["original_coherent_shadow_sha256"]!=sha(COHERENT)):
        raise ValueError("Existing original card and v3/Coherent source SHAs mismatch")
    if len(old["fights"])!=12 or len(v3["fights"])!=12:
        raise ValueError("12 total active/provisional original fight slots required")
    if sha(DB)!=REGIONAL_SOURCE_SHA:
        raise ValueError("Newly downloaded world MMA source must match the prespecified pinned SHA")

    historical,labels,manifest=load_matrix()
    external,exreport=load_external(historical)
    forms,formreport=supplement_current_feature_matrix(historical)
    byid={r["bout_id"]:r for r in labels}
    rows=[(f,byid[f["bout_id"]]) for f in historical if
          "2021-01-01"<=f["event_date"]<DAY and
          byid[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(rows)!=3015:raise ValueError("UFC history cohort/source cutoff not identical to registered v4")
    models=train(rows,forms,external,DAY)
    f_train=[f for f,l in rows];l_train=[l for f,l in rows]
    X,y=training_rows(f_train,l_train,DAY)
    methods=MultinomialFinish().fit(X,y)

    archive=_load_records(ARCHIVE,date.fromisoformat(DAY))
    if len(archive)!=8871:raise ValueError("Pinned original UFC archive changed")
    wanted=[x for f in old["fights"] for x in (f["a"],f["b"])]
    fighters,aliases=align_to_source(wanted,archive)
    pairs=[tuple(fighters[2*i:2*i+2]) for i in range(12)]
    if len({x for pair in pairs for x in pair})!=24:
        raise ValueError("12 original fights must contain 24 distinct fighters")

    resistance,_=build_from_records(archive,as_of_exclusive=DAY,query_bouts=pairs)
    resist=[x for x in resistance if x.get("query_only")]
    elog=[{"date":x["date"].isoformat(),"event":x["event"],"a":x["a"],"b":x["b"],
           "outcome":"/".join(x["result"])} for x in archive]
    quality=build_historical_opponent_quality(
        elog,query_date=DAY,query_bouts=pairs)
    quals=[x for x in quality if x.get("query_only")]
    recent=construct_record_history(archive,cutoff=DAY,query_date=DAY,
                                    query_bouts=tuple(pairs))
    if len(resist)!=12 or len(quals)!=12:raise ValueError("All 12 new query snapshots required")

    mapids=historic_verified_id_map()
    identity=[mapids.get(namekey(n)) for n in fighters]
    con=get_tables(DB)
    regional_history=history_for_ids(con,[id for id in identity if id is not None])
    newrows=[]
    for i,(f,(a,b)) in enumerate(zip(old["fights"],pairs),1):
        boutid=f"WSHLX_QATAR_WORLD_W4_{i:02d}"
        r=resist[i-1];q=quals[i-1]
        if (r["a"],r["b"])!=(a,b) or (q["a"],q["b"])!=(a,b):
            raise ValueError("Independent as-of builders disagree on UFC fighter alignment")
        feat={"event_date":DAY,"feature_as_of_exclusive":DAY,
              "event":"UFC Fight Night: Prochazka vs Stirling",
              "bout_id":boutid,"fighter_a":a,"fighter_b":b}
        for fields,rs,qs in ((RESISTANCE,r["a_pre"],r["b_pre"]),
                             (QUALITY,q["a_pre"],q["b_pre"])):
            for field in fields:
                if field not in rs or field not in qs:
                    raise ValueError("Missing required original pre-bout statistic "+field)
                feat["a_"+field]=rs[field]
                feat["b_"+field]=qs[field]
        if any(feat[side+"_prior_ufc_bouts"]!=feat[side+"_ufc_prior_bouts"] for side in ("a","b")):
            raise ValueError("Rival independent prior-UFC-count disagreement")
        form=recent.get((DAY,"__PREFIGHT_QUERY_NO_RESULTS__",*sorted((a,b))))
        if form is None or not form.get("query_only") or (form["a_name"],form["b_name"])!=(a,b):
            raise ValueError("Previously unknown fighter prospective recent form identity")
        forms[boutid]=(form["a"],form["b"])
        ida,idb=identity[2*(i-1):2*i]
        ra=encode_region(prior(regional_history[ida],DAY),verified=True) if ida is not None else encode_region(None,verified=False)
        rb=encode_region(prior(regional_history[idb],DAY),verified=True) if idb is not None else encode_region(None,verified=False)
        if ida is None and feat["a_prior_ufc_bouts"]>0:
            raise ValueError("Veteran A unexpectedly lacks world-source verified identity")
        if idb is None and feat["b_prior_ufc_bouts"]>0:
            raise ValueError("Veteran B unexpectedly lacks world-source verified identity")
        external[boutid]=(ra,rb,ida is not None and idb is not None)

        pp,verified=model_probas(feat,forms,external,models)
        cond=methods.predict(np.vstack((method_features(feat,"a"),method_features(feat,"b"))))
        predictions={}
        for head,p in pp.items():
            six=coherent_six(p,cond)
            side=0 if p>=.5 else 1
            j=int(np.argmax(six[3*side:3*side+3]))
            predictions[head]={
                "winner":f["a"] if side==0 else f["b"],
                "method":METHODS[j],
                "p_a_win":float(p),
                "p_winner":float(max(p,1-p)),
                "p_exact_fighter_method":float(six[3*side+j]),
                "six_joint":{k:float(six[kid]) for kid,k in enumerate(JOINT)},
                "research_only":True,
            }
        sparse=min(feat["a_prior_ufc_bouts"],feat["b_prior_ufc_bouts"])<5
        missing=ida is None or idb is None
        newrows.append({
            "fight_no":i,"a":f["a"],"b":f["b"],
            "original_betting_posture_unmodified":f["stage_a_posture"],
            "provisional":bool(i==12),
            "a_prior_UFC_bouts":int(feat["a_prior_ufc_bouts"]),
            "b_prior_UFC_bouts":int(feat["b_prior_ufc_bouts"]),
            "external_source_ids_verified_both":bool(verified),
            "external_source_fighter_ids":{
                "a":ida,"b":idb},
            "cross_promotion_identity_or_UFC_data_warning":
                "UNKNOWN_NONUFC_IDENTITY_PASS" if missing else
                "SPARSE_UFC_SAMPLE" if sparse else "NORMAL_RESEARCH",
            "not_authorized_for_any_bet":True,
            "research_variants":predictions,
        })
    if newrows[11]["original_betting_posture_unmodified"]!="PASS":
        raise ValueError("Unconfirmed debutant pair remains original PASS")
    result={
        "schema":"WSHLX_QATAR_SEPARATE_WORLDWIDE_WINNER_V4_PROSPECTIVE_RESEARCH_ONLY",
        "event_date":DAY,"locked_at_utc":stamp.isoformat(),
        "first_fight_at_utc":START_UTC.isoformat(),
        "original_stage_a_sha256":sha(FROZEN),
        "original_coherent_shadow_sha256":sha(COHERENT),
        "original_independent_v3_shadow_sha256":sha(V3),
        "source_UFC_pin_sha256":manifest["source_stats_sha256"],
        "external_source_version":"FightCanon db-2026-11-19-1934",
        "external_source_SHA256":REGIONAL_SOURCE_SHA,
        "regional_history_feature_cutoff_in_pipeline":"2026-11-08 exclusive",
        "all_fight_history_used_date_strictly_before_event":True,
        "training_fights":models["n_training_fights"],
        "method_trained_fights":len(y),
        "original_Reference_Historical_Unified_Coherent_and_v3_NOT_MODIFIED":True,
        "primary_registered_research_winner":"winner_v4_boost73",
        "other_three_variants_diagnostic_only":True,
        "no_betting_prices_observed":True,
        "no_official_wagers_or_model_promotion":True,
        "fights_predicted":len(newrows),
        "nov21_provisional_12th_fight_quarantined":True,
        "source_region_report":exreport,
        "source_UFC_form_report":formreport,
        "results_not_yet_observed":True,
        "fights":newrows,
    }
    if any(not x["not_authorized_for_any_bet"] for x in newrows):
        raise ValueError("Unapproved model cannot create official bets")
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "STATUS":"PREFIGHT_SEPARATE_WORLDWIDE_MMA_WINNER_V4_SHA_LOCKED_RESEARCH_ONLY",
        "locked":stamp.isoformat(),"primary":result["primary_registered_research_winner"],
        "source_sha":REGIONAL_SOURCE_SHA,
        "fights":[{"n":x["fight_no"],"a":x["a"],"b":x["b"],
            "winner":x["research_variants"]["winner_v4_boost73"]["winner"],
            "method":x["research_variants"]["winner_v4_boost73"]["method"],
            "winner_p":round(x["research_variants"]["winner_v4_boost73"]["p_winner"],4),
            "exact_p":round(x["research_variants"]["winner_v4_boost73"]["p_exact_fighter_method"],4),
            "identity_warning":x["cross_promotion_identity_or_UFC_data_warning"]}
            for x in newrows],
    },sort_keys=True))

if __name__=="__main__":main()
