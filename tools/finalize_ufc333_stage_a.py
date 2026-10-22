from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_DIR = ROOT / "data/locks/ufc333_2026-10-24"
RAW_PATH = LOCK_DIR / "stage_a_model_raw_three_view.json"
OUT_PATH = LOCK_DIR / "stage_a_final_selection.json"
AUDIT_PATH = LOCK_DIR / "stage_a_final_audit.json"

# Research decisions are deliberately separate from the model-raw artifact.
# No sportsbook prices are stored or used here.
RESEARCH = {
    1: {
        "tier": "B",
        "status": "SIDE",
        "reason": "Lucindo is the reference, historical, and OOF-unified side. The major caution is her long layoff; Caliari returned to the win column by submission in May. The layoff is already represented in the pre-fight state, so this lowers confidence rather than changing the side.",
        "tape": "Continuous playback unavailable in this environment. Official UFC preview/athlete history reviewed; a UFC full-fight source for Lucindo was located but not visually played here.",
    },
    2: {
        "tier": "C",
        "status": "LEAN",
        "reason": "All three winner views lean Gugnon, but both fighters have very little UFC evidence. Steele and Gugnon are both coming off first-round submissions, and the sparse-data flag is active.",
        "tape": "Continuous playback unavailable. Official UFC preview plus recent submission highlight/source metadata reviewed for Steele and Gugnon.",
    },
    3: {
        "tier": "PASS",
        "status": "PASS",
        "reason": "Reference keeps Oki, but the historical model favors Santos and the OOF-unified winner is effectively 50/50. Oki is also dropping to featherweight after consecutive stoppage losses. No verified input error was found, so the reference side is preserved but the fight is a Stage A pass.",
        "tape": "Continuous playback unavailable. Official preview/athlete history reviewed; a UFC full-fight source for Oki was located but not visually played here.",
    },
    4: {
        "tier": "B",
        "status": "SIDE",
        "reason": "Reference, historical, and OOF-unified all favor Malkoun. Vagaev has only one UFC bout and is moving up to middleweight, while Malkoun brings substantially more UFC evidence. Sparse-opponent uncertainty keeps this below the top tier.",
        "tape": "Continuous playback unavailable. Official UFC preview and athlete/fight-history material reviewed; no continuous fight footage was played here.",
    },
    5: {
        "tier": "PASS",
        "status": "PASS",
        "reason": "All model views favor Thicknesse, but Chopurov is an 11-0 UFC debutant with limited UFC-state data and meaningful regional championship experience. The matchup is explicitly sparse, so the side remains Thicknesse but the betting posture is pass.",
        "tape": "Continuous playback unavailable. Official UFC preview reviewed; a regional UAE Warriors full-fight source for Chopurov was located but not visually played here.",
    },
    6: {
        "tier": "PASS",
        "status": "PASS",
        "reason": "The reference side is Dawson at only about 52.7%, while both historical and OOF-unified lean Aliev. Dawson has far more UFC experience, but Aliev is unbeaten and built around a grinding wrestling game. This is near the research-flip threshold, but no material data omission was verified, so Dawson stays official and the fight is a pass.",
        "tape": "Continuous playback unavailable. Official UFC preview, athlete history, and public fight/stat metadata reviewed.",
    },
    7: {
        "tier": "PASS",
        "status": "PASS",
        "reason": "Reference favors Magomedov, but both historical and OOF-unified favor Rowston. Rowston enters on a seven-fight winning streak with three UFC wins, while Magomedov has the deeper UFC sample. The reference probability is not weak enough to justify a narrative flip, so keep Abus official but pass.",
        "tape": "Continuous playback unavailable. Official UFC preview and public finish/highlight metadata reviewed.",
    },
    8: {
        "tier": "B",
        "status": "SIDE",
        "reason": "All three winner views favor Yakhyaev, with the historical and OOF-unified models especially strong. He is 10-0 and has finished his first three UFC opponents in under four minutes combined, but Krylov is an experienced, dangerous finisher, so the small top-level sample still matters.",
        "tape": "Continuous playback unavailable. Official UFC preview/profile and recent Yakhyaev finish clips/source metadata reviewed; a full-fight source for Krylov was located but not visually played here.",
    },
    9: {
        "tier": "PASS",
        "status": "PASS",
        "reason": "Reference strongly favors Murzakanov, but historical and OOF-unified both favor Reyes. Murzakanov is also coming off his first career loss. Because no material reference-model input error was found, do not flip a 66% reference side; preserve Murzakanov and mark the fight pass because of the severe ensemble disagreement.",
        "tape": "Continuous playback unavailable. Official preview and public full-fight/highlight source metadata reviewed.",
    },
    10: {
        "tier": "C",
        "status": "LEAN",
        "reason": "Reference, historical, and OOF-unified all give Pico a modest edge. Keita is the replacement for Arnold Allen and returns only seven weeks after his most recent fight, while Pico has limited UFC sample. Keep Pico as the lean, not a strong side.",
        "tape": "Continuous playback unavailable. Official UFC preview reviewed; a UFC full-fight source for Pico and recent Keita finish source were located but not visually played here.",
    },
    11: {
        "tier": "C",
        "status": "LEAN",
        "reason": "All three winner views lean Volkov. His much deeper UFC experience is the clearest differentiator, but the probabilities remain modest and Kuniev is a dangerous heavyweight with finishing ability.",
        "tape": "Continuous playback unavailable. Official UFC preview reviewed; Volkov full-fight source was located but playback was unavailable, and Kuniev finish metadata was reviewed.",
    },
    12: {
        "tier": "B",
        "status": "SIDE",
        "reason": "All three winner views favor Kavanagh. His recent five-round experience is valuable, but Temirov has won 12 straight and returned with a first-round stoppage of Steve Erceg, so confidence is capped below elite.",
        "tape": "Continuous playback unavailable. Official UFC preview reviewed; a Kavanagh full-fight source and Temirov finish source were located but not visually played here.",
    },
    13: {
        "tier": "PASS",
        "status": "PASS",
        "reason": "Reference narrowly favors Merab, while historical and OOF-unified lean Yan. Their most recent meeting is directly relevant and already belongs to known pre-UFC-333 history; no missing-data reason was found to overwrite the reference. Keep Merab official, but the trilogy is a clear Stage A pass because the views disagree and the side is weak.",
        "tape": "Continuous playback unavailable. Official UFC trilogy coverage and coach material reviewed; a full-fight source for Yan-Dvalishvili II was located but not visually played here.",
    },
    14: {
        "tier": "C",
        "status": "LEAN",
        "reason": "Reference, historical, and OOF-unified all favor Evloev. His 20-0 record and 10-0 UFC run support the side, but Volkanovski's championship experience and all-around skill keep the winner probability modest. The current method model's KO preference is not trusted because Evloev has no UFC finish; historical and unified method views lean decision instead.",
        "tape": "Continuous playback unavailable. Official UFC fight-by-fight and coach analysis reviewed; full-fight sources for Volkanovski-Lopes I and Evloev-Sterling were located but not visually played here.",
    },
}

