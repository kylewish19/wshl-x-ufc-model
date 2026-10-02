from __future__ import annotations

import importlib.util
import json
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

rb = load_module("rebuild_v027_ufc332", ROOT / "tools/rebuild_v027.py")
stage331 = load_module("ufc331_stage_helpers_ufc332", ROOT / "tools/run_ufc331_stage_a.py")

from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.models import fighter_double_chance, joint_outcome_probabilities
from wshlx_ufc.simulation import simulate_joint_outcomes
from wshlx_ufc.selection_policy import evidence_adjusted_confidence
from wshlx_ufc.locks import freeze_payload
from wshlx_ufc.nonperformance import activity_dates_from_raw, apply_activity_recency

EVENT_DATE = pd.Timestamp("2026-10-03", tz="UTC")
TRIALS = 10_000
BASE_SEED = 3321003
RAW_DIR = ROOT / "data/raw/ufcvegas121_2026-09-26"

CARD = [
    {"a":"Court McGee","b":"Eric Nolan","weight_class":"Welterweight","scheduled_seconds":900},
    {"a":"Marvin Vettori","b":"Ismail Naurdiev","weight_class":"Middleweight","scheduled_seconds":900},
    {"a":"Rafael dos Anjos","b":"Alexander Hernandez","weight_class":"Lightweight","scheduled_seconds":900},
    {"a":"Jacobe Smith","b":"Bruce Whitehead","weight_class":"Welterweight","scheduled_seconds":900},
    {"a":"Johnny Walker","b":"Mick Parkin","weight_class":"Heavyweight","scheduled_seconds":900},
    {"a":"Anthony Wint","b":"Lucas Armand","weight_class":"Heavyweight","scheduled_seconds":900},
    {"a":"Marcus McGhee","b":"Anthony Romero","weight_class":"Featherweight","scheduled_seconds":900},
    {"a":"Damian Pinas","b":"Andrey Pulyaev","weight_class":"Middleweight","scheduled_seconds":900},
    {"a":"Imanol Rodriguez","b":"Alden Coria","weight_class":"Flyweight","scheduled_seconds":900},
    {"a":"Ateba Gautier","b":"Roman Kopylov","weight_class":"Middleweight","scheduled_seconds":900},
    {"a":"Roberto Soldic","b":"Khaos Williams","weight_class":"Welterweight","scheduled_seconds":900},
    {"a":"King Green","b":"Esteban Ribovics","weight_class":"Lightweight","scheduled_seconds":900},
    {"a":"Natalia Silva","b":"Wang Cong","weight_class":"Women's Flyweight","scheduled_seconds":1500},
    {"a":"Deiveson Figueiredo","b":"Payton Talbott","weight_class":"Bantamweight","scheduled_seconds":900},
]

# Current public UFC profile facts used only when the Sept. 27 UFCStats mirror
# lacks static values for new/debuting athletes.
PROFILE_OVERRIDES = {
    "Eric Nolan":{"age_years":29.0,"height_inches":72.0,"reach_inches":73.0},
    "Bruce Whitehead":{"age_years":29.0,"height_inches":71.0},
    "Anthony Wint":{"age_years":31.0,"height_inches":71.0,"reach_inches":78.0},
    "Lucas Armand":{"age_years":30.0},
    # UFC has two Anthony Romero profile records; force the Oct. 3 debutant's
    # known current-profile statics and blank an unverified reach so an older
    # same-name profile cannot leak into this fight.
    "Anthony Romero":{"age_years":29.0,"height_inches":65.0,"reach_inches":float("nan")},
    "Damian Pinas":{"age_years":24.0,"height_inches":73.0,"reach_inches":79.5},
    "Andrey Pulyaev":{"age_years":29.0,"height_inches":76.0,"reach_inches":78.5},
    "Imanol Rodriguez":{"age_years":26.0,"height_inches":64.0,"reach_inches":64.5},
    "Alden Coria":{"age_years":28.0,"height_inches":68.0,"reach_inches":67.0},
    "Roberto Soldic":{"age_years":31.0,"height_inches":70.5,"reach_inches":73.0},
}

