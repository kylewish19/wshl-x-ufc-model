from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class MulticlassGrade:
    accuracy: float
    brier: float
    logloss: float
    class_recall: dict[str, float]


def multiclass_brier(
    y_true: Sequence[str],
    probabilities: np.ndarray,
    classes: Sequence[str],
) -> float:
    class_to_i = {c: i for i, c in enumerate(classes)}
    one_hot = np.zeros_like(probabilities, dtype=float)
    for row, label in enumerate(y_true):
        one_hot[row, class_to_i[label]] = 1.0
    return float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1)))


def grade_multiclass(
    y_true: Sequence[str],
    probabilities: np.ndarray,
    classes: Sequence[str],
) -> MulticlassGrade:
    y = np.asarray(y_true, dtype=str)
    p = np.asarray(probabilities, dtype=float)

    if not len(y) or len(set(classes)) != len(classes) or not set(y).issubset(classes):
        raise ValueError("Expected nonempty labels and unique matching classes.")
    if p.shape != (len(y), len(classes)):
        raise ValueError("Probability matrix shape does not match labels/classes.")
    if not np.isfinite(p).all() or np.any(p < 0) or np.any(p > 1) or not np.allclose(p.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("Each probability row must be nonnegative and sum to 1.")

    pred = np.asarray(classes)[np.argmax(p, axis=1)]
    recalls: dict[str, float] = {}
    for c in classes:
        mask = y == c
        recalls[c] = float(np.mean(pred[mask] == c)) if mask.any() else float("nan")

    # Column order is the caller-provided class order, NOT alphabetical.
    # Match true labels explicitly; retain float64 epsilon clipping at zero.
    class_to_i = {c: i for i, c in enumerate(classes)}
    indices = np.array([class_to_i[label] for label in y], dtype=int)
    true_p = p[np.arange(len(y)), indices]
    nll = -np.mean(np.log(np.clip(true_p, np.finfo(float).eps, 1.0)))
    return MulticlassGrade(
        accuracy=float(np.mean(pred == y)),
        brier=multiclass_brier(y, p, classes),
        logloss=float(nll),
        class_recall=recalls,
    )


def binary_brier(y_true: Iterable[int], p_positive: Iterable[float]) -> float:
    y = np.asarray(list(y_true), dtype=float)
    p = np.asarray(list(p_positive), dtype=float)
    if y.shape != p.shape:
        raise ValueError("Binary labels and probabilities must have matching shapes.")
    return float(np.mean((p - y) ** 2))
