"""Probability coherence tools for OFFICIAL locked UFC market research.

Separate conditional-method and survival/hazard models can make
mathematically incompatible probability statements (e.g. P(fighter wins KO)
larger than P(fight finishes)). This shadow adjustment preserves the
frozen winner marginal, the hazard finish marginal, and conditional KO:SUB
proportions among finishes. It does NOT validate either estimator or
automatically authorize bets.

No outcomes, sportsbook prices or look-ahead inputs are used.
"""
from __future__ import annotations

from typing import Mapping

import numpy as np

JOINT_KEYS = ("A_KO", "A_SUB", "A_DEC", "B_KO", "B_SUB", "B_DEC")


def finish_probability(joint: Mapping[str, float]) -> float:
    return float(sum(float(joint[k]) for k in ("A_KO", "A_SUB", "B_KO", "B_SUB")))


def _validate(joint: Mapping[str, float], target_finish: float) -> np.ndarray:
    if set(joint) != set(JOINT_KEYS):
        raise ValueError("Joint must have exactly six fighter×method outcomes")
    values = np.array([float(joint[k]) for k in JOINT_KEYS], dtype=float)
    if not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("Joint probabilities must be finite and non-negative")
    if not np.isclose(values.sum(), 1, atol=1e-8):
        raise ValueError("Joint probabilities must sum to one")
    if not np.isfinite(target_finish) or not 0 <= target_finish <= 1:
        raise ValueError("GTD_NO must be a finite probability")
    return values


def reconcile_joint_with_finish_marginal(
    joint: Mapping[str, float],
    target_finish: float,
    *,
    tolerance: float = 1e-12,
    max_iterations: int = 5000,
) -> dict[str, float]:
    """IPF on (fighter, finish-or-decision), preserving original KO:SUB mix.

    This is a proposal for market COHERENCE diagnostics, not a model promotion.
    With strictly positive 2x2 source cell masses, the prescribed row/column
    marginals are jointly feasible (including boundary marginal values).
    """
    p = _validate(joint, target_finish)
    pa = float(p[:3].sum())
    rows = np.array([pa, 1.0 - pa], dtype=float)
    cols = np.array([target_finish, 1.0 - target_finish], dtype=float)
    finish_a = p[0] + p[1]
    finish_b = p[3] + p[4]
    raw = np.array([[finish_a, p[2]], [finish_b, p[5]]], dtype=float)

    # Positive smoothing handles structural source zeros; it is a shadow only.
    table = np.maximum(raw, 1e-14)
    for _ in range(max_iterations):
        table *= np.divide(rows, table.sum(axis=1),
                           out=np.zeros_like(rows), where=table.sum(axis=1) > 0)[:, None]
        table *= np.divide(cols, table.sum(axis=0),
                           out=np.zeros_like(cols), where=table.sum(axis=0) > 0)[None, :]
        err = max(
            float(np.max(np.abs(table.sum(axis=1) - rows))),
            float(np.max(np.abs(table.sum(axis=0) - cols))),
        )
        if err <= tolerance:
            break
    else:
        raise RuntimeError("Joint/finish IPF did not converge")

    ko_a = float(p[0] / finish_a) if finish_a > 0 else 0.5
    ko_b = float(p[3] / finish_b) if finish_b > 0 else 0.5
    out = np.array([
        table[0, 0] * ko_a, table[0, 0] * (1 - ko_a), table[0, 1],
        table[1, 0] * ko_b, table[1, 0] * (1 - ko_b), table[1, 1],
    ])
    assert abs(float(out.sum()) - 1) <= tolerance * 10
    assert abs(float(out[:3].sum()) - pa) <= tolerance * 10
    assert abs(float(out[[0, 1, 3, 4]].sum()) - target_finish) <= tolerance * 10
    return {k: float(v) for k, v in zip(JOINT_KEYS, out)}
