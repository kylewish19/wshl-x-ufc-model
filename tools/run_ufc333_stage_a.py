from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unicodedata
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


# Reuse the already-audited current/reference runner lineage. Importing this module
# configures the Vegas-122 runner for Edmonton; this script then redirects only the
# event/card/cutoff/artifact paths forward through completed Edmonton history.
edm = load_module("ufcedmonton_stage_a_for_ufc333", ROOT / "tools/run_ufcedmonton_stage_a.py")
mod = edm.mod

from wshlx_ufc.historical_data import (
    build_prefight_perspective_rows,
    col as hist_col,
    download_source_files,
    load_source_files,
    normalize_fighters,
)
from wshlx_ufc.historical_timing_model import (
    _encode_transform as hist_timing_encode_transform,
    symmetric_timing_frame,
)
from wshlx_ufc.unified_ensemble import (
    binary_logit_pool,
    blend_hazards,
    markets_from_hazards,
    multiclass_log_pool,
)

build_hist = load_module("build_historical_model_for_ufc333", ROOT / "scripts/build_historical_model.py")

EVENT_NAME = "UFC 333: Volkanovski vs Evloev"
EVENT_DATE = pd.Timestamp("2026-10-24", tz="UTC")
TRIALS = 10_000
BASE_SEED = 3331024

CARD = [
    {"a": "Iasmin Lucindo", "b": "Nicolle Caliari", "weight_class": "Women's Strawweight", "scheduled_seconds": 900},
    {"a": "Kody Steele", "b": "Noah Gugnon", "weight_class": "Lightweight", "scheduled_seconds": 900},
    {"a": "Bolaji Oki", "b": "Daniel Santos", "weight_class": "Featherweight", "scheduled_seconds": 900},
    {"a": "Abubakar Vagaev", "b": "Jacob Malkoun", "weight_class": "Middleweight", "scheduled_seconds": 900},
    {"a": "Colby Thicknesse", "b": "Asaf Chopurov", "weight_class": "Bantamweight", "scheduled_seconds": 900},
    {"a": "Grant Dawson", "b": "Nurullo Aliev", "weight_class": "Lightweight", "scheduled_seconds": 900},
    {"a": "Abus Magomedov", "b": "Cam Rowston", "weight_class": "Middleweight", "scheduled_seconds": 900},
    {"a": "Nikita Krylov", "b": "Abdul Rakhman Yakhyaev", "weight_class": "Light Heavyweight", "scheduled_seconds": 900},
    {"a": "Azamat Murzakanov", "b": "Dominick Reyes", "weight_class": "Light Heavyweight", "scheduled_seconds": 900},
    {"a": "Aaron Pico", "b": "Losene Keita", "weight_class": "Featherweight", "scheduled_seconds": 900},
    {"a": "Alexander Volkov", "b": "Rizvan Kuniev", "weight_class": "Heavyweight", "scheduled_seconds": 900},
    {"a": "Lone'er Kavanagh", "b": "Ramazan Temirov", "weight_class": "Flyweight", "scheduled_seconds": 900},
    {"a": "Petr Yan", "b": "Merab Dvalishvili", "weight_class": "Bantamweight", "scheduled_seconds": 1500, "title": True},
    {"a": "Alexander Volkanovski", "b": "Movsar Evloev", "weight_class": "Featherweight", "scheduled_seconds": 1500, "title": True},
]

METHOD_KEYS = ("A_KO", "A_SUB", "A_DEC", "B_KO", "B_SUB", "B_DEC")


