"""Transparent research baselines; NO model fitting, wagering or promotion.

Scores simple pre-event 2026 predictions against retrospective 2026 results.
This is NOT an unseen test era: previous WSHL_X research inspected 2026.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import math
import random

METHODS = ("KO_TKO", "SUB", "DEC")
BASELINES = ("coinflip", "prior_ufc_win_rate", "past_only_ufc_elo")
EPS = 1e-12


def _p(x: float) -> float:
    return min(1 - EPS, max(EPS, float(x)))


def _validate_join(features: list[dict], labels: list[dict]) -> list[tuple[dict, dict]]:
    lookup = {}
    for label in labels:
        key = label["bout_id"]
        if key in lookup:
            raise ValueError("Duplicate label ID")
        lookup[key] = label
    seen = set()
    joined = []
    for feature in features:
        key = feature["bout_id"]
        if key in seen or key not in lookup:
            raise ValueError("Feature/label mismatch")
        seen.add(key)
        label = lookup[key]
        if feature["event_date"] != label["event_date"]:
            raise ValueError("Feature/target time mismatch")
        if feature["feature_as_of_exclusive"] != feature["event_date"]:
            raise ValueError("Feature cutoff must be current event day EXCLUSIVE")
        joined.append((feature, label))
    if seen != set(lookup):
        raise ValueError("Label without source feature row")
    return joined


def _winner_probabilities(feature: dict) -> dict[str, float]:
    a, b = float(feature["a_ufc_elo_pre"]), float(feature["b_ufc_elo_pre"])
    elo_p = 1 / (1 + 10 ** ((b - a) / 400))
    def win_rate(side: str) -> float:
        n = float(feature[side + "_ufc_prior_bouts"])
        w = float(feature[side + "_ufc_prior_wins"])
        if not (0 <= w <= n):
            raise ValueError("Invalid historical wins / bouts")
        return (w + 2) / (n + 4)
    a_rate, b_rate = win_rate("a"), win_rate("b")
    return {
        "coinflip": 0.5,
        "prior_ufc_win_rate": _p(a_rate / (a_rate + b_rate)),
        "past_only_ufc_elo": _p(elo_p),
    }


def _summary(observations: list[dict]) -> dict:
    if not observations:
        raise ValueError("No decisive evaluation bouts")
    n = len(observations)
    return {
        "fights": n,
        "events": len({(o["date"], o["event"]) for o in observations}),
        "winner_accuracy": sum(o["winner_correct"] for o in observations) / n,
        "winner_brier": sum(o["winner_brier"] for o in observations) / n,
        "winner_log_loss": sum(o["winner_log_loss"] for o in observations) / n,
        "six_class_exact_accuracy": sum(o["six_correct"] for o in observations) / n,
        "six_class_brier": sum(o["six_brier"] for o in observations) / n,
        "six_class_log_loss": sum(o["six_log_loss"] for o in observations) / n,
    }


def benchmark_fixed_baselines(features: list[dict], labels: list[dict], *, seed: int = 19, bootstrap_samples: int = 1000) -> dict:
    joined = _validate_join(features, labels)
    train = [(f, l) for f, l in joined if f["data_partition"] == "training_2021_2025" and l["result_status"] == "DECISIVE"]
    test = [(f, l) for f, l in joined if f["data_partition"] == "retrospective_2026" and l["result_status"] == "DECISIVE"]
    if not train or not test:
        raise ValueError("Both training-period labels and later retrospective events required")
    method_counts = Counter(l["label_method"] for _, l in train)
    if set(method_counts) - set(METHODS):
        raise ValueError("Unexpected method class")
    # Uniform Dirichlet smoothing. Method prior comes only from 2021-25.
    denom = len(train) + len(METHODS)
    method_prior = {m: (method_counts[m] + 1) / denom for m in METHODS}
    most_common_method = max(METHODS, key=lambda m: (method_counts[m], -METHODS.index(m)))
    observations = {name: [] for name in BASELINES}
    for f, l in test:
        y = int(l["label_a_win"])
        m = l["label_method"]
        if m not in METHODS or y not in (0, 1):
            raise ValueError("Invalid retrospective target")
        for name, p_a in _winner_probabilities(f).items():
            six = {(side, met): (p_a if side == 1 else 1 - p_a) * method_prior[met]
                   for side in (1, 0) for met in METHODS}
            best = max(six, key=six.get)
            observations[name].append({
                "date": f["event_date"], "event": f["event"],
                "winner_correct": int((p_a >= 0.5) == bool(y)),
                "winner_brier": (p_a - y) ** 2,
                "winner_log_loss": -math.log(_p(p_a if y == 1 else 1 - p_a)),
                "six_correct": int(best == (y, m)),
                "six_brier": sum((p - int(key == (y, m))) ** 2 for key, p in six.items()),
                "six_log_loss": -math.log(_p(six[(y, m)])),
            })
    scores = {name: _summary(steps) for name, steps in observations.items()}
    # Cluster by event, never treat correlated bouts within a card as independent.
    grouped = defaultdict(list)
    for name in BASELINES:
        for obj in observations[name]:
            grouped[(name, obj["date"], obj["event"])].append(obj)
    events = sorted({(x["date"], x["event"]) for x in observations["coinflip"]})
    rng = random.Random(seed)
    differences = []
    for _ in range(bootstrap_samples):
        sample = [events[rng.randrange(len(events))] for _ in events]
        elo_vals = [r["winner_brier"] for d, e in sample for r in grouped[("past_only_ufc_elo", d, e)]]
        coin_vals = [r["winner_brier"] for d, e in sample for r in grouped[("coinflip", d, e)]]
        differences.append(sum(elo_vals) / len(elo_vals) - sum(coin_vals) / len(coin_vals))
    differences.sort()
    lo = differences[int(0.025 * (len(differences) - 1))]
    hi = differences[int(0.975 * (len(differences) - 1))]
    return {
        "schema": "WSHLX_FIXED_HISTORICAL_BENCHMARK_V1",
        "label_training_period": "2021-01-01 through 2025-12-31",
        "evaluation_period": "2026-01-01 through 2026-11-13",
        "evaluation_classification": "RESEARCH_RETROSPECTIVE_ALREADY_INSPECTED_NOT_UNSEEN",
        "training_decisive_bouts": len(train),
        "test_decisive_bouts": len(test),
        "training_method_counts": dict(method_counts),
        "training_only_smoothed_method_prior": method_prior,
        "training_plurality_method": most_common_method,
        "fixed_plurality_method_class_accuracy_on_2026": sum(l["label_method"] == most_common_method for _, l in test) / len(test),
        "baseline_scores": scores,
        "paired_event_bootstrap_elo_minus_coinflip_winner_brier_95pct": [lo, hi],
        "bootstrap_seed": seed,
        "bootstrap_events": len(events),
        "no_challenger_trained": True,
        "current_reference_not_replayed_on_matching_2026_bouts": True,
        "six_class_order": [f"{side}_{m}" for side in ("a", "b") for m in METHODS],
        "no_model_promotion": True,
    }
