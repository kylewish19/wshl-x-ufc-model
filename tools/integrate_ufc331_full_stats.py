from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

rb = load_module("rebuild_v027_fullstats", ROOT / "tools/rebuild_v027.py")
stage = load_module("ufc331_stage_a_fullstats", ROOT / "tools/run_ufc331_stage_a.py")

from wshlx_ufc.grading import multiclass_brier
from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger, V027_FEATURES
from wshlx_ufc.models import ConditionalMethodModel, WinnerModel
from wshlx_ufc.timing import DiscreteTimeHazardModel

RAW_DIR = ROOT / "data/raw/ufc331_2026-09-19"
CLEAN_LEDGER = ROOT / "data/results/clean_ufc_76_2026-09-19.csv"
OUT = ROOT / "reports/v031_ufc331_full_stats"
ART = ROOT / "artifacts/v031_ufc331_full_stats"
SOURCE_COMMIT = "a3c5452eee2f5bb4f5eae4ce958f0f23dd8863d8"
EVENT_DATE = pd.Timestamp("2026-09-19", tz="UTC")
ASOF_PRE = pd.Timestamp("2026-09-19", tz="UTC")
ASOF_POST = pd.Timestamp("2026-09-20", tz="UTC")

STATIC_OVERRIDES = {
    "Michael Aswell Jr.": {"age_years": 25.0, "height_inches": 68.0, "reach_inches": 69.0},
    "Gable Steveson": {"height_inches": 71.0, "reach_inches": 74.0},
}

STATE_FIELDS = [
    "prior_bouts","win_rate","finish_win_rate","ko_win_rate","sub_win_rate",
    "ko_loss_rate","sub_loss_rate","kd_for_per15","kd_against_per15",
    "sig_landed_per_min","sig_absorbed_per_min","sig_accuracy","sig_defense",
    "ground_for_per15","ground_against_per15","td_landed_per15",
    "td_attempts_per15","td_accuracy","td_defense","sub_att_per15",
    "sub_att_against_per15","ctrl_for_per15","ctrl_against_per15",
    "r3_retention","recent5_win_rate","recent5_finish_rate",
    "recent5_sig_diff_per_min","recent5_kd_for_per15",
    "recent5_td_landed_per15","recent5_sub_att_per15","days_since_last",
    "age_years","height_inches","reach_inches",
]


def parse_clock(s: object) -> float:
    m = re.match(r"^(\d+):(\d{2})$", str(s).strip())
    return float(int(m.group(1))*60+int(m.group(2))) if m else 0.0


def parse_count(s: object) -> tuple[float, float]:
    m = re.match(r"^\s*(\d+)\s+of\s+(\d+)\s*$", str(s))
    return (float(m.group(1)), float(m.group(2))) if m else (0.0,0.0)


def normalize_event_col(df: pd.DataFrame) -> pd.DataFrame:
    out=df.copy()
    out["EVENT"]=out["EVENT"].astype(str).str.strip()
    out["BOUT"]=out["BOUT"].astype(str).str.strip()
    return out


def grade_methods(y, p: pd.DataFrame):
    classes=["KO","SUB","DEC"]
    arr=p[classes].to_numpy(float)
    y=np.asarray(y,dtype=str)
    pred=np.asarray(classes)[np.argmax(arr,axis=1)]
    return {
        "n":int(len(y)),
        "accuracy":float(np.mean(pred==y)),
        "brier":float(multiclass_brier(y,arr,classes)),
        "log_loss":float(log_loss(y,arr[:,[2,0,1]],labels=["DEC","KO","SUB"])),
        "calls":{c:int(np.sum(pred==c)) for c in classes},
        "actual":{c:int(np.sum(y==c)) for c in classes},
        "recall":{c:(float(np.mean(pred[y==c]==c)) if np.any(y==c) else None) for c in classes},
    }