# Only methods that clear the conservative side + cross-model method gate.
OFFICIAL_METHOD = {8: "SUB"}


def normalize_method(label: str) -> str:
    return "KO/TKO" if label == "KO" else label


def side_prefix(row: dict, pick: str) -> str:
    return "A" if pick == row["a"] else "B"


def conditional_from_joint(joint: dict, prefix: str) -> dict[str, float]:
    vals = {m: float(joint[f"{prefix}_{m}"]) for m in ("KO", "SUB", "DEC")}
    total = sum(vals.values())
    if total <= 0:
        return {m: 0.0 for m in vals}
    return {m: v / total for m, v in vals.items()}


def top_method(dist: dict[str, float]) -> tuple[str, float]:
    method = max(dist, key=dist.get)
    return method, float(dist[method])


def exact_rounds_from_timing(timing: dict, scheduled_seconds: int) -> dict[str, float]:
    rounds = scheduled_seconds // 300
    starts = {1: 1.0}
    for rnd in range(2, rounds + 1):
        starts[rnd] = float(timing[f"ROUND_{rnd}_STARTS_YES"])
    gtd = float(timing["GTD_YES"])
    out = {}
    for rnd in range(1, rounds):
        nxt = starts[rnd + 1]
        out[f"FINISH_ROUND_{rnd}"] = max(0.0, starts[rnd] - nxt)
    out[f"FINISH_ROUND_{rounds}"] = max(0.0, starts[rounds] - gtd)
    out["GTD"] = gtd
    return out


