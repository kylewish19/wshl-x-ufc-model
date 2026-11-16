"""Research-only coherent six-state joint forecast projection (never auto-promoted).

The historical winner model is separately trained from its fighter+method
model, and the Unified blend pools winner and method independently. Their
method marginal can disagree with the explicitly selected fighter win P(A).
Here we compare frozen original six-state distributions to two constrained
joint projections without touching ANY archived model, pick or betting rule.

- winner_only: force A/B row margins to model winner P(A)
- winner_and_timing: additionally force fight finish (KO or SUB) vs DEC
  total to the same model's direct discrete-hazard GTD_NO forecast.

This second projection is iterative proportional fitting (I-projection on
the 2x2 A/B x finish/DEC table), preserving within-fighter KO:SUB ratios.
It is a POST-EVENT RESEARCH CHALLENGER, not a trained predictive model.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

JOINT_KEYS = ("A_KO", "A_SUB", "A_DEC", "B_KO", "B_SUB", "B_DEC")
FINISH_KEYS = ("A_KO", "A_SUB", "B_KO", "B_SUB")
DEC_KEYS = ("A_DEC", "B_DEC")
SIDES = {"A": ("A_KO", "A_SUB", "A_DEC"),
         "B": ("B_KO", "B_SUB", "B_DEC")}
METHODS = ("KO", "SUB", "DEC")

ROOT = Path(__file__).resolve().parents[2]
EVENTS = (
    ("ufc333_2026-10-24",
     "data/locks/ufc333_2026-10-24/stage_a_model_raw_three_view.json",
     "data/grades/ufc333_2026-10-24_stage_a_grade.json"),
    ("ufcvegas124_2026-11-07",
     "data/locks/ufcvegas124_2026-11-07/stage_a_model_raw_three_view.json",
     "data/results/ufcvegas124_2026-11-07_all_models_grading.json"),
    ("ufc334_2026-11-14",
     "data/locks/ufc334_2026-11-14/stage_a_model_raw_three_view.json",
     "data/results/ufc334_2026-11-14_all_models_grading.json"),
)
STORED = ROOT / "reports/ufc334_2026-11-14/THREE_EVENT_COHERENT_METHOD_SHADOW_EXPERIMENT.json"


def _sum(d: dict, keys) -> float:
    return sum(d[k] for k in keys)


def project(joint: dict, *, winner_p_a: float, finish_p: float | None = None,
            tolerance: float = 1e-11) -> dict[str, float]:
    """Keep the within-side KO:SUB ratio, while reconciling winner/finish margins.

    All six raw probabilities must be strictly positive (the archived
    probabilities are), ensuring finite IPF convergence without arbitrary
    invented pseudocounts.
    """
    if set(joint) != set(JOINT_KEYS):
        raise ValueError("Joint must contain exactly six fighter+method outcomes")
    q = {k: float(joint[k]) for k in JOINT_KEYS}
    if (any(not math.isfinite(v) or v <= 0 for v in q.values()) or
            abs(sum(q.values()) - 1) > 1e-5):
        raise ValueError("Joint must be strictly positive and sum to one")
    if not math.isfinite(winner_p_a) or not 0 < winner_p_a < 1:
        raise ValueError("Winner P(A) must be strictly between zero and one")
    if finish_p is not None and (
            not math.isfinite(finish_p) or not 0 < finish_p < 1):
        raise ValueError("Finish probability must lie strictly between 0 and 1")

    def normalize_rows():
        for side, target in (("A", winner_p_a), ("B", 1 - winner_p_a)):
            denom = _sum(q, SIDES[side])
            if denom <= 0:
                raise ValueError("Side contains zero mass")
            for key in SIDES[side]:
                q[key] *= target / denom

    normalize_rows()
    if finish_p is not None:
        for _ in range(1000):
            f, d = _sum(q, FINISH_KEYS), _sum(q, DEC_KEYS)
            if f <= 0 or d <= 0:
                raise ValueError("Invalid finish/decision margins")
            for key in FINISH_KEYS:
                q[key] *= finish_p / f
            for key in DEC_KEYS:
                q[key] *= (1 - finish_p) / d
            normalize_rows()
            if (abs(_sum(q, FINISH_KEYS) - finish_p) < tolerance and
                    abs(_sum(q, SIDES["A"]) - winner_p_a) < tolerance):
                break
        else:
            raise RuntimeError("Joint reconciliation failed to converge")
    if abs(sum(q.values()) - 1) > 1e-10:
        raise RuntimeError("Projected six-class mass is not normalized")
    if abs(_sum(q, SIDES["A"]) - winner_p_a) > tolerance:
        raise RuntimeError("Projected winner mass does not match selected winner model")
    if finish_p is not None and abs(_sum(q, FINISH_KEYS) - finish_p) > tolerance:
        raise RuntimeError("Projected method finish probability does not match timing")
    return q


def six_way_scores(joint: dict, *, fighter_side: str, method: str) -> dict:
    if fighter_side not in SIDES or method not in METHODS:
        raise ValueError("Method must be KO/SUB/DEC, draw not represented")
    key = f"{fighter_side}_{method}"
    return {
        "brier": sum((joint[k] - int(k == key)) ** 2 for k in JOINT_KEYS),
        "logloss": -math.log(max(1e-12, joint[key])),
        "p_true": joint[key],
    }


def outcomes_for_event(slug: str, grade: dict) -> dict:
    bouts = grade["bouts"] if slug.startswith("ufc333") else grade["fights"]
    result = {}
    for f in bouts:
        if slug.startswith("ufc333"):
            winner, method = f["actual"]["winner"], f["actual"]["method_class"]
        elif slug.startswith("ufcvegas124"):
            winner, method = f["winner"], f["method"]
        else:
            winner, method = f["actual"]["winner"], f["actual"]["method"]
        n = int(f["fight_no"])
        if n in result or method not in METHODS + ("DRAW",):
            raise ValueError("Duplicate or unknown real result")
        if (method == "DRAW") != (winner is None):
            raise ValueError("Majority draw has no binary winner")
        result[n] = {"winner": winner, "method": method}
    return result


def compute() -> dict:
    scored = {model: {
        "original": [], "winner_aligned": [], "winner_timing_aligned": [],
        "events": {}, "n": 0,
        "picks": {k: {"winner_correct": 0, "exact": 0, "method_counts": {"KO":0,"SUB":0,"DEC":0}}
                  for k in ("original","winner_aligned","winner_timing_aligned")},
        "event_picks": {},
    } for model in ("historical", "unified")}
    for slug, raw_path, grade_path in EVENTS:
        raw = json.loads((ROOT / raw_path).read_text())
        grade = json.loads((ROOT / grade_path).read_text())
        if raw.get("odds_used") is not False or raw.get("stage_a_frozen") is not True:
            raise ValueError("Original event Stage A is not frozen odds-blind")
        if raw["event_date"] != grade["event_date"] or not raw["fights"]:
            raise ValueError("Event identity mismatch")
        results = outcomes_for_event(slug, grade)
        if len(results) != len(raw["fights"]):
            raise ValueError("Missing original fight result")
        for model in scored:
            scored[model]["events"][slug] = {
                "original": [], "winner_aligned": [], "winner_timing_aligned": []
            }
            scored[model]["event_picks"][slug] = {
                k: {"winner_correct": 0, "exact": 0}
                for k in ("original","winner_aligned","winner_timing_aligned")
            }
        for f in raw["fights"]:
            n = f["fight_no"]
            winner = results[n]["winner"]
            method = results[n]["method"]
            if method != "DRAW" and winner not in (f["a"], f["b"]):
                raise ValueError("Actual winner identity differs from locked fighters")
            for model in scored:
                obj = (f["historical_shadow"] if model == "historical" else
                       f["oof_unified_shadow"])
                j = obj["joint_method"]
                a, t = float(obj["winner_p_a"]), float(obj["timing_direct"]["GTD_NO"])
                projections = {
                    "original": j,
                    "winner_aligned": project(j, winner_p_a=a),
                    "winner_timing_aligned": project(j, winner_p_a=a, finish_p=t),
                }
                scored[model]["n"] += 1
                if method == "DRAW":
                    # A six-outcome classification must NOT invent a winner on draws.
                    continue
                actual_side = "A" if winner == f["a"] else "B"
                selected_side = "A" if a >= 0.5 else "B"
                for candidate, joint in projections.items():
                    s = six_way_scores(joint, fighter_side=actual_side, method=method)
                    scored[model][candidate].append(s)
                    scored[model]["events"][slug][candidate].append(s)
                    chosen_method = max(METHODS, key=lambda m: joint[f"{selected_side}_{m}"])
                    pick = scored[model]["picks"][candidate]
                    pick["winner_correct"] += int(selected_side == actual_side)
                    pick["exact"] += int(selected_side == actual_side and chosen_method == method)
                    pick["method_counts"][chosen_method] += 1
                    scored[model]["event_picks"][slug][candidate]["winner_correct"] += int(
                        selected_side == actual_side)
                    scored[model]["event_picks"][slug][candidate]["exact"] += int(
                        selected_side == actual_side and chosen_method == method)

    def means(rows):
        if not rows:
            raise ValueError("No decisive rows")
        return {
            "n": len(rows),
            "mean_brier": sum(r["brier"] for r in rows) / len(rows),
            "mean_logloss": sum(r["logloss"] for r in rows) / len(rows),
        }

    return {
        model: {
            "all": {k: means(value[k]) for k in
                    ("original", "winner_aligned", "winner_timing_aligned")},
            "event": {
                slug: {k: means(values[k]) for k in
                       ("original", "winner_aligned", "winner_timing_aligned")}
                for slug, values in value["events"].items()},
            "fight_count": value["n"],
            "retrospective_exact_winner_method": value["picks"],
            "event_retrospective_exact": value["event_picks"],
        }
        for model, value in scored.items()
    }


def check_stored_experiment() -> dict:
    fresh = compute()
    stored = json.loads(STORED.read_text())
    assert stored["status"] == "POST_EVENT_CHALLENGER_NOT_PROMOTED"
    for model in ("historical", "unified"):
        assert fresh[model]["fight_count"] == 41
        for scope, data in (("all", fresh[model]["all"]),):
            for candidate, scores in data.items():
                for key in ("n", "mean_brier", "mean_logloss"):
                    if abs(scores[key] - stored["summary"][model][scope][candidate][key]) > 1e-10:
                        raise RuntimeError(
                            f"Stored research drift: {model}/{candidate}/{key}")
        for event, choices in fresh[model]["event"].items():
            for variant, scores in choices.items():
                for key in ("n", "mean_brier", "mean_logloss"):
                    original = stored["summary"][model]["event"][event][variant][key]
                    if abs(scores[key] - original) > 1e-10:
                        raise RuntimeError(f"Stored event research drift: {event}/{model}/{variant}/{key}")
    return fresh


if __name__ == "__main__":
    print(json.dumps(check_stored_experiment(), indent=2))