HISTORY_ALIASES = {
    # Current UFC branding/name variants.
    "kinggreen":"bobbygreen",
    "robertosoldic":"robertosoldic",
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
    # Sept. 27 full-stat mirror with completed fights through Sept. 26.
    old=rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF=pd.Timestamp("2026-09-27",tz="UTC")
    try:
        fights,stats,static=rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF=old
    fight_stats=rb.aggregate_fight_stats(fights,stats)
    history=completed_history(fights,fight_stats)
    activity_dates=activity_dates_from_raw(RAW_DIR)

    for target,source in HISTORY_ALIASES.items():
        if target==source: continue
        merged=list(history.get(target,[]))+list(history.get(source,[]))
        merged.sort(key=lambda x:pd.Timestamp(x["event_date"]))
        if merged: history[target]=merged
        if target not in static and source in static: static[target]=dict(static[source])

    ref_dir=ROOT/"artifacts/v027_reconstruction"
    new_dir=ROOT/"artifacts/v032_ufcvegas121_full_stats"
    ref_winner=joblib.load(ref_dir/"winner_reconstruction.joblib")
    new_winner=joblib.load(new_dir/"winner_v032.joblib")
    new_method=joblib.load(new_dir/"method_baseline_v032.joblib")
    new_resid=joblib.load(new_dir/"method_residual_v032.joblib")
    new_timing=joblib.load(new_dir/"timing_v032_30s.joblib")
    manifest=json.loads((new_dir/"manifest.json").read_text())
    fin_off=manifest["final_method_calibration"]["finish_offset"]
    sub_off=manifest["final_method_calibration"]["sub_given_finish_offset"]

    rows=[]
    for i,f in enumerate(CARD,1):
        a=rb.summarize_history(f["a"],history,static,EVENT_DATE)
        b=rb.summarize_history(f["b"],history,static,EVENT_DATE)
        apply_activity_recency(a,f["a"],EVENT_DATE,activity_dates)
        apply_activity_recency(b,f["b"],EVENT_DATE,activity_dates)

        for name,side in ((f["a"],a),(f["b"],b)):
            # Audited current-profile overrides take precedence for these
            # explicitly identified fighters; this prevents same-name/static
            # collisions for UFC debutants.
            for k,v in PROFILE_OVERRIDES.get(name,{}).items():
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

        jbase=joint_outcome_probabilities(p_ref,ba,bb)
        jcal=joint_outcome_probabilities(p_ref,ca,cb)
        jres=joint_outcome_probabilities(p_ref,ra,rbm)
        sim_cal=simulate_joint_outcomes(jcal,trials=TRIALS,seed=BASE_SEED+i)

        tx=pd.Series({n:wf.get(n,np.nan) for n in new_timing.base_feature_names_},index=new_timing.base_feature_names_)
        timing={k:float(v) for k,v in new_timing.market_probabilities(tx,f["scheduled_seconds"]).items()}
        tsim=timing_simulation(new_timing,tx,f["scheduled_seconds"],BASE_SEED+100+i)

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
        raw_conf=max(p_ref,1-p_ref)*10
        display_conf=evidence_adjusted_confidence(raw_conf,evidence["a_prior_ufc_bouts"],evidence["b_prior_ufc_bouts"])

        rows.append({
            "fight_no":i,**f,
            "winner_reference_p_a":p_ref,"winner_v032_p_a":p_new,
            "winner_reference_pick":f["a"] if p_ref>=.5 else f["b"],
            "winner_v032_pick":f["a"] if p_new>=.5 else f["b"],
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
            "timing_v032_direct":timing,"timing_v032_sim_10000":tsim,
            "evidence_density":evidence,
        })

    payload={
        "event":"UFC 332: Silva vs Wang",
        "event_date":"2026-10-03",
        "stage":"A_ODDS_BLIND_MODEL_RAW_V032_IDENTITY_AUDITED",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "odds_used":False,
        "model_state":{
            "champion_winner":"v0.27 reconstruction reference",
            "shadow_winner":"v0.32 full-stat shadow",
            "method_baseline":"v0.32 baseline",
            "method_calibration":"v0.32 calibrated leading shadow",
            "method_residual":"v0.32 residual comparison",
            "timing":"v0.32 30-second hazard shadow",
            "fighter_history_through":"2026-09-26",
            "clean_feedback_rows":87,
            "joint_simulations_per_fight":TRIALS,
            "timing_simulations_per_fight":TRIALS,
        },
        "fights":rows,
    }
    lock=freeze_payload(payload)
    out=ROOT/"data/locks/ufc332_2026-10-03"
    out.mkdir(parents=True,exist_ok=True)
    (out/"stage_a_model_raw_v032_identity_audited.json").write_text(
        json.dumps({"sha256":lock.sha256,"payload":lock.payload},indent=2,sort_keys=True),encoding="utf-8"
    )

    summary=[]
    for r in rows:
        p=r["winner_reference_p_a"]
        summary.append({
            "fight_no":r["fight_no"],
            "fight":f'{r["a"]} vs {r["b"]}',
            "reference_pick":r["winner_reference_pick"],
            "v032_pick":r["winner_v032_pick"],
            "reference_probability":max(p,1-p),
            "v032_probability":max(r["winner_v032_p_a"],1-r["winner_v032_p_a"]),
            "model_disagreement":r["winner_model_disagreement"],
            "sparse":r["sparse_ufc_evidence"],
            "confidence_10":r["evidence_adjusted_confidence_10"],
            "top_joint_calibrated":max(r["joint_calibrated"],key=r["joint_calibrated"].get),
            "top_joint_probability":max(r["joint_calibrated"].values()),
            "gtd_yes":r["timing_v032_direct"]["GTD_YES"],
            "over_1_5":r["timing_v032_direct"].get("OVER_1.5"),
            "over_2_5":r["timing_v032_direct"].get("OVER_2.5"),
            "over_3_5":r["timing_v032_direct"].get("OVER_3.5"),
            "over_4_5":r["timing_v032_direct"].get("OVER_4.5"),
            "evidence":r["evidence_density"],
        })
    (out/"stage_a_model_summary_v032_identity_audited.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({"sha256":lock.sha256,"summary":summary},indent=2))

if __name__=="__main__":
    main()
