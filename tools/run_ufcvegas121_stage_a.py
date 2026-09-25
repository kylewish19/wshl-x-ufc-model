from __future__ import annotations

import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

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

rb = load_module("rebuild_v027_vegas121", ROOT / "tools/rebuild_v027.py")
stage331 = load_module("ufc331_stage_helpers", ROOT / "tools/run_ufc331_stage_a.py")

from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.models import fighter_double_chance, joint_outcome_probabilities
from wshlx_ufc.simulation import simulate_joint_outcomes
from wshlx_ufc.selection_policy import evidence_adjusted_confidence, method_bet_gate
from wshlx_ufc.locks import freeze_payload

EVENT_DATE = pd.Timestamp("2026-09-26", tz="UTC")
TRIALS = 10_000
BASE_SEED = 121926
RAW_DIR = ROOT / "data/raw/ufc331_2026-09-19"

CARD = [
    {"a":"Vanessa Demopoulos","b":"Yazmin Jauregui","weight_class":"Women's Strawweight","scheduled_seconds":900},
    {"a":"John Castaneda","b":"Alatengheili","weight_class":"Bantamweight","scheduled_seconds":900},
    {"a":"Montel Jackson","b":"Ricky Simon","weight_class":"Bantamweight","scheduled_seconds":900},
    {"a":"Elves Brener","b":"Josiah Harrell","weight_class":"Lightweight","scheduled_seconds":900},
    {"a":"Rodolfo Bellato","b":"Christian Edwards","weight_class":"Light Heavyweight","scheduled_seconds":900},
    {"a":"Rodolfo Vieira","b":"Robert Bryczek","weight_class":"Middleweight","scheduled_seconds":900},
    {"a":"Brady Hiestand","b":"Rinya Nakamura","weight_class":"Bantamweight","scheduled_seconds":900},
    {"a":"Melissa Amaya","b":"Tina Black","weight_class":"Women's Strawweight","scheduled_seconds":900},
    {"a":"Mahammadali Osmanli","b":"Ilimbek Akylbek","weight_class":"Bantamweight","scheduled_seconds":900},
    {"a":"Luis Hernandez","b":"Sedriques Dumas","weight_class":"Light Heavyweight","scheduled_seconds":900},
    {"a":"Norma Dumont","b":"Ailin Perez","weight_class":"Women's Bantamweight","scheduled_seconds":900},
    {"a":"Raul Rosas Jr.","b":"Raoni Barcelos","weight_class":"Bantamweight","scheduled_seconds":1500},
]

# Current public UFC profile facts used only when the Sept. 20 UFCStats mirror
# lacks static values for new/debuting athletes.
PROFILE_OVERRIDES = {
    "Melissa Amaya":{"age_years":31.0,"height_inches":64.5,"reach_inches":64.5},
    "Ilimbek Akylbek":{"age_years":23.0,"height_inches":67.0,"reach_inches":66.5},
    "Luis Hernandez":{"age_years":30.0,"height_inches":69.0,"reach_inches":73.5},
    "Josiah Harrell":{"age_years":27.0,"height_inches":67.5,"reach_inches":68.0},
    "Christian Edwards":{"age_years":27.0,"height_inches":77.0,"reach_inches":78.0},
}

# Name reconciliation between user/UFC display names and UFCStats storage.
HISTORY_ALIASES = {
    "alatengheili":"heilialateng",
    "raulrosasjr":"raulrosasjr",
}

def completed_history(fights, fight_stats):
    return stage331.completed_history(fights, fight_stats)

def method_dict(row):
    return {k:float(row[k]) for k in ("KO","SUB","DEC")}

def calibrate_method(base: dict[str,float], finish_offset: float, sub_offset: float):
    cal=MethodInterceptCalibrator(ridge=0.5)
    cal.finish_offset_=float(finish_offset)
    cal.sub_offset_=float(sub_offset)
    cal.is_fitted_=True
    p=cal.predict_proba(
        baseline_ko=[base["KO"]],baseline_sub=[base["SUB"]],baseline_dec=[base["DEC"]]
    ).iloc[0]
    return method_dict(p)