def chronology_calibration(clean_oof: pd.DataFrame, ridge: float=0.5):
    ys=[]; bases=[]; cals=[]; folds=[]
    for test_date in sorted(clean_oof["event_date"].unique())[1:]:
        train=clean_oof.loc[clean_oof["event_date"]<test_date]
        test=clean_oof.loc[clean_oof["event_date"]==test_date]
        if len(train)<12:
            continue
        cal=MethodInterceptCalibrator(ridge=ridge).fit(
            actual_method=train["clean_actual_method"],
            baseline_ko=train["base_KO"],
            baseline_sub=train["base_SUB"],
            baseline_dec=train["base_DEC"],
        )
        pred=cal.predict_proba(
            baseline_ko=test["base_KO"],
            baseline_sub=test["base_SUB"],
            baseline_dec=test["base_DEC"],
        )
        ys.extend(test["clean_actual_method"].tolist())
        bases.append(test[["base_KO","base_SUB","base_DEC"]].rename(columns={
            "base_KO":"KO","base_SUB":"SUB","base_DEC":"DEC"
        }).reset_index(drop=True))
        cals.append(pred.reset_index(drop=True))
        folds.append({
            "test_date":test_date,
            "train_n":int(len(train)),
            "test_n":int(len(test)),
            "finish_offset":cal.finish_offset_,
            "sub_offset":cal.sub_offset_,
        })
    y=np.asarray(ys,dtype=str)
    return {
        "ridge":ridge,
        "baseline":grade_methods(y,pd.concat(bases,ignore_index=True)),
        "candidate":grade_methods(y,pd.concat(cals,ignore_index=True)),
        "folds":folds,
    }


def apply_static_overrides(name: str, summary: dict[str,float]):
    for k,v in STATIC_OVERRIDES.get(name,{}).items():
        summary[k]=float(v)


def build_history(fights, fight_stats):
    history=stage.completed_history(fights,fight_stats)
    for target, source in stage.HISTORY_ALIASES.items():
        merged=list(history.get(target,[]))+list(history.get(source,[]))
        merged.sort(key=lambda x: pd.Timestamp(x["event_date"]))
        history[target]=merged
    return history


def fighter_state_rows(fights, fight_stats, static):
    pre_fights=fights.loc[fights["event_date"]<EVENT_DATE].copy()
    post_fights=fights.loc[fights["event_date"]<=EVENT_DATE].copy()
    pre_history=build_history(pre_fights,fight_stats)
    post_history=build_history(post_fights,fight_stats)

    fighters=[]
    for f in stage.CARD:
        fighters.extend([f["a"],f["b"]])
    seen=[]
    for name in fighters:
        if name not in seen:
            seen.append(name)

    pre_rows=[]; post_rows=[]; delta_rows=[]
    for name in seen:
        pre=rb.summarize_history(name,pre_history,static,ASOF_PRE)
        post=rb.summarize_history(name,post_history,static,ASOF_POST)
        apply_static_overrides(name,pre)
        apply_static_overrides(name,post)
        pr={"fighter":name}; po={"fighter":name}; de={"fighter":name}
        for field in STATE_FIELDS:
            pv=float(pre.get(field,np.nan)); qv=float(post.get(field,np.nan))
            pr[field]=pv; po[field]=qv
            de[f"pre_{field}"]=pv; de[f"post_{field}"]=qv
            de[f"delta_{field}"]=qv-pv if np.isfinite(pv) and np.isfinite(qv) else np.nan
        pre_rows.append(pr); post_rows.append(po); delta_rows.append(de)
    return pd.DataFrame(pre_rows),pd.DataFrame(post_rows),pd.DataFrame(delta_rows)


