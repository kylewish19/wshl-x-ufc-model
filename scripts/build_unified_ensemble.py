#!/usr/bin/env python3
"""Learn WSHL-X unified winner/method/timing blend weights from frozen cards.

Base-model inputs come from the probabilities that were actually frozen before each
fight. Historical-model inputs come from untouched chronological test predictions, not
from the final all-history refit bundles. Weights are learned through 2026-10-10 and
UFC Edmonton (2026-10-17) is reserved as the first untouched ensemble holdout.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wshlx_ufc.historical_data import load_source_files, normalize_events
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

TRAIN_DATES = ("2026-09-19", "2026-09-26", "2026-10-03", "2026-10-10")
HOLDOUT_DATE = "2026-10-17"
LOCKS = {
    "2026-09-19": ROOT / "data/locks/ufc331_2026-09-19/stage_a_model_raw.json",
    "2026-09-26": ROOT / "data/locks/ufcvegas121_2026-09-26/stage_a_model_raw_v031_identity_audited.json",
    "2026-10-03": ROOT / "data/locks/ufc332_2026-10-03/stage_a_model_raw_v032_identity_audited.json",
    "2026-10-10": ROOT / "data/locks/ufcvegas122_2026-10-10/stage_a_model_raw_v033.json",
    "2026-10-17": ROOT / "data/locks/ufcedmonton_2026-10-17/stage_a_model_raw_v033.json",
}
CURRENT_TIMING_KEYS = (
    "timing_v033_direct", "timing_v032_direct", "timing_v031_direct", "timing_direct",
)
SIX_KEYS = ("A_KO", "A_SUB", "A_DEC", "B_KO", "B_SUB", "B_DEC")
HIST_METHOD_COLS = (
    "historical_WIN_KO_TKO", "historical_WIN_SUB", "historical_WIN_DEC",
    "historical_LOSS_KO_TKO", "historical_LOSS_SUB", "historical_LOSS_DEC",
)
TIMING_MARKETS = (
    "GTD_YES", "OVER_1.5", "OVER_2.5", "ROUND_2_STARTS_YES", "ROUND_3_STARTS_YES",
    "ROUND_4_STARTS_YES", "ROUND_5_STARTS_YES",
)
NAME_ALIASES = {
    "alatengheili": "heilialateng",
    "tinablack": "valescamachado",
    "mahammadaliosmanli": "mehemmedeliosmanli",
    "kinggreen": "bobbygreen",
    "stanleydorsainvil": "standorsainvil",
}


def norm_name(value: object) -> str:
    s = str(value or "").lower().replace("’", "'")
    s = re.sub(r"[^a-z0-9]+", "", s)
    return NAME_ALIASES.get(s, s)


def pair_key(a: object, b: object) -> tuple[str, str]:
    return tuple(sorted((norm_name(a), norm_name(b))))


def read_lock(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    payload = raw.get("payload", raw)
    if "fights" not in payload:
        raise ValueError(f"No fights in frozen lock: {path}")
    return payload


def apply_results_supplements(tables: dict[str, pd.DataFrame], supplement_dir: Path) -> dict[str, pd.DataFrame]:
    out = {k: v.copy() for k, v in tables.items()}
    if not supplement_dir.exists():
        return out
    known_dates = {
        pd.Timestamp(x).normalize()
        for x in pd.to_datetime(normalize_events(out["events"])["date"], errors="coerce").dropna()
    }
    for path in sorted(supplement_dir.glob("*.csv")):
        sup = pd.read_csv(path)
        dates = pd.to_datetime(sup["DATE"], errors="raise").dt.normalize()
        for raw_date in pd.unique(dates):
            date = pd.Timestamp(raw_date).normalize()
            if date in known_dates:
                continue
            rows = sup.loc[dates == date].copy()
            event_cols = [c for c in ("EVENT", "DATE", "LOCATION") if c in rows]
            out["events"] = pd.concat(
                [out["events"], rows[event_cols].drop_duplicates("EVENT")], ignore_index=True, sort=False
            )
            result_cols = [c for c in rows.columns if c not in {"DATE", "LOCATION", "SOURCE_URL"}]
            out["results"] = pd.concat([out["results"], rows[result_cols]], ignore_index=True, sort=False)
            known_dates.add(date)
    return out


def current_winner_probability(fight: dict) -> float:
    if "winner_reference_p_a" in fight:
        return float(fight["winner_reference_p_a"])
    if "p_a_win" in fight:
        return float(fight["p_a_win"])
    raise KeyError("frozen fight has no current/reference winner probability")


def current_method_distribution(fight: dict) -> np.ndarray:
    # Use the leading frozen method layer available on that card. UFC 331 predates the
    # accepted low-variance intercept calibration, so its baseline remains the honest input.
    joint = fight.get("joint_calibrated") or fight.get("joint_baseline")
    if joint is None:
        raise KeyError("frozen fight has no coherent joint method distribution")
    p = np.asarray([float(joint[k]) for k in SIX_KEYS], dtype=float)
    return p / p.sum()


def current_timing_distribution(fight: dict) -> dict[str, float]:
    for key in CURRENT_TIMING_KEYS:
        if key in fight:
            return {str(k): float(v) for k, v in fight[key].items()}
    raise KeyError("frozen fight has no direct timing probabilities")


def binary_metrics(y, p) -> dict[str, float]:
    yy = np.asarray(y, dtype=int); pp = np.clip(np.asarray(p, dtype=float), 1e-7, 1 - 1e-7)
    out = {
        "n": int(len(yy)),
        "accuracy": float(accuracy_score(yy, pp >= .5)),
        "brier": float(brier_score_loss(yy, pp)),
        "log_loss": float(log_loss(yy, pp, labels=[0, 1])),
    }
    out["roc_auc"] = float(roc_auc_score(yy, pp)) if len(np.unique(yy)) == 2 else None
    return out


def method_metrics(y, p) -> dict[str, float]:
    yy = np.asarray(y, dtype=int); pp = np.asarray(p, dtype=float)
    pp = np.clip(pp, 1e-9, 1.0); pp /= pp.sum(axis=1, keepdims=True)
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
    }


def timing_actual(market: str, finish_seconds: float, finish_observed: int, scheduled_seconds: int) -> int:
    if market == "GTD_YES":
        return int(finish_observed == 0)
    if market == "OVER_1.5": return int(finish_seconds > 450)
    if market == "OVER_2.5": return int(finish_seconds > 750)
    if market == "ROUND_2_STARTS_YES": return int(finish_seconds > 300)
    if market == "ROUND_3_STARTS_YES": return int(finish_seconds > 600)
    if market == "ROUND_4_STARTS_YES": return int(scheduled_seconds == 1500 and finish_seconds > 900)
    if market == "ROUND_5_STARTS_YES": return int(scheduled_seconds == 1500 and finish_seconds > 1200)
    raise KeyError(market)


def match_oriented_winner(lock_date: str, fight: dict, hist_winner: pd.DataFrame) -> pd.Series:
    d = pd.Timestamp(lock_date).normalize()
    work = hist_winner[pd.to_datetime(hist_winner["date"]).dt.normalize().eq(d)].copy()
    target_pair = pair_key(fight["a"], fight["b"])
    work = work[
        work.apply(lambda r: pair_key(r["fighter"], r["opponent"]) == target_pair, axis=1)
    ]
    if work.empty:
        raise RuntimeError(f"Historical winner prediction not found: {lock_date} {fight['a']} vs {fight['b']}")
    a = norm_name(fight["a"])
    oriented = work[work["fighter"].map(norm_name).eq(a)]
    if len(oriented) == 1:
        return oriented.iloc[0]
    # Normally mirrored rows guarantee a direct A perspective. This fallback keeps the
    # matcher robust to a missing mirror while preserving orientation.
    if len(work) == 1:
        row = work.iloc[0].copy()
        if norm_name(row["opponent"]) == a:
            row["historical_p_win"] = 1.0 - float(row["historical_p_win"])
            row["win"] = 1 - int(row["win"])
            row["fighter"], row["opponent"] = fight["a"], fight["b"]
            return row
    raise RuntimeError(f"Ambiguous historical winner match: {lock_date} {fight['a']} vs {fight['b']}")


def oriented_method_row(fight_id: str, fighter_a: str, hist_method: pd.DataFrame) -> pd.Series:
    work = hist_method[hist_method["fight_id"].astype(str).eq(str(fight_id))]
    a = norm_name(fighter_a)
    oriented = work[work["fighter"].map(norm_name).eq(a)]
    if len(oriented) == 1:
        return oriented.iloc[0]
    raise RuntimeError(f"Historical method perspective missing for fight_id={fight_id}, A={fighter_a}")


def build_rows(frame: pd.DataFrame, results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    hw = winner_test_predictions(frame)
    hm = method_test_predictions(frame)
    ht = timing_test_predictions(frame, results)
    ht = ht.set_index("fight_id", drop=False)

    fight_rows: list[dict] = []
    timing_rows: list[dict] = []
    for date, path in LOCKS.items():
        payload = read_lock(path)
        for fight in payload["fights"]:
            wrow = match_oriented_winner(date, fight, hw)
            fight_id = str(wrow["fight_id"])
            mrow = oriented_method_row(fight_id, fight["a"], hm)
            if fight_id not in ht.index:
                raise RuntimeError(f"Historical timing prediction missing: {fight_id}")
            trow = ht.loc[fight_id]
            if isinstance(trow, pd.DataFrame):
                trow = trow.iloc[0]

            current_method = current_method_distribution(fight)
            hist_method = np.asarray([float(mrow[c]) for c in HIST_METHOD_COLS], dtype=float)
            hist_method /= hist_method.sum()
            method_state = str(mrow["method_target"])
            if method_state not in METHOD_STATES:
                raise RuntimeError(f"Bad method target {method_state} for {fight_id}")
            actual_method_i = list(METHOD_STATES).index(method_state)

            fr = {
                "date": date, "fight_id": fight_id, "a": fight["a"], "b": fight["b"],
                "actual_a_win": int(wrow["win"]),
                "current_winner_p_a": current_winner_probability(fight),
                "historical_winner_p_a": float(wrow["historical_p_win"]),
                "actual_joint_class": actual_method_i,
            }
            for i, key in enumerate(SIX_KEYS):
                fr[f"current_{key}"] = float(current_method[i])
                fr[f"historical_{key}"] = float(hist_method[i])
            fight_rows.append(fr)

            current_timing = current_timing_distribution(fight)
            scheduled = int(trow["scheduled_seconds"])
            finish_seconds = float(trow["finish_seconds"])
            observed = int(trow["finish_observed"])
            for market in TIMING_MARKETS:
                if market not in current_timing:
                    continue
                hcol = f"historical_{market}"
                if hcol not in trow or pd.isna(trow[hcol]):
                    continue
                if market.startswith("ROUND_4") or market.startswith("ROUND_5"):
                    if scheduled != 1500:
                        continue
                timing_rows.append({
                    "date": date, "fight_id": fight_id, "fight": f"{fight['a']} vs {fight['b']}",
                    "market": market,
                    "actual": timing_actual(market, finish_seconds, observed, scheduled),
                    "current_probability": float(current_timing[market]),
                    "historical_probability": float(trow[hcol]),
                })
    return pd.DataFrame(fight_rows), pd.DataFrame(timing_rows)


def walk_forward(fights: pd.DataFrame, timing: pd.DataFrame) -> dict[str, object]:
    winner_rows = []; method_rows = []; timing_rows = []
    dates = sorted(set(fights.loc[fights["date"].isin(TRAIN_DATES), "date"]))
    for test_date in dates:
        train = fights[(fights["date"].isin(TRAIN_DATES)) & (fights["date"] < test_date)]
        test = fights[fights["date"].eq(test_date)]
        if len(train) < 20 or test.empty:
            continue
        wf = fit_binary_blend(train["actual_a_win"], train["current_winner_p_a"], train["historical_winner_p_a"])
        wp = binary_logit_pool(test["current_winner_p_a"], test["historical_winner_p_a"], wf.weight_current)
        for j, (_, row) in enumerate(test.iterrows()):
            winner_rows.append({"date": test_date, "actual": int(row["actual_a_win"]), "p": float(wp[j])})

        cur_m = train[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
        hist_m = train[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
        mf = fit_multiclass_blend(train["actual_joint_class"], cur_m, hist_m)
        test_cur = test[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
        test_hist = test[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
        mp = multiclass_log_pool(test_cur, test_hist, mf.weight_current)
        for j, (_, row) in enumerate(test.iterrows()):
            method_rows.append({"date": test_date, "actual": int(row["actual_joint_class"]), "p": mp[j]})

        ttrain = timing[(timing["date"].isin(TRAIN_DATES)) & (timing["date"] < test_date)]
        ttest = timing[timing["date"].eq(test_date)]
        if ttrain["fight_id"].nunique() >= 20 and not ttest.empty:
            tf = fit_grouped_binary_blend(
                ttrain["actual"], ttrain["current_probability"], ttrain["historical_probability"], ttrain["fight_id"]
            )
            tp = binary_logit_pool(ttest["current_probability"], ttest["historical_probability"], tf.weight_current)
            for j, (_, row) in enumerate(ttest.iterrows()):
                timing_rows.append({**row.to_dict(), "p": float(tp[j])})

    out: dict[str, object] = {"dates_scored": sorted({r["date"] for r in winner_rows})}
    if winner_rows:
        out["winner"] = binary_metrics([r["actual"] for r in winner_rows], [r["p"] for r in winner_rows])
    if method_rows:
        out["method"] = method_metrics([r["actual"] for r in method_rows], np.vstack([r["p"] for r in method_rows]))
    if timing_rows:
        t = pd.DataFrame(timing_rows)
        out["timing"] = binary_metrics(t["actual"], t["p"])
        out["timing"]["n_fights"] = int(t["fight_id"].nunique())
    return out


def evaluate_split(fights: pd.DataFrame, timing: pd.DataFrame, date: str, weights: dict[str, float]) -> dict[str, object]:
    f = fights[fights["date"].eq(date)].copy()
    t = timing[timing["date"].eq(date)].copy()
    out: dict[str, object] = {"date": date, "n_fights": int(len(f))}
    if f.empty:
        return out

    wp = binary_logit_pool(f["current_winner_p_a"], f["historical_winner_p_a"], weights["winner"])
    out["winner"] = {
        "current": binary_metrics(f["actual_a_win"], f["current_winner_p_a"]),
        "historical": binary_metrics(f["actual_a_win"], f["historical_winner_p_a"]),
        "unified": binary_metrics(f["actual_a_win"], wp),
    }

    cur = f[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
    hist = f[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
    uni = multiclass_log_pool(cur, hist, weights["method"])
    out["method"] = {
        "current": method_metrics(f["actual_joint_class"], cur),
        "historical": method_metrics(f["actual_joint_class"], hist),
        "unified": method_metrics(f["actual_joint_class"], uni),
    }

    if not t.empty:
        tp = binary_logit_pool(t["current_probability"], t["historical_probability"], weights["timing"])
        timing_summary = {
            "current": binary_metrics(t["actual"], t["current_probability"]),
            "historical": binary_metrics(t["actual"], t["historical_probability"]),
            "unified": binary_metrics(t["actual"], tp),
            "n_fights": int(t["fight_id"].nunique()),
            "per_market": {},
        }
        for market, g in t.assign(unified_probability=tp).groupby("market"):
            timing_summary["per_market"][market] = {
                "current": binary_metrics(g["actual"], g["current_probability"]),
                "historical": binary_metrics(g["actual"], g["historical_probability"]),
                "unified": binary_metrics(g["actual"], g["unified_probability"]),
            }
        out["timing"] = timing_summary
    return out


def main() -> int:
    historical_dir = ROOT / "data/historical"
    outdir = ROOT / "data/unified"
    outdir.mkdir(parents=True, exist_ok=True)
    frame_path = historical_dir / "prefight_perspective_rows.csv"
    if not frame_path.exists():
        raise SystemExit("Run build_historical_model.py before the unified ensemble build")
    frame = pd.read_csv(frame_path, low_memory=False)

    tables = load_source_files(ROOT / "data/raw/ufcstats_mirror")
    tables = apply_results_supplements(tables, ROOT / "data/supplemental/results")
    fights, timing = build_rows(frame, tables["results"])

    train = fights[fights["date"].isin(TRAIN_DATES)].copy()
    ttrain = timing[timing["date"].isin(TRAIN_DATES)].copy()
    if len(train) < 40:
        raise RuntimeError(f"Expected at least 40 matched training fights, got {len(train)}")
    if fights[fights["date"].eq(HOLDOUT_DATE)].empty:
        raise RuntimeError("Edmonton holdout did not match historical predictions")

    winner_fit = fit_binary_blend(train["actual_a_win"], train["current_winner_p_a"], train["historical_winner_p_a"])
    method_fit = fit_multiclass_blend(
        train["actual_joint_class"],
        train[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float),
        train[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float),
    )
    timing_fit = fit_grouped_binary_blend(
        ttrain["actual"], ttrain["current_probability"], ttrain["historical_probability"], ttrain["fight_id"]
    )
    weights = {
        "winner": winner_fit.weight_current,
        "method": method_fit.weight_current,
        "timing": timing_fit.weight_current,
    }

    weights_payload = {
        "status": "UNIFIED_ENSEMBLE_SHADOW_NOT_PROMOTED",
        "training_dates": list(TRAIN_DATES),
        "untouched_holdout_date": HOLDOUT_DATE,
        "design": {
            "winner": "convex logit pool: frozen current/reference ML + historical conditional ML",
            "method": "convex six-state geometric/log pool: frozen current joint method + historical six-state ML",
            "timing": "fight-balanced binary logit weight learned across coherent timing markets; deploy weight at hazard level",
            "weight_meaning": "weight_current; historical weight = 1 - weight_current",
            "grid_step": 0.025,
            "odds_used": False,
        },
        "winner": winner_fit.to_dict(),
        "method": method_fit.to_dict(),
        "timing": timing_fit.to_dict(),
    }
    (outdir / "unified_ensemble_weights.json").write_text(json.dumps(weights_payload, indent=2) + "\n", encoding="utf-8")

    # Audit output: show final unified probabilities for all recent training + holdout fights,
    # while never feeding the holdout outcomes into weight fitting.
    wp = binary_logit_pool(fights["current_winner_p_a"], fights["historical_winner_p_a"], weights["winner"])
    cur_m = fights[[f"current_{k}" for k in SIX_KEYS]].to_numpy(float)
    hist_m = fights[[f"historical_{k}" for k in SIX_KEYS]].to_numpy(float)
    uni_m = multiclass_log_pool(cur_m, hist_m, weights["method"])
    fight_audit = fights.copy()
    fight_audit["unified_winner_p_a"] = wp
    for i, key in enumerate(SIX_KEYS):
        fight_audit[f"unified_{key}"] = uni_m[:, i]
    fight_audit.to_csv(outdir / "unified_recent_predictions.csv", index=False)

    tp = binary_logit_pool(timing["current_probability"], timing["historical_probability"], weights["timing"])
    timing_audit = timing.copy(); timing_audit["unified_probability"] = tp
    timing_audit.to_csv(outdir / "unified_timing_predictions.csv", index=False)

    metrics = {
        "status": "SHADOW_ONLY",
        "training_fit": evaluate_split(
            fights.assign(date=np.where(fights["date"].isin(TRAIN_DATES), "TRAIN", fights["date"])),
            timing.assign(date=np.where(timing["date"].isin(TRAIN_DATES), "TRAIN", timing["date"])),
            "TRAIN", weights,
        ),
        "walk_forward_meta_validation": walk_forward(fights, timing),
        "edmonton_untouched_holdout": evaluate_split(fights, timing, HOLDOUT_DATE, weights),
        "warning": (
            "The unified weights are low-capacity but the frozen-card training sample is still small. "
            "Edmonton is one untouched event, not promotion proof. Keep base components visible and "
            "continue prospective grading before changing official roles."
        ),
    }
    (outdir / "unified_ensemble_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "matched_training_fights": int(len(train)),
        "matched_holdout_fights": int((fights["date"] == HOLDOUT_DATE).sum()),
        "timing_training_market_rows": int(len(ttrain)),
        "timing_training_fights": int(ttrain["fight_id"].nunique()),
        "training_dates": list(TRAIN_DATES),
        "holdout_date": HOLDOUT_DATE,
        "weights": weights,
        "files": [
            "unified_ensemble_weights.json", "unified_ensemble_metrics.json",
            "unified_recent_predictions.csv", "unified_timing_predictions.csv",
        ],
    }
    (outdir / "unified_build_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": manifest, "metrics": metrics}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
