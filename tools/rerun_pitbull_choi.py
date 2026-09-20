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

spec = importlib.util.spec_from_file_location("ufc331_stage_a", ROOT / "tools/run_ufc331_stage_a.py")
stage = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["ufc331_stage_a"] = stage
spec.loader.exec_module(stage)

from wshlx_ufc.models import joint_outcome_probabilities
from wshlx_ufc.simulation import simulate_joint_outcomes

EVENT_DATE = pd.Timestamp("2026-09-19", tz="UTC")
FIGHT = {
    "a": "Patricio Pitbull",
    "b": "Dooho Choi",
    "weight_class": "Featherweight",
    "scheduled_seconds": 900,
}
SEED = 3311910
TRIALS = 10_000

def main():
    raw_dir = ROOT / "build/pitbull_choi_rerun/raw"
    stage.rb.download_sources(raw_dir)
    fights, stats, static = stage.rb.load_fights(raw_dir)
    fight_stats = stage.rb.aggregate_fight_stats(fights, stats)
    history = stage.completed_history(fights, fight_stats)

    for target, source in stage.HISTORY_ALIASES.items():
        merged = list(history.get(target, [])) + list(history.get(source, []))
        merged.sort(key=lambda x: pd.Timestamp(x["event_date"]))
        history[target] = merged
        if target not in static and source in static:
            static[target] = dict(static[source])

    a = stage.rb.summarize_history(FIGHT["a"], history, static, EVENT_DATE)
    b = stage.rb.summarize_history(FIGHT["b"], history, static, EVENT_DATE)
    for name, side in [(FIGHT["a"], a), (FIGHT["b"], b)]:
        for key, value in stage.CURRENT_PROFILE_OVERRIDES.get(name, {}).items():
            side[key] = float(value)

    artifacts = ROOT / "artifacts/v027_reconstruction"
    winner_model = joblib.load(artifacts / "winner_reconstruction.joblib")
    method_model = joblib.load(artifacts / "method_baseline_reconstruction.joblib")
    residual_model = joblib.load(artifacts / "method_residual_v027.joblib")
    timing_model = joblib.load(artifacts / "timing_reconstruction.joblib")

    wf = stage.rb.winner_features(a, b, FIGHT["weight_class"], FIGHT["scheduled_seconds"])
    wx = pd.DataFrame([wf], columns=stage.rb.WINNER_FEATURES)
    p_a = float(winner_model.predict_proba(wx)[0, 0])

    amf = stage.rb.method_features(a, b, FIGHT["weight_class"], FIGHT["scheduled_seconds"])
    bmf = stage.rb.method_features(b, a, FIGHT["weight_class"], FIGHT["scheduled_seconds"])
    amx = pd.DataFrame([amf], columns=stage.rb.METHOD_BASE_FEATURES)
    bmx = pd.DataFrame([bmf], columns=stage.rb.METHOD_BASE_FEATURES)
    base_a_df = method_model.predict_proba(amx)
    base_b_df = method_model.predict_proba(bmx)
    base_a = {k: float(base_a_df.iloc[0][k]) for k in ("KO", "SUB", "DEC")}
    base_b = {k: float(base_b_df.iloc[0][k]) for k in ("KO", "SUB", "DEC")}

    ar = stage.rb.residual_features(a, b)
    br = stage.rb.residual_features(b, a)
    arx = pd.DataFrame([ar], columns=list(stage.rb.V027_FEATURES))
    brx = pd.DataFrame([br], columns=list(stage.rb.V027_FEATURES))
    shadow_a_df = residual_model.predict_proba(
        arx, baseline_ko=[base_a["KO"]], baseline_sub=[base_a["SUB"]], baseline_dec=[base_a["DEC"]]
    )
    shadow_b_df = residual_model.predict_proba(
        brx, baseline_ko=[base_b["KO"]], baseline_sub=[base_b["SUB"]], baseline_dec=[base_b["DEC"]]
    )
    shadow_a = {k: float(shadow_a_df.iloc[0][k]) for k in ("KO", "SUB", "DEC")}
    shadow_b = {k: float(shadow_b_df.iloc[0][k]) for k in ("KO", "SUB", "DEC")}

    joint = joint_outcome_probabilities(p_a, base_a, base_b)
    sim = simulate_joint_outcomes(joint, trials=TRIALS, seed=SEED)

    tx = pd.Series(
        {name: wf.get(name, np.nan) for name in timing_model.base_feature_names_},
        index=timing_model.base_feature_names_,
    )
    timing = {k: float(v) for k, v in timing_model.market_probabilities(tx, 900).items()}

    report = {
        "event":"UFC 331: Van vs Pantoja 2",
        "fight":"Patricio Pitbull vs Dooho Choi",
        "rerun_type":"ISOLATED_ODDS_BLIND_RECHECK",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "trials":TRIALS,
        "winner":{"Patricio Pitbull":p_a,"Dooho Choi":1.0-p_a},
        "conditional_method_if_pitbull_wins_baseline":base_a,
        "conditional_method_if_choi_wins_baseline":base_b,
        "conditional_method_if_pitbull_wins_v027_shadow":shadow_a,
        "conditional_method_if_choi_wins_v027_shadow":shadow_b,
        "joint_outcomes_baseline":joint,
        "joint_simulation_10000":sim,
        "timing":timing,
        "evidence_density":{
            "pitbull_prior_ufc_bouts":int(a["prior_bouts"]),
            "choi_prior_ufc_bouts":int(b["prior_bouts"]),
            "pitbull_days_since_last":float(a["days_since_last"]),
            "choi_days_since_last":float(b["days_since_last"]),
            "pitbull_age":float(a["age_years"]),
            "choi_age":float(b["age_years"]),
            "pitbull_reach":float(a["reach_inches"]),
            "choi_reach":float(b["reach_inches"])
        },
        "governance":{"odds_used_as_features":False,"official_stage_a_lock_unchanged":True,"purpose":"isolated diagnostic rerun requested by user"}
    }

    out=ROOT/"reports/ufc331_2026-09-19"
    out.mkdir(parents=True,exist_ok=True)
    (out/"pitbull_choi_isolated_rerun.json").write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
