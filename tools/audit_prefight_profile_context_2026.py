"""Benchmark NEW sourced pre-fight context against the unchanged 38-feature
winner+method research design, on identical chronological historical bouts.

Source URL and fixed SHA through the repository's pinned 2026-11-08
UFCStats-compatible secondary archive. Current weight class is an announced
pre-fight attribute; historical same-class counts and layoff use strictly
PRIOR bout dates. DOB is stable; historical height/reach availability/revisions
are NOT independently established. Thus these are retrospective experiments.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import csv,json,math
import numpy as np

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.prefight_profile_context import metadata_for_features,checked_file,PROFILE_SOURCE,RESULT_SOURCE
from research_exact_outcomes_phase2 import (
    DATES,OUT,fit_train,probabilities,scored,aggregate,event_bootstrap,prepared,sha,
)

ROOT=Path(__file__).resolve().parents[1]
OUTDIR=ROOT/"reports/model_health/2026-11-19_new_prefight_context"
BASE=list(range(38))
# Eight observed or explicitly flagged new pre-fight metadata quantities.
# All unobserved measures have paired missingness flags: never fake an
# unobserved regional record or direct get-up statistic.
CONTEXT=[41,42,43,47,48]
AGE_CONTEXT=CONTEXT+[38,44]
PHYSICAL=AGE_CONTEXT+[39,40,45,46,49]
VARIANTS={
 "base_38":BASE,
 "prior_weightclass_and_layoff":BASE+CONTEXT,
 "prior_weightclass_layoff_and_age":BASE+AGE_CONTEXT,
 "age_height_reach_context":BASE+PHYSICAL,
}

def supplemental(f,records):
    context=records.get(f["bout_id"])
    pair=[]
    for side in ("a","b"):
        m=context.get(side) if context else None
        if m is None:
            pair.append(np.array([0.,0.,0.,0.,0.,0.,1.,1.,1.,1.,1.,0.]))
            continue
        age=m.get("age_on_event_day")
        height=m.get("height_inches")
        reach=m.get("reach_inches")
        same=m.get("prior_same_weightclass_bouts")
        days=m.get("days_since_last_ufc_bout")
        recent=m.get("prior_ufc_bouts_last365")
        extra=[
            (float(age)-30)/15 if age is not None else 0.,
            (float(height)-70)/15 if height is not None else 0.,
            (float(reach)-72)/18 if reach is not None else 0.,
            math.log1p(float(same)) if same is not None else 0.,
            math.log1p(float(days))/7 if days is not None else 0.,
            math.log1p(float(recent)) if recent is not None else 0.,
            float(age is None),float(height is None),float(reach is None),
            float(same is None),float(days is None),
            float(bool(m.get("profile_found"))),
        ]
        if any(not math.isfinite(z) for z in extra):raise ValueError("Nonfinite source metadata")
        pair.append(np.asarray(extra,float))
    return pair

def audit_context(fights,metadata,audit):
    year_rows={}
    for year in ("2021","2022","2023","2024","2025","2026"):
        feats=[f for f in fights if f["event_date"].startswith(year)]
        n=len(feats)
        if n==0:continue
        joined=sum(f["bout_id"] in metadata for f in feats)
        ages=sum(m.get("age_on_event_day") is not None for f in feats
                 if (m:=metadata.get(f["bout_id"],{}).get("a",{})))
        both_ages=sum(all(metadata[f["bout_id"]][side]["age_on_event_day"] is not None
                          for side in ("a","b")) for f in feats if f["bout_id"] in metadata)
        both_reach=sum(all(metadata[f["bout_id"]][side]["reach_inches"] is not None
                           for side in ("a","b")) for f in feats if f["bout_id"] in metadata)
        both_layoff=sum(all(metadata[f["bout_id"]][side]["days_since_last_ufc_bout"] is not None
                            for side in ("a","b")) for f in feats if f["bout_id"] in metadata)
        both_samewc=sum(all(metadata[f["bout_id"]][side]["prior_same_weightclass_bouts"] is not None
                            for side in ("a","b")) for f in feats if f["bout_id"] in metadata)
        year_rows[year]={
            "bouts":n,"metadata_bout_joins":joined,
            "both_fighters_have_age":both_ages,
            "both_fighters_have_reach":both_reach,
            "both_fighters_have_prior_UFC_layoff":both_layoff,
            "both_fighters_have_same_weightclass_bouts_count":both_samewc,
        }
    return {**audit,"by_year":year_rows,
            "new_fields_use_pre_event_bout_history_and_static_profile_snapshot":True,
            "2026_profile_reach_or_height_may_not_equal_historical_available_value":True,
            "verified_regional_or_getups_added":False,
            "neither_current_career_winrate_nor_fighter_now_weight_used":True}

def run():
    features,labels,manifest=load_matrix()
    context,origin=metadata_for_features(features)
    observed=[f for f in features if "2021-01-01"<=f["event_date"]<"2026-11-14"]
    audit=audit_context(observed,context,origin)
    baseline=prepared(features,labels)
    enriched=[]
    for f,l,a,b,y in baseline:
        ea,eb=supplemental(f,context)
        enriched.append((f,l,np.r_[a,ea],np.r_[b,eb],y))
    if len(enriched)!=3015 or any(len(x[2])!=50 for x in enriched):
        raise ValueError("Metadata row count/dimensionality drift")
    peryear={};all_rows=[]
    for year,begin,end,expected in DATES:
        target=[x for x in enriched if begin<=x[0]["event_date"]<end]
        if len(target)!=expected:raise ValueError("Evaluation population changed")
        by_model=defaultdict(list)
        for name,columns in VARIANTS.items():
            fit=fit_train(enriched,begin,columns)
            for f,l,a,b,_ in target:
                p,ff,dd=probabilities(fit,a,b,columns)
                for mode,q in (("factorized6",ff),("direct6",dd)):
                    p_mode=p if mode=="factorized6" else float(dd[:3].sum())
                    scored_row=scored(f,l,p_mode,q,mode,name)
                    by_model[mode+"__"+name].append(scored_row)
                    all_rows.append(scored_row)
        if len(by_model)!=8:raise ValueError("Missing a prespecified model")
        peryear[year]={
            "evaluated":len(target),
            "summary":{name:aggregate(rows) for name,rows in by_model.items()},
            "paired_improvement_over_38":{mode:{
                name:{
                    "exact":event_bootstrap(by_model[mode+"__"+name],by_model[mode+"__base_38"],"exact"),
                    "six_log_loss":event_bootstrap(by_model[mode+"__"+name],by_model[mode+"__base_38"],"six_log_loss"),
                } for name in VARIANTS if name!="base_38"
            } for mode in ("factorized6","direct6")},
        }
    OUTDIR.mkdir(parents=True,exist_ok=True)
    forecasts=OUTDIR/"historical_context_2024_2026_forecasts.csv"
    with forecasts.open("w",newline="",encoding="utf-8") as h:
        w=csv.DictWriter(h,fieldnames=list(all_rows[0]));w.writeheader();w.writerows(all_rows)
    report={
        "schema":"WSHLX_SOURCED_FIGHT_CONTEXT_ABLATION_2026_11_19",
        "model_source_sha256":manifest["source_stats_sha256"],
        "original_ufc_qatar_nov21_pred_lock_untouched":True,
        "research_only_no_fanduel_wagers_or_model_promotion":True,
        "profile_archive_sha256":sha(checked_file(PROFILE_SOURCE)),
        "historical_bout_results_sha256":sha(checked_file(RESULT_SOURCE)),
        "age_from_DOB_with_current_2026_snapshot":True,
        "not_immutable_historically_dated_height_reach":True,
        "pre_event_only_same_day_not_updated":True,
        "sources":audit,
        "models":VARIANTS,
        "yearly":peryear,
        "probability_file_sha256":sha(forecasts),
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    dest=OUTDIR/"sourced_context_results.json"
    dest.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
       "metadata_join":audit["feature_bouts_joined"],
       "metadata_missing":audit["feature_bouts_unmatched"],
       "by_year":{y:{m:{k:d[k] for k in ("n","winner_hits","exact_hits","six_log_loss")}
                     for m,d in f["summary"].items() if "factorized" in m}
                  for y,f in peryear.items()},
       "context_coverage":audit["by_year"],
       "status":"RESEARCH_RESULTS_ONLY_NO_PROMOTION"
    },sort_keys=True,allow_nan=False))

if __name__=="__main__":run()