def selected_double_chance(all_dc: dict, prefix: str) -> dict[str, float]:
    return {
        "KO_OR_SUB": float(all_dc[f"{prefix}_KO_OR_SUB"]),
        "KO_OR_DEC": float(all_dc[f"{prefix}_KO_OR_DEC"]),
        "SUB_OR_DEC": float(all_dc[f"{prefix}_SUB_OR_DEC"]),
    }


def build_fight(row: dict) -> dict:
    n = int(row["fight_no"])
    research = RESEARCH[n]
    pick = str(row["winner_reference_pick"])
    prefix = side_prefix(row, pick)
    p_a = float(row["winner_reference_p_a"])
    p_official = p_a if prefix == "A" else 1.0 - p_a

    current_cond = dict(row[f"method_if_{prefix.lower()}_wins_calibrated"])
    current_cond = {k: float(v) for k, v in current_cond.items()}
    hist_cond = conditional_from_joint(row["historical_shadow"]["joint_method"], prefix)
    unified_cond = conditional_from_joint(row["oof_unified_shadow"]["joint_method"], prefix)
    cur_m, cur_mp = top_method(current_cond)
    hist_m, hist_mp = top_method(hist_cond)
    uni_m, uni_mp = top_method(unified_cond)
    labels_agree = cur_m == hist_m == uni_m
    method_score = (cur_mp + hist_mp + uni_mp) / 3.0 * 10.0 if labels_agree else min(cur_mp, hist_mp, uni_mp) * 10.0

    exact = {
        "KO_TKO": float(row["joint_calibrated"][f"{prefix}_KO"]),
        "SUB": float(row["joint_calibrated"][f"{prefix}_SUB"]),
        "DEC": float(row["joint_calibrated"][f"{prefix}_DEC"]),
    }
    exact_sim = {
        "KO_TKO": float(row["joint_calibrated_sim_10000"][f"{prefix}_KO"]),
        "SUB": float(row["joint_calibrated_sim_10000"][f"{prefix}_SUB"]),
        "DEC": float(row["joint_calibrated_sim_10000"][f"{prefix}_DEC"]),
    }

    hist_p_a = float(row["historical_shadow"]["winner_p_a"])
    unified_p_a = float(row["oof_unified_shadow"]["winner_p_a"])
    method_label = OFFICIAL_METHOD.get(n)
    method_gate = (
        f"OFFICIAL METHOD — {pick} by {method_label}"
        if method_label
        else ("PASS — NO METHOD BET" if research["status"] == "PASS" else "SIDE ONLY — NO METHOD BET")
    )

    timing = {k: float(v) for k, v in row["timing_v033_sim_10000"].items()}
    timing_direct = {k: float(v) for k, v in row["timing_v033_direct"].items()}
    unified_timing = {k: float(v) for k, v in row["oof_unified_shadow"]["timing_sim_10000"].items()}

    return {
        "fight_no": n,
        "a": row["a"],
        "b": row["b"],
        "weight_class": row["weight_class"],
        "scheduled_rounds": int(row["scheduled_seconds"] // 300),
        "official_reference_pick": pick,
        "official_reference_probability": p_official,
        "official_reference_probability_a": p_a,
        "confidence_10_model_raw": float(row["evidence_adjusted_confidence_10"]),
        "confidence_tier_after_research": research["tier"],
        "stage_a_posture": research["status"],
        "research_override": "NONE — reference side preserved",
        "winner_views": {
            "reference": {"pick": pick, "probability": p_official},
            "historical_shadow": {
                "pick": row["historical_shadow"]["winner_pick"],
                "probability": max(hist_p_a, 1.0 - hist_p_a),
            },
            "oof_unified_shadow": {
                "pick": row["oof_unified_shadow"]["winner_pick"],
                "probability": max(unified_p_a, 1.0 - unified_p_a),
            },
        },
        "shadow_disagreement": {
            "historical_vs_reference": bool(row["oof_unified_shadow"]["historical_disagrees_with_reference"]),
            "unified_vs_reference": bool(row["oof_unified_shadow"]["winner_disagrees_with_reference"]),
        },
        "method": {
            "official_gate": method_gate,
            "official_method_if_any": method_label,
            "method_score_10": round(method_score, 3),
            "score_definition": "Cross-model conditional-method concentration; average top-method probability x10 when current/historical/unified agree, otherwise conservative minimum x10.",
            "current_conditional_if_official_winner": current_cond,
            "historical_conditional_if_official_winner": hist_cond,
            "oof_unified_conditional_if_official_winner": unified_cond,
            "top_method_current": normalize_method(cur_m),
            "top_method_historical": normalize_method(hist_m),
            "top_method_unified": normalize_method(uni_m),
            "winner_plus_method_current_direct": exact,
            "winner_plus_method_current_sim_10000": exact_sim,
        },
        "double_chance_current": selected_double_chance(row["double_chance_calibrated"], prefix),
        "timing_current": {
            "direct": timing_direct,
            "sim_10000": timing,
            "exact_finish_round_from_sim_10000": exact_rounds_from_timing(timing, int(row["scheduled_seconds"])),
        },
        "timing_oof_unified_shadow": {
            "sim_10000": unified_timing,
            "exact_finish_round_sim_10000": {
                k: v for k, v in unified_timing.items() if k.startswith("FINISH_ROUND_")
            },
        },
        "evidence_density": row["evidence_density"],
        "sparse_ufc_evidence": bool(row["sparse_ufc_evidence"]),
        "research_reason": research["reason"],
        "tape_provenance": {
            "classification": "UNAVAILABLE_FOR_CONTINUOUS_VISUAL_REVIEW_IN_CURRENT_ENVIRONMENT",
            "note": research["tape"],
            "integrity_rule": "No claim that a full fight was watched unless continuous playback was actually available.",
        },
    }


def main() -> None:
    raw_bytes = RAW_PATH.read_bytes()
    raw = json.loads(raw_bytes)
    fights = [build_fight(r) for r in raw["fights"]]

    payload = {
        "event": "UFC 333: Volkanovski vs Evloev",
        "event_date": "2026-10-24",
        "freeze_type": "PRE_WEIGH_IN_STAGE_A_ODDS_BLIND",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage_a_frozen": True,
        "odds_used": False,
        "weigh_in_context": "Not yet available at this pre-weigh-in freeze; any later material miss/cancellation/injury must be documented as a pre-event audit amendment, never a hindsight rewrite.",
        "raw_model_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "raw_model_path": str(RAW_PATH.relative_to(ROOT)),
        "model_history_through": "2026-10-17",
        "simulation": {
            "current_joint_per_fight": 10000,
            "current_timing_per_fight": 10000,
            "oof_unified_joint_per_fight": 10000,
            "oof_unified_timing_per_fight": 10000,
        },
        "governance": {
            "official_reference_model_unchanged": True,
            "historical_shadow_only": True,
            "oof_unified_shadow_only": True,
            "oof_weights": {"winner_current": 0.30, "method_current": 0.375, "timing_current": 0.75},
            "pr_1_merged": False,
            "challenger_promoted": False,
            "research_side_flips": 0,
            "odds_influenced_stage_a": False,
        },
        "research": {
            "card_identity_verified": True,
            "official_ufc_card_count": 14,
            "tape_limit": "No continuous fight-video playback was available in this environment. Full-fight/clip sources were located where possible and logged honestly as source availability rather than watched tape.",
            "price_fields_policy": "Any sportsbook prices visible on public event pages were ignored and not stored in the finalizer.",
        },
        "fights": fights,
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    audit = {
        "event": payload["event"],
        "event_date": payload["event_date"],
        "stage_a_frozen": True,
        "freeze_type": payload["freeze_type"],
        "odds_used": False,
        "fights": len(fights),
        "side_flips_from_reference": 0,
        "passes": [f["fight_no"] for f in fights if f["stage_a_posture"] == "PASS"],
        "official_methods": [
            {"fight_no": f["fight_no"], "method": f["method"]["official_method_if_any"]}
            for f in fights if f["method"]["official_method_if_any"]
        ],
        "shadow_side_disagreements": [
            f["fight_no"] for f in fights
            if f["shadow_disagreement"]["historical_vs_reference"]
            or f["shadow_disagreement"]["unified_vs_reference"]
        ],
        "raw_model_sha256": payload["raw_model_sha256"],
        "governance": payload["governance"],
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps({
        "status": "STAGE_A_FROZEN_PRE_WEIGH_IN",
        "passes": audit["passes"],
        "official_methods": audit["official_methods"],
        "shadow_side_disagreements": audit["shadow_side_disagreements"],
    }, indent=2))


if __name__ == "__main__":
    main()
