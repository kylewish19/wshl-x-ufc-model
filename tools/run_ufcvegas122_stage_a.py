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


rb = load_module("rebuild_v027_ufcvegas122", ROOT / "tools/rebuild_v027.py")
stage331 = load_module("ufc331_stage_helpers_ufcvegas122", ROOT / "tools/run_ufc331_stage_a.py")

from wshlx_ufc.method_calibration import MethodInterceptCalibrator
from wshlx_ufc.models import fighter_double_chance, joint_outcome_probabilities
from wshlx_ufc.simulation import simulate_joint_outcomes
from wshlx_ufc.selection_policy import evidence_adjusted_confidence
from wshlx_ufc.locks import freeze_payload
from wshlx_ufc.nonperformance import activity_dates_from_raw, apply_activity_recency

EVENT_DATE = pd.Timestamp("2026-10-10", tz="UTC")
TRIALS = 10_000
BASE_SEED = 1221010
RAW_DIR = ROOT / "data/raw/ufc332_2026-10-03"

CARD = [
    {"a":"Ernesta Kareckaite","b":"Melissa Gatto","weight_class":"Women's Flyweight","scheduled_seconds":900},
    {"a":"Alice Pereira","b":"Daria Zhelezniakova","weight_class":"Women's Bantamweight","scheduled_seconds":900},
    {"a":"Allen Frye Jr.","b":"RJ Harris","weight_class":"Heavyweight","scheduled_seconds":900},
    {"a":"Felipe Franco","b":"Brendson Ribeiro","weight_class":"Light Heavyweight","scheduled_seconds":900},
    {"a":"Niko Price","b":"Leon Shahbazyan","weight_class":"Welterweight","scheduled_seconds":900},
    {"a":"Francisco Prado","b":"Ismael Bonfim","weight_class":"Lightweight","scheduled_seconds":900},
    {"a":"Julius Walker","b":"Gerald Meerschaert","weight_class":"Light Heavyweight","scheduled_seconds":900},
    {"a":"Malcolm Wellmaker","b":"Otari Tanzilovi","weight_class":"Bantamweight","scheduled_seconds":900},
    {"a":"Andre Fili","b":"Kai Kamaka III","weight_class":"Featherweight","scheduled_seconds":900},
    {"a":"Loopy Godinez","b":"Ketlen Souza","weight_class":"Women's Strawweight","scheduled_seconds":900},
    {"a":"Matheus Camilo","b":"Jai Herbert","weight_class":"Lightweight","scheduled_seconds":900},
    {"a":"Brendan Allen","b":"Christian Leroy Duncan","weight_class":"Middleweight","scheduled_seconds":1500},
]

# Canonical display-name variants only. No odds or post-fight information.
HISTORY_ALIASES = {
    "loopygodinez": "lupitagodinez",
    "dariazhelezniakova": "daryazheleznyakova",
    "allenfryejr": "allenfrye",
}


def completed_history(fights, fight_stats):
    return stage331.completed_history(fights, fight_stats)


def method_dict(row):
    return {k: float(row[k]) for k in ("KO", "SUB", "DEC")}


def calibrate_method(base: dict[str, float], finish_offset: float, sub_offset: float):
    cal = MethodInterceptCalibrator(ridge=0.5)
    cal.finish_offset_ = float(finish_offset)
    cal.sub_offset_ = float(sub_offset)
    cal.is_fitted_ = True
    p = cal.predict_proba(
        baseline_ko=[base["KO"]], baseline_sub=[base["SUB"]], baseline_dec=[base["DEC"]]
    ).iloc[0]
    return method_dict(p)


