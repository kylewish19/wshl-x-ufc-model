#!/usr/bin/env python3
"""Evaluate context-aware current/historical blending for all three unified heads.

The historical component is informed by the full causal UFC history.  Direct
current-vs-historical blend fitting is restricted to fights where a contemporaneous
WSHL-X current-model probability was honestly recoverable.  Context is prefight only.
All outputs are shadow diagnostics; nothing here promotes a production model.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import build_unified_ensemble as base
from wshlx_ufc.contextual_ensemble import (
    fit_contextual_binary_blend,
    fit_contextual_grouped_binary_blend,
    fit_contextual_multiclass_blend,
    grouped_binary_log_loss,
    rowwise_binary_logit_pool,
    rowwise_multiclass_log_pool,
)
from wshlx_ufc.historical_data import build_prefight_perspective_rows, load_source_files
from wshlx_ufc.unified_ensemble import (
    binary_logit_pool,
    fit_binary_blend,
    fit_grouped_binary_blend,
    fit_multiclass_blend,
    multiclass_log_pool,
)

RAW_ROOT = ROOT / "data/raw/ufcedmonton_2026-10-17"
UNIFIED_ROOT = ROOT / "data/unified"
OUT_ROOT = ROOT / "reports/contextual_unified_through_2026-10-17"
SHADOW_PATH = UNIFIED_ROOT / "contextual_unified_shadow.json"
SIX_KEYS = base.SIX_KEYS
L2 = 8.0
INTERCEPT_L2 = 2.0

WINNER_FEATURES = (
    "model_disagreement",
    "historical_confidence",
    "min_ufc_fights_log",
    "experience_gap_log",
    "age_gap_abs",
    "reach_gap_abs",
    "max_layoff_log",
)
METHOD_FEATURES = (
    "method_js",
    "historical_method_confidence",
    "min_ufc_fights_log",
    "experience_gap_log",
    "grappling_access_log",
    "combined_finish_rate",
    "combined_sub_rate",
    "upper_weight_class",
)
TIMING_FEATURES = (
    "prob_disagreement",
    "historical_confidence",
    "min_ufc_fights_log",
    "max_layoff_log",
    "combined_finish_rate",
    "horizon_fraction",
    "upper_weight_class",
    "five_round",
)


def _json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def _num(frame: pd.DataFrame, col: str) -> pd.Series:
    if col not in frame:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[col], errors="coerce")


def _row_mean(*series: pd.Series) -> pd.Series:
    return pd.concat(series, axis=1).mean(axis=1, skipna=True)


def fight_context_table(frame: pd.DataFrame) -> pd.DataFrame:
    """One orientation-invariant prefight context row per fight."""
    f = frame.copy()
    f["date"] = pd.to_datetime(f["date"], errors="coerce")
    f = f.sort_values(["date", "fight_id", "fighter"]).drop_duplicates("fight_id", keep="first").copy()

    a_fights = _num(f, "ufc_fights")
    b_fights = _num(f, "opp_ufc_fights")
    a_age, b_age = _num(f, "age"), _num(f, "opp_age")
    a_reach, b_reach = _num(f, "reach"), _num(f, "opp_reach")
    a_lay, b_lay = _num(f, "layoff_days"), _num(f, "opp_layoff_days")

    min_fights = pd.concat([a_fights, b_fights], axis=1).min(axis=1, skipna=True)
    experience_gap = (a_fights - b_fights).abs()
    max_layoff = pd.concat([a_lay, b_lay], axis=1).max(axis=1, skipna=True)

    td_total = _num(f, "td_per15").fillna(0) + _num(f, "opp_td_per15").fillna(0)
    sub_total = _num(f, "sub_att_per15").fillna(0) + _num(f, "opp_sub_att_per15").fillna(0)
    ctrl_total = _num(f, "ctrl_sec_per_min").fillna(0) + _num(f, "opp_ctrl_sec_per_min").fillna(0)
    grappling_access = td_total + 2.0 * sub_total + 0.25 * ctrl_total

    weight = f.get("weight_class", pd.Series("", index=f.index)).fillna("").astype(str)
    upper_weight = weight.str.contains("Heavyweight", case=False, regex=False).astype(float)
    rounds = _num(f, "scheduled_rounds")

    out = pd.DataFrame({
        "fight_id": f["fight_id"].astype(str),
        "context_date": f["date"].dt.strftime("%Y-%m-%d"),
        "weight_class": weight,
        "scheduled_rounds": rounds,
        "min_ufc_fights": min_fights,
        "min_ufc_fights_log": np.log1p(min_fights.clip(lower=0)),
        "experience_gap": experience_gap,
        "experience_gap_log": np.log1p(experience_gap.clip(lower=0)),
        "age_gap_abs": (a_age - b_age).abs(),
        "reach_gap_abs": (a_reach - b_reach).abs(),
        "max_layoff_days": max_layoff,
        "max_layoff_log": np.log1p(max_layoff.clip(lower=0)),
        "combined_finish_rate": _row_mean(_num(f, "finish_win_rate"), _num(f, "opp_finish_win_rate")),
        "combined_sub_rate": _row_mean(_num(f, "sub_win_rate"), _num(f, "opp_sub_win_rate")),
        "combined_ko_rate": _row_mean(_num(f, "ko_win_rate"), _num(f, "opp_ko_win_rate")),
        "grappling_access_log": np.log1p(grappling_access.clip(lower=0)),
        "upper_weight_class": upper_weight,
        "five_round": (rounds >= 5).astype(float),
    })
    out["sparse_any"] = (out["min_ufc_fights"] < 2).astype(float)
    out["established_pair"] = (out["min_ufc_fights"] >= 4).astype(float)
    out["large_experience_gap"] = (out["experience_gap"] >= 5).astype(float)
    out["large_age_gap"] = (out["age_gap_abs"] >= 5).astype(float)
    out["large_reach_gap"] = (out["reach_gap_abs"] >= 4).astype(float)
    out["long_layoff"] = (out["max_layoff_days"] >= 365).astype(float)
    return out.reset_index(drop=True)


def _js_divergence(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aa = np.clip(np.asarray(a, dtype=float), 1e-12, 1.0)
    bb = np.clip(np.asarray(b, dtype=float), 1e-12, 1.0)
    aa /= aa.sum(axis=1, keepdims=True)
    bb /= bb.sum(axis=1, keepdims=True)
    mm = 0.5 * (aa + bb)
    return 0.5 * np.sum(aa * np.log(aa / mm), axis=1) + 0.5 * np.sum(bb * np.log(bb / mm), axis=1)


def _norm_entropy(p: np.ndarray) -> np.ndarray:
    pp = np.clip(np.asarray(p, dtype=float), 1e-12, 1.0)
    pp /= pp.sum(axis=1, keepdims=True)
    return -np.sum(pp * np.log(pp), axis=1) / math.log(pp.shape[1])


def add_winner_context(df: pd.DataFrame, ctx: pd.DataFrame) -> pd.DataFrame:
    out = df.merge(ctx, on="fight_id", how="left", validate="many_to_one")
    out["model_disagreement"] = (out["current_winner_p_a"] - out["historical_winner_p_a"]).abs()
    out["historical_confidence"] = 2.0 * (out["historical_winner_p_a"] - 0.5).abs()
    out["current_confidence"] = 2.0 * (out["current_winner_p_a"] - 0.5).abs()
    out["high_disagreement"] = (out["model_disagreement"] >= 0.15).astype(float)
    return out


def add_method_context(df: pd.DataFrame, ctx: pd.DataFrame) -> pd.DataFrame:
    out = df.merge(ctx, on="fight_id", how="left", validate="many_to_one")
    cur = out[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
    hist = out[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
    out["method_js"] = _js_divergence(cur, hist)
    out["historical_method_confidence"] = 1.0 - _norm_entropy(hist)
    out["current_method_confidence"] = 1.0 - _norm_entropy(cur)
    out["high_disagreement"] = (out["method_js"] >= 0.05).astype(float)
    return out


def _timing_horizon(row: pd.Series) -> float:
    market = str(row["market"])
    rounds = int(row.get("scheduled_rounds") or 3)
    scheduled = rounds * 300
    fixed = {
        "OVER_1.5": 450,
        "OVER_2.5": 750,
        "ROUND_2_STARTS_YES": 300,
        "ROUND_3_STARTS_YES": 600,
        "ROUND_4_STARTS_YES": 900,
        "ROUND_5_STARTS_YES": 1200,
    }
    seconds = scheduled if market == "GTD_YES" else fixed.get(market, scheduled)
    return float(seconds / max(scheduled, 1))


def add_timing_context(df: pd.DataFrame, ctx: pd.DataFrame) -> pd.DataFrame:
    out = df.merge(ctx, on="fight_id", how="left", validate="many_to_one")
    out["prob_disagreement"] = (out["current_probability"] - out["historical_probability"]).abs()
    out["historical_confidence"] = 2.0 * (out["historical_probability"] - 0.5).abs()
    out["current_confidence"] = 2.0 * (out["current_probability"] - 0.5).abs()
    out["horizon_fraction"] = out.apply(_timing_horizon, axis=1)
    out["high_disagreement"] = (out["prob_disagreement"] >= 0.15).astype(float)
    return out


def _weight_summary(frame: pd.DataFrame, weights: np.ndarray) -> dict:
    work = frame.copy()
    work["weight_current"] = np.asarray(weights, dtype=float)
    work["weight_historical"] = 1.0 - work["weight_current"]

    def stats(g: pd.DataFrame) -> dict:
        return {
            "n": int(len(g)),
            "mean_current": float(g["weight_current"].mean()),
            "median_current": float(g["weight_current"].median()),
            "mean_historical": float(g["weight_historical"].mean()),
            "min_current": float(g["weight_current"].min()),
            "max_current": float(g["weight_current"].max()),
        }

    out = {"overall": stats(work), "regimes": {}}
    regimes = {
        "sparse_any": "sparse_any",
        "established_pair": "established_pair",
        "large_experience_gap": "large_experience_gap",
        "large_age_gap": "large_age_gap",
        "large_reach_gap": "large_reach_gap",
        "long_layoff": "long_layoff",
        "upper_weight_class": "upper_weight_class",
        "five_round": "five_round",
        "high_disagreement": "high_disagreement",
    }
    for name, col in regimes.items():
        if col in work:
            g = work[pd.to_numeric(work[col], errors="coerce").fillna(0) > 0.5]
            if len(g):
                out["regimes"][name] = stats(g)
    return out


def _winner_full(df: pd.DataFrame) -> tuple[dict, dict, np.ndarray, np.ndarray]:
    global_fit = fit_binary_blend(df["actual_a_win"], df["current_winner_p_a"], df["historical_winner_p_a"])
    gate = fit_contextual_binary_blend(
        df,
        df["actual_a_win"],
        df["current_winner_p_a"],
        df["historical_winner_p_a"],
        WINNER_FEATURES,
        prior_weight_current=global_fit.weight_current,
        l2=L2,
        intercept_l2=INTERCEPT_L2,
    )
    w = gate.weights(df)
    contextual = rowwise_binary_logit_pool(df["current_winner_p_a"], df["historical_winner_p_a"], w)
    global_p = binary_logit_pool(df["current_winner_p_a"], df["historical_winner_p_a"], global_fit.weight_current)
    metrics = {
        "current": base.binary_metrics(df["actual_a_win"], df["current_winner_p_a"]),
        "historical": base.binary_metrics(df["actual_a_win"], df["historical_winner_p_a"]),
        "global_unified": base.binary_metrics(df["actual_a_win"], global_p),
        "contextual_unified": base.binary_metrics(df["actual_a_win"], contextual),
    }
    return global_fit.to_dict(), gate.to_dict(), w, contextual


def _method_full(df: pd.DataFrame) -> tuple[dict, dict, np.ndarray, np.ndarray]:
    cur = df[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
    hist = df[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
    y = df["actual_joint_class"].to_numpy(int)
    global_fit = fit_multiclass_blend(y, cur, hist)
    gate = fit_contextual_multiclass_blend(
        df, y, cur, hist, METHOD_FEATURES,
        prior_weight_current=global_fit.weight_current,
        l2=L2, intercept_l2=INTERCEPT_L2,
    )
    w = gate.weights(df)
    contextual = rowwise_multiclass_log_pool(cur, hist, w)
    global_p = multiclass_log_pool(cur, hist, global_fit.weight_current)
    metrics = {
        "current": base.method_metrics(y, cur),
        "historical": base.method_metrics(y, hist),
        "global_unified": base.method_metrics(y, global_p),
        "contextual_unified": base.method_metrics(y, contextual),
    }
    return global_fit.to_dict(), gate.to_dict(), w, contextual


def _timing_full(df: pd.DataFrame) -> tuple[dict, dict, np.ndarray, np.ndarray, dict]:
    y = df["actual"].to_numpy(int)
    cur = df["current_probability"].to_numpy(float)
    hist = df["historical_probability"].to_numpy(float)
    groups = df["fight_id"].astype(str).to_numpy()
    global_fit = fit_grouped_binary_blend(y, cur, hist, groups)
    gate = fit_contextual_grouped_binary_blend(
        df, y, cur, hist, groups, TIMING_FEATURES,
        prior_weight_current=global_fit.weight_current,
        l2=L2, intercept_l2=INTERCEPT_L2,
    )
    w = gate.weights(df)
    contextual = rowwise_binary_logit_pool(cur, hist, w)
    global_p = binary_logit_pool(cur, hist, global_fit.weight_current)
    metrics = {
        "current": base.binary_metrics(y, cur),
        "historical": base.binary_metrics(y, hist),
        "global_unified": base.binary_metrics(y, global_p),
        "contextual_unified": base.binary_metrics(y, contextual),
    }
    grouped = {
        "current": grouped_binary_log_loss(y, cur, groups),
        "historical": grouped_binary_log_loss(y, hist, groups),
        "global_unified": grouped_binary_log_loss(y, global_p, groups),
        "contextual_unified": grouped_binary_log_loss(y, contextual, groups),
    }
    return global_fit.to_dict(), gate.to_dict(), w, contextual, grouped


def winner_walk_forward(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = []
    folds = {}
    for date in sorted(df["date"].astype(str).unique()):
        tr = df[df["date"].astype(str) < date]
        te = df[df["date"].astype(str) == date]
        if len(tr) < 40 or te.empty:
            continue
        global_fit = fit_binary_blend(tr["actual_a_win"], tr["current_winner_p_a"], tr["historical_winner_p_a"])
        gate = fit_contextual_binary_blend(
            tr, tr["actual_a_win"], tr["current_winner_p_a"], tr["historical_winner_p_a"], WINNER_FEATURES,
            prior_weight_current=global_fit.weight_current, l2=L2, intercept_l2=INTERCEPT_L2,
        )
        w = gate.weights(te)
        cp = rowwise_binary_logit_pool(te["current_winner_p_a"], te["historical_winner_p_a"], w)
        gp = binary_logit_pool(te["current_winner_p_a"], te["historical_winner_p_a"], global_fit.weight_current)
        cm = base.binary_metrics(te["actual_a_win"], cp)
        gm = base.binary_metrics(te["actual_a_win"], gp)
        folds[date] = {"train_n": int(len(tr)), "test_n": int(len(te)), "global_weight_current": global_fit.weight_current, "global": gm, "contextual": cm, "mean_context_weight_current": float(np.mean(w))}
        for i, (_, r) in enumerate(te.iterrows()):
            rows.append({"date": date, "fight_id": r["fight_id"], "actual": int(r["actual_a_win"]), "current": float(r["current_winner_p_a"]), "historical": float(r["historical_winner_p_a"]), "global": float(gp[i]), "contextual": float(cp[i]), "context_weight_current": float(w[i])})
    out = pd.DataFrame(rows)
    overall = {}
    if len(out):
        overall = {k: base.binary_metrics(out["actual"], out[k]) for k in ("current", "historical", "global", "contextual")}
    return out, {"folds": folds, "overall": overall}


def method_walk_forward(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = []
    folds = {}
    for date in sorted(df["date"].astype(str).unique()):
        tr = df[df["date"].astype(str) < date]
        te = df[df["date"].astype(str) == date]
        if len(tr) < 40 or te.empty:
            continue
        tr_cur = tr[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
        tr_hist = tr[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
        te_cur = te[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
        te_hist = te[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
        global_fit = fit_multiclass_blend(tr["actual_joint_class"], tr_cur, tr_hist)
        gate = fit_contextual_multiclass_blend(
            tr, tr["actual_joint_class"], tr_cur, tr_hist, METHOD_FEATURES,
            prior_weight_current=global_fit.weight_current, l2=L2, intercept_l2=INTERCEPT_L2,
        )
        w = gate.weights(te)
        cp = rowwise_multiclass_log_pool(te_cur, te_hist, w)
        gp = multiclass_log_pool(te_cur, te_hist, global_fit.weight_current)
        cm = base.method_metrics(te["actual_joint_class"], cp)
        gm = base.method_metrics(te["actual_joint_class"], gp)
        folds[date] = {"train_n": int(len(tr)), "test_n": int(len(te)), "global_weight_current": global_fit.weight_current, "global": gm, "contextual": cm, "mean_context_weight_current": float(np.mean(w))}
        for i, (_, r) in enumerate(te.iterrows()):
            row = {"date": date, "fight_id": r["fight_id"], "actual_joint_class": int(r["actual_joint_class"]), "context_weight_current": float(w[i])}
            for j, key in enumerate(SIX_KEYS):
                row[f"global_{key}"] = float(gp[i, j]); row[f"contextual_{key}"] = float(cp[i, j])
            rows.append(row)
    out = pd.DataFrame(rows)
    overall = {}
    if len(out):
        y = out["actual_joint_class"].to_numpy(int)
        gp = out[[f"global_{k}" for k in SIX_KEYS]].to_numpy(float)
        cp = out[[f"contextual_{k}" for k in SIX_KEYS]].to_numpy(float)
        overall = {"global": base.method_metrics(y, gp), "contextual": base.method_metrics(y, cp)}
    return out, {"folds": folds, "overall": overall}


def timing_walk_forward(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = []
    folds = {}
    for date in sorted(df["date"].astype(str).unique()):
        tr = df[df["date"].astype(str) < date]
        te = df[df["date"].astype(str) == date]
        if tr["fight_id"].nunique() < 40 or te.empty:
            continue
        global_fit = fit_grouped_binary_blend(tr["actual"], tr["current_probability"], tr["historical_probability"], tr["fight_id"])
        gate = fit_contextual_grouped_binary_blend(
            tr, tr["actual"], tr["current_probability"], tr["historical_probability"], tr["fight_id"], TIMING_FEATURES,
            prior_weight_current=global_fit.weight_current, l2=L2, intercept_l2=INTERCEPT_L2,
        )
        w = gate.weights(te)
        cp = rowwise_binary_logit_pool(te["current_probability"], te["historical_probability"], w)
        gp = binary_logit_pool(te["current_probability"], te["historical_probability"], global_fit.weight_current)
        groups = te["fight_id"].astype(str)
        folds[date] = {
            "train_fights": int(tr["fight_id"].nunique()), "test_fights": int(te["fight_id"].nunique()),
            "global_weight_current": global_fit.weight_current,
            "global_grouped_log_loss": grouped_binary_log_loss(te["actual"], gp, groups),
            "contextual_grouped_log_loss": grouped_binary_log_loss(te["actual"], cp, groups),
            "global": base.binary_metrics(te["actual"], gp), "contextual": base.binary_metrics(te["actual"], cp),
            "mean_context_weight_current": float(np.mean(w)),
        }
        for i, (_, r) in enumerate(te.iterrows()):
            rows.append({"date": date, "fight_id": r["fight_id"], "market": r["market"], "actual": int(r["actual"]), "current": float(r["current_probability"]), "historical": float(r["historical_probability"]), "global": float(gp[i]), "contextual": float(cp[i]), "context_weight_current": float(w[i])})
    out = pd.DataFrame(rows)
    overall = {}
    if len(out):
        groups = out["fight_id"].astype(str)
        overall = {
            k: {**base.binary_metrics(out["actual"], out[k]), "grouped_log_loss": grouped_binary_log_loss(out["actual"], out[k], groups)}
            for k in ("current", "historical", "global", "contextual")
        }
    return out, {"folds": folds, "overall": overall}


def main() -> int:
    tables = load_source_files(RAW_ROOT)
    frame = build_prefight_perspective_rows(tables["events"], tables["results"], tables["stats"], tables["fighters"])
    context = fight_context_table(frame)

    winner = add_winner_context(pd.read_csv(UNIFIED_ROOT / "expanded_unified_winner_predictions.csv"), context)
    method = add_method_context(pd.read_csv(UNIFIED_ROOT / "expanded_unified_method_predictions.csv"), context)
    timing = add_timing_context(pd.read_csv(UNIFIED_ROOT / "expanded_unified_timing_predictions.csv"), context)

    wg, wc, ww, wp = _winner_full(winner)
    mg, mc, mw, mp = _method_full(method)
    tg, tc, tw, tp, timing_grouped = _timing_full(timing)

    winner["context_weight_current"] = ww; winner["contextual_probability"] = wp
    method["context_weight_current"] = mw
    for i, key in enumerate(SIX_KEYS): method[f"contextual_{key}"] = mp[:, i]
    timing["context_weight_current"] = tw; timing["contextual_probability"] = tp

    wwf, wwf_report = winner_walk_forward(winner)
    mwf, mwf_report = method_walk_forward(method)
    twf, twf_report = timing_walk_forward(timing)

    # Recompute descriptive full-fit metrics explicitly for the report.
    winner_global_p = binary_logit_pool(winner["current_winner_p_a"], winner["historical_winner_p_a"], wg["weight_current"])
    winner_metrics = {
        "current": base.binary_metrics(winner["actual_a_win"], winner["current_winner_p_a"]),
        "historical": base.binary_metrics(winner["actual_a_win"], winner["historical_winner_p_a"]),
        "global_unified": base.binary_metrics(winner["actual_a_win"], winner_global_p),
        "contextual_unified": base.binary_metrics(winner["actual_a_win"], wp),
    }
    cur_m = method[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
    hist_m = method[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
    global_m = multiclass_log_pool(cur_m, hist_m, mg["weight_current"])
    method_metrics = {
        "current": base.method_metrics(method["actual_joint_class"], cur_m),
        "historical": base.method_metrics(method["actual_joint_class"], hist_m),
        "global_unified": base.method_metrics(method["actual_joint_class"], global_m),
        "contextual_unified": base.method_metrics(method["actual_joint_class"], mp),
    }
    global_t = binary_logit_pool(timing["current_probability"], timing["historical_probability"], tg["weight_current"])
    timing_metrics = {
        "current": base.binary_metrics(timing["actual"], timing["current_probability"]),
        "historical": base.binary_metrics(timing["actual"], timing["historical_probability"]),
        "global_unified": base.binary_metrics(timing["actual"], global_t),
        "contextual_unified": base.binary_metrics(timing["actual"], tp),
        "grouped_log_loss": timing_grouped,
    }

    diagnostic = {
        "status": "CONTEXTUAL_UNIFIED_SHADOW_DIAGNOSTIC_ONLY",
        "trained_through": "2026-10-17",
        "odds_used": False,
        "historical_backbone": {
            "perspective_rows": int(len(frame)),
            "unique_fights": int(frame["fight_id"].nunique()),
            "first_date": str(pd.to_datetime(frame["date"]).min().date()),
            "last_date": str(pd.to_datetime(frame["date"]).max().date()),
            "note": "Historical component/context state uses the full causal UFC history; direct blend fitting only uses fights with honestly recoverable contemporaneous current-model probabilities.",
        },
        "direct_comparison_population": {
            "winner_fights": int(len(winner)),
            "method_fights": int(len(method)),
            "timing_fights": int(timing["fight_id"].nunique()),
            "timing_market_rows": int(len(timing)),
        },
        "regularization": {"l2": L2, "intercept_l2": INTERCEPT_L2, "purpose": "keep context gates low-capacity and shrunk toward the global blend"},
        "winner": {"features": list(WINNER_FEATURES), "global_fit": wg, "context_gate": wc, "full_fit_metrics": winner_metrics, "weight_summary": _weight_summary(winner, ww), "walk_forward": wwf_report},
        "method": {"features": list(METHOD_FEATURES), "global_fit": mg, "context_gate": mc, "full_fit_metrics": method_metrics, "weight_summary": _weight_summary(method, mw), "walk_forward": mwf_report},
        "timing": {"features": list(TIMING_FEATURES), "global_fit": tg, "context_gate": tc, "full_fit_metrics": timing_metrics, "weight_summary": _weight_summary(timing, tw), "walk_forward": twf_report},
        "governance": {
            "production_change": False,
            "promotion_allowed_from_this_report": False,
            "reason": "Context families were selected after reviewing prior cards. They require future frozen prospective validation even if retrospective/walk-forward metrics improve.",
            "global_unified_remains_baseline": True,
        },
    }

    shadow = {
        "status": "SHADOW_ONLY_NOT_PROMOTED",
        "trained_through": "2026-10-17",
        "winner": {"features": list(WINNER_FEATURES), "global_fit": wg, "context_gate": wc},
        "method": {"features": list(METHOD_FEATURES), "global_fit": mg, "context_gate": mc},
        "timing": {"features": list(TIMING_FEATURES), "global_fit": tg, "context_gate": tc},
        "governance": diagnostic["governance"],
    }

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    winner.to_csv(OUT_ROOT / "winner_full_fit.csv", index=False)
    method.to_csv(OUT_ROOT / "method_full_fit.csv", index=False)
    timing.to_csv(OUT_ROOT / "timing_full_fit.csv", index=False)
    wwf.to_csv(OUT_ROOT / "winner_walk_forward.csv", index=False)
    mwf.to_csv(OUT_ROOT / "method_walk_forward.csv", index=False)
    twf.to_csv(OUT_ROOT / "timing_walk_forward.csv", index=False)
    _json(OUT_ROOT / "diagnostic.json", diagnostic)
    _json(SHADOW_PATH, shadow)
    print(json.dumps(diagnostic, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
