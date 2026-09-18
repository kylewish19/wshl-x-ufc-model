from __future__ import annotations

from collections import Counter
from typing import Mapping

import numpy as np


JOINT_KEYS = ("A_KO", "A_SUB", "A_DEC", "B_KO", "B_SUB", "B_DEC")


def simulate_joint_outcomes(
    joint: Mapping[str, float],
    *,
    trials: int = 10_000,
    seed: int = 19,
) -> dict[str, float]:
    """Seeded Monte Carlo over the six coherent winner+method outcomes."""
    if trials <= 0:
        raise ValueError("trials must be positive.")

    probs = np.asarray([joint[k] for k in JOINT_KEYS], dtype=float)
    if np.any(probs < 0):
        raise ValueError("Probabilities cannot be negative.")
    if not np.isclose(probs.sum(), 1.0, atol=1e-9):
        raise ValueError("Joint probabilities must sum to 1.")

    rng = np.random.default_rng(seed)
    draws = rng.choice(len(JOINT_KEYS), size=trials, p=probs)
    counts = Counter(JOINT_KEYS[i] for i in draws)
    return {k: counts.get(k, 0) / trials for k in JOINT_KEYS}