def timing_simulation(model, xrow, scheduled_seconds, seed):
    hazards=np.clip(model._hazards_for_one(xrow,scheduled_seconds),0.0,1.0)
    rng=np.random.default_rng(seed)
    n_bins=len(hazards)
    finish_bins=np.full(TRIALS,n_bins,dtype=int)
    for t in range(TRIALS):
        for i,h in enumerate(hazards):
            if rng.random()<h:
                finish_bins[t]=i
                break
    durations=np.where(
        finish_bins==n_bins,scheduled_seconds,
        np.minimum((finish_bins+1)*model.bin_seconds,scheduled_seconds)
    ).astype(float)
    finished=finish_bins<n_bins
    out={}
    thresholds=[0.5,1.5,2.5]+([3.5,4.5] if scheduled_seconds==1500 else [])
    for r in thresholds:
        sec=int(round(r*300))
        po=float(np.mean(durations>sec))
        out[f"OVER_{r}"]=po
        out[f"UNDER_{r}"]=1-po
    out["GTD_YES"]=float(np.mean(~finished)); out["GTD_NO"]=1-out["GTD_YES"]
    for rnd in range(2,scheduled_seconds//300+1):
        sec=(rnd-1)*300
        py=float(np.mean(durations>sec))
        out[f"ROUND_{rnd}_STARTS_YES"]=py
        out[f"ROUND_{rnd}_STARTS_NO"]=1-py
    return out

def main():
    # Load Sept. 20 mirror and retain every completed fight through UFC 331.
    old=rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF=pd.Timestamp("2026-09-20",tz="UTC")
    try:
        fights,stats,static=rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF=old
    fight_stats=rb.aggregate_fight_stats(fights,stats)
    history=completed_history(fights,fight_stats)

    # Alias merge without deleting source provenance.
    for target,source in HISTORY_ALIASES.items():
        if target==source: continue
        merged=list(history.get(target,[]))+list(history.get(source,[]))
        merged.sort(key=lambda x:pd.Timestamp(x["event_date"]))
        if merged: history[target]=merged
        if target not in static and source in static: static[target]=dict(static[source])

    ref_dir=ROOT/"artifacts/v027_reconstruction"
    new_dir=ROOT/"artifacts/v031_ufc331_full_stats"
    ref_winner=joblib.load(ref_dir/"winner_reconstruction.joblib")
    ref_method=joblib.load(ref_dir/"method_baseline_reconstruction.joblib")
    ref_resid=joblib.load(ref_dir/"method_residual_v027.joblib")
    ref_timing=joblib.load(ref_dir/"timing_reconstruction.joblib")
    new_winner=joblib.load(new_dir/"winner_v031.joblib")
    new_method=joblib.load(new_dir/"method_baseline_v031.joblib")
    new_resid=joblib.load(new_dir/"method_residual_v031.joblib")
    new_timing=joblib.load(new_dir/"timing_v031_30s.joblib")
    manifest=json.loads((new_dir/"manifest.json").read_text())
    fin_off=manifest["final_method_calibration"]["finish_offset"]
    sub_off=manifest["final_method_calibration"]["sub_given_finish_offset"]

    rows=[]
    for i,f in enumerate(CARD,1):
        a=rb.summarize_history(f["a"],history,static,EVENT_DATE)
        b=rb.summarize_history(f["b"],history,static,EVENT_DATE)
        for name,side in ((f["a"],a),(f["b"],b)):
            for k,v in PROFILE_OVERRIDES.get(name,{}).items():
                if not np.isfinite(side.get(k,np.nan)):
                    side[k]=float(v)

        wf=rb.winner_features(a,b,f["weight_class"],f["scheduled_seconds"])
        wx=pd.DataFrame([wf],columns=rb.WINNER_FEATURES)
        p_ref=float(ref_winner.predict_proba(wx)[0,0])
        p_new=float(new_winner.predict_proba(wx)[0,0])

        amf=rb.method_features(a,b,f["weight_class"],f["scheduled_seconds"])
        bmf=rb.method_features(b,a,f["weight_class"],f["scheduled_seconds"])
        amx=pd.DataFrame([amf],columns=rb.METHOD_BASE_FEATURES)
        bmx=pd.DataFrame([bmf],columns=rb.METHOD_BASE_FEATURES)
        ba=method_dict(new_method.predict_proba(amx).iloc[0])
        bb=method_dict(new_method.predict_proba(bmx).iloc[0])
        ca=calibrate_method(ba,fin_off,sub_off)
        cb=calibrate_method(bb,fin_off,sub_off)

        arx=pd.DataFrame([rb.residual_features(a,b)],columns=list(rb.V027_FEATURES))
        brx=pd.DataFrame([rb.residual_features(b,a)],columns=list(rb.V027_FEATURES))
        ra=method_dict(new_resid.predict_proba(
            arx,baseline_ko=[ba["KO"]],baseline_sub=[ba["SUB"]],baseline_dec=[ba["DEC"]]
        ).iloc[0])
        rbm=method_dict(new_resid.predict_proba(
            brx,baseline_ko=[bb["KO"]],baseline_sub=[bb["SUB"]],baseline_dec=[bb["DEC"]]
        ).iloc[0])

        jbase=joint_outcome_probabilities(p_new,ba,bb)
        jcal=joint_outcome_probabilities(p_new,ca,cb)
        jres=joint_outcome_probabilities(p_new,ra,rbm)
        sim_cal=simulate_joint_outcomes(jcal,trials=TRIALS,seed=BASE_SEED+i)

        tx=pd.Series({n:wf.get(n,np.nan) for n in new_timing.base_feature_names_},index=new_timing.base_feature_names_)
        timing={k:float(v) for k,v in new_timing.market_probabilities(tx,f["scheduled_seconds"]).items()}
        tsim=timing_simulation(new_timing,tx,f["scheduled_seconds"],BASE_SEED+100+i)

        tx_ref=pd.Series({n:wf.get(n,np.nan) for n in ref_timing.base_feature_names_},index=ref_timing.base_feature_names_)
        timing_ref={k:float(v) for k,v in ref_timing.market_probabilities(tx_ref,f["scheduled_seconds"]).items()}

        def finite_or_none(x):
            return None if not np.isfinite(x) else float(x)

        evidence={
            "a_prior_ufc_bouts":int(a["prior_bouts"]),
            "b_prior_ufc_bouts":int(b["prior_bouts"]),
            "a_days_since_last":finite_or_none(a["days_since_last"]),
            "b_days_since_last":finite_or_none(b["days_since_last"]),
            "a_age":finite_or_none(a["age_years"]),"b_age":finite_or_none(b["age_years"]),
            "a_reach":finite_or_none(a["reach_inches"]),"b_reach":finite_or_none(b["reach_inches"]),
        }
        sparse=min(evidence["a_prior_ufc_bouts"],evidence["b_prior_ufc_bouts"])<2
        raw_conf=max(p_new,1-p_new)*10
        display_conf=evidence_adjusted_confidence(raw_conf,evidence["a_prior_ufc_bouts"],evidence["b_prior_ufc_bouts"])

        rows.append({
            "fight_no":i,**f,
            "winner_reference_p_a":p_ref,"winner_v031_p_a":p_new,
            "winner_reference_pick":f["a"] if p_ref>=.5 else f["b"],
            "winner_v031_pick":f["a"] if p_new>=.5 else f["b"],
            "winner_model_disagreement":(p_ref>=.5)!=(p_new>=.5),
            "raw_probability_confidence_10":raw_conf,
            "evidence_adjusted_confidence_10":display_conf,
            "sparse_ufc_evidence":sparse,
            "method_if_a_wins_baseline":ba,"method_if_b_wins_baseline":bb,
            "method_if_a_wins_calibrated":ca,"method_if_b_wins_calibrated":cb,
            "method_if_a_wins_residual":ra,"method_if_b_wins_residual":rbm,
            "joint_baseline":jbase,"joint_calibrated":jcal,"joint_residual":jres,
            "double_chance_calibrated":fighter_double_chance(jcal),
            "joint_calibrated_sim_10000":sim_cal,
            "timing_v031_direct":timing,"timing_v031_sim_10000":tsim,
            "timing_reference_60s":timing_ref,
            "evidence_density":evidence,
        })

    payload={
        "event":"UFC Fight Night: Rosas Jr. vs Barcelos (UFC Vegas 121)",
        "event_date":"2026-09-26",
        "stage":"A_ODDS_BLIND_MODEL_RAW_V031_PROSPECTIVE_TEST",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "odds_used":False,
        "model_state":{
            "reference_winner":"v0.27 reconstruction reference",
            "prospective_winner":"v0.31 full-stat shadow",
            "method_baseline":"v0.31 baseline",
            "method_calibration":"v0.31 intercept calibration",
            "method_residual":"v0.31 residual comparison",
            "timing":"v0.31 30-second hazard shadow",
            "fighter_history_through":"2026-09-19",
            "clean_feedback_rows":76,
            "joint_simulations_per_fight":TRIALS,
            "timing_simulations_per_fight":TRIALS,
        },
        "fights":rows,
    }
    lock=freeze_payload(payload)
    out=ROOT/"data/locks/ufcvegas121_2026-09-26"
    out.mkdir(parents=True,exist_ok=True)
    (out/"stage_a_model_raw_v031.json").write_text(
        json.dumps({"sha256":lock.sha256,"payload":lock.payload},indent=2,sort_keys=True),encoding="utf-8"
    )

    summary=[]
    for r in rows:
        p=r["winner_v031_p_a"]
        summary.append({
            "fight_no":r["fight_no"],
            "fight":f'{r["a"]} vs {r["b"]}',
            "reference_pick":r["winner_reference_pick"],
            "v031_pick":r["winner_v031_pick"],
            "v031_probability":max(p,1-p),
            "model_disagreement":r["winner_model_disagreement"],
            "sparse":r["sparse_ufc_evidence"],
            "confidence_10":r["evidence_adjusted_confidence_10"],
            "top_joint_calibrated":max(r["joint_calibrated"],key=r["joint_calibrated"].get),
            "top_joint_probability":max(r["joint_calibrated"].values()),
            "gtd_yes":r["timing_v031_direct"]["GTD_YES"],
            "over_1_5":r["timing_v031_direct"].get("OVER_1.5"),
            "over_2_5":r["timing_v031_direct"].get("OVER_2.5"),
            "evidence":r["evidence_density"],
        })
    (out/"stage_a_model_summary_v031.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({"sha256":lock.sha256,"summary":summary},indent=2))


if __name__=="__main__":
    main()
