"""Context-aware low-capacity pooling for the WSHL-X unified shadow model.

These helpers learn a *row-specific* current-vs-historical weight from prefight
context while preserving the same coherent log-pooling used by the global unified
ensemble.  They are deliberately regularized and intended for shadow/diagnostic use
until prospective evidence supports promotion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.metrics import log_loss

from .unified_ensemble import EPS, fit_binary_blend, fit_grouped_binary_blend, fit_multiclass_blend


def _clip(p):
    return np.clip(np.asarray(p, dtype=float), EPS, 1.0 - EPS)


def _logit(p):
    q = _clip(p)
    return np.log(q / (1.0 - q))


def _sigmoid(z):
    z = np.clip(np.asarray(z, dtype=float), -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


def rowwise_binary_logit_pool(current, historical, weight_current) -> np.ndarray:
    """Binary logit pool with one current-model weight per row."""
    pc = _clip(current)
    ph = _clip(historical)
    w = np.asarray(weight_current, dtype=float)
    if not (pc.shape == ph.shape == w.shape):
        raise ValueError("current/historical/weight_current must have matching shapes")
    if np.any((w < 0.0) | (w > 1.0)):
        raise ValueError("weight_current must be in [0, 1]")
    return _sigmoid(w * _logit(pc) + (1.0 - w) * _logit(ph))


def rowwise_multiclass_log_pool(current, historical, weight_current) -> np.ndarray:
    """Multiclass geometric pool with one current-model weight per row."""
    pc = np.clip(np.asarray(current, dtype=float), EPS, 1.0)
    ph = np.clip(np.asarray(historical, dtype=float), EPS, 1.0)
    w = np.asarray(weight_current, dtype=float)
    if pc.shape != ph.shape or pc.ndim != 2 or len(w) != pc.shape[0]:
        raise ValueError("multiclass arrays must align row-wise with weight_current")
    if np.any((w < 0.0) | (w > 1.0)):
        raise ValueError("weight_current must be in [0, 1]")
    pc = pc / pc.sum(axis=1, keepdims=True)
    ph = ph / ph.sum(axis=1, keepdims=True)
    logp = w[:, None] * np.log(pc) + (1.0 - w[:, None]) * np.log(ph)
    logp -= logp.max(axis=1, keepdims=True)
    out = np.exp(logp)
    return out / out.sum(axis=1, keepdims=True)


def _prepare_features(
    frame: pd.DataFrame,
    feature_names: Sequence[str],
    medians: np.ndarray | None = None,
    scales: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not feature_names:
        raise ValueError("At least one context feature is required")
    x = frame.loc[:, list(feature_names)].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if medians is None:
        medians = np.nanmedian(x, axis=0)
        medians = np.where(np.isfinite(medians), medians, 0.0)
    x = np.where(np.isfinite(x), x, medians[None, :])
    if scales is None:
        scales = np.nanstd(x, axis=0)
        scales = np.where(np.isfinite(scales) & (scales > 1e-8), scales, 1.0)
    z = (x - medians[None, :]) / scales[None, :]
    return z, np.asarray(medians, dtype=float), np.asarray(scales, dtype=float)


@dataclass(frozen=True)
class ContextualBlendFit:
    feature_names: tuple[str, ...]
    medians: tuple[float, ...]
    scales: tuple[float, ...]
    intercept: float
    coefficients: tuple[float, ...]
    prior_weight_current: float
    l2: float
    intercept_l2: float
    n: int
    objective: float
    optimizer_success: bool
    optimizer_message: str

    def weights(self, frame: pd.DataFrame) -> np.ndarray:
        z, _, _ = _prepare_features(
            frame,
            self.feature_names,
            np.asarray(self.medians, dtype=float),
            np.asarray(self.scales, dtype=float),
        )
        eta = float(self.intercept) + z @ np.asarray(self.coefficients, dtype=float)
        return _sigmoid(eta)

    def to_dict(self) -> dict:
        out = asdict(self)
        out["mean_abs_coefficient"] = float(np.mean(np.abs(self.coefficients))) if self.coefficients else 0.0
        return out


def _prior_logit(weight: float) -> float:
    return float(_logit(np.asarray([np.clip(float(weight), 0.025, 0.975)]))[0])


def _fit_gate(
    frame: pd.DataFrame,
    feature_names: Sequence[str],
    loss_fn,
    *,
    prior_weight_current: float,
    l2: float = 5.0,
    intercept_l2: float = 1.0,
) -> ContextualBlendFit:
    z, medians, scales = _prepare_features(frame, feature_names)
    prior_eta = _prior_logit(prior_weight_current)
    x0 = np.zeros(z.shape[1] + 1, dtype=float)
    x0[0] = prior_eta

    def objective(theta: np.ndarray) -> float:
        eta = theta[0] + z @ theta[1:]
        w = _sigmoid(eta)
        predictive = float(loss_fn(w))
        slope_penalty = float(l2) * float(np.mean(theta[1:] ** 2)) if len(theta) > 1 else 0.0
        intercept_penalty = float(intercept_l2) * float((theta[0] - prior_eta) ** 2)
        return predictive + slope_penalty + intercept_penalty

    result = minimize(
        objective,
        x0,
        method="L-BFGS-B",
        bounds=[(-6.0, 6.0)] + [(-2.5, 2.5)] * z.shape[1],
        options={"maxiter": 2000, "ftol": 1e-12},
    )
    theta = np.asarray(result.x, dtype=float)
    return ContextualBlendFit(
        feature_names=tuple(str(x) for x in feature_names),
        medians=tuple(float(x) for x in medians),
        scales=tuple(float(x) for x in scales),
        intercept=float(theta[0]),
        coefficients=tuple(float(x) for x in theta[1:]),
        prior_weight_current=float(prior_weight_current),
        l2=float(l2),
        intercept_l2=float(intercept_l2),
        n=int(len(frame)),
        objective=float(result.fun),
        optimizer_success=bool(result.success),
        optimizer_message=str(result.message),
    )


def fit_contextual_binary_blend(
    frame: pd.DataFrame,
    y,
    current,
    historical,
    feature_names: Sequence[str],
    *,
    prior_weight_current: float | None = None,
    l2: float = 5.0,
    intercept_l2: float = 1.0,
) -> ContextualBlendFit:
    yy = np.asarray(y, dtype=int)
    pc = _clip(current)
    ph = _clip(historical)
    if len(frame) == 0 or not (len(frame) == len(yy) == len(pc) == len(ph)):
        raise ValueError("binary inputs must be non-empty and row-aligned")
    if prior_weight_current is None:
        prior_weight_current = fit_binary_blend(yy, pc, ph).weight_current

    def loss_fn(w):
        p = rowwise_binary_logit_pool(pc, ph, w)
        return log_loss(yy, p, labels=[0, 1])

    return _fit_gate(
        frame,
        feature_names,
        loss_fn,
        prior_weight_current=float(prior_weight_current),
        l2=l2,
        intercept_l2=intercept_l2,
    )


def fit_contextual_multiclass_blend(
    frame: pd.DataFrame,
    y,
    current: np.ndarray,
    historical: np.ndarray,
    feature_names: Sequence[str],
    *,
    prior_weight_current: float | None = None,
    l2: float = 5.0,
    intercept_l2: float = 1.0,
) -> ContextualBlendFit:
    yy = np.asarray(y, dtype=int)
    pc = np.asarray(current, dtype=float)
    ph = np.asarray(historical, dtype=float)
    if len(frame) == 0 or pc.shape != ph.shape or pc.shape[0] != len(yy) or len(frame) != len(yy):
        raise ValueError("multiclass inputs must be non-empty and row-aligned")
    labels = list(range(pc.shape[1]))
    if prior_weight_current is None:
        prior_weight_current = fit_multiclass_blend(yy, pc, ph).weight_current

    def loss_fn(w):
        p = rowwise_multiclass_log_pool(pc, ph, w)
        return log_loss(yy, p, labels=labels)

    return _fit_gate(
        frame,
        feature_names,
        loss_fn,
        prior_weight_current=float(prior_weight_current),
        l2=l2,
        intercept_l2=intercept_l2,
    )


def grouped_binary_log_loss(y, p, groups) -> float:
    yy = np.asarray(y, dtype=int)
    pp = _clip(p)
    gg = np.asarray(groups)
    if len(yy) == 0 or not (len(yy) == len(pp) == len(gg)):
        raise ValueError("grouped inputs must be non-empty and aligned")
    losses = -(yy * np.log(pp) + (1 - yy) * np.log(1 - pp))
    unique = list(dict.fromkeys(gg.tolist()))
    return float(np.mean([losses[gg == g].mean() for g in unique]))


def fit_contextual_grouped_binary_blend(
    frame: pd.DataFrame,
    y,
    current,
    historical,
    groups,
    feature_names: Sequence[str],
    *,
    prior_weight_current: float | None = None,
    l2: float = 5.0,
    intercept_l2: float = 1.0,
) -> ContextualBlendFit:
    yy = np.asarray(y, dtype=int)
    pc = _clip(current)
    ph = _clip(historical)
    gg = np.asarray(groups)
    if len(frame) == 0 or not (len(frame) == len(yy) == len(pc) == len(ph) == len(gg)):
        raise ValueError("grouped binary inputs must be non-empty and row-aligned")
    if prior_weight_current is None:
        prior_weight_current = fit_grouped_binary_blend(yy, pc, ph, gg).weight_current

    def loss_fn(w):
        p = rowwise_binary_logit_pool(pc, ph, w)
        return grouped_binary_log_loss(yy, p, gg)

    return _fit_gate(
        frame,
        feature_names,
        loss_fn,
        prior_weight_current=float(prior_weight_current),
        l2=l2,
        intercept_l2=intercept_l2,
    )