def timing_simulation(model, xrow, scheduled_seconds, seed):
    hazards = np.clip(model._hazards_for_one(xrow, scheduled_seconds), 0.0, 1.0)
    rng = np.random.default_rng(seed)
    n_bins = len(hazards)
    finish_bins = np.full(TRIALS, n_bins, dtype=int)
    for t in range(TRIALS):
        for i, h in enumerate(hazards):
            if rng.random() < h:
                finish_bins[t] = i
                break
    durations = np.where(
        finish_bins == n_bins,
        scheduled_seconds,
        np.minimum((finish_bins + 1) * model.bin_seconds, scheduled_seconds),
    ).astype(float)
    finished = finish_bins < n_bins
    out = {}
    thresholds = [0.5, 1.5, 2.5] + ([3.5, 4.5] if scheduled_seconds == 1500 else [])
    for r in thresholds:
        sec = int(round(r * 300))
        po = float(np.mean(durations > sec))
        out[f"OVER_{r}"] = po
        out[f"UNDER_{r}"] = 1.0 - po
    out["GTD_YES"] = float(np.mean(~finished))
    out["GTD_NO"] = 1.0 - out["GTD_YES"]
    for rnd in range(2, scheduled_seconds // 300 + 1):
        sec = (rnd - 1) * 300
        py = float(np.mean(durations > sec))
        out[f"ROUND_{rnd}_STARTS_YES"] = py
        out[f"ROUND_{rnd}_STARTS_NO"] = 1.0 - py
    return out


def main():
    # Include completed UFC performance through UFC 332, exclude this event.
    old = rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF = pd.Timestamp("2026-10-04", tz="UTC")
    try:
        fights, stats, static = rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF = old

    fight_stats = rb.aggregate_fight_stats(fights, stats)
    history = completed_history(fights, fight_stats)
    activity_dates = activity_dates_from_raw(RAW_DIR)

    for target, source in HISTORY_ALIASES.items():
        if target == source:
            continue
        merged = list(history.get(target, [])) + list(history.get(source, []))
        # Deduplicate exact historical rows if both display variants point at the same athlete.
        seen = set()
        deduped = []
        for item in sorted(merged, key=lambda x: pd.Timestamp(x["event_date"])):
            key = (str(item.get("event_date")), float(item.get("duration_seconds", 0.0)), bool(item.get("win")), str(item.get("method")))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        if deduped:
            history[target] = deduped
        if target not in static and source in static:
            static[target] = dict(static[source])

    ref_dir = ROOT / "artifacts/v027_reconstruction"
    new_dir = ROOT / "artifacts/v033_ufc332_full_stats"
    ref_winner = joblib.load(ref_dir / "winner_reconstruction.joblib")
    new_winner = joblib.load(new_dir / "winner_v033.joblib")
    new_method = joblib.load(new_dir / "method_baseline_v033.joblib")
    new_resid = joblib.load(new_dir / "method_residual_v033.joblib")
    new_timing = joblib.load(new_dir / "timing_v033_30s.joblib")
    manifest = json.loads((new_dir / "manifest.json").read_text())
    fin_off = manifest["final_method_calibration"]["finish_offset"]
    sub_off = manifest["final_method_calibration"]["sub_given_finish_offset"]

    rows = []
    for i, f in enumerate(CARD, 1):
        a = rb.summarize_history(f["a"], history, static, EVENT_DATE)
        b = rb.summarize_history(f["b"], history, static, EVENT_DATE)
        apply_activity_recency(a, f["a"], EVENT_DATE, activity_dates)
        apply_activity_recency(b, f["b"], EVENT_DATE, activity_dates)

        wf = rb.winner_features(a, b, f["weight_class"], f["scheduled_seconds"])
        wx = pd.DataFrame([wf], columns=rb.WINNER_FEATURES)
        p_ref = float(ref_winner.predict_proba(wx)[0, 0])
        p_new = float(new_winner.predict_proba(wx)[0, 0])

        amf = rb.method_features(a, b, f["weight_class"], f["scheduled_seconds"])
        bmf = rb.method_features(b, a, f["weight_class"], f["scheduled_seconds"])
        amx = pd.DataFrame([amf], columns=rb.METHOD_BASE_FEATURES)
        bmx = pd.DataFrame([bmf], columns=rb.METHOD_BASE_FEATURES)
        ba = method_dict(new_method.predict_proba(amx).iloc[0])
        bb = method_dict(new_method.predict_proba(bmx).iloc[0])
        ca = calibrate_method(ba, fin_off, sub_off)
        cb = calibrate_method(bb, fin_off, sub_off)

        arx = pd.DataFrame([rb.residual_features(a, b)], columns=list(rb.V027_FEATURES))
        brx = pd.DataFrame([rb.residual_features(b, a)], columns=list(rb.V027_FEATURES))
        ra = method_dict(new_resid.predict_proba(
            arx, baseline_ko=[ba["KO"]], baseline_sub=[ba["SUB"]], baseline_dec=[ba["DEC"]]
        ).iloc[0])
        rbm = method_dict(new_resid.predict_proba(
            brx, baseline_ko=[bb["KO"]], baseline_sub=[bb["SUB"]], baseline_dec=[bb["DEC"]]
        ).iloc[0])

        jbase = joint_outcome_probabilities(p_ref, ba, bb)
        jcal = joint_outcome_probabilities(p_ref, ca, cb)
        jres = joint_outcome_probabilities(p_ref, ra, rbm)
        sim_cal = simulate_joint_outcomes(jcal, trials=TRIALS, seed=BASE_SEED + i)

        tx = pd.Series({n: wf.get(n, np.nan) for n in new_timing.base_feature_names_}, index=new_timing.base_feature_names_)
        timing = {k: float(v) for k, v in new_timing.market_probabilities(tx, f["scheduled_seconds"]).items()}
        tsim = timing_simulation(new_timing, tx, f["scheduled_seconds"], BASE_SEED + 100 + i)

        def finite_or_none(x):
            return None if not np.isfinite(x) else float(x)

        evidence = {
            "a_prior_ufc_bouts": int(a["prior_bouts"]),
            "b_prior_ufc_bouts": int(b["prior_bouts"]),
            "a_days_since_last": finite_or_none(a["days_since_last"]),
            "b_days_since_last": finite_or_none(b["days_since_last"]),
            "a_age": finite_or_none(a["age_years"]),
            "b_age": finite_or_none(b["age_years"]),
            "a_reach": finite_or_none(a["reach_inches"]),
            "b_reach": finite_or_none(b["reach_inches"]),
        }
        sparse = min(evidence["a_prior_ufc_bouts"], evidence["b_prior_ufc_bouts"]) < 2
        raw_conf = max(p_ref, 1 - p_ref) * 10
        display_conf = evidence_adjusted_confidence(
            raw_conf, evidence["a_prior_ufc_bouts"], evidence["b_prior_ufc_bouts"]
        )

        rows.append({
            "fight_no": i, **f,
            "winner_reference_p_a": p_ref,
            "winner_v033_p_a": p_new,
            "winner_reference_pick": f["a"] if p_ref >= 0.5 else f["b"],
            "winner_v033_pick": f["a"] if p_new >= 0.5 else f["b"],
            "winner_model_disagreement": (p_ref >= 0.5) != (p_new >= 0.5),
            "raw_probability_confidence_10": raw_conf,
            "evidence_adjusted_confidence_10": display_conf,
            "sparse_ufc_evidence": sparse,
            "method_if_a_wins_baseline": ba,
            "method_if_b_wins_baseline": bb,
            "method_if_a_wins_calibrated": ca,
            "method_if_b_wins_calibrated": cb,
            "method_if_a_wins_residual": ra,
            "method_if_b_wins_residual": rbm,
            "joint_baseline": jbase,
            "joint_calibrated": jcal,
            "joint_residual": jres,
            "double_chance_calibrated": fighter_double_chance(jcal),
            "joint_calibrated_sim_10000": sim_cal,
            "timing_v033_direct": timing,
            "timing_v033_sim_10000": tsim,
            "evidence_density": evidence,
        })

    payload = {
        "event": "UFC Vegas 122: Allen vs Duncan",
        "event_date": "2026-10-10",
        "stage": "A_ODDS_BLIND_MODEL_RAW_V033",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "odds_used": False,
        "model_state": {
            "champion_winner": "v0.27 reconstruction reference",
            "shadow_winner": "v0.33 full-stat shadow",
            "method_baseline": "v0.33 baseline",
            "method_calibration": "v0.33 calibrated leading shadow",
            "method_residual": "v0.33 residual comparison",
            "timing": "v0.33 30-second hazard shadow",
            "fighter_history_through": "2026-10-03",
            "clean_feedback_rows": 101,
            "joint_simulations_per_fight": TRIALS,
            "timing_simulations_per_fight": TRIALS,
        },
        "fights": rows,
    }
    lock = freeze_payload(payload)
    out = ROOT / "data/locks/ufcvegas122_2026-10-10"
    out.mkdir(parents=True, exist_ok=True)
    (out / "stage_a_model_raw_v033.json").write_text(
        json.dumps({"sha256": lock.sha256, "payload": lock.payload}, indent=2, sort_keys=True), encoding="utf-8"
    )

    summary = []
    for r in rows:
        p = r["winner_reference_p_a"]
        summary.append({
            "fight_no": r["fight_no"],
            "fight": f'{r["a"]} vs {r["b"]}',
            "reference_pick": r["winner_reference_pick"],
            "v033_pick": r["winner_v033_pick"],
            "reference_probability": max(p, 1 - p),
            "v033_probability": max(r["winner_v033_p_a"], 1 - r["winner_v033_p_a"]),
            "model_disagreement": r["winner_model_disagreement"],
            "sparse": r["sparse_ufc_evidence"],
            "confidence_10": r["evidence_adjusted_confidence_10"],
            "top_joint_calibrated": max(r["joint_calibrated"], key=r["joint_calibrated"].get),
            "top_joint_probability": max(r["joint_calibrated"].values()),
            "gtd_yes": r["timing_v033_direct"]["GTD_YES"],
            "over_1_5": r["timing_v033_direct"].get("OVER_1.5"),
            "over_2_5": r["timing_v033_direct"].get("OVER_2.5"),
            "over_3_5": r["timing_v033_direct"].get("OVER_3.5"),
            "over_4_5": r["timing_v033_direct"].get("OVER_4.5"),
            "evidence": r["evidence_density"],
        })
    (out / "stage_a_model_summary_v033.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"sha256": lock.sha256, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
