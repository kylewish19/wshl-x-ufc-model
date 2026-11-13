#!/usr/bin/env python3
"""Build large causal OOF comparisons for WSHL-X current-style vs historical UFC models.

This is a diagnostic/shadow reconstruction, not a claim that today's model existed in
past seasons.  For each calendar-year fold, every model is trained only on fights dated
before that year and then predicts that year's fights.  The current-style side reuses
the core v0.27/v0.33 winner, conditional-method and 30-second timing architectures with
prefight full-stat features.  The historical side refits the leakage-aware conditional-
rate challenger on the same pre-fold history.

Method intercept/residual calibration learned from the 2026 WSHL clean ledger is not
backfilled into old seasons; the reconstructed current-style method head is therefore
the baseline conditional method architecture.  That limitation is intentional and is
recorded in the manifest.
"""
from __future__ import annotations

import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rb = _load_module("rebuild_v027_oof", ROOT / "tools/rebuild_v027.py")

from wshlx_ufc.contextual_ensemble import (
    fit_contextual_binary_blend,
    fit_contextual_grouped_binary_blend,
    fit_contextual_multiclass_blend,
    grouped_binary_log_loss,
    rowwise_binary_logit_pool,
    rowwise_multiclass_log_pool,
)
from wshlx_ufc.historical_data import (
    build_prefight_perspective_rows,
    download_source_files,
    load_source_files,
)
from wshlx_ufc.historical_method_model import fit_historical_method_model
from wshlx_ufc.historical_model import fit_historical_winner_model
from wshlx_ufc.historical_outcomes import METHOD_STATES, add_timing_targets
from wshlx_ufc.historical_timing_model import (
    _encode_transform as historical_timing_encode_transform,
    fit_historical_timing_model,
    symmetric_timing_frame,
)
from wshlx_ufc.models import ConditionalMethodModel, WinnerModel, joint_outcome_probabilities
from wshlx_ufc.timing import DiscreteTimeHazardModel
from wshlx_ufc.unified_ensemble import (
    binary_logit_pool,
    fit_binary_blend,
    fit_grouped_binary_blend,
    fit_multiclass_blend,
    multiclass_log_pool,
)

RAW = ROOT / "data/raw/historical_current_style_oof"
OUT = ROOT / "data/unified/historical_oof"
REPORT = ROOT / "reports/historical_oof_contextual_through_2026-10-17"
MIN_TRAIN_FIGHTS = 800
MIN_FOLD_YEAR = 2008
FINAL_CUTOFF = pd.Timestamp("2026-10-18", tz="UTC")
METHOD_KEYS = ("A_KO", "A_SUB", "A_DEC", "B_KO", "B_SUB", "B_DEC")
HIST_METHOD_KEYS = (
    "WIN_KO_TKO", "WIN_SUB", "WIN_DEC", "LOSS_KO_TKO", "LOSS_SUB", "LOSS_DEC"
)
TIMING_MARKETS = (
    "GTD_YES", "OVER_1.5", "OVER_2.5", "ROUND_2_STARTS_YES", "ROUND_3_STARTS_YES",
    "ROUND_4_STARTS_YES", "ROUND_5_STARTS_YES",
)


def _date(s):
    return pd.to_datetime(s, errors="coerce", utc=True)


def _pair_key(date, a, b):
    return (
        str(pd.Timestamp(date).date()),
        tuple(sorted((rb.norm_name(a), rb.norm_name(b)))),
    )


def _current_method_candidates(frame: pd.DataFrame, side: str) -> pd.DataFrame:
    if side not in {"a", "b"}:
        raise ValueError(side)
    other = "b" if side == "a" else "a"
    out = pd.DataFrame(index=frame.index)
    for f in rb.SIDE_RATE_FIELDS:
        out[f"winner_{f}"] = pd.to_numeric(frame[f"{side}_{f}"], errors="coerce")
        out[f"opponent_{f}"] = pd.to_numeric(frame[f"{other}_{f}"], errors="coerce")
    for f in rb.SIDE_RATE_FIELDS:
        if f in {"days_since_last", "southpaw"}:
            continue
        d = pd.to_numeric(frame[f"diff_{f}"], errors="coerce")
        out[f"diff_{f}"] = d if side == "a" else -d
    for c in ("scheduled_five_round", "is_heavyweight", "is_womens", "same_stance"):
        out[c] = pd.to_numeric(frame[c], errors="coerce")
    return out[rb.METHOD_BASE_FEATURES]


