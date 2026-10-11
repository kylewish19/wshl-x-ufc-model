from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

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


rb = load_module("rebuild_v027_v034_winner", ROOT / "tools/rebuild_v027.py")
from wshlx_ufc.models import WinnerModel

RAW_DIR = ROOT / "data/raw/ufc332_2026-10-03"
CLEAN = ROOT / "data/results/clean_ufc_101_2026-10-03.csv"
OUT = ROOT / "reports/v034_winner_interactions"
ART = ROOT / "artifacts/v034_winner_interactions"

PACE_FEATURES = [
    "a_sig_attempted_per_min",
    "b_sig_attempted_per_min",
    "diff_sig_attempted_per_min",
]
ACCESS_FEATURES = [
    "diff_td_access",
    "diff_submission_access",
    "diff_control_access",
]
DAMAGE_FEATURES = [
    "diff_damage_pressure",
    "diff_striking_vulnerability",
    "reach_damage_interaction",
]
EXPERIENCE_FEATURES = ["experience_gap_log"]

VARIANTS = {
    "base": [],
    "pace_only": PACE_FEATURES,
    "access_only": ACCESS_FEATURES,
    "damage_only": DAMAGE_FEATURES,
    "experience_only": EXPERIENCE_FEATURES,
    "access_plus_pace": ACCESS_FEATURES + PACE_FEATURES,
    "full": PACE_FEATURES + ACCESS_FEATURES + DAMAGE_FEATURES + EXPERIENCE_FEATURES,
}


def safe_mul(a: pd.Series, b: pd.Series) -> pd.Series:
    return pd.to_numeric(a, errors="coerce") * pd.to_numeric(b, errors="coerce")


def attempts_per_min(landed_per_min: pd.Series, accuracy: pd.Series) -> pd.Series:
    landed = pd.to_numeric(landed_per_min, errors="coerce")
    acc = pd.to_numeric(accuracy, errors="coerce")
    out = landed / acc.where(acc > 1e-6)
    return out.replace([np.inf, -np.inf], np.nan)


