from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


V027_FEATURES = (
    "knockdown_interaction",
    "ground_strike_interaction",
    "submission_attempt_interaction",
    "td_access_interaction",
    "control_interaction",
    "offensive_wrestling_exposure_interaction",
    "winner_round3_retention",
    "opponent_round3_retention",
    "winner_log_ufc_bouts",
    "opponent_log_ufc_bouts",
)


def _clip_probability(p: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    return np.clip(np.asarray(p, dtype=float), eps, 1.0 - eps)


def _logit(p: np.ndarray) -> np.ndarray:
    p = _clip_probability(p)
    return np.log(p / (1.0 - p))


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


@dataclass
class OffsetLogisticRidge:
    """Binary logistic residual model with a fixed baseline-logit offset.

    This intentionally treats the baseline model probability as an offset
    rather than a freely reweighted feature. The fitted coefficients therefore
    represent a regularized correction to the frozen baseline.
    """

    ridge: float = 10.0
    max_iter: int = 100
    tol: float = 1e-8

    def fit(self, x: np.ndarray, y: np.ndarray, baseline_p: np.ndarray) -> "OffsetLogisticRidge":
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        offset = _logit(np.asarray(baseline_p, dtype=float))

        if x.ndim != 2:
            raise ValueError("x must be 2D")
        if len(y) != len(x) or len(offset) != len(x):
            raise ValueError("x, y and baseline_p lengths must match")
        if set(np.unique(y)) - {0.0, 1.0}:
            raise ValueError("y must be binary")
        if len(np.unique(y)) < 2:
            raise ValueError("both binary classes are required")

        beta = np.zeros(x.shape[1], dtype=float)
        eye = np.eye(x.shape[1], dtype=float)

        for _ in range(self.max_iter):
            p = _sigmoid(offset + x @ beta)
            grad = x.T @ (p - y) + self.ridge * beta
            w = np.clip(p * (1.0 - p), 1e-8, None)
            hess = x.T @ (x * w[:, None]) + self.ridge * eye
            step = np.linalg.solve(hess, grad)
            beta_next = beta - step
            if np.max(np.abs(beta_next - beta)) < self.tol:
                beta = beta_next
                break
            beta = beta_next

        self.coef_ = beta
        return self

    def predict_proba(self, x: np.ndarray, baseline_p: np.ndarray) -> np.ndarray:
        if not hasattr(self, "coef_"):
            raise RuntimeError("model is not fitted")
        x = np.asarray(x, dtype=float)
        return _sigmoid(_logit(np.asarray(baseline_p, dtype=float)) + x @ self.coef_)


@dataclass
class V027MethodResidualChallenger:
    """Reconstruction of the lost v0.26 *idea*, under a new version.

    Required row perspective is selected/actual winner versus opponent.
    It never accepts sportsbook data and does not train on both fighter sides as
    independent target outcomes.
    """

    ridge: float = 10.0
    clip_z: float = 5.0

    def __post_init__(self) -> None:
        self.imputer = SimpleImputer(strategy="median", add_indicator=True)
        self.scaler = StandardScaler()
        self.finish_head = OffsetLogisticRidge(ridge=self.ridge)
        self.sub_head = OffsetLogisticRidge(ridge=self.ridge)

    def _select(self, frame: pd.DataFrame) -> pd.DataFrame:
        missing = [c for c in V027_FEATURES if c not in frame]
        if missing:
            raise ValueError(f"missing v0.27 features: {missing}")
        return frame.loc[:, V027_FEATURES].astype(float)

    def _fit_transform(self, frame: pd.DataFrame) -> np.ndarray:
        x = self._select(frame)
        x_imp = self.imputer.fit_transform(x)
        z = self.scaler.fit_transform(x_imp)
        return np.clip(z, -self.clip_z, self.clip_z)

    def _transform(self, frame: pd.DataFrame) -> np.ndarray:
        x = self._select(frame)
        x_imp = self.imputer.transform(x)
        z = self.scaler.transform(x_imp)
        return np.clip(z, -self.clip_z, self.clip_z)

    def fit(
        self,
        frame: pd.DataFrame,
        *,
        actual_method,
        baseline_ko,
        baseline_sub,
        baseline_dec,
    ) -> "V027MethodResidualChallenger":
        method = np.char.upper(np.asarray(actual_method, dtype=str))
        if set(np.unique(method)) - {"KO", "SUB", "DEC"}:
            raise ValueError("methods must be KO, SUB or DEC")

        p_ko = np.asarray(baseline_ko, dtype=float)
        p_sub = np.asarray(baseline_sub, dtype=float)
        p_dec = np.asarray(baseline_dec, dtype=float)
        total = p_ko + p_sub + p_dec
        if not np.allclose(total, 1.0, atol=1e-5):
            raise ValueError("baseline KO/SUB/DEC probabilities must sum to one")

        x = self._fit_transform(frame)

        y_finish = (method != "DEC").astype(float)
        baseline_finish = 1.0 - p_dec
        self.finish_head.fit(x, y_finish, baseline_finish)

        finish_mask = method != "DEC"
        if finish_mask.sum() < 2 or len(np.unique(method[finish_mask])) < 2:
            raise ValueError("SUB-vs-KO head requires both finish classes")

        y_sub = (method[finish_mask] == "SUB").astype(float)
        denom = p_ko[finish_mask] + p_sub[finish_mask]
        baseline_sub_given_finish = np.divide(
            p_sub[finish_mask],
            denom,
            out=np.full_like(denom, 0.5),
            where=denom > 0,
        )
        self.sub_head.fit(x[finish_mask], y_sub, baseline_sub_given_finish)
        self.is_fitted_ = True
        return self

    def predict_proba(
        self,
        frame: pd.DataFrame,
        *,
        baseline_ko,
        baseline_sub,
        baseline_dec,
    ) -> pd.DataFrame:
        if not getattr(self, "is_fitted_", False):
            raise RuntimeError("model is not fitted")

        p_ko0 = np.asarray(baseline_ko, dtype=float)
        p_sub0 = np.asarray(baseline_sub, dtype=float)
        p_dec0 = np.asarray(baseline_dec, dtype=float)
        if not np.allclose(p_ko0 + p_sub0 + p_dec0, 1.0, atol=1e-5):
            raise ValueError("baseline KO/SUB/DEC probabilities must sum to one")

        x = self._transform(frame)
        p_finish = self.finish_head.predict_proba(x, 1.0 - p_dec0)

        denom = p_ko0 + p_sub0
        p_sub_given_finish0 = np.divide(
            p_sub0,
            denom,
            out=np.full_like(denom, 0.5),
            where=denom > 0,
        )
        p_sub_given_finish = self.sub_head.predict_proba(x, p_sub_given_finish0)

        p_sub = p_finish * p_sub_given_finish
        p_ko = p_finish * (1.0 - p_sub_given_finish)
        p_dec = 1.0 - p_finish

        out = pd.DataFrame({"KO": p_ko, "SUB": p_sub, "DEC": p_dec}, index=frame.index)
        return out.div(out.sum(axis=1), axis=0)