def _actual_joint(row) -> int:
    method_i = {"KO": 0, "SUB": 1, "DEC": 2}[str(row.method)]
    return method_i if int(row.winner_is_a) else 3 + method_i


def _timing_actuals(row) -> dict[str, int]:
    duration = float(row.duration_seconds)
    scheduled = int(row.scheduled_seconds)
    observed = int((str(row.method) != "DEC") or duration < scheduled)
    out = {
        "GTD_YES": int(observed == 0),
        "OVER_1.5": int(duration > 450),
        "OVER_2.5": int(duration > 750),
        "ROUND_2_STARTS_YES": int(duration > 300),
        "ROUND_3_STARTS_YES": int(duration > 600),
    }
    if scheduled == 1500:
        out["ROUND_4_STARTS_YES"] = int(duration > 900)
        out["ROUND_5_STARTS_YES"] = int(duration > 1200)
    return out


def _binary_metrics(y, p):
    yy = np.asarray(y, dtype=int)
    pp = np.clip(np.asarray(p, dtype=float), 1e-7, 1 - 1e-7)
    out = {
        "n": int(len(yy)),
        "accuracy": float(accuracy_score(yy, pp >= .5)),
        "brier": float(brier_score_loss(yy, pp)),
        "log_loss": float(log_loss(yy, pp, labels=[0, 1])),
    }
    out["roc_auc"] = float(roc_auc_score(yy, pp)) if len(np.unique(yy)) == 2 else None
    return out


def _method_metrics(y, p):
    yy = np.asarray(y, dtype=int)
    pp = np.asarray(p, dtype=float)
    pp = np.clip(pp, 1e-9, 1.0)
    pp /= pp.sum(axis=1, keepdims=True)
    onehot = np.eye(6)[yy]
    method_true = yy % 3
    method_prob = np.column_stack([pp[:, i] + pp[:, i + 3] for i in range(3)])
    winner_true = yy < 3
    winner_prob = pp[:, :3].sum(axis=1)
    return {
        "n": int(len(yy)),
        "joint_accuracy": float(np.mean(np.argmax(pp, axis=1) == yy)),
        "winner_accuracy": float(np.mean((winner_prob >= .5) == winner_true)),
        "method_accuracy": float(np.mean(np.argmax(method_prob, axis=1) == method_true)),
        "log_loss": float(log_loss(yy, pp, labels=list(range(6)))),
        "multiclass_brier": float(np.mean(np.sum((pp - onehot) ** 2, axis=1))),
        "ko_recall": float(np.mean(np.argmax(method_prob[method_true == 0], axis=1) == 0)) if np.any(method_true == 0) else None,
        "sub_recall": float(np.mean(np.argmax(method_prob[method_true == 1], axis=1) == 1)) if np.any(method_true == 1) else None,
        "dec_recall": float(np.mean(np.argmax(method_prob[method_true == 2], axis=1) == 2)) if np.any(method_true == 2) else None,
    }


def _historical_a_rows(frame: pd.DataFrame) -> dict[tuple, int]:
    out = {}
    for i, r in frame.iterrows():
        key = _pair_key(r["date"], r["fighter"], r["opponent"])
        # Prefer the lexicographically first stored row only as a stable fallback.
        out.setdefault(key, i)
    return out


def _hist_row_for_a(hist_test: pd.DataFrame, date, a, b):
    key = _pair_key(date, a, b)
    subset = hist_test[
        (hist_test["date"].map(lambda x: str(pd.Timestamp(x).date())) == key[0])
        & hist_test["fighter"].map(rb.norm_name).eq(rb.norm_name(a))
        & hist_test["opponent"].map(rb.norm_name).eq(rb.norm_name(b))
    ]
    if subset.empty:
        # Source ordering may be opposite but mirrored rows should still exist.
        subset = hist_test[
            (hist_test["date"].map(lambda x: str(pd.Timestamp(x).date())) == key[0])
            & hist_test["fighter"].map(rb.norm_name).eq(rb.norm_name(a))
            & hist_test["fight_id"].astype(str).str.contains("", regex=False)
        ]
    return None if subset.empty else subset.index[0]