def ufc331_fight_stat_summary():
    stats=normalize_event_col(pd.read_csv(RAW_DIR/"ufc331_fight_stats.csv"))
    results=normalize_event_col(pd.read_csv(RAW_DIR/"ufc331_fight_results.csv"))
    rows=[]
    for bout,g in stats.groupby("BOUT",sort=False):
        res=results.loc[results["BOUT"]==bout].iloc[0]
        a,b=[x.strip() for x in bout.split(" vs. ",1)]
        outcome=str(res["OUTCOME"]).strip().upper()
        winner=a if outcome=="W/L" else b
        agg={}
        for fighter,fg in g.groupby("FIGHTER",sort=False):
            vals={"kd":0.0,"sig_landed":0.0,"sig_attempted":0.0,"total_landed":0.0,
                  "total_attempted":0.0,"td_landed":0.0,"td_attempted":0.0,
                  "sub_att":0.0,"ctrl_seconds":0.0}
            for _,r in fg.iterrows():
                vals["kd"] += float(pd.to_numeric(r.get("KD"),errors="coerce") or 0.0)
                sl,sa=parse_count(r.get("SIG.STR.")); tl,ta=parse_count(r.get("TOTAL STR."))
                tdl,tda=parse_count(r.get("TD"))
                vals["sig_landed"]+=sl; vals["sig_attempted"]+=sa
                vals["total_landed"]+=tl; vals["total_attempted"]+=ta
                vals["td_landed"]+=tdl; vals["td_attempted"]+=tda
                sub=pd.to_numeric(r.get("SUB.ATT"),errors="coerce")
                vals["sub_att"] += 0.0 if pd.isna(sub) else float(sub)
                vals["ctrl_seconds"] += parse_clock(r.get("CTRL"))
            agg[str(fighter).strip()]=vals
        av=agg.get(a,{}); bv=agg.get(b,{})
        row={
            "bout":bout,"winner":winner,"method":str(res["METHOD"]).strip(),
            "round":int(res["ROUND"]),"time":str(res["TIME"]).strip(),
        }
        for prefix,vals in [("a",av),("b",bv)]:
            for k,v in vals.items():
                row[f"{prefix}_{k}"]=v
        for k in ("kd","sig_landed","sig_attempted","total_landed","total_attempted",
                  "td_landed","td_attempted","sub_att","ctrl_seconds"):
            row[f"diff_a_minus_b_{k}"]=float(av.get(k,0.0)-bv.get(k,0.0))
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    availability=json.loads((RAW_DIR/"availability.json").read_text())
    if not availability.get("full_card_stats_available"):
        raise RuntimeError("UFC 331 full stats are not complete")

    # Reuse the core parser against the Sept. 20 full-stat snapshot and include
    # all fights through Sept. 19. The causal snapshotter freezes each fight
    # before its own result/stats are added to fighter history.
    old_cutoff=rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF=pd.Timestamp("2026-09-20",tz="UTC")
    try:
        fights,stats,static=rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF=old_cutoff

    fight_stats=rb.aggregate_fight_stats(fights,stats)
    winner_df,method_df,timing_df=rb.enrich_and_snapshot(fights,fight_stats,static)

    clean=pd.read_csv(CLEAN_LEDGER)
    clean_rows=rb.find_clean_rows(clean,method_df)
    clean_oof=rb.add_clean_oof_baselines(clean_rows,method_df)

    winner_bench=rb.winner_clean_benchmark(clean,winner_df)
    residual_bench=rb.chronology_residual_benchmark(clean_oof)
    calibration_bench=chronology_calibration(clean_oof,ridge=0.5)

    ART.mkdir(parents=True,exist_ok=True)
    winner=WinnerModel(c=0.25).fit(winner_df[rb.WINNER_FEATURES],winner_df["winner_is_a"])
    method=ConditionalMethodModel(finish_c=0.10,sub_c=0.10).fit(
        method_df[rb.METHOD_BASE_FEATURES],method_df["method"]
    )
    residual=V027MethodResidualChallenger(ridge=10.0,clip_z=5.0).fit(
        clean_oof[list(V027_FEATURES)],
        actual_method=clean_oof["clean_actual_method"],
        baseline_ko=clean_oof["base_KO"],
        baseline_sub=clean_oof["base_SUB"],
        baseline_dec=clean_oof["base_DEC"],
    )
    calibrator=MethodInterceptCalibrator(ridge=0.5).fit(
        actual_method=clean_oof["clean_actual_method"],
        baseline_ko=clean_oof["base_KO"],
        baseline_sub=clean_oof["base_SUB"],
        baseline_dec=clean_oof["base_DEC"],
    )
    timing=DiscreteTimeHazardModel(bin_seconds=30,c=0.10).fit(
        timing_df[rb.TIMING_FEATURES],
        timing_df["duration_seconds"].to_numpy(float),
        timing_df["scheduled_seconds"].to_numpy(int),
        ((timing_df["method"]!="DEC") | (timing_df["duration_seconds"]<timing_df["scheduled_seconds"])).astype(int).to_numpy(),
    )

    paths={
        "winner":ART/"winner_v031.joblib",
        "method_baseline":ART/"method_baseline_v031.joblib",
        "method_residual":ART/"method_residual_v031.joblib",
        "timing_30s":ART/"timing_v031_30s.joblib",
    }
    joblib.dump(winner,paths["winner"])
    joblib.dump(method,paths["method_baseline"])
    joblib.dump(residual,paths["method_residual"])
    joblib.dump(timing,paths["timing_30s"])

    pre_state,post_state,deltas=fighter_state_rows(fights,fight_stats,static)
    fight_summary=ufc331_fight_stat_summary()

    OUT.mkdir(parents=True,exist_ok=True)
    pre_state.to_csv(OUT/"ufc331_fighter_state_pre_event.csv",index=False)
    post_state.to_csv(OUT/"ufc331_fighter_state_post_event.csv",index=False)
    deltas.to_csv(OUT/"ufc331_fighter_state_deltas.csv",index=False)
    fight_summary.to_csv(OUT/"ufc331_fight_stat_summary.csv",index=False)
    clean_oof.to_csv(OUT/"clean76_oof_method_inputs_fullstats.csv",index=False)

    import hashlib
    def sha(path):
        h=hashlib.sha256()
        with Path(path).open("rb") as f:
            for block in iter(lambda:f.read(1024*1024),b""):
                h.update(block)
        return h.hexdigest()

    manifest={
        "status":"V0.31_UFC331_FULL_STATS_SHADOW",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":{
            "upstream_repo":"Greco1899/scrape_ufc_stats",
            "upstream_commit":SOURCE_COMMIT,
            "full_card_stats_available":True,
            "unique_bouts":12,
            "fighter_round_stat_rows":52,
        },
        "population":{
            "training_rows":int(len(winner_df)),
            "clean_feedback_rows":int(len(clean_oof)),
            "latest_event_date":str(fights["event_date"].max()),
        },
        "causal_rule":{
            "ufc331_prefight_rows_use_ufc331_stats":False,
            "ufc331_stats_update_future_fighter_state":True,
            "same_day_fights_frozen_before_same_day_history_updates":True,
            "pantoja_ufc323_injury_stoppage_excluded_from_post_event_performance_history":True,
        },
        "benchmarks":{
            "winner_clean76":winner_bench,
            "method_residual_clean76":residual_bench,
            "method_intercept_calibration_clean76":calibration_bench,
        },
        "final_method_calibration":{
            "ridge":0.5,
            "finish_offset":calibrator.finish_offset_,
            "sub_given_finish_offset":calibrator.sub_offset_,
        },
        "artifact_sha256":{k:sha(v) for k,v in paths.items()},
        "promotion":{
            "authorized":False,
            "role":"shadow_candidate_and_current_data_state",
            "note":"The refreshed full-stat snapshot is the current data backbone. Model promotion still requires unseen-card validation.",
        },
    }
    (ART/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
    (OUT/"benchmark.json").write_text(json.dumps(manifest["benchmarks"],indent=2,sort_keys=True),encoding="utf-8")

    report=[
        "# v0.31 UFC 331 full-stat integration","",
        "- Full UFC 331 bouts with stats: **12/12**",
        "- Fighter-round stat rows: **52**",
        f"- Causal training rows through UFC 331: **{len(winner_df):,}**",
        f"- Clean graded feedback rows: **{len(clean_oof)}**",
        "- Timing bins: **30 seconds**",
        "",
        "## Causal handling","",
        "UFC 331 round stats do not alter UFC 331's own prefight features. They enter each fighter's history only after the fight, so they affect future cards.",
        "The prior Pantoja-Van injury stoppage remains excluded from Pantoja's performance-history aggregation while the official result remains preserved.",
        "",
        "## Winner benchmark","",
        f"- Accuracy: **{winner_bench['accuracy']:.4f}**",
        f"- Brier: **{winner_bench['brier']:.6f}**",
        f"- Log loss: **{winner_bench['log_loss']:.6f}**",
        "",
        "## Method calibration chronology","",
        f"- Baseline accuracy: **{calibration_bench['baseline']['accuracy']:.4f}**",
        f"- Calibrated accuracy: **{calibration_bench['candidate']['accuracy']:.4f}**",
        f"- Baseline Brier: **{calibration_bench['baseline']['brier']:.6f}**",
        f"- Calibrated Brier: **{calibration_bench['candidate']['brier']:.6f}**",
        "",
        "## Status","",
        "**Full UFC 331 stats integrated.** The data state is current through Sept. 19; model artifacts remain shadow until the next unseen UFC card.",
    ]
    (OUT/"BUILD_REPORT.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
