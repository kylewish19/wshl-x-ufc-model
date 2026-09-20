from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def _clip(p, eps: float = 1e-6):
    return np.clip(np.asarray(p, dtype=float), eps, 1.0 - eps)


def _logit(p):
    p = _clip(p)
    return np.log(p / (1.0 - p))


def _sigmoid(z):
    z = np.clip(np.asarray(z, dtype=float), -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


def _fit_offset(y, baseline_p, ridge: float = 2.0, max_iter: int = 100, tol: float = 1e-10) -> float:
    y = np.asarray(y, dtype=float)
    offset = _logit(np.asarray(baseline_p, dtype=float))
    if len(y) != len(offset):
        raise ValueError("y and baseline_p lengths must match")
    if len(np.unique(y)) < 2:
        return 0.0

    delta = 0.0
    for _ in range(max_iter):
        p = _sigmoid(offset + delta)
        grad = float(np.sum(p - y) + ridge * delta)
        hess = float(np.sum(p * (1.0 - p)) + ridge)
        step = grad / max(hess, 1e-12)
        nxt = delta - step
        if abs(nxt - delta) < tol:
            delta = nxt
            break
        delta = nxt
    return float(delta)


@dataclass
class MethodInterceptCalibrator:
    """Low-variance calibration layer for conditional method probabilities.

    It learns only two scalar corrections from graded feedback:
      1. finish vs decision;
      2. submission vs KO conditional on a finish.

    This is intentionally much lower capacity than the v0.27 feature residual.
    """

    ridge: float = 2.0

    def fit(self, *, actual_method, baseline_ko, baseline_sub, baseline_dec):
        method = np.char.upper(np.asarray(actual_method, dtype=str))
        if set(np.unique(method)) - {"KO", "SUB", "DEC"}:
            raise ValueError("methods must be KO, SUB or DEC")

        p_ko = np.asarray(baseline_ko, dtype=float)
        p_sub = np.asarray(baseline_sub, dtype=float)
        p_dec = np.asarray(baseline_dec, dtype=float)
        if not np.allclose(p_ko + p_sub + p_dec, 1.0, atol=1e-5):
            raise ValueError("baseline probabilities must sum to one")

        y_finish = (method != "DEC").astype(float)
        self.finish_offset_ = _fit_offset(y_finish, 1.0 - p_dec, self.ridge)

        mask = method != "DEC"
        denom = p_ko[mask] + p_sub[mask]
        p_sub_given_finish = np.divide(
            p_sub[mask], denom, out=np.full_like(denom, 0.5), where=denom > 0
        )
        y_sub = (method[mask] == "SUB").astype(float)
        self.sub_offset_ = _fit_offset(y_sub, p_sub_given_finish, self.ridge)
        self.is_fitted_ = True
        return self

    def predict_proba(self, *, baseline_ko, baseline_sub, baseline_dec) -> pd.DataFrame:
        if not getattr(self, "is_fitted_", False):
            raise RuntimeError("calibrator is not fitted")

        p_ko0 = np.asarray(baseline_ko, dtype=float)
        p_sub0 = np.asarray(baseline_sub, dtype=float)
        p_dec0 = np.asarray(baseline_dec, dtype=float)
        if not np.allclose(p_ko0 + p_sub0 + p_dec0, 1.0, atol=1e-5):
            raise ValueError("baseline probabilities must sum to one")

        p_finish = _sigmoid(_logit(1.0 - p_dec0) + self.finish_offset_)
        denom = p_ko0 + p_sub0
        p_sub_given_finish0 = np.divide(
            p_sub0, denom, out=np.full_like(denom, 0.5), where=denom > 0
        )
        p_sub_given_finish = _sigmoid(
            _logit(p_sub_given_finish0) + self.sub_offset_
        )

        p_sub = p_finish * p_sub_given_finish
        p_ko = p_finish * (1.0 - p_sub_given_finish)
        p_dec = 1.0 - p_finish
        out = pd.DataFrame({"KO": p_ko, "SUB": p_sub, "DEC": p_dec})
        return out.div(out.sum(axis=1), axis=0)