def _prepare_sources():
    if RAW.exists():
        shutil.rmtree(RAW)
    RAW.mkdir(parents=True, exist_ok=True)
    download_source_files(RAW)
    tables = load_source_files(RAW)

    old_cutoff = rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF = FINAL_CUTOFF
    try:
        fights, stats, static = rb.load_fights(RAW)
    finally:
        rb.TRAINING_CUTOFF = old_cutoff
    fight_stats = rb.aggregate_fight_stats(fights, stats)
    winner_df, method_df, timing_df = rb.enrich_and_snapshot(fights, fight_stats, static)
    for df in (winner_df, method_df, timing_df):
        df["event_date"] = _date(df["event_date"])

    hist = build_prefight_perspective_rows(
        tables["events"], tables["results"], tables["stats"], tables["fighters"]
    )
    hist["date"] = _date(hist["date"])
    return tables, winner_df, method_df, timing_df, hist


def _fold_years(winner_df: pd.DataFrame) -> list[int]:
    years = sorted(int(x) for x in winner_df["event_date"].dt.year.unique())
    out = []
    for year in years:
        if year < MIN_FOLD_YEAR:
            continue
        train_n = int((winner_df["event_date"].dt.year < year).sum())
        if train_n >= MIN_TRAIN_FIGHTS:
            out.append(year)
    return out


def _historical_timing_predictions(bundle, hist_test, raw_results):
    targeted = add_timing_targets(hist_test, raw_results)
    sym = symmetric_timing_frame(targeted)
    sym = sym.dropna(subset=["finish_seconds", "scheduled_seconds", "finish_observed"]).copy()
    if sym.empty:
        return {}, sym
    enc = historical_timing_encode_transform(sym, bundle.rate_encoders)
    probs = {}
    for _, r in enc.iterrows():
        try:
            p = bundle.market_probabilities_from_encoded(r, int(r["scheduled_seconds"]))
        except Exception:
            continue
        probs[str(r["fight_id"])] = p
    return probs, enc


