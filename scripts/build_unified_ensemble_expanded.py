#!/usr/bin/env python3
"""Build the expanded WSHL-X unified ensemble through UFC Edmonton.

This is the post-Edmonton candidate builder. It preserves the original Edmonton
holdout experiment separately and then admits Edmonton as past data for future use.
Recovered historical cards are admitted head-by-head only where contemporaneous,
pre-result probabilities are honestly recoverable. Missing heads are never imputed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import build_unified_ensemble as base
from wshlx_ufc.ensemble_eligibility import (
    filter_lock_payload,
    merge_unsupported_pairs,
    norm_name,
    unsupported_pairs_by_date,
    unsupported_result_pairs_by_date,
)
from wshlx_ufc.historical_data import load_source_files
from wshlx_ufc.historical_eval_exports import (
    method_test_predictions,
    timing_test_predictions,
    winner_test_predictions,
)
from wshlx_ufc.historical_outcomes import METHOD_STATES
from wshlx_ufc.unified_ensemble import (
    binary_logit_pool,
    fit_binary_blend,
    fit_grouped_binary_blend,
    fit_multiclass_blend,
    multiclass_log_pool,
)

NORMAL_LOCKS = {
    "2026-09-19": ROOT / "data/locks/ufc331_2026-09-19/stage_a_model_raw.json",
    "2026-09-26": ROOT / "data/locks/ufcvegas121_2026-09-26/stage_a_model_raw_v031_identity_audited.json",
    "2026-10-03": ROOT / "data/locks/ufc332_2026-10-03/stage_a_model_raw_v032_identity_audited.json",
    "2026-10-10": ROOT / "data/locks/ufcvegas122_2026-10-10/stage_a_model_raw_v033.json",
    "2026-10-17": ROOT / "data/locks/ufcedmonton_2026-10-17/stage_a_model_raw_v033.json",
}
RECOVERED_WINNER = ROOT / "data/recovered/recovered_winner_locks_2026-08-08_2026-08-15.csv"
RECOVERED_FULL = ROOT / "data/recovered/recovered_full_head_locks_2026-08-29_2026-09-05.csv"
RECOVERED_TIMING = ROOT / "data/recovered/recovered_timing_locks_2026-08-29_2026-09-05.csv"
TRAIN_THROUGH = "2026-10-17"
SIX_KEYS = base.SIX_KEYS
HIST_METHOD_COLS = base.HIST_METHOD_COLS
TIMING_MARKETS = base.TIMING_MARKETS
CURRENT_TIMING_KEYS = base.CURRENT_TIMING_KEYS


def _historical_bundle(frame: pd.DataFrame, results: pd.DataFrame):
    hw = winner_test_predictions(frame)
    hm = method_test_predictions(frame)
    ht = timing_test_predictions(frame, results).set_index("fight_id", drop=False)
    return hw, hm, ht


def _historical_match(date: str, a: str, b: str, hw: pd.DataFrame):
    return base.match_oriented_winner(date, {"a": a, "b": b}, hw)


def _method_row(date: str, a: str, b: str, current: np.ndarray, hw, hm) -> dict:
    wrow = _historical_match(date, a, b, hw)
    fight_id = str(wrow["fight_id"])
    mrow = base.oriented_method_row(fight_id, a, hm)
    hist = np.asarray([float(mrow[c]) for c in HIST_METHOD_COLS], dtype=float)
    hist /= hist.sum()
    state = str(mrow["method_target"])
    if state not in METHOD_STATES:
        raise RuntimeError(f"Unsupported method target {state} for {date} {a} vs {b}")
    cur = np.asarray(current, dtype=float)
    cur = np.clip(cur, 1e-12, None)
    cur /= cur.sum()
    row = {
        "date": date,
        "fight_id": fight_id,
        "a": a,
        "b": b,
        "actual_joint_class": list(METHOD_STATES).index(state),
    }
    for i, key in enumerate(SIX_KEYS):
        row[f"current_{key}"] = float(cur[i])
        row[f"historical_{key}"] = float(hist[i])
    return row


def _winner_row(date: str, a: str, b: str, current_p_a: float, hw, source: str) -> dict:
    wrow = _historical_match(date, a, b, hw)
    return {
        "date": date,
        "fight_id": str(wrow["fight_id"]),
        "a": a,
        "b": b,
        "actual_a_win": int(wrow["win"]),
        "current_winner_p_a": float(current_p_a),
        "historical_winner_p_a": float(wrow["historical_p_win"]),
        "source": source,
    }


def _timing_rows(date: str, a: str, b: str, current: dict[str, float], hw, ht, source: str) -> list[dict]:
    wrow = _historical_match(date, a, b, hw)
    fight_id = str(wrow["fight_id"])
    if fight_id not in ht.index:
        raise RuntimeError(f"Historical timing prediction missing for {date} {a} vs {b}")
    hrow = ht.loc[fight_id]
    if isinstance(hrow, pd.DataFrame):
        hrow = hrow.iloc[0]
    scheduled = int(hrow["scheduled_seconds"])
    finish_seconds = float(hrow["finish_seconds"])
    observed = int(hrow["finish_observed"])
    rows = []
    for market in TIMING_MARKETS:
        if market not in current:
            continue
        hcol = f"historical_{market}"
        if hcol not in hrow or pd.isna(hrow[hcol]):
            continue
        if (market.startswith("ROUND_4") or market.startswith("ROUND_5")) and scheduled != 1500:
            continue
        rows.append({
            "date": date,
            "fight_id": fight_id,
            "fight": f"{a} vs {b}",
            "market": market,
            "actual": base.timing_actual(market, finish_seconds, observed, scheduled),
            "current_probability": float(current[market]),
            "historical_probability": float(hrow[hcol]),
            "source": source,
        })
    return rows


def build_rows(frame: pd.DataFrame, results: pd.DataFrame, unsupported) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    hw, hm, ht = _historical_bundle(frame, results)
    winner_rows: list[dict] = []
    method_rows: list[dict] = []
    timing_rows: list[dict] = []
    provenance = {
        "winner_only_recovered": [],
        "full_head_recovered": [],
        "normal_frozen_locks": [],
        "excluded_unsupported": [],
    }

    if RECOVERED_WINNER.exists():
        rw = pd.read_csv(RECOVERED_WINNER)
        for _, r in rw.iterrows():
            date = str(r["event_date"])
            pair = tuple(sorted((norm_name(r["a"]), norm_name(r["b"]))))
            if pair in unsupported.get(pd.Timestamp(date).normalize(), set()):
                provenance["excluded_unsupported"].append(f"{date}: {r['a']} vs {r['b']}")
                continue
            winner_rows.append(_winner_row(date, str(r["a"]), str(r["b"]), float(r["p_a_win"]), hw, "recovered_winner_only"))
        provenance["winner_only_recovered"] = sorted(rw["event_date"].astype(str).unique().tolist())

    if RECOVERED_FULL.exists():
        rf = pd.read_csv(RECOVERED_FULL)
        for _, r in rf.iterrows():
            date = str(r["event_date"])
            a, b = str(r["a"]), str(r["b"])
            pair = tuple(sorted((norm_name(a), norm_name(b))))
            if pair in unsupported.get(pd.Timestamp(date).normalize(), set()):
                provenance["excluded_unsupported"].append(f"{date}: {a} vs {b}")
                continue
            winner_rows.append(_winner_row(date, a, b, float(r["p_a_win"]), hw, "recovered_full_head"))
            current = np.asarray([float(r[k]) for k in SIX_KEYS], dtype=float)
            method_rows.append(_method_row(date, a, b, current, hw, hm))
        provenance["full_head_recovered"] = sorted(rf["event_date"].astype(str).unique().tolist())

    timing_lookup = {}
    if RECOVERED_TIMING.exists():
        rt = pd.read_csv(RECOVERED_TIMING)
        col_map = {
            "gtd_yes": "GTD_YES",
            "over_1_5": "OVER_1.5",
            "over_2_5": "OVER_2.5",
            "round_2_starts_yes": "ROUND_2_STARTS_YES",
            "round_3_starts_yes": "ROUND_3_STARTS_YES",
            "round_4_starts_yes": "ROUND_4_STARTS_YES",
            "round_5_starts_yes": "ROUND_5_STARTS_YES",
        }
        for _, r in rt.iterrows():
            date = str(r["event_date"]); a, b = str(r["a"]), str(r["b"])
            current = {}
            for col, market in col_map.items():
                if col in r and not pd.isna(r[col]):
                    current[market] = float(r[col])
            timing_rows.extend(_timing_rows(date, a, b, current, hw, ht, "recovered_timing"))
            timing_lookup[(date, norm_name(a), norm_name(b))] = True

    for date, path in NORMAL_LOCKS.items():
        payload = base.read_lock(path)
        payload, dropped = filter_lock_payload(payload, card_date=date, unsupported=unsupported)
        provenance["excluded_unsupported"].extend(f"{date}: {x}" for x in dropped)
        for fight in payload["fights"]:
            a, b = str(fight["a"]), str(fight["b"])
            winner_rows.append(_winner_row(date, a, b, base.current_winner_probability(fight), hw, "native_frozen_lock"))
            method_rows.append(_method_row(date, a, b, base.current_method_distribution(fight), hw, hm))
            timing_rows.extend(_timing_rows(date, a, b, base.current_timing_distribution(fight), hw, ht, "native_frozen_lock"))
        provenance["normal_frozen_locks"].append(date)

    winner = pd.DataFrame(winner_rows).drop_duplicates(["date", "fight_id"], keep="last").sort_values(["date", "fight_id"]).reset_index(drop=True)
    method = pd.DataFrame(method_rows).drop_duplicates(["date", "fight_id"], keep="last").sort_values(["date", "fight_id"]).reset_index(drop=True)
    timing = pd.DataFrame(timing_rows).drop_duplicates(["date", "fight_id", "market"], keep="last").sort_values(["date", "fight_id", "market"]).reset_index(drop=True)
    provenance["excluded_unsupported"] = sorted(set(provenance["excluded_unsupported"]))
    return winner, method, timing, provenance


def _fit_winner(df: pd.DataFrame):
    return fit_binary_blend(df["actual_a_win"], df["current_winner_p_a"], df["historical_winner_p_a"])


def _fit_method(df: pd.DataFrame):
    return fit_multiclass_blend(
        df["actual_joint_class"],
        df[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float),
        df[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float),
    )


def _fit_timing(df: pd.DataFrame):
    return fit_grouped_binary_blend(
        df["actual"], df["current_probability"], df["historical_probability"], df["fight_id"]
    )


def _winner_metrics(df: pd.DataFrame, weight: float) -> dict:
    uni = binary_logit_pool(df["current_winner_p_a"], df["historical_winner_p_a"], weight)
    return {
        "current": base.binary_metrics(df["actual_a_win"], df["current_winner_p_a"]),
        "historical": base.binary_metrics(df["actual_a_win"], df["historical_winner_p_a"]),
        "unified": base.binary_metrics(df["actual_a_win"], uni),
    }


def _method_metrics(df: pd.DataFrame, weight: float) -> dict:
    cur = df[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
    hist = df[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
    uni = multiclass_log_pool(cur, hist, weight)
    return {
        "current": base.method_metrics(df["actual_joint_class"], cur),
        "historical": base.method_metrics(df["actual_joint_class"], hist),
        "unified": base.method_metrics(df["actual_joint_class"], uni),
    }


def _timing_metrics(df: pd.DataFrame, weight: float) -> dict:
    uni = binary_logit_pool(df["current_probability"], df["historical_probability"], weight)
    out = {
        "current": base.binary_metrics(df["actual"], df["current_probability"]),
        "historical": base.binary_metrics(df["actual"], df["historical_probability"]),
        "unified": base.binary_metrics(df["actual"], uni),
        "n_fights": int(df["fight_id"].nunique()),
        "per_market": {},
    }
    for market, g in df.assign(unified_probability=uni).groupby("market"):
        out["per_market"][market] = {
            "current": base.binary_metrics(g["actual"], g["current_probability"]),
            "historical": base.binary_metrics(g["actual"], g["historical_probability"]),
            "unified": base.binary_metrics(g["actual"], g["unified_probability"]),
        }
    return out


def walk_forward(winner: pd.DataFrame, method: pd.DataFrame, timing: pd.DataFrame) -> dict:
    out: dict[str, object] = {"winner": {}, "method": {}, "timing": {}}
    w_rows = []
    for date in sorted(winner["date"].unique()):
        tr = winner[winner["date"] < date]; te = winner[winner["date"] == date]
        if len(tr) < 20 or te.empty:
            continue
        fit = _fit_winner(tr)
        p = binary_logit_pool(te["current_winner_p_a"], te["historical_winner_p_a"], fit.weight_current)
        metrics = base.binary_metrics(te["actual_a_win"], p)
        out["winner"][date] = {"train_n": int(len(tr)), "test_n": int(len(te)), "weight_current": fit.weight_current, "metrics": metrics}
        w_rows.extend(zip(te["actual_a_win"].astype(int), p))
    if w_rows:
        out["winner_overall"] = base.binary_metrics([x[0] for x in w_rows], [x[1] for x in w_rows])

    m_y = []; m_p = []
    for date in sorted(method["date"].unique()):
        tr = method[method["date"] < date]; te = method[method["date"] == date]
        if len(tr) < 20 or te.empty:
            continue
        fit = _fit_method(tr)
        p = multiclass_log_pool(
            te[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float),
            te[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float),
            fit.weight_current,
        )
        metrics = base.method_metrics(te["actual_joint_class"], p)
        out["method"][date] = {"train_n": int(len(tr)), "test_n": int(len(te)), "weight_current": fit.weight_current, "metrics": metrics}
        m_y.extend(te["actual_joint_class"].astype(int).tolist()); m_p.extend(p.tolist())
    if m_y:
        out["method_overall"] = base.method_metrics(m_y, np.asarray(m_p, dtype=float))

    t_y = []; t_p = []
    for date in sorted(timing["date"].unique()):
        tr = timing[timing["date"] < date]; te = timing[timing["date"] == date]
        if tr["fight_id"].nunique() < 20 or te.empty:
            continue
        fit = _fit_timing(tr)
        p = binary_logit_pool(te["current_probability"], te["historical_probability"], fit.weight_current)
        metrics = base.binary_metrics(te["actual"], p)
        out["timing"][date] = {
            "train_fights": int(tr["fight_id"].nunique()), "test_fights": int(te["fight_id"].nunique()),
            "test_market_rows": int(len(te)), "weight_current": fit.weight_current, "metrics": metrics,
        }
        t_y.extend(te["actual"].astype(int).tolist()); t_p.extend(p.tolist())
    if t_y:
        out["timing_overall"] = base.binary_metrics(t_y, t_p)
    return out


def main() -> int:
    frame_path = ROOT / "data/historical/prefight_perspective_rows.csv"
    if not frame_path.exists():
        raise SystemExit("Run build_historical_model.py before expanded unified build")
    frame = pd.read_csv(frame_path, low_memory=False)
    tables = load_source_files(ROOT / "data/raw/ufcstats_mirror")
    tables = base.apply_results_supplements(tables, ROOT / "data/supplemental/results")
    unsupported = merge_unsupported_pairs(
        unsupported_pairs_by_date(frame),
        unsupported_result_pairs_by_date(tables["results"], tables["events"]),
    )
    base.norm_name = norm_name

    winner, method, timing, provenance = build_rows(frame, tables["results"], unsupported)
    if winner.empty or method.empty or timing.empty:
        raise RuntimeError("Expanded unified build produced an empty head")
    if winner["date"].max() != TRAIN_THROUGH or method["date"].max() != TRAIN_THROUGH or timing["date"].max() != TRAIN_THROUGH:
        raise RuntimeError("Expanded unified heads do not all include Edmonton through 2026-10-17")

    wfit = _fit_winner(winner); mfit = _fit_method(method); tfit = _fit_timing(timing)
    weights = {"winner": wfit.weight_current, "method": mfit.weight_current, "timing": tfit.weight_current}
    wf = walk_forward(winner, method, timing)

    outdir = ROOT / "data/unified"
    outdir.mkdir(parents=True, exist_ok=True)

    wp = binary_logit_pool(winner["current_winner_p_a"], winner["historical_winner_p_a"], weights["winner"])
    winner_audit = winner.copy(); winner_audit["unified_winner_p_a"] = wp
    winner_audit.to_csv(outdir / "expanded_unified_winner_predictions.csv", index=False)

    cur = method[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
    hist = method[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
    mp = multiclass_log_pool(cur, hist, weights["method"])
    method_audit = method.copy()
    for i, key in enumerate(SIX_KEYS): method_audit[f"unified_{key}"] = mp[:, i]
    method_audit.to_csv(outdir / "expanded_unified_method_predictions.csv", index=False)

    tp = binary_logit_pool(timing["current_probability"], timing["historical_probability"], weights["timing"])
    timing_audit = timing.copy(); timing_audit["unified_probability"] = tp
    timing_audit.to_csv(outdir / "expanded_unified_timing_predictions.csv", index=False)

    weights_payload = {
        "status": "EXPANDED_UNIFIED_ENSEMBLE_SHADOW_NOT_PROMOTED",
        "trained_through": TRAIN_THROUGH,
        "odds_used": False,
        "weight_meaning": "weight_current; historical weight = 1 - weight_current",
        "grid_step": 0.025,
        "head_specific_eligibility": True,
        "winner": wfit.to_dict(), "method": mfit.to_dict(), "timing": tfit.to_dict(),
        "training_population": {
            "winner_fights": int(len(winner)),
            "winner_dates": sorted(winner["date"].unique().tolist()),
            "method_fights": int(len(method)),
            "method_dates": sorted(method["date"].unique().tolist()),
            "timing_fights": int(timing["fight_id"].nunique()),
            "timing_market_rows": int(len(timing)),
            "timing_dates": sorted(timing["date"].unique().tolist()),
        },
        "provenance": provenance,
        "governance": {
            "edmonton_now_training_data": True,
            "edmonton_holdout_must_be_preserved_separately": True,
            "august_22_not_admitted": "Final fight-day probabilities have not yet been recovered at sufficient precision; pre-weigh-in values are not silently substituted.",
            "older_legacy_cards_not_admitted": "Odds-influenced, conflicting, aggregate-only, or result-era reconstructions remain excluded.",
            "promotion": False,
        },
    }
    (outdir / "expanded_unified_weights.json").write_text(json.dumps(weights_payload, indent=2) + "\n", encoding="utf-8")

    metrics = {
        "status": "SHADOW_ONLY",
        "full_fit_descriptive": {
            "winner": _winner_metrics(winner, weights["winner"]),
            "method": _method_metrics(method, weights["method"]),
            "timing": _timing_metrics(timing, weights["timing"]),
        },
        "chronological_walk_forward": wf,
        "warning": "Full-fit metrics are descriptive, not prospective proof. Use chronological walk-forward and separately preserved Edmonton holdout evidence for validation.",
    }
    (outdir / "expanded_unified_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "status": "EXPANDED_UNIFIED_BUILD_COMPLETE_SHADOW",
        "trained_through": TRAIN_THROUGH,
        "weights": weights,
        "winner_fights": int(len(winner)), "method_fights": int(len(method)),
        "timing_fights": int(timing["fight_id"].nunique()), "timing_market_rows": int(len(timing)),
        "files": [
            "expanded_unified_weights.json", "expanded_unified_metrics.json",
            "expanded_unified_winner_predictions.csv", "expanded_unified_method_predictions.csv",
            "expanded_unified_timing_predictions.csv",
        ],
    }
    (outdir / "expanded_unified_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": manifest, "weights": weights, "walk_forward": wf}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
