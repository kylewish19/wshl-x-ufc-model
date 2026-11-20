"""Use verified Nov7 UFCStats archive to train FUTURE-ONLY UFC shadow models.

Predictions for Nov7 had already been frozen/graded, so this script may NOW
use its 14 completed fights as post-event training rows. It MUST NOT rewrite
the old v0.27 champion, its Stage A, Stage B, or the 153 frozen grade ledger.

Two temporal layers:
  1. Preserve all 139 truly causal baseline OOF method rows unchanged.
  2. Append 14 *pre-event recorded* baseline conditional method probabilities
     evaluated after the fights, mapped to the actual known winner.
     Training a post-Nov7 calibrator with those observations is causal for
     future matchups, not evidence of Nov7 pre-fight wager performance.

November 8 source is pinned by full CSV hashes in availability.json.
No post-event fight stats can be applied to the *same date's* prefight
feature snapshots. rb.enrich_and_snapshot groups same-day bouts and only
updates fighter history after the date group is processed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:raise RuntimeError(f"Cannot load {path}")
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


rb=load_module("rebuild_v027_post_vegas124",ROOT/"tools/rebuild_v027.py")
from wshlx_ufc.models import WinnerModel, ConditionalMethodModel
from wshlx_ufc.timing import DiscreteTimeHazardModel
from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger,V027_FEATURES
from wshlx_ufc.nonperformance import activity_dates_from_raw

RAW=ROOT/"data/raw/ufcvegas124_2026-11-07"
AV=RAW/"availability.json"
PRIOR_OOF=ROOT/"reports/ufc333_2026-10-24/full_stats/clean139_causal_method_inputs.csv"
CLEAN=ROOT/"data/results/clean_ufc_153_2026-11-07.csv"
STAGE_A=ROOT/"data/locks/ufcvegas124_2026-11-07/stage_a_final_selection.json"
RAW_MODEL=ROOT/"data/locks/ufcvegas124_2026-11-07/stage_a_model_raw_three_view.json"
GRADED=ROOT/"data/results/ufcvegas124_2026-11-07_all_models_grading.json"
OUTPUT=ROOT/"reports/ufcvegas124_2026-11-07/full_stats"
ART=ROOT/"artifacts/ufcvegas124_post_event_shadow"
FIGHTERS=ROOT/"data/results/ufcvegas124_2026-11-07_fighter_full_stats.csv"
CUTOFF="2026-11-07"
SOURCE_COMMIT="c742842f29466758fedc3906dbad28d6d320a8da"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _date(s):
    return str(s)[:10]


def fixes(fights,stats,static):
    """Carry previously documented distinct aliases into the rebuilt backbone."""
    aliases=[
        ("Kai Kamaka","Kai Kamaka III",None),
        ("Zach Reese","Zachary Reese",None),
    ]
    for old,new,weight in aliases:
        key,nkey=rb.norm_name(old),rb.norm_name(new)
        for field in ("fighter_a","fighter_b","winner"):
            mask=fights[field].map(rb.norm_name).eq(key)
            fights.loc[mask,field]=new
        mask=stats["FIGHTER_KEY"].eq(key)
        stats.loc[mask,"FIGHTER"]=new
        stats.loc[mask,"FIGHTER_KEY"]=nkey
        if key in static and nkey not in static:
            static[nkey]=dict(static[key]);static[nkey]["name"]=new

    # Anthony Romero from the older cards is a DISTINCT person from
    # the 2026 UFC332 fighter. This policy is inherited from prior models.
    alias=rb.norm_name("Anthony Romero")
    old_name="Anthony Romero (The Genius)"
    for field in ("fighter_a","fighter_b","winner"):
        mask=fights[field].map(rb.norm_name).eq(alias)&fights["event"].ne("UFC 332: Silva vs. Wang")
        fights.loc[mask,field]=old_name
    mask=stats["FIGHTER_KEY"].eq(alias)&stats["EVENT_KEY"].ne("UFC 332: Silva vs. Wang")
    stats.loc[mask,"FIGHTER"]=old_name
    stats.loc[mask,"FIGHTER_KEY"]=rb.norm_name(old_name)
    return fights,stats,static


def validate_inputs():
    avail=json.loads(AV.read_text())
    lock=json.loads(STAGE_A.read_text())
    raw=json.loads(RAW_MODEL.read_text())
    grades=json.loads(GRADED.read_text())
    if avail["upstream_commit"]!=SOURCE_COMMIT or avail["full_card_stats_available"] is not True:
        raise RuntimeError("Pinned Nov8 full-stat evidence not verified")
    if (avail["unique_result_bouts"],avail["fighter_round_stat_rows"])!=(14,68):
        raise RuntimeError("Source 14 fights or 68 round rows missing")
    if avail["frozen_stage_a_sha256"]!=sha(STAGE_A):
        raise RuntimeError("Original Stage A modified after results")
    for file,info in avail["source_csv_files"].items():
        if sha(RAW/file)!=info["sha256"]:
            raise RuntimeError("Pinned full UFCStats source hash mismatch")
    # The RAW artifact intentionally has stage_a_frozen=False. Its bytes are
    # bound by SHA256 into the separately frozen Stage A final_selection file.
    if raw["stage_a_frozen"] is not False or raw["odds_used"] is not False:
        raise RuntimeError("Original raw three-view snapshot odds-blind status changed")
    if lock["stage_a_frozen"] is not True or lock["odds_used"] is not False:
        raise RuntimeError("Authoritative Stage A final lock no longer frozen")
    if lock["raw_model_sha256"] != sha(RAW_MODEL):
        raise RuntimeError("Authoritative frozen Stage A hash no longer matches raw three-view predictions")
    if not grades["all_fights"]==14 or grades["scoreboards"]["unified"]["winner_W"]!=11:
        raise RuntimeError("Grading audit missing")
    clean=pd.read_csv(CLEAN)
    if len(clean)!=153 or sum(clean["event_date"].astype(str)==CUTOFF)!=14:
        raise RuntimeError("Clean official 153 winner+method feedback ledger absent")
    oof=pd.read_csv(PRIOR_OOF)
    if len(oof)!=139 or oof["event_date"].astype(str).str[:10].ge(CUTOFF).any():
        raise RuntimeError("Pre-Nov7 method OOF baseline modified")
    return avail,lock,raw,grades,clean,oof


def method_additions(method_df,clean,lock,raw):
    delta=clean.loc[clean["event_date"].astype(str)==CUTOFF]
    if len(delta)!=14:raise RuntimeError("Expected 14 official Nov7 feedback rows")
    rows=rb.find_clean_rows(delta,method_df)
    if len(rows)!=14 or not rows["event_date"].astype(str).str.startswith(CUTOFF).all():
        raise RuntimeError("No unique match between 14 official outcomes and UFCStats method features")
    out=[]
    for _,row in rows.iterrows():
        side={rb.norm_name(row["fighter_a"]),rb.norm_name(row["fighter_b"])}
        match=next((f for f in lock["fights"] if
                    {rb.norm_name(f["a"]),rb.norm_name(f["b"])}==side),None)
        if match is None:raise RuntimeError(f"Unknown official bout identity: {row['bout']}")
        model_raw=raw["fights"][match["fight_no"]-1]
        if model_raw["fight_no"]!=match["fight_no"]:
            raise RuntimeError("Model/fight alignment changed")
        known_winner=rb.norm_name(row["winner"])
        if known_winner not in side:
            raise RuntimeError("Known actual winner isn't in bout")
        baseline=(model_raw["method_if_a_wins_baseline"]
                  if rb.norm_name(match["a"])==known_winner
                  else model_raw["method_if_b_wins_baseline"])
        if not np.isclose(sum(baseline.values()),1,atol=1e-8):
            raise RuntimeError("Pre-event conditional method baseline not normalized")
        record=row.to_dict()
        record["base_KO"]=float(baseline["KO"])
        record["base_SUB"]=float(baseline["SUB"])
        record["base_DEC"]=float(baseline["DEC"])
        record["causal_method_probability_origin"]="FROZEN_PRE_EVENT_BASELINE_CONDITIONAL_ON_POST_EVENT_KNOWN_WINNER"
        record["basis_locked_model_sha256"]=sha(RAW_MODEL)
        out.append(record)
    frame=pd.DataFrame(out).sort_values("fight_key")
    if frame["fight_key"].nunique()!=14:
        raise RuntimeError("Duplicated post-event conditional method training rows")
    return frame


def export_stats(fights,stats,aggregates):
    rows=[]
    nov=fights[fights["event_date"].astype(str).str.startswith(CUTOFF)]
    for f in nov.itertuples(index=False):
        for name,other in ((f.fighter_a,f.fighter_b),(f.fighter_b,f.fighter_a)):
            k=(rb.norm_text(f.event),rb.norm_text(f.bout),rb.norm_name(name))
            observed=aggregates.get(k)
            if observed is None:
                raise RuntimeError(f"Missing fighter stats for {f.bout}: {name}")
            row={
                "event_date":CUTOFF,"fight":f.bout,"fighter":name,"opponent":other,
                "actual_winner":f.winner,"actual_method":f.method,"finish_round":f.finish_round,
                "duration_seconds":f.duration_seconds,"ufcstats_fight_url":f.fight_url,
                "source_snapshot_sha":SOURCE_COMMIT,
                "post_event_data_training_only":True,
            }
            for col in ("sig_landed","sig_attempted","kd_for","ground_landed",
                        "ground_attempted","td_landed","td_attempted",
                        "sub_att","ctrl_seconds","r1_sig_landed","r3_sig_landed"):
                if col not in observed:raise RuntimeError(f"Missing stat measure {col}")
                row[col]=observed[col]
            rows.append(row)
    frame=pd.DataFrame(rows)
    if len(frame)!=28 or len(frame[["fight","fighter"]].drop_duplicates())!=28:
        raise RuntimeError("Expected 28 fighter-fight full-stat rows")
    return frame


def main():
    if OUTPUT.exists() or ART.exists() or FIGHTERS.exists():
        raise RuntimeError("Refusing to overwrite post-event shadow training artifact/manifest")
    avail,lock,raw,grades,clean,prior_oof=validate_inputs()
    rb.TRAINING_CUTOFF=pd.Timestamp("2026-11-08",tz="UTC")
    fights,stats,static=rb.load_fights(RAW)
    fights,stats,static=fixes(fights,stats,static)
    matches=fights[fights["event_date"].astype(str).str.startswith(CUTOFF)]
    if len(matches)!=14 or len(matches["bout"].unique())!=14:
        raise RuntimeError(f"Exact 14 Nov7 UFC fights missing from performance rebuild: {len(matches)}")
    if not (fights["event_date"]<rb.TRAINING_CUTOFF).all():
        raise RuntimeError("Training includes future event(s)")
    aggregates=rb.aggregate_fight_stats(fights,stats)
    observed=export_stats(fights,stats,aggregates)
    winner_df,method_df,timing_df=rb.enrich_and_snapshot(fights,aggregates,static)
    if not all(len(frame)==len(fights) for frame in (winner_df,method_df,timing_df)):
        raise RuntimeError("Training perspectives must be 1:1 with decided UFC bouts")
    if sum(winner_df["event_date"].astype(str).str.startswith(CUTOFF))!=14:
        raise RuntimeError("Round stats not present in causal training snapshots")
    # Feature matrix cannot contain actual post-fight result labels or today's
    # strike/takedown stats; these may only appear in historical updates for
    # future fight dates after Nov7.
    for group,cols in (
        (winner_df,rb.WINNER_FEATURES),
        (method_df,rb.METHOD_BASE_FEATURES),
        (timing_df,rb.TIMING_FEATURES),
    ):
        forbidden=({"winner","method","duration_seconds","fight_url",
                    "kd_for","sig_landed","sub_att","td_landed","ctrl_seconds"}&set(cols))
        if forbidden:raise RuntimeError(f"Post-event feature leakage columns: {sorted(forbidden)}")
        if not set(cols).issubset(group.columns):
            raise RuntimeError("Model feature schema changed or missing")
    current_method_additions=method_additions(method_df,clean,lock,raw)
    all_oof=pd.concat([prior_oof,current_method_additions[prior_oof.columns]],ignore_index=True)
    if len(all_oof)!=153 or sum(all_oof["event_date"].astype(str).str.startswith(CUTOFF))!=14:
        raise RuntimeError("Causal method feedback 139+14 incomplete")
    if not all_oof[["base_KO","base_SUB","base_DEC"]].notna().all().all():
        raise RuntimeError("Missing pre-event method probabilities in feedback")
    if not np.allclose(all_oof[["base_KO","base_SUB","base_DEC"]].sum(axis=1),1,atol=1e-7):
        raise RuntimeError("Method OOF baselines do not sum to one")
    if current_method_additions["clean_actual_method"].value_counts().to_dict()!={"DEC":7,"KO":6,"SUB":1}:
        raise RuntimeError("Post-event submission/finish counts differ from official grades")

    # Date-group snapshots ensure new Nov7 postfight stats cannot leak into
    # Nov7 evaluation; fitted models are strictly DEPLOYABLE AFTER Nov7.
    winner=WinnerModel(c=0.25).fit(winner_df[list(rb.WINNER_FEATURES)],winner_df["winner_is_a"])
    baseline=ConditionalMethodModel(finish_c=0.1,sub_c=0.1).fit(
        method_df[list(rb.METHOD_BASE_FEATURES)],method_df["method"]
    )
    timing=DiscreteTimeHazardModel(bin_seconds=30,c=0.10).fit(
        timing_df[list(rb.TIMING_FEATURES)],
        timing_df["duration_seconds"].to_numpy(float),
        timing_df["scheduled_seconds"].to_numpy(int),
        ((timing_df["method"]!="DEC")|
         (timing_df["duration_seconds"]<timing_df["scheduled_seconds"])).astype(int).to_numpy(),
    )
    calibrator=MethodInterceptCalibrator(ridge=0.5).fit(
        actual_method=all_oof["clean_actual_method"],
        baseline_ko=all_oof["base_KO"],
        baseline_sub=all_oof["base_SUB"],
        baseline_dec=all_oof["base_DEC"],
    )
    residual=V027MethodResidualChallenger(ridge=10.0,clip_z=5.0).fit(
        all_oof[list(V027_FEATURES)],
        actual_method=all_oof["clean_actual_method"],
        baseline_ko=all_oof["base_KO"],
        baseline_sub=all_oof["base_SUB"],
        baseline_dec=all_oof["base_DEC"],
    )

    OUTPUT.mkdir(parents=True,exist_ok=True)
    ART.mkdir(parents=True,exist_ok=True)
    observed.to_csv(FIGHTERS,index=False)
    current_method_additions.to_csv(OUTPUT/"nov7_14_frozen_pre_event_baseline_method_feedback.csv",index=False)
    all_oof.to_csv(OUTPUT/"clean153_causal_method_inputs.csv",index=False)
    method_df[method_df["event_date"].astype(str).str.startswith(CUTOFF)].to_csv(
        OUTPUT/"nov7_prefight_method_features_separated_from_result_targets.csv",index=False
    )
    saved={}
    for name,obj in (
        ("winner",winner),("method_baseline",baseline),
        ("method_calibrator",calibrator),("method_residual",residual),
        ("timing_30s",timing),
    ):
        filename=ART/f"{name}_shadow_through_2026-11-07.joblib"
        joblib.dump(obj,filename,compress=3)
        saved[name]={"path":str(filename.relative_to(ROOT)),"sha256":sha(filename)}
    activity=activity_dates_from_raw(RAW)
    activity_file=ART/"activity_last_dates.json"
    activity_file.write_text(json.dumps({k:v.isoformat() for k,v in sorted(activity.items())},
                                        indent=2,sort_keys=True)+"\n")

    report={
        "status":"NOV7_FULL_STATS_INTEGRATED_FOR_POST_EVENT_FUTURE_ONLY_SHADOW_TRAINING",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "event_date":CUTOFF,"upstream_commit":SOURCE_COMMIT,
        "source_kind":"third_party_pinned_ufcstats_scrape",
        "source_availability_sha256":sha(AV),
        "frozen_stage_a_sha256":sha(STAGE_A),
        "frozen_raw_model_sha256":sha(RAW_MODEL),
        "graded_14_sha256":sha(GRADED),
        "clean_153_sha256":sha(CLEAN),
        "original_clean_139_oof_sha256":sha(PRIOR_OOF),
        "clean139_oof_untouched":True,
        "new_causal_frozen_pred_rows":14,
        "new_full_stat_fighter_rows":len(observed),
        "new_full_stat_round_rows":avail["fighter_round_stat_rows"],
        "training_dates":"All historical completed UFC bouts with event_date < 2026-11-08",
        "post_event_training_bouts":len(fights),
        "post_event_last_date":str(fights["event_date"].max()),
        "training_winner_rows":len(winner_df),
        "training_method_rows":len(method_df),
        "training_timing_rows":len(timing_df),
        "causal_method_clean_feedback_rows":len(all_oof),
        "method_training_class_counts":method_df["method"].value_counts().astype(int).to_dict(),
        "post_event_actual_method_counts":current_method_additions["clean_actual_method"].value_counts().astype(int).to_dict(),
        "model_paths":saved,
        "governance":{
            "model_role":"FUTURE_ONLY_CHALLENGER_SHADOW",
            "original_14_predictions_unmodified":True,
            "legacy_153_winner_method_grade_ledger_unmodified":True,
            "official_champion_v027_unmodified":True,
            "historical_conditional_stale_model_not_automatically_promoted":True,
            "pricing_gates_not_relaxed":True,
            "model_promotion":False,
            "method_recalibration_refit_after_event_only":True,
            "new_model_predictions_not_back_scored_as_Nov7_frozen_picks":True,
            "future_chronological_backtesting_required":True,
            "data_stats_for_Nov7_are_postfight_only":True,
        },
    }
    (OUTPUT/"integration_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    (ART/"manifest.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "status":report["status"],"source_bouts":14,
        "fighter_stat_rows":len(observed),"historical_training_bouts":len(fights),
        "original_feedback":139,"new_feedback":14,
        "future_only":True,"promoted":False,
        "artifacts":saved,
    },indent=2))


if __name__=="__main__":
    main()