def build_oof():
    tables, winner_df, method_df, timing_df, hist = _prepare_sources()
    years = _fold_years(winner_df)
    if not years:
        raise RuntimeError("No eligible OOF folds")

    winner_rows, method_rows, timing_rows, fold_manifest = [], [], [], []
    hist_method_targeted = None

    for year in years:
        train_mask = winner_df["event_date"].dt.year < year
        test_mask = winner_df["event_date"].dt.year == year
        wtr, wte = winner_df.loc[train_mask].copy(), winner_df.loc[test_mask].copy()
        mtr = method_df.loc[method_df["event_date"].dt.year < year].copy()
        ttr = timing_df.loc[timing_df["event_date"].dt.year < year].copy()
        tte = timing_df.loc[timing_df["event_date"].dt.year == year].copy()
        if len(wtr) < MIN_TRAIN_FIGHTS or wte.empty:
            continue

        current_w = WinnerModel(c=0.25).fit(wtr[rb.WINNER_FEATURES], wtr["winner_is_a"])
        p_cur_w = current_w.predict_proba(wte[rb.WINNER_FEATURES])[:, 0]

        current_m = ConditionalMethodModel(finish_c=0.10, sub_c=0.10).fit(
            mtr[rb.METHOD_BASE_FEATURES], mtr["method"]
        )
        pa_m = current_m.predict_proba(_current_method_candidates(wte, "a"))
        pb_m = current_m.predict_proba(_current_method_candidates(wte, "b"))

        observed_t = ((ttr["method"].astype(str) != "DEC") | (ttr["duration_seconds"] < ttr["scheduled_seconds"])).astype(int)
        current_t = DiscreteTimeHazardModel(bin_seconds=30, c=0.10).fit(
            ttr[rb.TIMING_FEATURES], ttr["duration_seconds"].to_numpy(float),
            ttr["scheduled_seconds"].to_numpy(int), observed_t.to_numpy(int)
        )

        htr = hist.loc[hist["date"].dt.year < year].copy()
        hte = hist.loc[hist["date"].dt.year == year].copy()
        if hte.empty:
            continue
        historical_w, _ = fit_historical_winner_model(htr)
        p_hist_rows = historical_w.predict_proba(hte)
        p_hist_w = pd.Series(p_hist_rows, index=hte.index)

        historical_m, _ = fit_historical_method_model(htr)
        p_hist_method = historical_m.predict_joint_probabilities(hte)

        historical_t, _ = fit_historical_timing_model(htr, tables["results"])
        hist_timing_map, hist_timing_encoded = _historical_timing_predictions(historical_t, hte, tables["results"])
        hist_fight_meta = {
            str(r["fight_id"]): _pair_key(r["date"], r["fighter"], r["opponent"])
            for _, r in hte.drop_duplicates("fight_id", keep="first").iterrows()
        }
        hist_timing_by_pair = {
            hist_fight_meta[fid]: probs for fid, probs in hist_timing_map.items() if fid in hist_fight_meta
        }

        matched = 0
        for pos, (idx, r) in enumerate(wte.iterrows()):
            hidx = _hist_row_for_a(hte, r.event_date, r.fighter_a, r.fighter_b)
            if hidx is None:
                continue
            matched += 1
            pc = float(p_cur_w[pos])
            ph = float(p_hist_w.loc[hidx])
            context = {
                "model_disagreement": abs(pc - ph),
                "historical_confidence": abs(ph - .5) * 2.0,
                "min_ufc_fights_log": math.log1p(max(0.0, min(float(r.a_prior_bouts), float(r.b_prior_bouts)))),
                "experience_gap_log": math.log1p(abs(float(r.diff_prior_bouts))),
                "age_gap_abs": abs(float(r.diff_age_years)) if pd.notna(r.diff_age_years) else np.nan,
                "reach_gap_abs": abs(float(r.diff_reach_inches)) if pd.notna(r.diff_reach_inches) else np.nan,
                "max_layoff_log": math.log1p(max(0.0, np.nanmax([float(r.a_days_since_last), float(r.b_days_since_last)]))) if not (pd.isna(r.a_days_since_last) and pd.isna(r.b_days_since_last)) else np.nan,
                "is_heavyweight": float(r.is_heavyweight),
                "five_round": float(r.scheduled_five_round),
            }
            base = {
                "year": year, "date": str(pd.Timestamp(r.event_date).date()), "fight_key": r.fight_key,
                "event": r.event, "a": r.fighter_a, "b": r.fighter_b,
                "actual_a_win": int(r.winner_is_a), "current_p_a": pc, "historical_p_a": ph,
                **context,
            }
            winner_rows.append(base)

            cur_joint = joint_outcome_probabilities(
                pc,
                {k: float(pa_m.loc[idx, k]) for k in ("KO", "SUB", "DEC")},
                {k: float(pb_m.loc[idx, k]) for k in ("KO", "SUB", "DEC")},
            )
            hp = p_hist_method.loc[hidx]
            hist_joint = dict(zip(METHOD_KEYS, [float(hp[k]) for k in HIST_METHOD_KEYS]))
            cj = np.array([cur_joint[k] for k in METHOD_KEYS], float)
            hj = np.array([hist_joint[k] for k in METHOD_KEYS], float)
            js_m = .5 * (
                np.sum(cj * np.log(np.clip(cj, 1e-12, 1) / np.clip((cj + hj) / 2, 1e-12, 1)))
                + np.sum(hj * np.log(np.clip(hj, 1e-12, 1) / np.clip((cj + hj) / 2, 1e-12, 1)))
            )
            mr = {
                **base,
                "actual_joint_class": _actual_joint(r),
                "method_js": float(js_m),
                "historical_method_confidence": float(np.max(hj) - 1 / 6),
                "grappling_access_log": math.log1p(max(0.0, np.nansum([
                    r.a_td_landed_per15, r.b_td_landed_per15, r.a_sub_att_per15, r.b_sub_att_per15
                ]))),
                "combined_finish_rate": float(np.nanmean([r.a_finish_win_rate, r.b_finish_win_rate])),
                "combined_sub_rate": float(np.nanmean([r.a_sub_win_rate, r.b_sub_win_rate])),
            }
            for k in METHOD_KEYS:
                mr[f"current_{k}"] = float(cur_joint[k])
                mr[f"historical_{k}"] = float(hist_joint[k])
            method_rows.append(mr)

            trow = tte.loc[tte["fight_key"].eq(r.fight_key)]
            if trow.empty:
                continue
            tr = trow.iloc[0]
            try:
                current_timing = current_t.market_probabilities(tr[rb.TIMING_FEATURES], int(tr.scheduled_seconds))
            except Exception:
                continue
            hist_timing = hist_timing_by_pair.get(_pair_key(r.event_date, r.fighter_a, r.fighter_b))
            if not hist_timing:
                continue
            actuals = _timing_actuals(tr)
            horizon = {
                "GTD_YES": 1.0,
                "OVER_1.5": 450 / float(tr.scheduled_seconds),
                "OVER_2.5": 750 / float(tr.scheduled_seconds),
                "ROUND_2_STARTS_YES": 300 / float(tr.scheduled_seconds),
                "ROUND_3_STARTS_YES": 600 / float(tr.scheduled_seconds),
                "ROUND_4_STARTS_YES": 900 / float(tr.scheduled_seconds),
                "ROUND_5_STARTS_YES": 1200 / float(tr.scheduled_seconds),
            }
            for market, actual in actuals.items():
                if market not in current_timing or market not in hist_timing:
                    continue
                pc_t, ph_t = float(current_timing[market]), float(hist_timing[market])
                timing_rows.append({
                    **base,
                    "market": market, "actual": int(actual),
                    "current_probability": pc_t, "historical_probability": ph_t,
                    "prob_disagreement": abs(pc_t - ph_t),
                    "historical_timing_confidence": abs(ph_t - .5) * 2.0,
                    "combined_finish_rate": float(np.nanmean([r.a_finish_win_rate, r.b_finish_win_rate])),
                    "horizon_fraction": float(horizon[market]),
                })

        fold_manifest.append({
            "year": year,
            "current_train_fights": int(len(wtr)),
            "current_test_fights": int(len(wte)),
            "historical_train_fights": int(htr["fight_id"].nunique()),
            "historical_test_fights": int(hte["fight_id"].nunique()),
            "aligned_winner_fights": int(matched),
        })
        print(json.dumps(fold_manifest[-1]))

    winner = pd.DataFrame(winner_rows).drop_duplicates(["fight_key"], keep="last")
    method = pd.DataFrame(method_rows).drop_duplicates(["fight_key"], keep="last")
    timing = pd.DataFrame(timing_rows).drop_duplicates(["fight_key", "market"], keep="last")
    return winner, method, timing, fold_manifest, winner_df, hist


