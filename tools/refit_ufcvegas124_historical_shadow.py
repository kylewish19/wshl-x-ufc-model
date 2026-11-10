"""Rebuild the historical-conditional UFC winner shadow AFTER Nov7 full stats.

The historical shadow was fitted only through 2026-10-17 on Nov7 fight day.
This version IS NOT Nov7's historical pick engine. It uses Nov7 post-event
fighter statistics solely to forecast events after Nov7. It does not
change champion v0.27 or promote this research artifact automatically.

Historical full-source fighter identity policy:
  Anthony Romero (UFC332 prospect) and previously competing same-name
  fighter must remain DISTINCT; the old fighter is tagged and has no
  borrowed birthdate/physical measurements from the current fighter.
  Kai Kamaka & Kai Kamaka III and Zach Reese & Zachary Reese are the
  same fighters with earlier aliases, and are unified in source rows.

The internal chronological test is a development backtest. It cannot
count as genuine pre-event Nov7 prospective prediction.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd

from wshlx_ufc.historical_data import build_prefight_perspective_rows
from wshlx_ufc.historical_model import LEAKAGE_COLUMNS,fit_historical_winner_model

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/raw/ufcvegas124_2026-11-07"
INTEGRATION=ROOT/"reports/ufcvegas124_2026-11-07/full_stats/integration_report.json"
SOURCE=RAW/"availability.json"
REPORT=ROOT/"reports/ufcvegas124_2026-11-07/historical_shadow_refit.json"
ARTDIR=ROOT/"artifacts/ufcvegas124_post_event_historical"
ART=ARTDIR/"historical_conditional_shadow_trained_through_2026-11-07.joblib"
REQUIRED_SOURCE_SHA="c742842f29466758fedc3906dbad28d6d320a8da"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def clean_name(n,event):
    s=str(n).strip()
    if s=="Anthony Romero" and event!="UFC 332: Silva vs. Wang":
        return "Anthony Romero (The Genius)"
    if s=="Kai Kamaka":
        return "Kai Kamaka III"
    if s=="Zach Reese":
        return "Zachary Reese"
    return s


def map_bout(label,event):
    sides=re.split(r"\s+vs\.?\s+",str(label).strip(),maxsplit=1,flags=re.I)
    if len(sides)!=2:
        raise ValueError(f"Cannot parse fighter pair {label!r}")
    return " vs. ".join(clean_name(s,event) for s in sides)


def source_frames():
    ev=pd.read_csv(RAW/"ufc_event_details.csv")
    results=pd.read_csv(RAW/"ufc_fight_results.csv")
    stats=pd.read_csv(RAW/"ufc_fight_stats.csv")
    fighters=pd.read_csv(RAW/"ufc_fighter_tott.csv")
    # Replace text aliases in-memory only; the pinned raw source bytes
    # are preserved exactly with their upstream SHA manifest.
    results["EVENT"]=results["EVENT"].astype(str).str.strip()
    stats["EVENT"]=stats["EVENT"].astype(str).str.strip()
    results["BOUT"]=[
        map_bout(label,event) for label,event in zip(results["BOUT"],results["EVENT"])
    ]
    stats["BOUT"]=[
        map_bout(label,event) for label,event in zip(stats["BOUT"],stats["EVENT"])
    ]
    stats["FIGHTER"]=[
        clean_name(n,e) for n,e in zip(stats["FIGHTER"],stats["EVENT"])
    ]
    fighters["FIGHTER"]=fighters["FIGHTER"].replace({
        "Kai Kamaka":"Kai Kamaka III","Zach Reese":"Zachary Reese"
    })
    if (fighters["FIGHTER"]=="Anthony Romero (The Genius)").any():
        # We deliberately do not copy today's Anthony Romero physical traits
        # into the older fighter's training rows.
        fighters=fighters[fighters["FIGHTER"]!="Anthony Romero (The Genius)"]
    return ev,results,stats,fighters


def main():
    if REPORT.exists() or ART.exists():
        raise RuntimeError("Historical shadow refit artifact already exists; do not overwrite")
    audit=json.loads(SOURCE.read_text())
    integration=json.loads(INTEGRATION.read_text())
    if (audit["upstream_commit"]!=REQUIRED_SOURCE_SHA or
        not audit["full_card_stats_available"] or audit["fighter_round_stat_rows"]!=68):
        raise RuntimeError("Nov7 full stat evidence missing, historical fit blocked")
    if integration["post_event_training_bouts"]<8000 or integration["new_causal_frozen_pred_rows"]!=14:
        raise RuntimeError("Full baseline pre-event integration missing")
    event,result,stats,profiles=source_frames()
    frame=build_prefight_perspective_rows(event,result,stats,profiles)
    if len(frame)<14000:
        raise RuntimeError(f"Missing historical mirrored fighter perspectives: {len(frame)}")
    frame["date"]=pd.to_datetime(frame["date"],utc=True)
    nov=frame[frame["date"].dt.strftime("%Y-%m-%d")=="2026-11-07"]
    if len(nov)!=28 or nov["fight_id"].nunique()!=14:
        raise RuntimeError(f"Expected 28 Nov7 mirrored perspectives across 14 fights, got {len(nov)}")
    if frame["date"].max()>pd.Timestamp("2026-11-07T23:59:59Z"):
        raise RuntimeError("Historical fit contains future-dated fights")
    if not frame.groupby("fight_id")["win"].agg(["count","sum"]).eq([2,1]).all(axis=None):
        raise RuntimeError("Historical model perspectives are not one fighter W / other L")
    # Ensure observed fight output (win, outcome, method, round, etc.) never
    # enters the learnable historical feature vector.
    bundle,split_metrics=fit_historical_winner_model(frame)
    forbidden=set(bundle.feature_columns)&LEAKAGE_COLUMNS
    forbidden|={x for x in bundle.feature_columns if
               x.lower().startswith(("fight_","target_","post_")) or "method" in x.lower()}
    if forbidden:
        raise RuntimeError(f"Post-fight information in model predictors: {sorted(forbidden)}")
    if str(pd.Timestamp(bundle.history_end).date())!="2026-11-07":
        raise RuntimeError("Historical shadow not fitted through Nov7")
    ARTDIR.mkdir(parents=True,exist_ok=True)
    joblib.dump(bundle,ART,compress=3)
    report={
        "status":"HISTORICAL_CONDITIONAL_MODEL_RETRAINED_WITH_NOV7_POSTEVENT_STATS_FUTURE_ONLY",
        "trained_through":"2026-11-07",
        "eligible_for_predictions_starting":"2026-11-08",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "raw_ufcstats_archive_commit":REQUIRED_SOURCE_SHA,
        "raw_ufcstats_availability_sha256":sha(SOURCE),
        "full_stats_integration_report_sha256":sha(INTEGRATION),
        "training_mirrored_fighter_perspectives":len(frame),
        "training_completed_fights":frame["fight_id"].nunique(),
        "nov7_perspectives":len(nov),
        "nov7_fights":nov["fight_id"].nunique(),
        "training_min_date":str(frame["date"].min().date()),
        "training_max_date":str(frame["date"].max().date()),
        "identity_reconciliation":{
            "Anthony Romero":"Two distinct fighters, earlier name disambiguated; no borrowed physical traits",
            "Kai Kamaka III":"Earlier Kai Kamaka alias unified into same historical state",
            "Zachary Reese":"Earlier Zach Reese alias unified into same historical state",
            "source_files_mutated":False,
        },
        "model":{
            "source":"wshlx_ufc.historical_model.fit_historical_winner_model",
            "fit_artifact_sha256":sha(ART),
            "fit_artifact_path":str(ART.relative_to(ROOT)),
            "feature_columns":bundle.feature_columns,
            "feature_count":len(bundle.feature_columns),
            "trained_on_frozen_Nov7_predictions":False,
            "uses_all_completed_Nov7_postfight_results_for_future_training":True,
            "calibration_temperature":float(bundle.calibration_temperature),
        },
        "time_split_evaluation":split_metrics,
        "time_split_role":"POST_EVENT_RETROSPECTIVE_RESEARCH_DEVELOPMENT; not scored as Nov7 pre-fight official selections",
        "governance":{
            "future_only_shadow":True,
            "champion_v027_unchanged":True,
            "original_historical_nov7_shadow_fitted_through_2026_10_17_unchanged":True,
            "no_retroactive_backdating_of_Nov7_predictions":True,
            "promotion_approved":False,
            "minimum_300_genuinely_prospective_fight_validation_gate_remains":True,
            "betting_price_gates_not_relaxed":True,
        }
    }
    REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:report[k] for k in ("status","training_mirrored_fighter_perspectives",
                                            "training_completed_fights","nov7_perspectives",
                                            "training_max_date","time_split_evaluation","governance")},indent=2))


if __name__=="__main__":
    main()
