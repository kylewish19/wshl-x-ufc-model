from __future__ import annotations

import json
from pathlib import Path

from wshlx_ufc.selection_policy import method_bet_gate

ROOT = Path(__file__).resolve().parents[1]
LOCK_DIR = ROOT / "data/locks/ufcvegas122_2026-10-10"
RAW = LOCK_DIR / "stage_a_model_raw_v033.json"
OUT = LOCK_DIR / "stage_a_gate_summary_v033.json"


def top_method(d: dict[str, float]) -> str:
    return max(d, key=d.get)


def main():
    locked = json.loads(RAW.read_text())
    payload = locked["payload"]
    rows = []
    for f in payload["fights"]:
        pick_a = float(f["winner_reference_p_a"]) >= 0.5
        side = "a" if pick_a else "b"
        side_letter = "A" if pick_a else "B"
        winner = f["a"] if pick_a else f["b"]
        p_win = float(f["winner_reference_p_a"] if pick_a else 1.0 - f["winner_reference_p_a"])
        baseline = f[f"method_if_{side}_wins_baseline"]
        calibrated = f[f"method_if_{side}_wins_calibrated"]
        residual = f[f"method_if_{side}_wins_residual"]
        method = top_method(calibrated)
        p_cond = float(calibrated[method])
        p_joint = float(f["joint_calibrated"][f"{side_letter}_{method}"])
        ev = f["evidence_density"]
        gate = method_bet_gate(
            winner_probability=p_win,
            exact_joint_method_probability=p_joint,
            conditional_method_probability=p_cond,
            baseline_top_method=top_method(baseline),
            shadow_top_method=method,
            fighter_a_prior_ufc_bouts=int(ev["a_prior_ufc_bouts"]),
            fighter_b_prior_ufc_bouts=int(ev["b_prior_ufc_bouts"]),
        )
        timing = f["timing_v033_direct"]
        rows.append({
            "fight_no": f["fight_no"],
            "fight": f'{f["a"]} vs {f["b"]}',
            "winner": winner,
            "winner_probability": p_win,
            "winner_v033_probability": float(f["winner_v033_p_a"] if pick_a else 1.0 - f["winner_v033_p_a"]),
            "winner_model_disagreement": bool(f["winner_model_disagreement"]),
            "confidence_10": float(f["evidence_adjusted_confidence_10"]),
            "sparse": bool(f["sparse_ufc_evidence"]),
            "selected_side_method_baseline": baseline,
            "selected_side_method_calibrated": calibrated,
            "selected_side_method_residual": residual,
            "secondary_method": method,
            "conditional_method_probability": p_cond,
            "exact_joint_method_probability": p_joint,
            "method_gate_eligible": bool(gate.eligible),
            "method_gate_reasons": list(gate.reasons),
            "double_chance_calibrated": f["double_chance_calibrated"],
            "timing": timing,
            "evidence": ev,
        })
    OUT.write_text(json.dumps({
        "event": payload["event"],
        "event_date": payload["event_date"],
        "raw_lock_sha256": locked["sha256"],
        "odds_used": False,
        "rows": rows,
    }, indent=2), encoding="utf-8")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