def _split_meta(df: pd.DataFrame):
    years = np.array(sorted(df["year"].unique()), dtype=int)
    if len(years) < 4:
        cut = int(np.quantile(years, .75))
    else:
        cut = int(years[max(1, int(math.floor(len(years) * .75))) - 1])
    train = df["year"] <= cut
    test = df["year"] > cut
    if test.sum() == 0:
        cut = int(years[-2]); train = df["year"] <= cut; test = df["year"] > cut
    return train, test, cut


def analyze_context(winner: pd.DataFrame, method: pd.DataFrame, timing: pd.DataFrame):
    report = {"status": "HISTORICAL_CURRENT_STYLE_OOF_CONTEXT_DIAGNOSTIC_ONLY"}

    # Winner meta-model.
    tr, te, cut = _split_meta(winner)
    wf = ["model_disagreement", "historical_confidence", "min_ufc_fights_log", "experience_gap_log", "age_gap_abs", "reach_gap_abs", "max_layoff_log", "is_heavyweight", "five_round"]
    g = fit_binary_blend(winner.loc[tr, "actual_a_win"], winner.loc[tr, "current_p_a"], winner.loc[tr, "historical_p_a"])
    cg = fit_contextual_binary_blend(
        winner.loc[tr], winner.loc[tr, "actual_a_win"], winner.loc[tr, "current_p_a"], winner.loc[tr, "historical_p_a"], wf,
        prior_weight_current=g.weight_current, l2=8.0, intercept_l2=2.0,
    )
    pg = binary_logit_pool(winner.loc[te, "current_p_a"], winner.loc[te, "historical_p_a"], g.weight_current)
    wc = cg.weights(winner.loc[te]); pc = rowwise_binary_logit_pool(winner.loc[te, "current_p_a"], winner.loc[te, "historical_p_a"], wc)
    report["winner"] = {
        "train_through_year": cut, "test_years": sorted(winner.loc[te, "year"].unique().tolist()),
        "global_fit": g.to_dict(), "context_gate": cg.to_dict(),
        "test": {
            "current": _binary_metrics(winner.loc[te, "actual_a_win"], winner.loc[te, "current_p_a"]),
            "historical": _binary_metrics(winner.loc[te, "actual_a_win"], winner.loc[te, "historical_p_a"]),
            "global": _binary_metrics(winner.loc[te, "actual_a_win"], pg),
            "contextual": _binary_metrics(winner.loc[te, "actual_a_win"], pc),
            "mean_context_current_weight": float(np.mean(wc)),
        },
    }

    # Method meta-model.
    tr, te, cut = _split_meta(method)
    mf = ["method_js", "historical_method_confidence", "min_ufc_fights_log", "experience_gap_log", "grappling_access_log", "combined_finish_rate", "combined_sub_rate", "is_heavyweight", "five_round"]
    cur_cols = [f"current_{k}" for k in METHOD_KEYS]; hist_cols = [f"historical_{k}" for k in METHOD_KEYS]
    gm = fit_multiclass_blend(method.loc[tr, "actual_joint_class"], method.loc[tr, cur_cols].to_numpy(float), method.loc[tr, hist_cols].to_numpy(float))
    cm = fit_contextual_multiclass_blend(
        method.loc[tr], method.loc[tr, "actual_joint_class"], method.loc[tr, cur_cols].to_numpy(float), method.loc[tr, hist_cols].to_numpy(float), mf,
        prior_weight_current=gm.weight_current, l2=8.0, intercept_l2=2.0,
    )
    pgm = multiclass_log_pool(method.loc[te, cur_cols].to_numpy(float), method.loc[te, hist_cols].to_numpy(float), gm.weight_current)
    wm = cm.weights(method.loc[te]); pcm = rowwise_multiclass_log_pool(method.loc[te, cur_cols].to_numpy(float), method.loc[te, hist_cols].to_numpy(float), wm)
    report["method"] = {
        "train_through_year": cut, "test_years": sorted(method.loc[te, "year"].unique().tolist()),
        "global_fit": gm.to_dict(), "context_gate": cm.to_dict(),
        "test": {
            "current": _method_metrics(method.loc[te, "actual_joint_class"], method.loc[te, cur_cols].to_numpy(float)),
            "historical": _method_metrics(method.loc[te, "actual_joint_class"], method.loc[te, hist_cols].to_numpy(float)),
            "global": _method_metrics(method.loc[te, "actual_joint_class"], pgm),
            "contextual": _method_metrics(method.loc[te, "actual_joint_class"], pcm),
            "mean_context_current_weight": float(np.mean(wm)),
        },
    }

    # Timing meta-model, grouped by fight.
    tr, te, cut = _split_meta(timing)
    tf = ["prob_disagreement", "historical_timing_confidence", "min_ufc_fights_log", "max_layoff_log", "combined_finish_rate", "horizon_fraction", "is_heavyweight", "five_round"]
    gt = fit_grouped_binary_blend(timing.loc[tr, "actual"], timing.loc[tr, "current_probability"], timing.loc[tr, "historical_probability"], timing.loc[tr, "fight_key"])
    ct = fit_contextual_grouped_binary_blend(
        timing.loc[tr], timing.loc[tr, "actual"], timing.loc[tr, "current_probability"], timing.loc[tr, "historical_probability"], timing.loc[tr, "fight_key"], tf,
        prior_weight_current=gt.weight_current, l2=8.0, intercept_l2=2.0,
    )
    pgt = binary_logit_pool(timing.loc[te, "current_probability"], timing.loc[te, "historical_probability"], gt.weight_current)
    wt = ct.weights(timing.loc[te]); pct = rowwise_binary_logit_pool(timing.loc[te, "current_probability"], timing.loc[te, "historical_probability"], wt)
    report["timing"] = {
        "train_through_year": cut, "test_years": sorted(timing.loc[te, "year"].unique().tolist()),
        "global_fit": gt.to_dict(), "context_gate": ct.to_dict(),
        "test": {
            "current": _binary_metrics(timing.loc[te, "actual"], timing.loc[te, "current_probability"]),
            "historical": _binary_metrics(timing.loc[te, "actual"], timing.loc[te, "historical_probability"]),
            "global": _binary_metrics(timing.loc[te, "actual"], pgt),
            "contextual": _binary_metrics(timing.loc[te, "actual"], pct),
            "grouped_log_loss": {
                "current": grouped_binary_log_loss(timing.loc[te, "actual"], timing.loc[te, "current_probability"], timing.loc[te, "fight_key"]),
                "historical": grouped_binary_log_loss(timing.loc[te, "actual"], timing.loc[te, "historical_probability"], timing.loc[te, "fight_key"]),
                "global": grouped_binary_log_loss(timing.loc[te, "actual"], pgt, timing.loc[te, "fight_key"]),
                "contextual": grouped_binary_log_loss(timing.loc[te, "actual"], pct, timing.loc[te, "fight_key"]),
            },
            "mean_context_current_weight": float(np.mean(wt)),
        },
    }
    report["governance"] = {
        "production_change": False,
        "promotion_allowed_from_this_report": False,
        "reason": "This is a reconstructed historical OOF development study. Context families and architecture were designed with knowledge of later UFC history; future frozen prospective cards are still required for promotion.",
    }
    return report