def add_interactions(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()

    out["a_sig_attempted_per_min"] = attempts_per_min(out["a_sig_landed_per_min"], out["a_sig_accuracy"])
    out["b_sig_attempted_per_min"] = attempts_per_min(out["b_sig_landed_per_min"], out["b_sig_accuracy"])
    out["diff_sig_attempted_per_min"] = out["a_sig_attempted_per_min"] - out["b_sig_attempted_per_min"]

    a_td_weak = 1.0 - pd.to_numeric(out["b_td_defense"], errors="coerce")
    b_td_weak = 1.0 - pd.to_numeric(out["a_td_defense"], errors="coerce")
    a_td_access = safe_mul(out["a_td_landed_per15"], a_td_weak)
    b_td_access = safe_mul(out["b_td_landed_per15"], b_td_weak)
    out["diff_td_access"] = a_td_access - b_td_access

    a_sub_access = safe_mul(out["a_sub_att_per15"], 1.0 + pd.to_numeric(out["b_sub_att_against_per15"], errors="coerce"))
    b_sub_access = safe_mul(out["b_sub_att_per15"], 1.0 + pd.to_numeric(out["a_sub_att_against_per15"], errors="coerce"))
    out["diff_submission_access"] = a_sub_access - b_sub_access

    a_ctrl_access = safe_mul(out["a_ctrl_for_per15"] / 900.0, 1.0 + pd.to_numeric(out["b_ctrl_against_per15"], errors="coerce") / 900.0)
    b_ctrl_access = safe_mul(out["b_ctrl_for_per15"] / 900.0, 1.0 + pd.to_numeric(out["a_ctrl_against_per15"], errors="coerce") / 900.0)
    out["diff_control_access"] = a_ctrl_access - b_ctrl_access

    a_damage = safe_mul(out["a_kd_for_per15"], 1.0 + pd.to_numeric(out["b_kd_against_per15"], errors="coerce"))
    b_damage = safe_mul(out["b_kd_for_per15"], 1.0 + pd.to_numeric(out["a_kd_against_per15"], errors="coerce"))
    out["diff_damage_pressure"] = a_damage - b_damage

    a_strike_vuln = safe_mul(out["a_sig_landed_per_min"], pd.to_numeric(out["b_sig_absorbed_per_min"], errors="coerce"))
    b_strike_vuln = safe_mul(out["b_sig_landed_per_min"], pd.to_numeric(out["a_sig_absorbed_per_min"], errors="coerce"))
    out["diff_striking_vulnerability"] = a_strike_vuln - b_strike_vuln

    reach_diff = pd.to_numeric(out["diff_reach_inches"], errors="coerce")
    out["reach_damage_interaction"] = reach_diff * (a_damage + b_damage)

    a_exp = np.log1p(pd.to_numeric(out["a_prior_bouts"], errors="coerce").clip(lower=0))
    b_exp = np.log1p(pd.to_numeric(out["b_prior_bouts"], errors="coerce").clip(lower=0))
    out["experience_gap_log"] = a_exp - b_exp
    return out


def match_clean(clean: pd.DataFrame, winner_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    used: set[int] = set()
    for c in clean.itertuples(index=False):
        date = str(c.event_date)
        f1, f2 = [x.strip() for x in str(c.fight).split(" vs ", 1)]
        nset = {rb.norm_name(f1), rb.norm_name(f2)}
        cand = winner_df.loc[winner_df["event_date"].str.startswith(date)]
        best_i, best_score = None, -1
        for i, r in cand.iterrows():
            rset = {rb.norm_name(r["fighter_a"]), rb.norm_name(r["fighter_b"])}
            score = len(nset & rset)
            if score > best_score and int(i) not in used:
                best_i, best_score = i, score
        if best_i is None or best_score < 2:
            raise RuntimeError(f"Could not match {date} {c.fight}")
        used.add(int(best_i))
        row = winner_df.loc[best_i].to_dict()
        row["clean_fight"] = str(c.fight)
        rows.append(row)
    return pd.DataFrame(rows)


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float | int]:
    pred = (p >= 0.5).astype(int)
    return {
        "n": int(len(y)),
        "accuracy": float(np.mean(pred == y)),
        "wins": int(np.sum(pred == y)),
        "losses": int(np.sum(pred != y)),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(log_loss(y, np.column_stack([1.0 - p, p]), labels=[0, 1])),
    }


def main() -> None:
    old_cutoff = rb.TRAINING_CUTOFF
    rb.TRAINING_CUTOFF = pd.Timestamp("2026-10-04", tz="UTC")
    try:
        fights, stats, static = rb.load_fights(RAW_DIR)
    finally:
        rb.TRAINING_CUTOFF = old_cutoff

    fight_stats = rb.aggregate_fight_stats(fights, stats)
    winner_df, _, _ = rb.enrich_and_snapshot(fights, fight_stats, static)
    winner_df = add_interactions(winner_df)

    clean = pd.read_csv(CLEAN)
    sample = add_interactions(match_clean(clean, winner_df))
    y = sample["winner_is_a"].to_numpy(int)
    base_features = list(rb.WINNER_FEATURES)

    probabilities: dict[str, np.ndarray] = {name: np.full(len(sample), np.nan) for name in VARIANTS}

    for cutoff in sorted(sample["event_date"].unique()):
        train = winner_df.loc[winner_df["event_date"] < cutoff].copy()
        mask = sample["event_date"] == cutoff
        for name, extra in VARIANTS.items():
            features = base_features + extra
            model = WinnerModel(c=0.25).fit(train[features], train["winner_is_a"])
            probabilities[name][mask] = model.predict_proba(sample.loc[mask, features])[:, 0]

    variant_metrics = {name: metrics(y, p) for name, p in probabilities.items()}
    base_m = variant_metrics["base"]

    candidates = []
    for name, m in variant_metrics.items():
        if name == "base":
            continue
        candidates.append(
            {
                "name": name,
                "features": VARIANTS[name],
                "metrics": m,
                "delta_accuracy": m["accuracy"] - base_m["accuracy"],
                "delta_brier": m["brier"] - base_m["brier"],
                "delta_log_loss": m["log_loss"] - base_m["log_loss"],
                "passes_retrospective_metric_gate": bool(
                    m["accuracy"] >= base_m["accuracy"]
                    and m["brier"] < base_m["brier"]
                    and m["log_loss"] < base_m["log_loss"]
                ),
            }
        )

    best = min(candidates, key=lambda x: (x["metrics"]["brier"], x["metrics"]["log_loss"]))

    comparison = sample[["event_date", "clean_fight", "fighter_a", "fighter_b", "winner"]].copy()
    comparison["winner_is_a"] = y
    for name, p in probabilities.items():
        comparison[f"p_a_{name}"] = p
        comparison[f"correct_{name}"] = ((p >= 0.5).astype(int) == y).astype(int)

    payload = {
        "status": "V0.34_WINNER_FEATURE_ABLATION_RETROSPECTIVE_BENCHMARK",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "clean_sample": "clean_ufc_101_2026-10-03.csv",
        "base": base_m,
        "variants": candidates,
        "best_retrospective_variant": best["name"],
        "best_variant_passes_metric_gate": best["passes_retrospective_metric_gate"],
        "governance_note": "All new features were designed after UFC Vegas 122. This ablation is retrospective development evidence only. No variant may replace the official winner reference without future frozen-card validation.",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    (OUT / "benchmark.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    comparison.to_csv(OUT / "oof_comparison_101.csv", index=False)

    best_features = base_features + VARIANTS[best["name"]]
    best_model = WinnerModel(c=0.25).fit(winner_df[best_features], winner_df["winner_is_a"])
    joblib.dump(best_model, ART / "winner_v034_best_shadow.joblib")
    (ART / "manifest.json").write_text(
        json.dumps(
            {
                "status": "SHADOW_ONLY_NOT_PROMOTED",
                "trained_through": "2026-10-03",
                "selected_retrospective_variant": best["name"],
                "selected_features": VARIANTS[best["name"]],
                "benchmark": payload,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    report = [
        "# v0.34 winner feature ablation",
        "",
        "Created after the UFC Vegas 122 miss audit. Every candidate remains **shadow-only**.",
        "",
        f"Base: **{base_m['wins']}-{base_m['losses']} ({base_m['accuracy']:.1%})**, Brier {base_m['brier']:.4f}, log loss {base_m['log_loss']:.4f}",
        "",
        "## Variants",
        "",
    ]
    for c in sorted(candidates, key=lambda x: x["metrics"]["brier"]):
        m = c["metrics"]
        report.append(
            f"- **{c['name']}**: {m['wins']}-{m['losses']} ({m['accuracy']:.1%}), Brier {m['brier']:.4f} ({c['delta_brier']:+.4f}), log loss {m['log_loss']:.4f} ({c['delta_log_loss']:+.4f}); retrospective gate={'PASS' if c['passes_retrospective_metric_gate'] else 'FAIL'}"
        )
    report += [
        "",
        f"Best retrospective Brier variant: **{best['name']}**.",
        "",
        "## Governance",
        "",
        "This is multiple-hypothesis development work performed after UFC Vegas 122. Even a retrospective PASS is not enough for promotion. The official winner reference stays unchanged; the selected candidate is stored only as a future-card shadow.",
    ]
    (OUT / "BUILD_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
