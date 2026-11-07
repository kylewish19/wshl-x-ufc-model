"""Probability calibration utilities for the historical UFC winner challenger.

The first calibration policy is deliberately conservative: positive temperature
scaling on model logits.  A positive temperature is a monotonic transform, so it
preserves ordering, ROC-AUC, and the 0.50 decision boundary while allowing confidence
to contract or expand.  The temperature is selected on chronological validation data
only; the untouched test period is scored afterward.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score


def _as_probabilities(values: Iterable[float]) -> np.ndarray:
    return np.clip(np.asarray(list(values), dtype=float), 1e-6, 1.0 - 1e-6)


def logit(values: Iterable[float]) -> np.ndarray:
    p = _as_probabilities(values)
    return np.log(p / (1.0 - p))


def sigmoid(values: Iterable[float]) -> np.ndarray:
    z = np.clip(np.asarray(list(values), dtype=float), -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-z))


@dataclass(frozen=True)
class TemperatureCalibrator:
    """Symmetric monotonic logit-temperature calibrator."""

    temperature: float = 1.0

    def transform(self, probabilities: Iterable[float]) -> np.ndarray:
        if not np.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError("temperature must be finite and > 0")
        return sigmoid(logit(probabilities) / self.temperature)


def calibration_metrics(y: Iterable[float], p: Iterable[float]) -> dict[str, float]:
    yy = np.asarray(list(y), dtype=int)
    pp = _as_probabilities(p)
    metrics = {
        "log_loss": float(log_loss(yy, pp, labels=[0, 1])),
        "brier": float(brier_score_loss(yy, pp)),
    }
    metrics["roc_auc"] = float(roc_auc_score(yy, pp)) if len(np.unique(yy)) == 2 else np.nan
    return metrics


def fit_temperature_calibrator(
    y: Iterable[float],
    probabilities: Iterable[float],
    *,
    temperatures: Iterable[float] | None = None,
) -> tuple[TemperatureCalibrator, dict[str, float]]:
    """Choose temperature by validation log loss only.

    The default grid is dense around 1.0 and extends far enough to correct substantial
    overconfidence.  Because every candidate temperature is positive, discrimination
    and the 0.50 winner pick are mathematically preserved.
    """
    yy = np.asarray(list(y), dtype=int)
    pp = _as_probabilities(probabilities)
    if len(yy) != len(pp):
        raise ValueError("y and probabilities must have the same length")
    if len(yy) == 0:
        raise ValueError("calibration requires at least one row")

    if temperatures is None:
        temperatures = np.unique(
            np.concatenate(
                [
                    np.linspace(0.50, 1.00, 26),
                    np.linspace(1.00, 2.00, 81),
                    np.linspace(2.00, 5.00, 61),
                ]
            )
        )

    raw = calibration_metrics(yy, pp)
    best_t = 1.0
    best_loss = raw["log_loss"]
    best_brier = raw["brier"]

    for value in temperatures:
        t = float(value)
        if not np.isfinite(t) or t <= 0:
            continue
        calibrated = TemperatureCalibrator(t).transform(pp)
        loss = float(log_loss(yy, calibrated, labels=[0, 1]))
        brier = float(brier_score_loss(yy, calibrated))
        if (loss < best_loss - 1e-12) or (
            abs(loss - best_loss) <= 1e-12 and brier < best_brier
        ):
            best_t = t
            best_loss = loss
            best_brier = brier

    calibrator = TemperatureCalibrator(best_t)
    calibrated = calibration_metrics(yy, calibrator.transform(pp))
    report = {
        "temperature": float(best_t),
        "raw_log_loss": raw["log_loss"],
        "calibrated_log_loss": calibrated["log_loss"],
        "raw_brier": raw["brier"],
        "calibrated_brier": calibrated["brier"],
        "raw_roc_auc": raw["roc_auc"],
        "calibrated_roc_auc": calibrated["roc_auc"],
    }
    return calibrator, report
