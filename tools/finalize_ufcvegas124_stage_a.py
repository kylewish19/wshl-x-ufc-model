from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_DIR = ROOT / "data/locks/ufcvegas124_2026-11-07"
RAW_PATH = LOCK_DIR / "stage_a_model_raw_three_view.json"
OUT_PATH = LOCK_DIR / "stage_a_final_selection.json"
AUDIT_PATH = LOCK_DIR / "stage_a_final_audit.json"

# Research decisions are deliberately separate from the model-raw artifact.
# No sportsbook prices are stored or used here.
RESEARCH = {
    1: {"tier": "PASS", "status": "PASS", "reason": "Parsons has just one UFC bout and has not fought in the UFC for more than three years; Souza is a 9-1 Brazilian prospect with exceptionally limited UFC-specific history. Three model winner views align on Parsons, but severe inactivity and uncertain prospect transfer outweigh the point estimate.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    2: {"tier": "B", "status": "SIDE", "reason": "All three models select Ko. He has UFC wrestling/control evidence and faces Turman returning from a near-three-year Octagon absence; the recent Ko loss and uncertainty about Turman's form after the layoff prevent an A tier. Style issue: control acquisition vs Turman's reactive submissions.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    3: {"tier": "C", "status": "LEAN", "reason": "All three models strongly prefer Kondratavicius, but he has only one UFC fight, where he had conditioning questions; Petroski brings 13 UFC bouts and a grappling route despite a three-fight losing skid. Treat 78% as potentially overconfident because of one-bout prospect data.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    4: {"tier": "PASS", "status": "PASS", "reason": "Bashi has three UFC bouts, while Calderon is a 0-UFC-fight Fury FC featherweight champion replacing injured Brennan on four days notice. UFC history alone cannot reflect Calderon's regional five-round championship experience. All views favor Bashi, but the opponent's tiny-sample uncertainty triggers pass.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    5: {"tier": "PASS", "status": "PASS", "reason": "All views prefer Magomedov, whose first UFC bout ended by a rare Scottish-twister submission; Delano also has only one UFC fight and beat experienced Robert Ruchala by decision. His submission probability is a research signal, not a promoted exact-method wager: the historic SUB-vs-KO recall and sample size are weak.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    6: {"tier": "C", "status": "LEAN", "reason": "All three views favor Karine Silva by a small 57% edge, but Gabriella Fernandes enters with several wins including a technical submission of Wang Cong, while Silva has lost three of four. Small edge and opponent's grappling means cautious lean; no method promotion.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    7: {"tier": "PASS", "status": "PASS", "reason": "Reference narrowly selects UFC debutant Lorenco on limited regional/DWCS finishing data, but historical and unified models favor Petersen, who has seven UFC bouts. This is the biggest style/sample-transfer disagreement and is heavyweight high variance. Preserve the reference pick for post-event calibration, mark pass.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    8: {"tier": "PASS", "status": "PASS", "reason": "Nakamura won Road to UFC by a late TKO and Schmid returned for his second UFC fight after his May short-notice debut. All views lean Nakamura, but both have only one official UFC bout in the current history; do not promote a method or timing bet on that evidence.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    9: {"tier": "PASS", "status": "PASS", "reason": "Raposo won his last two on the scorecards; Degli enters his UFC debut after a 13-fight win streak and DWCS submission. History-limited prospect transfer especially risks misclassifying a counter-grappling submission path. All models lean Raposo, but opponent sample zero so pass.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    10: {"tier": "C", "status": "LEAN", "reason": "Nina Milosevic is the strong three-view winner side after a striking/KO UFC debut and nine-fight streak; Cachoeira has veteran power but has lost three straight. The raw 85.7% is NOT a reliable lock because Milosevic has one UFC bout, so cap confidence at a speculative C lean and keep out of safe anchors.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    11: {"tier": "PASS", "status": "PASS", "reason": "All three views select Lucas Fernando but reference is only 52.4%. Elekana has three consecutive UFC wins including a submission of Junior Tafa, while Fernando won his UFC debut by third-round TKO. Competing finishing routes, limited Fernando sample, and low margin make pass.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    12: {"tier": "C", "status": "LEAN", "reason": "All three models prefer Smith, but their strength differs sharply: reference ~59.5%, historical ~83.2%, unified ~77.5%. Grant is 40 with extensive UFC experience and has won three of his last four; Smith is 24 on an eight-fight streak with three UFC wins. Age/experience gap supports the side but magnitude disagreement requires a C lean.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    13: {"tier": "A-", "status": "SIDE", "reason": "All three model views agree on Suarez against Jandiroba and both have substantial UFC evidence. Suarez has a recent RNC of Godinez, but Jandiroba is a proven submission grappler who rebounded against Ricci. Strongest relatively well-supported odds-blind side; do not treat grappler-vs-grappler as an automatic SUB, and leave exact method unpromoted.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
    14: {"tier": "PASS", "status": "PASS", "reason": "Official reference selects Cortes Acosta at 63.8% while both historical (Walker 66.5%) and unified (Walker 57.7%) choose Walker. He moved to heavyweight only last month and KO'd Mick Parkin; Cortes Acosta lost two recent decisions against Volkov and Blaydes. This is a five-round short-notice heavyweight matchup with serious distribution shift. Preserve raw reference, pass pending better data.", "tape": "UFC official preview and public result/stat summaries read. Continuous full-fight footage was NOT played in this environment; no tape-complete claim."},
}

# Only methods that clear the conservative side + cross-model method gate.
OFFICIAL_METHOD = {}  # zero official method props: repeated weak SUB/KO calibration, no price validation


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
    # Freeze governance: no method wagers when method calibration is unreliable.
    # Historical-conditional and OOF-unified outputs remain SHADOWS, with
    # fixed historical model fitted through October 17 (NOT October 31).
    # All 14 reference winner picks must remain stable after the pre-price lock.
    if len(fights) != 14: raise RuntimeError("Expected the full 14-bout UFC Vegas 124 card")
    if any(f["method"]["official_method_if_any"] for f in fights): raise RuntimeError("No official method promotions passed")

    payload = {
        "event": "UFC Fight Night: Cortes Acosta vs Walker",
        "event_date": "2026-11-07",
        "freeze_type": "STAGE_A_ODDS_BLIND_WEIGH_IN_VERIFICATION_PENDING",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage_a_frozen": True,
        "odds_used": False,
        "weigh_in_context": "Official weigh-ins started November 6; complete athlete scale readings were not independently verified at this freeze. Verify final weights and any late changes before FanDuel Stage B. Never rewrite frozen pre-price probabilities.",
        "raw_model_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "raw_model_path": str(RAW_PATH.relative_to(ROOT)),
        "model_history_through": "2026-10-31",
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
            "material_late_change_audited": "Calderon for injured Brennan; short-notice heavyweight headliner",
            "model_reference_weights_fit_through": "2026-09-12",
            "current_retrained_shadows_fit_through": "2026-10-31",
            "odds_influenced_stage_a": False,
        },
        "research": {
            "card_identity_verified": True,
            "card_source": "https://www.ufc.com/event/ufc-fight-night-november-07-2026",
            "official_preview": "https://www.ufc.com/news/fight-by-fight-preview-ufc-fight-night-cortes-acosta-vs-walker",
            "official_changes": "https://www.ufc.com/news/updates-ufc-fight-night-cortes-acosta-vs-walker",
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
        "ref_frozen_vs_historical_not_retrained": True,
        "source_fighter_features_through": "2026-10-31",
        "historical_artifact_fitted_through": "2026-10-17",
        "method_official_gate_policy": "NO EXACT METHOD OFFICIAL; keep descriptive class and props candidate only",
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
        "status": "STAGE_A_FROZEN_PENDING_WEIGHT_VERIFICATION",
        "passes": audit["passes"],
        "official_methods": audit["official_methods"],
        "shadow_side_disagreements": audit["shadow_side_disagreements"],
    }, indent=2))


if __name__ == "__main__":
    main()