def norm_name(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def title_weight_class(f: dict) -> str:
    if not f.get("title"):
        return str(f["weight_class"])
    return f"UFC {f['weight_class']} Title Bout"


def double_chance(joint: dict[str, float]) -> dict[str, float]:
    return {
        "A_KO_OR_SUB": joint["A_KO"] + joint["A_SUB"],
        "A_KO_OR_DEC": joint["A_KO"] + joint["A_DEC"],
        "A_SUB_OR_DEC": joint["A_SUB"] + joint["A_DEC"],
        "B_KO_OR_SUB": joint["B_KO"] + joint["B_SUB"],
        "B_KO_OR_DEC": joint["B_KO"] + joint["B_DEC"],
        "B_SUB_OR_DEC": joint["B_SUB"] + joint["B_DEC"],
    }


def simulate_joint(joint: dict[str, float], seed: int) -> dict[str, float]:
    probs = np.asarray([joint[k] for k in METHOD_KEYS], dtype=float)
    probs = np.clip(probs, 0.0, None)
    probs /= probs.sum()
    rng = np.random.default_rng(seed)
    draws = rng.choice(len(METHOD_KEYS), size=TRIALS, p=probs)
    return {k: float(np.mean(draws == i)) for i, k in enumerate(METHOD_KEYS)}


def simulate_timing_hazards(hazards: np.ndarray, scheduled_seconds: int, seed: int) -> dict[str, float]:
    h = np.clip(np.asarray(hazards, dtype=float), 0.0, 1.0)
    rng = np.random.default_rng(seed)
    n_bins = len(h)
    finish_bins = np.full(TRIALS, n_bins, dtype=int)
    for t in range(TRIALS):
        for i, hazard in enumerate(h):
            if rng.random() < hazard:
                finish_bins[t] = i
                break
    finished = finish_bins < n_bins
    durations = np.where(
        finished,
        np.minimum((finish_bins + 1) * 30, scheduled_seconds),
        scheduled_seconds,
    ).astype(float)

    out: dict[str, float] = {}
    thresholds = [0.5, 1.5, 2.5] + ([3.5, 4.5] if scheduled_seconds == 1500 else [])
    for r in thresholds:
        sec = int(round(r * 300))
        p_over = float(np.mean(durations > sec))
        out[f"OVER_{r}"] = p_over
        out[f"UNDER_{r}"] = 1.0 - p_over
    out["GTD_YES"] = float(np.mean(~finished))
    out["GTD_NO"] = 1.0 - out["GTD_YES"]

    rounds = scheduled_seconds // 300
    for rnd in range(1, rounds + 1):
        lo = (rnd - 1) * 300
        hi = rnd * 300
        out[f"FINISH_ROUND_{rnd}"] = float(np.mean(finished & (durations > lo) & (durations <= hi)))
    for rnd in range(2, rounds + 1):
        sec = (rnd - 1) * 300
        p = float(np.mean(durations > sec))
        out[f"ROUND_{rnd}_STARTS_YES"] = p
        out[f"ROUND_{rnd}_STARTS_NO"] = 1.0 - p
    return out


def configure_current_runner():
    mod.EVENT_DATE = EVENT_DATE
    mod.BASE_SEED = BASE_SEED
    mod.RAW_DIR = ROOT / "data/raw/ufcedmonton_2026-10-17"
    mod.CARD = [{k: v for k, v in f.items() if k in {"a", "b", "weight_class", "scheduled_seconds"}} for f in CARD]
    mod.HISTORY_ALIASES.update({"loneerkavanagh": "loneerkavanagh"})

    def causal_load(raw_dir):
        old = mod.rb.TRAINING_CUTOFF
        mod.rb.TRAINING_CUTOFF = pd.Timestamp("2026-10-18", tz="UTC")
        try:
            return edm._orig_load(raw_dir)
        finally:
            mod.rb.TRAINING_CUTOFF = old

    mod.rb.load_fights = causal_load

    def redirected_load(path, *args, **kwargs):
        p = Path(path)
        s = str(p)
        mapping = {
            "winner_v033.joblib": "winner_v033_through_2026-10-17.joblib",
            "method_baseline_v033.joblib": "method_baseline_v033_through_2026-10-17.joblib",
            "method_residual_v033.joblib": "method_residual_v033_through_2026-10-17.joblib",
            "timing_v033_30s.joblib": "timing_v033_30s_through_2026-10-17.joblib",
        }
        if "artifacts/v033_ufc332_full_stats" in s:
            p = ROOT / "artifacts/v033_ufcedmonton_full_stats" / mapping.get(p.name, p.name)
        return edm._orig_joblib_load(p, *args, **kwargs)

    mod.joblib.load = redirected_load

    def read_text_redirect(self, *args, **kwargs):
        if str(self).endswith("artifacts/v033_ufc332_full_stats/manifest.json"):
            return edm._orig_read_text(ROOT / "artifacts/v033_ufcedmonton_full_stats/manifest.json", *args, **kwargs)
        return edm._orig_read_text(self, *args, **kwargs)

    Path.read_text = read_text_redirect


def current_payload_and_hazards():
    configure_current_runner()
    captured_hazards: list[np.ndarray] = []
    original_timing_simulation = mod.timing_simulation

    def capture_timing(model, xrow, scheduled_seconds, seed):
        captured_hazards.append(np.clip(model._hazards_for_one(xrow, scheduled_seconds), 0.0, 1.0))
        return original_timing_simulation(model, xrow, scheduled_seconds, seed)

    mod.timing_simulation = capture_timing

    old_dir = ROOT / "data/locks/ufcvegas122_2026-10-10"
    protected = {}
    for name in ("stage_a_model_raw_v033.json", "stage_a_model_summary_v033.json"):
        path = old_dir / name
        protected[path] = path.read_bytes() if path.exists() else None

    try:
        mod.main()
        generated = json.loads((old_dir / "stage_a_model_raw_v033.json").read_text())
        payload = generated["payload"]
    finally:
        for path, backup in protected.items():
            if backup is None:
                if path.exists():
                    path.unlink()
            else:
                path.write_bytes(backup)
        mod.timing_simulation = original_timing_simulation
        Path.read_text = edm._orig_read_text

    if len(captured_hazards) != len(CARD):
        raise RuntimeError(f"expected {len(CARD)} current hazard curves, got {len(captured_hazards)}")

    payload["event"] = EVENT_NAME
    payload["event_date"] = "2026-10-24"
    payload["stage"] = "A_ODDS_BLIND_MODEL_RAW_THREE_VIEW_NOT_FROZEN"
    payload["odds_used"] = False
    payload["model_state"]["fighter_history_through"] = "2026-10-17"
    payload["model_state"]["shadow_winner"] = "v0.33 full-stat shadow retrained through 2026-10-17"
    payload["model_state"]["method_baseline"] = "v0.33 baseline retrained through 2026-10-17"
    payload["model_state"]["method_calibration"] = "v0.33 calibrated leading shadow retrained through 2026-10-17"
    payload["model_state"]["method_residual"] = "v0.33 residual comparison retrained through 2026-10-17"
    payload["model_state"]["timing"] = "v0.33 30-second hazard shadow retrained through 2026-10-17"
    payload["model_state"]["clean_feedback_rows_note"] = "post-Edmonton state; exact count retained in artifact manifest/ledger"
    return payload, captured_hazards


def source_name_map(fighters: pd.DataFrame) -> dict[str, str]:
    normalized = normalize_fighters(fighters)
    out: dict[str, str] = {}
    for name in normalized["fighter"].astype(str):
        key = norm_name(name)
        if key and key not in out:
            out[key] = name
    return out


def historical_prospective_frame():
    with tempfile.TemporaryDirectory(prefix="ufc333_hist_") as tmp:
        tmp_path = Path(tmp)
        download_source_files(tmp_path)
        tables = load_source_files(tmp_path)
        tables, supplemental_rows = build_hist.apply_results_supplements(
            tables, ROOT / "data/supplemental/results"
        )

        fmap = source_name_map(tables["fighters"])
        events = tables["events"].copy()
        ec = hist_col(events, "EVENT")
        dc = hist_col(events, "DATE")
        lc = hist_col(events, "LOCATION")
        if ec is None or dc is None:
            raise RuntimeError("historical events source missing EVENT/DATE")
        events = events[events[ec].astype(str) != EVENT_NAME].copy()
        new_event = {c: np.nan for c in events.columns}
        new_event[ec] = EVENT_NAME
        new_event[dc] = "10/24/2026"
        if lc is not None:
            new_event[lc] = "Abu Dhabi, United Arab Emirates"
        events = pd.concat([events, pd.DataFrame([new_event])], ignore_index=True)

        results = tables["results"].copy()
        rec = hist_col(results, "EVENT")
        if rec is None:
            raise RuntimeError("historical results source missing EVENT")
        results = results[results[rec].astype(str) != EVENT_NAME].copy()

        fake_rows = []
        source_pairs = []
        for f in CARD:
            a_src = fmap.get(norm_name(f["a"]), f["a"])
            b_src = fmap.get(norm_name(f["b"]), f["b"])
            source_pairs.append((a_src, b_src))
            row = {c: np.nan for c in results.columns}

            def set_if(header: str, value):
                c = hist_col(results, header)
                if c is not None:
                    row[c] = value
                else:
                    row[header] = value

            set_if("EVENT", EVENT_NAME)
            set_if("BOUT", f"{a_src} vs. {b_src}")
            set_if("OUTCOME", "W/L")
            set_if("WEIGHTCLASS", title_weight_class(f))
            set_if("METHOD", "DEC")
            set_if("ROUND", 5 if f["scheduled_seconds"] == 1500 else 3)
            set_if("TIME", "5:00")
            tf = "5 Rnd (5-5)" if f["scheduled_seconds"] == 1500 else "3 Rnd (5-5)"
            ctf = hist_col(results, "TIME_FORMAT", "TIME FORMAT")
            if ctf is not None:
                row[ctf] = tf
            else:
                row["TIME_FORMAT"] = tf
            fake_rows.append(row)

        results = pd.concat([results, pd.DataFrame(fake_rows)], ignore_index=True, sort=False)
        frame = build_prefight_perspective_rows(events, results, tables["stats"], tables["fighters"])
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        target = frame[
            (frame["event"].astype(str) == EVENT_NAME)
            & (frame["date"].dt.date == pd.Timestamp("2026-10-24").date())
        ].copy()

    if len(target) != 2 * len(CARD):
        found = target[["fighter", "opponent"]].to_dict("records") if len(target) else []
        raise RuntimeError(f"expected {2 * len(CARD)} prospective historical rows, got {len(target)}; rows={found}")

    return target, source_pairs, int(supplemental_rows)


def add_historical_and_unified(payload: dict, current_hazards: list[np.ndarray]):
    prospective, source_pairs, supplemental_rows = historical_prospective_frame()

    hist_dir = ROOT / "artifacts/historical_conditional_through_2026-10-17"
    hist_winner = joblib.load(hist_dir / "historical_winner_model.joblib")
    hist_method = joblib.load(hist_dir / "historical_method_model.joblib")
    hist_timing = joblib.load(hist_dir / "historical_timing_model.joblib")

    oof = json.loads((ROOT / "data/unified/oof_global_unified_shadow.json").read_text())
    w_winner = float(oof["winner"]["weight_current"])
    w_method = float(oof["method"]["weight_current"])
    w_timing = float(oof["timing"]["weight_current"])

    p_hist_all = hist_winner.predict_proba(prospective)
    p_hist_series = pd.Series(p_hist_all, index=prospective.index)
    hist_joint_all = hist_method.predict_joint_probabilities(prospective)

    timing_base = symmetric_timing_frame(prospective)
    timing_base["scheduled_seconds"] = (
        pd.to_numeric(timing_base["scheduled_rounds"], errors="coerce") * 300
    ).astype(int)
    timing_encoded = hist_timing_encode_transform(timing_base, hist_timing.rate_encoders)
    timing_by_id = timing_encoded.set_index("fight_id", drop=False)

    for i, (f, a_src_b_src, row) in enumerate(zip(CARD, source_pairs, payload["fights"]), 1):
        a_src, b_src = a_src_b_src
        subset = prospective[
            prospective["fighter"].map(norm_name).eq(norm_name(a_src))
            & prospective["opponent"].map(norm_name).eq(norm_name(b_src))
        ]
        if len(subset) != 1:
            raise RuntimeError(f"could not uniquely align historical A row for {f['a']} vs {f['b']}")
        idx = subset.index[0]
        fight_id = str(prospective.loc[idx, "fight_id"])

        p_hist_a = float(p_hist_series.loc[idx])
        hist_joint_row = hist_joint_all.loc[idx]
        hist_joint = {
            "A_KO": float(hist_joint_row["WIN_KO_TKO"]),
            "A_SUB": float(hist_joint_row["WIN_SUB"]),
            "A_DEC": float(hist_joint_row["WIN_DEC"]),
            "B_KO": float(hist_joint_row["LOSS_KO_TKO"]),
            "B_SUB": float(hist_joint_row["LOSS_SUB"]),
            "B_DEC": float(hist_joint_row["LOSS_DEC"]),
        }

        if fight_id not in timing_by_id.index:
            raise RuntimeError(f"historical timing row missing for {fight_id}")
        htrow = timing_by_id.loc[fight_id]
        if isinstance(htrow, pd.DataFrame):
            htrow = htrow.iloc[0]
        scheduled = int(f["scheduled_seconds"])
        hist_timing_direct = {
            k: float(v)
            for k, v in hist_timing.market_probabilities_from_encoded(htrow, scheduled).items()
        }
        hist_hazards = np.asarray(hist_timing._hazards(htrow, scheduled), dtype=float)

        p_cur_a = float(row["winner_reference_p_a"])
        p_uni_a = float(binary_logit_pool([p_cur_a], [p_hist_a], w_winner)[0])

        cur_joint = np.asarray([[float(row["joint_calibrated"][k]) for k in METHOD_KEYS]], dtype=float)
        hist_joint_arr = np.asarray([[hist_joint[k] for k in METHOD_KEYS]], dtype=float)
        uni_joint_arr = multiclass_log_pool(cur_joint, hist_joint_arr, w_method)[0]
        uni_joint = {k: float(uni_joint_arr[j]) for j, k in enumerate(METHOD_KEYS)}

        uni_hazards = blend_hazards(
            current_hazards[i - 1],
            hist_hazards,
            w_timing,
            current_bin_seconds=30,
            historical_bin_seconds=int(hist_timing.hazard_model.bin_seconds),
            output_bin_seconds=30,
        )
        uni_timing_direct = {
            k: float(v) for k, v in markets_from_hazards(uni_hazards, scheduled, bin_seconds=30).items()
        }

        row["historical_shadow"] = {
            "source_fighter_a": a_src,
            "source_fighter_b": b_src,
            "winner_p_a": p_hist_a,
            "winner_pick": f["a"] if p_hist_a >= 0.5 else f["b"],
            "joint_method": hist_joint,
            "double_chance": double_chance(hist_joint),
            "timing_direct": hist_timing_direct,
            "history_end": "2026-10-17",
        }
        row["oof_unified_shadow"] = {
            "status": "PREFERRED_PROSPECTIVE_SHADOW_NOT_PROMOTED",
            "winner_weight_current": w_winner,
            "method_weight_current": w_method,
            "timing_weight_current": w_timing,
            "winner_p_a": p_uni_a,
            "winner_pick": f["a"] if p_uni_a >= 0.5 else f["b"],
            "joint_method": uni_joint,
            "double_chance": double_chance(uni_joint),
            "joint_sim_10000": simulate_joint(uni_joint, BASE_SEED + 500 + i),
            "timing_direct": uni_timing_direct,
            "timing_sim_10000": simulate_timing_hazards(uni_hazards, scheduled, BASE_SEED + 1000 + i),
            "winner_disagrees_with_reference": (p_uni_a >= 0.5) != (p_cur_a >= 0.5),
            "historical_disagrees_with_reference": (p_hist_a >= 0.5) != (p_cur_a >= 0.5),
        }

    payload["model_state"]["historical_shadow"] = "historical conditional winner/method/timing through 2026-10-17"
    payload["model_state"]["oof_unified_shadow"] = {
        "status": oof["status"],
        "source_cutoff": oof["source_cutoff"],
        "winner_weight_current": w_winner,
        "method_weight_current": w_method,
        "timing_weight_current": w_timing,
        "promotion": False,
        "official_model_unchanged": True,
    }
    payload["historical_source_refresh"] = {
        "supplemental_result_rows_applied": supplemental_rows,
        "prospective_rows": int(len(prospective)),
        "synthetic_outcomes_used_only_to_emit_prefight_rows": True,
        "synthetic_outcomes_used_as_features_or_targets_for_prediction": False,
    }


def main():
    payload, current_hazards = current_payload_and_hazards()
    add_historical_and_unified(payload, current_hazards)

    payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["stage_a_frozen"] = False
    payload["research_tape_complete"] = False
    payload["weigh_in_context_status"] = "NOT_YET_IN_MODEL_RAW"
    payload["governance"] = {
        "official_reference_unchanged": True,
        "historical_shadow_only": True,
        "oof_unified_shadow_only": True,
        "pr_1_merge_or_promotion_performed": False,
        "odds_used": False,
        "note": "Model-raw three-view artifact only. Do not treat as final Stage A freeze until research/tape verification is attached.",
    }

    out = ROOT / "data/locks/ufc333_2026-10-24"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "stage_a_model_raw_three_view.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    audit = {
        "event": EVENT_NAME,
        "event_date": "2026-10-24",
        "card_fights": len(CARD),
        "odds_used": False,
        "stage_a_frozen": False,
        "post_event_history_through": "2026-10-17",
        "current_joint_simulations_per_fight": TRIALS,
        "current_timing_simulations_per_fight": TRIALS,
        "unified_joint_simulations_per_fight": TRIALS,
        "unified_timing_simulations_per_fight": TRIALS,
        "required_next_step": "complete tape/research verification, attach provenance, then freeze final Stage A before Stage B prices",
    }
    (out / "stage_a_model_raw_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8"
    )

    summary = []
    for r in payload["fights"]:
        p = float(r["winner_reference_p_a"])
        h = float(r["historical_shadow"]["winner_p_a"])
        u = float(r["oof_unified_shadow"]["winner_p_a"])
        summary.append({
            "fight_no": r["fight_no"],
            "fight": f'{r["a"]} vs {r["b"]}',
            "reference_pick": r["a"] if p >= 0.5 else r["b"],
            "reference_probability": max(p, 1 - p),
            "historical_pick": r["a"] if h >= 0.5 else r["b"],
            "historical_probability": max(h, 1 - h),
            "unified_pick": r["a"] if u >= 0.5 else r["b"],
            "unified_probability": max(u, 1 - u),
            "reference_vs_unified_disagreement": (p >= 0.5) != (u >= 0.5),
            "reference_vs_historical_disagreement": (p >= 0.5) != (h >= 0.5),
        })
    (out / "stage_a_model_raw_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({"status": "MODEL_RAW_NOT_FROZEN", "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
