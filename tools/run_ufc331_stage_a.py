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

spec = importlib.util.spec_from_file_location("rebuild_v027", ROOT / "tools/rebuild_v027.py")
rb = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["rebuild_v027"] = rb
spec.loader.exec_module(rb)

from wshlx_ufc.models import fighter_double_chance, joint_outcome_probabilities
from wshlx_ufc.simulation import simulate_joint_outcomes
from wshlx_ufc.locks import freeze_payload

EVENT_DATE = pd.Timestamp("2026-09-19", tz="UTC")
TRIALS = 10_000
BASE_SEED = 33119


# Card-specific identity/static corrections discovered during the post-run audit.
# These use prefight public UFC profile information only; no odds or post-fight data.
HISTORY_ALIASES = {
    "patriciopitbull": "patriciofreire",
}

CURRENT_PROFILE_OVERRIDES = {
    "Michael Aswell Jr.": {"age_years": 25.0, "height_inches": 68.0, "reach_inches": 69.0},
    "Gable Steveson": {"height_inches": 71.0, "reach_inches": 74.0},
}

CARD = [
    {"a":"Giga Chikadze","b":"Joanderson Brito","weight_class":"Featherweight","scheduled_seconds":900},
    {"a":"Casey O'Neill","b":"Eduarda Moura","weight_class":"Women's Flyweight","scheduled_seconds":900},
    {"a":"Edmen Shahbazyan","b":"Brunno Ferreira","weight_class":"Middleweight","scheduled_seconds":900},
    {"a":"Ryan Gandra","b":"Ozzy Diaz","weight_class":"Middleweight","scheduled_seconds":900},
    {"a":"Michael Aswell Jr.","b":"Joosang Yoo","weight_class":"Featherweight","scheduled_seconds":900},
    {"a":"Tai Tuivasa","b":"Robelis Despaigne","weight_class":"Heavyweight","scheduled_seconds":900},
    {"a":"Marlon Vera","b":"Charles Jourdain","weight_class":"Bantamweight","scheduled_seconds":900},
    {"a":"Alonzo Menifield","b":"Iwo Baraniewski","weight_class":"Light Heavyweight","scheduled_seconds":900},
    {"a":"Gable Steveson","b":"Sean Sharaf","weight_class":"Heavyweight","scheduled_seconds":900},
    {"a":"Patricio Pitbull","b":"Dooho Choi","weight_class":"Featherweight","scheduled_seconds":900},
    {"a":"Arman Tsarukyan","b":"Mauricio Ruffy","weight_class":"Lightweight","scheduled_seconds":1500},
    {"a":"Joshua Van","b":"Alexandre Pantoja","weight_class":"Flyweight","scheduled_seconds":1500},
]


def completed_history(fights, fight_stats):
    history = {}
    for date, group in fights.groupby("event_date", sort=True):
        pending = []
        for fight in group.itertuples(index=False):
            ek = rb.norm_text(fight.event)
            bk = rb.norm_text(fight.bout)
            sa = fight_stats.get((ek, bk, rb.norm_name(fight.fighter_a)), {})
            sb = fight_stats.get((ek, bk, rb.norm_name(fight.fighter_b)), {})
            for fighter_name, own, opp in [
                (fight.fighter_a, sa, sb),
                (fight.fighter_b, sb, sa),
            ]:
                key = rb.norm_name(fighter_name)
                item = {
                    "event_date": date,
                    "duration_seconds": float(fight.duration_seconds),
                    "win": rb.norm_name(fight.winner) == key,
                    "method": fight.method,
                }
                for f in [
                    "kd_for","sig_landed","sig_attempted","ground_landed",
                    "ground_attempted","td_landed","td_attempted","sub_att",
                    "ctrl_seconds","r1_sig_landed","r1_seconds","r3_sig_landed",
                    "r3_seconds",
                ]:
                    item[f] = float(own.get(f, 0.0))
                    item[f"opp_{f}"] = float(opp.get(f, 0.0))
                pending.append((key, item))
        for key, item in pending:
            history.setdefault(key, []).append(item)
    return history