def main():
    OUT.mkdir(parents=True, exist_ok=True); REPORT.mkdir(parents=True, exist_ok=True)
    winner, method, timing, folds, winner_all, hist_all = build_oof()
    if min(len(winner), len(method)) < 1000 or timing["fight_key"].nunique() < 1000:
        raise RuntimeError(f"OOF population unexpectedly small: winner={len(winner)} method={len(method)} timing_fights={timing['fight_key'].nunique()}")
    winner.to_csv(OUT / "winner_oof.csv", index=False)
    method.to_csv(OUT / "method_oof.csv", index=False)
    timing.to_csv(OUT / "timing_oof.csv", index=False)
    report = analyze_context(winner, method, timing)
    manifest = {
        "status": "CAUSAL_CURRENT_STYLE_VS_HISTORICAL_OOF_RECONSTRUCTION",
        "odds_used": False,
        "source_cutoff": "2026-10-17",
        "fold_unit": "calendar_year",
        "training_rule": "strictly dates before fold year",
        "min_train_fights": MIN_TRAIN_FIGHTS,
        "folds": folds,
        "population": {
            "winner_fights": int(len(winner)),
            "method_fights": int(len(method)),
            "timing_fights": int(timing["fight_key"].nunique()),
            "timing_market_rows": int(len(timing)),
            "first_oof_year": int(winner["year"].min()),
            "last_oof_year": int(winner["year"].max()),
            "full_current_feature_fights": int(len(winner_all)),
            "historical_backbone_fights": int(hist_all["fight_id"].nunique()),
        },
        "architecture": {
            "winner": "WinnerModel C=.25 on v0.27/v0.33 full-stat prefight features",
            "method": "ConditionalMethodModel finish-vs-decision then sub-vs-KO; historical reconstruction intentionally excludes 2026-only intercept/residual calibration",
            "timing": "DiscreteTimeHazardModel 30-second bins C=.10",
            "historical": "conditional-rate historical winner/method/timing challengers refit inside each causal fold",
        },
        "governance": report["governance"],
    }
    (REPORT / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    (REPORT / "contextual_diagnostic.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({"manifest": manifest["population"], "winner_test": report["winner"]["test"], "method_test": report["method"]["test"], "timing_test": report["timing"]["test"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
