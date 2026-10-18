"""Constrained ensemble utilities for the WSHL-X UFC unified shadow layer.

The ensemble deliberately uses low-capacity convex pooling. With only a modest clean
prospective ledger, learned weights must be interpretable and difficult to overfit.
The component models remain independently inspectable; this module only combines their
pre-fight probabilities.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

import numpy as np
from sklearn.metrics import log_loss

EPS = 1e-7


def _clip(p):
    return np.clip(np.asarray(p, dtype=float), EPS, 1.0 - EPS)


def _logit(p):
    q = _clip(p)
    return np.log(q / (1.0 - q))


def _sigmoid(z):
    z = np.clip(np.asarray(z, dtype=float), -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


def binary_logit_pool(current, historical, weight_current: float) -> np.ndarray:
    """Convex pool of two binary probabilities on the log-odds scale."""
    w = float(weight_current)
    if not 0.0 <= w <= 1.0:
        raise ValueError("weight_current must be in [0, 1]")
    z = w * _logit(current) + (1.0 - w) * _logit(historical)
    return _sigmoid(z)


def multiclass_log_pool(current, historical, weight_current: float) -> np.ndarray:
    """Geometric/log pool of two coherent multiclass distributions."""
    w = float(weight_current)
    if not 0.0 <= w <= 1.0:
        raise ValueError("weight_current must be in [0, 1]")
    a = np.clip(np.asarray(current, dtype=float), EPS, 1.0)
    b = np.clip(np.asarray(historical, dtype=float), EPS, 1.0)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError("current and historical must be same-shape 2D arrays")
    a = a / a.sum(axis=1, keepdims=True)
    b = b / b.sum(axis=1, keepdims=True)
    logp = w * np.log(a) + (1.0 - w) * np.log(b)
    logp -= logp.max(axis=1, keepdims=True)
    out = np.exp(logp)
    return out / out.sum(axis=1, keepdims=True)


@dataclass(frozen=True)
class BlendFit:
    weight_current: float
    loss: float
    current_loss: float
    historical_loss: float
    n: int

    @property
    def weight_historical(self) -> float:
        return 1.0 - self.weight_current

    @property
    def improvement_vs_best_base(self) -> float:
        return min(self.current_loss, self.historical_loss) - self.loss

    def to_dict(self) -> dict[str, float | int]:
        out = asdict(self)
        out["weight_historical"] = self.weight_historical
        out["improvement_vs_best_base"] = self.improvement_vs_best_base
        return out


def _weight_grid(grid: Iterable[float] | None = None) -> np.ndarray:
    if grid is None:
        return np.linspace(0.0, 1.0, 41)
    out = np.unique(np.asarray(list(grid), dtype=float))
    if len(out) == 0 or np.any((out < 0.0) | (out > 1.0)):
        raise ValueError("grid weights must be within [0, 1]")
    return out


def fit_binary_blend(y, current, historical, *, grid: Iterable[float] | None = None) -> BlendFit:
    yy = np.asarray(y, dtype=int)
    pc = _clip(current)
    ph = _clip(historical)
    if len(yy) == 0 or not (len(yy) == len(pc) == len(ph)):
        raise ValueError("y/current/historical lengths must match and be non-empty")
    current_loss = float(log_loss(yy, pc, labels=[0, 1]))
    historical_loss = float(log_loss(yy, ph, labels=[0, 1]))
    best_w, best_loss = 1.0, np.inf
    for w in _weight_grid(grid):
        loss = float(log_loss(yy, binary_logit_pool(pc, ph, float(w)), labels=[0, 1]))
        if loss < best_loss - 1e-12:
            best_w, best_loss = float(w), loss
    return BlendFit(best_w, best_loss, current_loss, historical_loss, int(len(yy)))


def _group_mean_binary_log_loss(y, p, groups) -> float:
    yy = np.asarray(y, dtype=int)
    pp = _clip(p)
    gg = np.asarray(groups)
    if len(yy) == 0 or not (len(yy) == len(pp) == len(gg)):
        raise ValueError("y/p/groups lengths must match and be non-empty")
    losses = -(yy * np.log(pp) + (1 - yy) * np.log(1 - pp))
    unique = list(dict.fromkeys(gg.tolist()))
    return float(np.mean([losses[gg == g].mean() for g in unique]))


def fit_grouped_binary_blend(
    y,
    current,
    historical,
    groups,
    *,
    grid: Iterable[float] | None = None,
) -> BlendFit:
    """Fit one binary blend while giving each fight/group equal objective weight.

    Timing markets are correlated and five-round fights expose more markets than
    three-round fights. Averaging loss within fight before averaging across fights stops
    those extra markets from granting five-round bouts disproportionate influence.
    """
    yy = np.asarray(y, dtype=int)
    pc = _clip(current)
    ph = _clip(historical)
    gg = np.asarray(groups)
    if len(yy) == 0 or not (len(yy) == len(pc) == len(ph) == len(gg)):
        raise ValueError("y/current/historical/groups lengths must match and be non-empty")
    current_loss = _group_mean_binary_log_loss(yy, pc, gg)
    historical_loss = _group_mean_binary_log_loss(yy, ph, gg)
    best_w, best_loss = 1.0, np.inf
    for w in _weight_grid(grid):
        pooled = binary_logit_pool(pc, ph, float(w))
        loss = _group_mean_binary_log_loss(yy, pooled, gg)
        if loss < best_loss - 1e-12:
            best_w, best_loss = float(w), loss
    return BlendFit(best_w, best_loss, current_loss, historical_loss, int(len(np.unique(gg))))


def fit_multiclass_blend(
    y: Sequence[int] | np.ndarray,
    current: np.ndarray,
    historical: np.ndarray,
    *,
    grid: Iterable[float] | None = None,
) -> BlendFit:
    yy = np.asarray(y, dtype=int)
    pc = np.asarray(current, dtype=float)
    ph = np.asarray(historical, dtype=float)
    if len(yy) == 0 or pc.shape != ph.shape or pc.shape[0] != len(yy):
        raise ValueError("multiclass inputs must be non-empty and row-aligned")
    labels = list(range(pc.shape[1]))
    pc = np.clip(pc, EPS, 1.0); pc /= pc.sum(axis=1, keepdims=True)
    ph = np.clip(ph, EPS, 1.0); ph /= ph.sum(axis=1, keepdims=True)
    current_loss = float(log_loss(yy, pc, labels=labels))
    historical_loss = float(log_loss(yy, ph, labels=labels))
    best_w, best_loss = 1.0, np.inf
    for w in _weight_grid(grid):
        pooled = multiclass_log_pool(pc, ph, float(w))
        loss = float(log_loss(yy, pooled, labels=labels))
        if loss < best_loss - 1e-12:
            best_w, best_loss = float(w), loss
    return BlendFit(best_w, best_loss, current_loss, historical_loss, int(len(yy)))


def resample_hazards(hazards, from_bin_seconds: int, to_bin_seconds: int = 30) -> np.ndarray:
    """Split coarser hazards into equal conditional sub-bin hazards.

    If a 60-second interval has finish hazard h, two 30-second sub-bins receive hazard
    1-sqrt(1-h), preserving the original 60-second survival probability exactly.
    """
    h = np.clip(np.asarray(hazards, dtype=float), EPS, 1.0 - EPS)
    if from_bin_seconds == to_bin_seconds:
        return h.copy()
    if from_bin_seconds < to_bin_seconds or from_bin_seconds % to_bin_seconds:
        raise ValueError("from_bin_seconds must be an integer multiple of to_bin_seconds")
    ratio = from_bin_seconds // to_bin_seconds
    sub = 1.0 - np.power(1.0 - h, 1.0 / ratio)
    return np.repeat(sub, ratio)


def blend_hazards(
    current_hazards,
    historical_hazards,
    weight_current: float,
    *,
    current_bin_seconds: int = 30,
    historical_bin_seconds: int = 30,
    output_bin_seconds: int = 30,
) -> np.ndarray:
    a = resample_hazards(current_hazards, current_bin_seconds, output_bin_seconds)
    b = resample_hazards(historical_hazards, historical_bin_seconds, output_bin_seconds)
    n = min(len(a), len(b))
    if n == 0:
        return np.array([], dtype=float)
    return binary_logit_pool(a[:n], b[:n], weight_current)


def markets_from_hazards(hazards, scheduled_seconds: int, *, bin_seconds: int = 30) -> dict[str, float]:
    """Derive a coherent UFC timing market set from one hazard curve."""
    h = np.clip(np.asarray(hazards, dtype=float), 0.0, 1.0)
    survival = np.cumprod(1.0 - h)
    endpoints = np.arange(1, len(survival) + 1) * int(bin_seconds)

    def survive(seconds: int) -> float:
        if seconds <= 0:
            return 1.0
        if seconds > scheduled_seconds:
            return 0.0
        pos = np.flatnonzero(endpoints <= seconds)
        return 1.0 if not len(pos) else float(survival[pos[-1]])

    rounds = int(scheduled_seconds) // 300
    out: dict[str, float] = {}
    thresholds = [0.5, 1.5, 2.5] + ([3.5, 4.5] if rounds == 5 else [])
    for r in thresholds:
        p = survive(int(round(r * 300)))
        out[f"OVER_{r}"] = p
        out[f"UNDER_{r}"] = 1.0 - p
    gtd = survive(int(scheduled_seconds))
    out["GTD_YES"], out["GTD_NO"] = gtd, 1.0 - gtd
    prior = 1.0
    for rnd in range(1, rounds + 1):
        end = survive(rnd * 300)
        out[f"FINISH_ROUND_{rnd}"] = max(0.0, prior - end)
        prior = end
    for rnd in range(2, rounds + 1):
        p = survive((rnd - 1) * 300)
        out[f"ROUND_{rnd}_STARTS_YES"] = p
        out[f"ROUND_{rnd}_STARTS_NO"] = 1.0 - p
    return out