def timing_simulation(model, xrow, scheduled_seconds, seed):
    hazards = np.clip(model._hazards_for_one(xrow, scheduled_seconds), 0.0, 1.0)
    rng = np.random.default_rng(seed)
    n_bins = len(hazards)
    finished_bins = np.full(TRIALS, n_bins, dtype=int)
    for t in range(TRIALS):
        for i, h in enumerate(hazards):
            if rng.random() < h:
                finished_bins[t] = i
                break

    # Bin i represents a finish during ((i*bin),(i+1)*bin]. Use bin end
    # conservatively for market-survival summaries.
    durations = np.where(
        finished_bins == n_bins,
        scheduled_seconds,
        np.minimum((finished_bins + 1) * model.bin_seconds, scheduled_seconds),
    ).astype(float)
    finished = finished_bins < n_bins

    out = {}
    thresholds = [0.5,1.5,2.5] + ([3.5,4.5] if scheduled_seconds == 1500 else [])
    for r in thresholds:
        sec = int(round(r * 300))
        p_over = float(np.mean(durations > sec))
        out[f"OVER_{r}"] = p_over
        out[f"UNDER_{r}"] = 1.0 - p_over

    out["GTD_YES"] = float(np.mean(~finished))
    out["GTD_NO"] = 1.0 - out["GTD_YES"]
    scheduled_rounds = scheduled_seconds // 300
    for rnd in range(2, scheduled_rounds + 1):
        sec = (rnd - 1) * 300
        p = float(np.mean(durations > sec))
        out[f"ROUND_{rnd}_STARTS_YES"] = p
        out[f"ROUND_{rnd}_STARTS_NO"] = 1.0 - p

    finish_round = {}
    for rnd in range(1, scheduled_rounds + 1):
        lo=(rnd-1)*300
        hi=rnd*300
        finish_round[f"R{rnd}_FINISH"] = float(np.mean(finished & (durations > lo) & (durations <= hi)))
    finish_round["DEC_GTD"] = out["GTD_YES"]
    return out, finish_round


def method_dict(dfrow):
    return {k: float(dfrow[k]) for k in ("KO","SUB","DEC")}


