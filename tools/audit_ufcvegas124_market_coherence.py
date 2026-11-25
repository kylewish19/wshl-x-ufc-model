"""Review UFC Vegas124 pre-price method vs timing coherence.

Original reference side, conditional method, timing and simulated predictions
remain frozen. Saves an odds-blind, *unpromoted* IPF-coherence shadow and a
conservative prop-market block policy. Never silently rewrite Stage A.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from wshlx_ufc.coherence import (
    JOINT_KEYS,
    finish_probability,
    reconcile_joint_with_finish_marginal,
)
from wshlx_ufc.models import fighter_double_chance

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/locks/ufcvegas124_2026-11-07"
RAW = DIR / "stage_a_model_raw_three_view.json"
LOCK = DIR / "stage_a_final_selection.json"
AUDIT = DIR / "stage_a_final_audit.json"
OUT = DIR / "stage_a_coherence_shadow.json"
OUT_AUDIT = DIR / "stage_a_coherence_audit.json"
GAP_GATE = 0.15  # Diagnostic threshold, NOT a betting edge.


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(a: float, b: float, label: str) -> None:
    if abs(a - b) > 1e-8:
        raise RuntimeError(f"Coherence check failed: {label}: {a} != {b}")


def main():
    raw = json.loads(RAW.read_text())
    frozen = json.loads(LOCK.read_text())
    audit = json.loads(AUDIT.read_text())
    if not frozen["stage_a_frozen"] or frozen["odds_used"] or len(frozen["fights"]) != 14:
        raise RuntimeError("Official 14-fight frozen Stage A required and price-free")
    if sha(RAW) != frozen["raw_model_sha256"] or audit["raw_model_sha256"] != sha(RAW):
        raise RuntimeError("Stage A raw source was modified after the freeze")
    if raw["event_date"] != "2026-11-07" or not raw["odds_used"] is False:
        raise RuntimeError("Wrong card or non-odds-blind raw model")
    if len(raw["fights"]) != 14:
        raise RuntimeError("Raw 14-fight model incomplete")

    rows = []
    failures = []
    gaps = []
    for r, f in zip(raw["fights"], frozen["fights"]):
        if r["fight_no"] != f["fight_no"] or f["a"] != r["a"] or f["b"] != r["b"]:
            raise RuntimeError("Freeze/raw fight order mismatch")
        original = {k: float(r["joint_calibrated"][k]) for k in JOINT_KEYS}
        finish_joint = finish_probability(original)
        finish_hazard = float(r["timing_v033_direct"]["GTD_NO"])
        gap = finish_joint - finish_hazard
        adjusted = reconcile_joint_with_finish_marginal(original, finish_hazard)
        p_ref = float(r["winner_reference_p_a"])
        check(sum(original[k] for k in ("A_KO","A_SUB","A_DEC")), p_ref, "reference side marginal")
        check(sum(adjusted[k] for k in ("A_KO","A_SUB","A_DEC")), p_ref, "corrected side marginal")
        check(finish_probability(adjusted), finish_hazard, "adjusted finish")
        check(sum(adjusted[k] for k in ("A_DEC","B_DEC")), 1 - finish_hazard, "adjusted GTD")
        all_in_bounds = all(0 <= p <= 1 for p in adjusted.values())
        if not all_in_bounds:
            raise RuntimeError("Reconciled shadow contains invalid probabilities")
        impossible = [
            k for k in ("A_KO","A_SUB","B_KO","B_SUB")
            if original[k] > finish_hazard + 1e-9
        ]
        if impossible:
            failures.append({"fight_no": f["fight_no"], "impossible_exact_method_keys": impossible})
        gap_flag = abs(gap) > GAP_GATE
        gaps.append(gap_flag)
        rows.append({
            "fight_no": r["fight_no"],
            "fight": f'{f["a"]} vs {f["b"]}',
            "reference_pick": f["official_reference_pick"],
            "reference_win_probability": f["official_reference_probability"],
            "unreconciled_method_finish_probability": finish_joint,
            "timing_hazard_finish_probability": finish_hazard,
            "finish_probability_gap_pp": 100 * gap,
            "large_gap_over_15pp": gap_flag,
            "raw_exact_fighter_finish_exceeds_GTD_NO": impossible,
            "current_joint_original_frozen_unchanged": original,
            "candidate_joint_reconciled_shadow": adjusted,
            "candidate_double_chance_reconciled_shadow": fighter_double_chance(adjusted),
            "candidate_not_an_official_stage_a_or_stage_b_pick": True,
            "method_props_price_gate": "BLOCKED_UNTIL_PROSPECTIVE_COHERENCE_CALIBRATION",
            "timing_props_price_gate": (
                "BLOCKED_PENDING_FAMILY_RECONCILIATION" if gap_flag else "INDEPENDENT_TIMING_MODEL_ONLY_NOT_PRICE_ACCEPTED"
            ),
        })
    payload = {
        "status": "SHADOW_ONLY_METHOD_TIMING_COHERENCE_RECONCILIATION_BEFORE_PRICING",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "event": frozen["event"], "event_date": frozen["event_date"],
        "source_frozen_stage_a_sha256": sha(LOCK),
        "source_raw_model_sha256": sha(RAW),
        "odds_used": False,
        "stage_a_winner_and_props_untouched": True,
        "algorithm": "iterative proportional fitting of fighter×finish vs fighter×DEC to preserve reference winner P, timing GTD_NO P and within-winner KO/SUB relative mix; no new training and no hidden event outcomes",
        "policy": {
            "promoted_model": False, "new_official_method_picks": 0,
            "reconciled_shadow_prices_playable": False,
            "reason": "Probability coherence fixes mathematical compatibility only. It is NOT evidence of predictive calibration or EV.",
            "all_exact_method_market_prices_blocked": True,
            "severe_gap_threshold_pp": 15,
            "independent_timing_market_family_requires_own_prospective_checks": True,
        },
        "fights": rows,
    }
    summary = {
        "status": payload["status"],
        "fights": len(rows), "severe_gap_count": sum(gaps),
        "impossible_exact_fighter_finish_count": len(failures),
        "impossible_cases": failures,
        "max_absolute_gap_pp": max(abs(r["finish_probability_gap_pp"]) for r in rows),
        "odds_used": False, "new_official_method_bets": 0,
        "shadow_not_promoted": True,
        "frozen_source_sha256": sha(LOCK),
        "link_to_shadow": str(OUT.relative_to(ROOT)),
        "note": "Original Stage A is immutable. This flags cross-family probability inconsistency and preserves an unvalidated math-only coherence shadow."
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    OUT_AUDIT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
