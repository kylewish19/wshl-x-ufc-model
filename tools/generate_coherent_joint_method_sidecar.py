"""Generate ONLY a separate pre-fight coherence-challenger research sidecar.

This code never trains, reweights, recalibrates, or overwrites Stage A, Stage B,
Reference, Historical, Unified, 10k sims, or the wager authorization path.
It requires the exact final frozen odds-blind raw pre-event file and SHA.
The output is an explicitly UNAPPROVED research shadow; wager markets cannot
be authorized from this sidecar alone. Replays after event are labeled as such.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from wshlx_ufc.joint_coherence_shadow import project, JOINT_KEYS


def build_sidecar(frozen: dict, raw: dict, raw_bytes: bytes,
                  *, generated_date: str) -> dict:
    expected = frozen.get("raw_model_sha256",
                          frozen.get("original_stage_a_raw_sha256"))
    if (frozen.get("stage_a_frozen") is not True or
            frozen.get("odds_used") is not False or
            raw.get("odds_used") is not False or
            hashlib.sha256(raw_bytes).hexdigest() != expected):
        raise ValueError("Missing verified odds-blind frozen Stage A/raw hash")
    if (not (frozen["event_date"] == raw["event_date"]) or
            len(frozen["fights"]) != len(raw["fights"]) or
            not raw["fights"]):
        raise ValueError("Event/card identity mismatch")
    if generated_date < "2001-01-01":
        raise ValueError("Bad generation date")
    freeze_by_no = {f["fight_no"]: f for f in frozen["fights"]}
    if len(freeze_by_no) != len(frozen["fights"]):
        raise ValueError("Duplicate fight")
    fights = []
    for f in raw["fights"]:
        n = f["fight_no"]
        orig = freeze_by_no[n]
        if (f["a"], f["b"]) != (orig["a"], orig["b"]):
            raise ValueError("Original fight identity mismatch")
        shadow = {}
        for label, key in (
                ("historical", "historical_shadow"),
                ("unified", "oof_unified_shadow")):
            obj = f[key]
            winner_p_a = float(obj["winner_p_a"])
            finish_p = float(obj["timing_direct"]["GTD_NO"])
            joint = obj["joint_method"]
            shadow[label] = {
                "original_archived_joint": {k: joint[k] for k in JOINT_KEYS},
                "original_winner_p_a": winner_p_a,
                "original_direct_timing_gtd_no": finish_p,
                "projected_winner_only": project(
                    joint, winner_p_a=winner_p_a),
                "projected_winner_and_timing": project(
                    joint, winner_p_a=winner_p_a, finish_p=finish_p),
                "prediction_changes_to_original": False,
                "bet_authorized": False,
            }
        fights.append({
            "fight_no": n, "a": f["a"], "b": f["b"],
            "models": shadow, "bet_authorized": False,
        })
    return {
        "schema": "WSHL_X_COHERENT_JOINT_METHOD_PRE_EVENT_RESEARCH_SIDECAR_V1",
        "event": frozen["event"], "event_date": frozen["event_date"],
        "generated_date_utc": generated_date,
        "pre_event_shadow": generated_date <= frozen["event_date"],
        "generated_after_event_replay": generated_date > frozen["event_date"],
        "source_original_raw_sha256": expected,
        "source_original_stage_a_frozen": True,
        "derived_from_frozen_odds_blind_three_view_data_only": True,
        "post_event_results_used_as_inputs": False,
        "fanduel_odds_used": False,
        "original_model_weights_or_picks_changed": False,
        "original_10000_simulation_suites_changed": False,
        "new_model_trained": False,
        "wager_gate": "UNAPPROVED_SHADOW_RESEARCH_ONLY",
        "bet_authorized": False,
        "original_reference_or_historical_or_unified_promoted": False,
        "source_bout_count": len(fights), "fights": fights,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-a-final", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise RuntimeError("Refusing to overwrite existing shadow file")
    raw_bytes = args.raw.read_bytes()
    frozen = json.loads(args.stage_a_final.read_text())
    raw = json.loads(raw_bytes)
    generated_date = datetime.now(timezone.utc).date().isoformat()
    out = build_sidecar(frozen, raw, raw_bytes, generated_date=generated_date)
    if not out["pre_event_shadow"]:
        # Research replays are allowed but must NEVER be called a locked
        # prospective card or retrospectively slipped into an old wager ledger.
        print("CAUTION: retrospective replay, not prospective prediction")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(f"{len(out['fights'])} research shadow joint projections; zero approved bets.")


if __name__ == "__main__":
    main()
