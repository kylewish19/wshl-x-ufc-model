"""Pre-event UTC/Git-commit locked UFC Qatar research-only Winner v3 cohort.

Not a revised Stage A, not the Coherent Challenger, not an authorized bet.
The new independently trained WINNER head (logit_recent_57 primary) is
paired with a separately fitted, same-sample date-safe multinomial method.
The original frozen Reference/Historical/Unified remains untouched.

The source UFCStats-compatible archive is PINNED THROUGH 2026-11-07; later
events, including completed Nov14 UFC334, are not incorporated. Source
histories are used only before the Nov21 query date. All 12 matchups include
one separately flagged provisional bout, which is always research PASS.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import date,datetime,timezone
from pathlib import Path
import hashlib,json,math,re,unicodedata
import numpy as np

from wshlx_ufc.historical_feature_matrix import RESISTANCE,QUALITY,load_matrix
from wshlx_ufc.prefight_finish_resistance import ARCHIVE,_load_records,build_from_records
from wshlx_ufc.prefight_opponent_quality import build_historical_opponent_quality
from wshlx_ufc.winner_recent_form_v3 import (
    construct_record_history,supplement_current_feature_matrix,
)
from wshlx_ufc.finish_v1_research import (
    MultinomialFinish,training_rows,method_features,coherent_six,METHODS,
)
from benchmark_winner_recent_form_v3 import fit_candidates,heads

ROOT=Path(__file__).resolve().parents[1]
DATE="2026-11-21"
START_UTC=datetime.fromisoformat("2026-11-21T15:00:00+00:00")
FINAL=ROOT/"data/locks/ufcqatar_2026-11-21/stage_a_final_selection.json"
AUDIT=ROOT/"data/locks/ufcqatar_2026-11-21/stage_a_final_audit.json"
COHERENT=ROOT/"data/shadow_locks/ufcqatar_2026-11-21/coherent_joint_pre_event_shadow.json"
OUTPUT=ROOT/"data/shadow_locks/ufcqatar_2026-11-21/winner_v3_prospective_shadow.json"
HEADS=("ufc_winrate","past_only_elo","logit_original_38",
       "logit_recent_57","boost_original_38","boost_recent_57")
CELLS=("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def namekey(name):
    a=unicodedata.normalize("NFKD",str(name))
    return re.sub("[^a-z0-9]","",a.encode("ascii","ignore").decode("ascii").lower())

def align_to_source(names,records):
    """Reject ambiguous historical fighter-name aliases, never fuzzy guess."""
    idx=defaultdict(set)
    for r in records:
        for x in (r["a"],r["b"]):
            idx[namekey(x)].add(x)
    resolved=[];metadata=[]
    for name in names:
        variants=idx.get(namekey(name),set())
        if len(variants)>1:
            raise ValueError("Unresolved ambiguous fighter alias: "+name+" "+str(sorted(variants)))
        mapped=next(iter(variants)) if variants else name
        resolved.append(mapped)
        metadata.append({
            "screen_name":name,"source_name":mapped,
            "source_name_matched":bool(variants),
            "prior_ufc_name_resolution":"EXACT_NORMALIZED_MATCH_IN_PINNED_ARCHIVE" if variants else
                "NO_MATCHING_UFC_SOURCE_NAME_REQUIRES_INDEPENDENT_ALIAS_VERIFICATION",
        })
    if len(set(resolved))!=len(resolved):
        raise ValueError("Multiple fighters falsely map to same source identity")
    return resolved,metadata

def main():
    now=datetime.now(timezone.utc)
    if now>=START_UTC:
        raise RuntimeError("Cannot claim prospectively locked model after event began")
    if OUTPUT.exists():
        raise FileExistsError("Never overwrite a first pre-event Winner v3 shadow")
    source=json.loads(FINAL.read_text())
    audit=json.loads(AUDIT.read_text())
    if (not source["stage_a_frozen"] or source["odds_used"] or
        source["event_date"]!=DATE or
        audit["final_sha256"]!=sha(FINAL) or
        audit["raw_sha256"]!=source["raw_model_sha256"]):
        raise ValueError("The original independent Stage A has invalid SHA")
    if len(source["fights"])!=12 or
        any((int(x["fight_no"])!=i) for i,x in enumerate(source["fights"],1)):
        raise ValueError("Expected 11 official plus exactly 1 provisional matchup")
    if not COHERENT.exists():
        raise FileNotFoundError("Original Nov21 Coherent Challenger lock required and unchanged")

    features,labels,manifest=load_matrix()
    forms,form_report=supplement_current_feature_matrix(features)
    bylabels={l["bout_id"]:l for l in labels}
    training=[(f,bylabels[f["bout_id"]]) for f in features
              if "2021-01-01"<=f["event_date"]<DATE
              and bylabels[f["bout_id"]]["result_status"]=="DECISIVE"]
    if len(training)!=3015:
        raise ValueError("Training historical population/source vintage changed")
    classifiers=fit_candidates(training,forms,DATE)
    trainf=[f for f,l in training];trainl=[l for f,l in training]
    X,y=training_rows(trainf,trainl,DATE)
    method=MultinomialFinish().fit(X,y)

    archive_records=_load_records(ARCHIVE,date.fromisoformat(DATE))
    if len(archive_records)!=8871:
        raise ValueError("Pinned source historical fight count changed")
    fights=source["fights"]
    names=[name for f in fights for name in (f["a"],f["b"])]
    aligned,identity=align_to_source(names,archive_records)
    queries=[tuple(aligned[2*i:2*i+2]) for i in range(len(fights))]
    if len({x for pair in queries for x in pair})!=24:
        raise ValueError("Not exactly 24 separate fighter identities")

    # BOTH separate matchup feature pipelines are strictly prospective:
    # resistance historical records, and past-UFC-only opponent strength.
    resistance,_=build_from_records(archive_records,as_of_exclusive=DATE,
                                    query_bouts=queries)
    rq=[x for x in resistance if x.get("query_only")]
    quality_history=[
        {"date":r["date"].isoformat(),"event":r["event"],
         "a":r["a"],"b":r["b"],"outcome":"/".join(r["result"])}
        for r in archive_records
    ]
    q=build_historical_opponent_quality(quality_history,
                                        query_date=DATE,query_bouts=queries)
    qq=[x for x in q if x.get("query_only")]
    formsnap=construct_record_history(archive_records,cutoff=DATE,
                                      query_date=DATE,query_bouts=tuple(queries))
    if len(rq)!=12 or len(qq)!=12:raise ValueError("Queries did not produce 12 new source-independent states")

    out=[]
    for i,(f,pair) in enumerate(zip(fights,queries),1):
        a,b=pair
        r=rq[i-1]; qrow=qq[i-1]
        if (r["a"],r["b"])!=pair or (qrow["a"],qrow["b"])!=pair:
            raise ValueError("Independent history identity or ordering mismatch")
        boutid=f"WSHLX_QATAR_WINNER_V3_{i:02d}"
        feat={
            "bout_id":boutid,
            "feature_as_of_exclusive":DATE,"event_date":DATE,
            "event":"UFC Fight Night: Prochazka vs Stirling",
            "fighter_a":a,"fighter_b":b,
            "source_class":"INDEPENDENT_QUERY_NO_RESULTS",
        }
        for fields,lhs,rhs in (
            (RESISTANCE,r["a_pre"],r["b_pre"]),
            (QUALITY,qrow["a_pre"],qrow["b_pre"]),
        ):
            for field in fields:
                if field not in lhs or field not in rhs:
                    raise ValueError("Query missing required historic feature "+field)
                feat["a_"+field]=lhs[field]
                feat["b_"+field]=rhs[field]
        for side in ("a","b"):
            if feat[side+"_prior_ufc_bouts"]!=feat[side+"_ufc_prior_bouts"]:
                raise ValueError("Different as-of record builders disagree")
        form=formsnap.get((DATE,"__PREFIGHT_QUERY_NO_RESULTS__",*sorted(pair)))
        if form is None or not form.get("query_only") or (form["a_name"],form["b_name"])!=pair:
            raise ValueError("Pre-event form query missing or mismatched")
        forms[boutid]=(form["a"],form["b"])

        winnerheads=heads(feat,forms,classifiers)
        cond=method.predict(np.vstack([method_features(feat,"a"),method_features(feat,"b")]))
        research={}
        for name in HEADS:
            p=winnerheads[name]
            six=coherent_six(p,cond)
            side=0 if p>=.5 else 1
            own=np.asarray(six[side*3:side*3+3])
            mx=int(np.argmax(own))
            winner=f["a"] if side==0 else f["b"]
            research[name]={
                "winner":winner,"p_winner":max(p,1-p),"p_a":p,
                "method":METHODS[mx],
                "p_exact_winner_method":float(own[mx]),
                "six_joint":{k:float(six[j]) for j,k in enumerate(CELLS)},
                "independent_method_head":"MultinomialFinish trained 2021 through Nov7 historical results",
                "research_only":True,
            }
            if abs(sum(research[name]["six_joint"].values())-1)>1e-8:
                raise ValueError("Bad research six probability")
        sparse=min(feat["a_prior_ufc_bouts"],feat["b_prior_ufc_bouts"])<3
        debut=min(feat["a_prior_ufc_bouts"],feat["b_prior_ufc_bouts"])==0
        unknown=(not identity[2*(i-1)]["source_name_matched"] or
                 not identity[2*(i-1)+1]["source_name_matched"])
        out.append({
            "fight_no":i,"a":f["a"],"b":f["b"],
            "source_a":a,"source_b":b,
            "identity_a":identity[2*(i-1)],
            "identity_b":identity[2*(i-1)+1],
            "a_prior_ufc_bouts":feat["a_prior_ufc_bouts"],
            "b_prior_ufc_bouts":feat["b_prior_ufc_bouts"],
            "a_stats_coverage":feat["a_stats_coverage"],
            "b_stats_coverage":feat["b_stats_coverage"],
            "source_alias_unverified":unknown,
            "research_uncertainty":"HIGH_UNVERIFIED_UFC_IDENTITY" if unknown else
              "HIGH_SPARSE_UFC_PRIOR" if sparse else "NORMAL_RESEARCH_SHADOW",
            "provisional_bout":bool(i==12),
            "original_official_stage_a_status":f["stage_a_posture"],
            "not_authorized_for_betting":True,
            "research_models":research,
        })
        if i==12 and not f["stage_a_posture"]=="PASS":
            raise ValueError("Provisional 0-UFC sample must remain PASS")
    if not all(r["not_authorized_for_betting"] for r in out):
        raise ValueError("Prospective shadow must be research-only")
    result={
        "schema":"WSHLX_UFC_QATAR_WINNER_V3_ACTUAL_FUTURE_PRE_EVENT_SHADOW",
        "event_date":DATE,"locked_at_utc":now.isoformat(),
        "event_first_fight_utc":START_UTC.isoformat(),
        "original_stage_a_sha256":sha(FINAL),
        "original_coherent_shadow_sha256":sha(COHERENT),
        "original_stage_a_frozen_at_utc":source["frozen_at_utc"],
        "source_archive_ufc_fight_stats_sha256":manifest["source_stats_sha256"],
        "historical_source_through":"2026-11-07",
        "nov14_UFC334_outcomes_used":False,
        "real_later_results_available_to_training":False,
        "all_input_fighter_history_strictly_before_event_date":True,
        "winner_v3_primary_prespecified":"logit_recent_57",
        "winner_v3_not_a_promoted_official_fourth_production_model":True,
        "other_winner_models_research_diagnostics_only":[h for h in HEADS if h!="logit_recent_57"],
        "conditional_method_model_training_decisive_bouts":len(y),
        "training_decisive_bouts":len(training),
        "new_feature_family":"Past-only significant striking accuracy, striking defence, recent 3/5 results, form and grappling",
        "source_form_date_join_audit":form_report,
        "original_stage_a_and_coherent_shadow_unchanged":True,
        "betting_odds_used":False,"fan_duel_stage_b_approval":False,
        "fighter_method_bets_approved":0,
        "research_prediction_bouts":len(out),
        "nov21_provisional_bout_explicit":True,
        "research_results_not_yet_observed":True,
        "fights":out,
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "STATUS":"PREFIGHT_WINNER_V3_SEPARATE_RESEARCH_SHADOW_LOCKED",
        "source_sha256":manifest["source_stats_sha256"],
        "lock_timestamp":now.isoformat(),
        "original_a_sha256":result["original_stage_a_sha256"],
        "coherent_sha256":result["original_coherent_shadow_sha256"],
        "primary_research_choices":[{"n":x["fight_no"],
            "winner":x["research_models"]["logit_recent_57"]["winner"],
            "method":x["research_models"]["logit_recent_57"]["method"],
            "p_win":round(x["research_models"]["logit_recent_57"]["p_winner"],4),
            "p_exact":round(x["research_models"]["logit_recent_57"]["p_exact_winner_method"],4),
            "uncertainty":x["research_uncertainty"]} for x in out],
    },sort_keys=True))

if __name__=="__main__":main()