def main():
    raw_dir = ROOT / "build/ufc331_stage_a/raw"
    rb.download_sources(raw_dir)
    fights, stats, static = rb.load_fights(raw_dir)
    fight_stats = rb.aggregate_fight_stats(fights, stats)
    history = completed_history(fights, fight_stats)

    # Canonicalize known fighter-name aliases without deleting the original provenance.
    for target, source in HISTORY_ALIASES.items():
        merged = list(history.get(target, [])) + list(history.get(source, []))
        merged.sort(key=lambda x: pd.Timestamp(x["event_date"]))
        history[target] = merged
        if target not in static and source in static:
            static[target] = dict(static[source])

    artifacts = ROOT / "artifacts/v027_reconstruction"
    winner_model = joblib.load(artifacts / "winner_reconstruction.joblib")
    method_model = joblib.load(artifacts / "method_baseline_reconstruction.joblib")
    residual_model = joblib.load(artifacts / "method_residual_v027.joblib")
    timing_model = joblib.load(artifacts / "timing_reconstruction.joblib")

    rows=[]
    for i,f in enumerate(CARD, start=1):
        a = rb.summarize_history(f["a"], history, static, EVENT_DATE)
        b = rb.summarize_history(f["b"], history, static, EVENT_DATE)
        for name, side in [(f["a"], a), (f["b"], b)]:
            for key, value in CURRENT_PROFILE_OVERRIDES.get(name, {}).items():
                side[key] = float(value)
        wf = rb.winner_features(a,b,f["weight_class"],f["scheduled_seconds"])
        wx = pd.DataFrame([wf], columns=rb.WINNER_FEATURES)
        p_a = float(winner_model.predict_proba(wx)[0,0])

        amf = rb.method_features(a,b,f["weight_class"],f["scheduled_seconds"])
        bmf = rb.method_features(b,a,f["weight_class"],f["scheduled_seconds"])
        ar = rb.residual_features(a,b)
        br = rb.residual_features(b,a)

        amx = pd.DataFrame([amf], columns=rb.METHOD_BASE_FEATURES)
        bmx = pd.DataFrame([bmf], columns=rb.METHOD_BASE_FEATURES)
        base_a_df = method_model.predict_proba(amx)
        base_b_df = method_model.predict_proba(bmx)
        base_a = method_dict(base_a_df.iloc[0])
        base_b = method_dict(base_b_df.iloc[0])

        arx = pd.DataFrame([ar], columns=list(rb.V027_FEATURES))
        brx = pd.DataFrame([br], columns=list(rb.V027_FEATURES))
        shadow_a_df = residual_model.predict_proba(
            arx,
            baseline_ko=[base_a["KO"]],
            baseline_sub=[base_a["SUB"]],
            baseline_dec=[base_a["DEC"]],
        )
        shadow_b_df = residual_model.predict_proba(
            brx,
            baseline_ko=[base_b["KO"]],
            baseline_sub=[base_b["SUB"]],
            baseline_dec=[base_b["DEC"]],
        )
        shadow_a = method_dict(shadow_a_df.iloc[0])
        shadow_b = method_dict(shadow_b_df.iloc[0])

        joint_base = joint_outcome_probabilities(p_a, base_a, base_b)
        joint_shadow = joint_outcome_probabilities(p_a, shadow_a, shadow_b)
        dc = fighter_double_chance(joint_base)
        sim_base = simulate_joint_outcomes(joint_base,trials=TRIALS,seed=BASE_SEED+i)
        sim_shadow = simulate_joint_outcomes(joint_shadow,trials=TRIALS,seed=BASE_SEED+100+i)

        tx = pd.Series({name: wf.get(name, np.nan) for name in timing_model.base_feature_names_}, index=timing_model.base_feature_names_)
        timing_direct = timing_model.market_probabilities(tx,f["scheduled_seconds"])
        timing_sim, finish_round = timing_simulation(
            timing_model,tx,f["scheduled_seconds"],BASE_SEED+200+i
        )

        # Diagnostics for how much historical UFC evidence the model has.
        meta = {
            "a_prior_ufc_bouts": int(a["prior_bouts"]),
            "b_prior_ufc_bouts": int(b["prior_bouts"]),
            "a_days_since_last": None if not np.isfinite(a["days_since_last"]) else float(a["days_since_last"]),
            "b_days_since_last": None if not np.isfinite(b["days_since_last"]) else float(b["days_since_last"]),
            "a_age": None if not np.isfinite(a["age_years"]) else float(a["age_years"]),
            "b_age": None if not np.isfinite(b["age_years"]) else float(b["age_years"]),
            "a_reach": None if not np.isfinite(a["reach_inches"]) else float(a["reach_inches"]),
            "b_reach": None if not np.isfinite(b["reach_inches"]) else float(b["reach_inches"]),
        }

        rows.append({
            "fight_no":i,
            **f,
            "p_a_win":p_a,
            "p_b_win":1-p_a,
            "method_if_a_wins_baseline":base_a,
            "method_if_b_wins_baseline":base_b,
            "method_if_a_wins_v027_shadow":shadow_a,
            "method_if_b_wins_v027_shadow":shadow_b,
            "joint_baseline":joint_base,
            "joint_v027_shadow":joint_shadow,
            "double_chance_baseline":dc,
            "joint_sim_10000":sim_base,
            "shadow_joint_sim_10000":sim_shadow,
            "timing_direct":{k:float(v) for k,v in timing_direct.items()},
            "timing_sim_10000":timing_sim,
            "finish_round_sim_10000":finish_round,
            "evidence_density":meta,
        })

    payload={
        "event":"UFC 331: Van vs Pantoja 2",
        "event_date":"2026-09-19",
        "stage":"A_MODEL_ONLY_ODDS_BLIND_V2_IDENTITY_AUDITED",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "data_corrections":{
            "patricio_pitbull_alias":"Merged UFCStats history stored as Patricio Freire + Patricio Pitbull",
            "michael_aswell_jr_static":"Age 25, height 68, reach 69 from current UFC profile",
            "gable_steveson_static":"Height 71, reach 74 from current UFC profile",
            "odds_used":False
        },
        "model_state":{
            "winner":"winner_reconstruction shadow/current operational reconstruction",
            "method_baseline":"method_baseline_reconstruction",
            "method_shadow":"v0.27-reconstruction residual (not promoted)",
            "timing":"timing_reconstruction",
            "training_data_through":"2026-09-12",
            "trials_per_joint_layer":TRIALS,
            "trials_timing":TRIALS,
        },
        "fights":rows,
    }
    lock=freeze_payload(payload)
    out=ROOT/"data/locks/ufc331_2026-09-19"
    out.mkdir(parents=True,exist_ok=True)
    (out/"stage_a_model_raw_v2.json").write_text(
        json.dumps({"sha256":lock.sha256,"payload":lock.payload},indent=2,sort_keys=True),
        encoding="utf-8"
    )

    summary=[]
    for r in rows:
        jb=r["joint_baseline"]
        winner=r["a"] if r["p_a_win"]>=.5 else r["b"]
        method_key=max(jb,key=jb.get)
        summary.append({
            "fight":f'{r["a"]} vs {r["b"]}',
            "winner_model":winner,
            "winner_probability":max(r["p_a_win"],r["p_b_win"]),
            "top_joint_outcome":method_key,
            "top_joint_probability":jb[method_key],
            "gtd_yes":r["timing_direct"]["GTD_YES"],
            "gtd_no":r["timing_direct"]["GTD_NO"],
            "model_evidence":r["evidence_density"],
        })
    (out/"stage_a_model_summary_v2.json").write_text(
        json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8"
    )
    print(json.dumps({"lock_sha256":lock.sha256,"summary":summary},indent=2))


if __name__=="__main__":
    main()
