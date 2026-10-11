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

INTERACTION_FEATURES = [
    "diff_td_access",
    "diff_submission_access",
    "diff_control_access",
    "diff_damage_pressure",
    "diff_striking_vulnerability",
    "reach_damage_interaction",
    "experience_gap_log",
]


def safe_mul(a: pd.Series, b: pd.Series) -> pd.Series:
    return pd.to_numeric(a, errors="coerce") * pd.to_numeric(b, errors="coerce")


def add_interactions(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()

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
    sample = match_clean(clean, winner_df)
    sample = add_interactions(sample)

    base_features = list(rb.WINNER_FEATURES)
    candidate_features = base_features + INTERACTION_FEATURES
    p_base = np.full(len(sample), np.nan)
    p_candidate = np.full(len(sample), np.nan)

    for cutoff in sorted(sample["event_date"].unique()):
        train = winner_df.loc[winner_df["event_date"] < cutoff].copy()
        mask = sample["event_date"] == cutoff
        base = WinnerModel(c=0.25).fit(train[base_features], train["winner_is_a"])
        cand = WinnerModel(c=0.25).fit(train[candidate_features], train["winner_is_a"])
        p_base[mask] = base.predict_proba(sample.loc[mask, base_features])[:, 0]
        p_candidate[mask] = cand.predict_proba(sample.loc[mask, candidate_features])[:, 0]

    y = sample["winner_is_a"].to_numpy(int)
    m_base = metrics(y, p_base)
    m_candidate = metrics(y, p_candidate)

    improved_brier = m_candidate["brier"] < m_base["brier"]
    improved_log = m_candidate["log_loss"] < m_base["log_loss"]
    nonworse_acc = m_candidate["accuracy"] >= m_base["accuracy"]
    promotion_ready = bool(improved_brier and improved_log and nonworse_acc)

    comparison = sample[["event_date", "clean_fight", "fighter_a", "fighter_b", "winner"]].copy()
    comparison["p_a_base"] = p_base
    comparison["p_a_candidate"] = p_candidate
    comparison["base_pick_a"] = (p_base >= 0.5).astype(int)
    comparison["candidate_pick_a"] = (p_candidate >= 0.5).astype(int)
    comparison["winner_is_a"] = y
    comparison["base_correct"] = (comparison["base_pick_a"] == y).astype(int)
    comparison["candidate_correct"] = (comparison["candidate_pick_a"] == y).astype(int)
    comparison["candidate_minus_base_p_a"] = p_candidate - p_base

    payload = {
        "status": "V0.34_WINNER_INTERACTION_CHALLENGER_RETROSPECTIVE_BENCHMARK",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "clean_sample": "clean_ufc_101_2026-10-03.csv",
        "base": m_base,
        "candidate": m_candidate,
        "delta": {
            "accuracy": m_candidate["accuracy"] - m_base["accuracy"],
            "brier": m_candidate["brier"] - m_base["brier"],
            "log_loss": m_candidate["log_loss"] - m_base["log_loss"],
        },
        "interaction_features": INTERACTION_FEATURES,
        "promotion_ready_on_retrospective_metrics_only": promotion_ready,
        "governance_note": "These interactions were designed after UFC Vegas 122. Historical OOF improvement is development evidence only, not prospective proof. Do not replace the official winner reference without future-card validation.",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    (OUT / "benchmark.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    comparison.to_csv(OUT / "oof_comparison_101.csv", index=False)

    final_candidate = WinnerModel(c=0.25).fit(winner_df[candidate_features], winner_df["winner_is_a"])
    joblib.dump(final_candidate, ART / "winner_v034_interactions.joblib")
    (ART / "manifest.json").write_text(
        json.dumps(
            {
                "status": "SHADOW_ONLY",
                "trained_through": "2026-10-03",
                "base_features": base_features,
                "interaction_features": INTERACTION_FEATURES,
                "benchmark": payload,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    report = [
        "# v0.34 winner interaction challenger",
        "",
        "This challenger was created after the UFC Vegas 122 miss audit. It is **shadow-only** regardless of retrospective results.",
        "",
        f"- Base OOF: **{m_base['wins']}-{m_base['losses']} ({m_base['accuracy']:.1%})**, Brier {m_base['brier']:.4f}, log loss {m_base['log_loss']:.4f}",
        f"- Candidate OOF: **{m_candidate['wins']}-{m_candidate['losses']} ({m_candidate['accuracy']:.1%})**, Brier {m_candidate['brier']:.4f}, log loss {m_candidate['log_loss']:.4f}",
        f"- Candidate minus base Brier: **{payload['delta']['brier']:+.4f}** (lower is better)",
        f"- Candidate minus base log loss: **{payload['delta']['log_loss']:+.4f}** (lower is better)",
        "",
        "## Added matchup interactions",
        "",
        "- takedown access versus opponent takedown defense",
        "- submission access versus opponent submission exposure",
        "- control access versus opponent control conceded",
        "- knockdown pressure versus opponent knockdown vulnerability",
        "- striking output versus opponent absorption",
        "- reach × damage-pressure interaction",
        "- log UFC-experience gap",
        "",
        "## Governance",
        "",
        "These features were designed after UFC Vegas 122, so even a strong historical OOF result is not prospective proof. The current official winner reference stays unchanged until the challenger proves itself on future frozen cards.",
    ]
    (OUT / "BUILD_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
