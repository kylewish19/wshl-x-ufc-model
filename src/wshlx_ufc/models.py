from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


METHODS = ("KO", "SUB", "DEC")


def _binary_pipeline(c: float = 0.25) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=c,
                    solver="lbfgs",
                    max_iter=5000,
                    class_weight=None,
                    random_state=19,
                ),
            ),
        ]
    )


@dataclass
class WinnerModel:
    """Binary winner learner. y=1 means fighter A wins."""

    c: float = 0.25

    def __post_init__(self) -> None:
        self.pipeline = _binary_pipeline(self.c)
        self.feature_names_: list[str] | None = None

    def fit(self, x: pd.DataFrame, y: Sequence[int]) -> "WinnerModel":
        self.feature_names_ = list(x.columns)
        self.pipeline.fit(x, np.asarray(y, dtype=int))
        return self

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        pa = self.pipeline.predict_proba(x)[:, 1]
        return np.column_stack([pa, 1.0 - pa])


@dataclass
class ConditionalMethodModel:
    """Two-head conditional method learner.

    Head 1 predicts finish versus decision.
    Head 2 predicts submission versus KO given a finish.

    Training rows represent the eventual winning fighter's *prefight* feature
    view. This avoids duplicating both fighter sides as independent outcomes.
    """

    finish_c: float = 0.10
    sub_c: float = 0.10

    def __post_init__(self) -> None:
        self.finish_model = _binary_pipeline(self.finish_c)
        self.sub_model = _binary_pipeline(self.sub_c)
        self.feature_names_: list[str] | None = None
        self.sub_head_fitted_: bool = False

    def fit(self, x: pd.DataFrame, method: Sequence[str]) -> "ConditionalMethodModel":
        labels = np.char.upper(np.asarray(method, dtype=str))
        invalid = sorted(set(labels) - set(METHODS))
        if invalid:
            raise ValueError(f"Unknown method labels: {invalid}")

        self.feature_names_ = list(x.columns)
        is_finish = (labels != "DEC").astype(int)
        if len(np.unique(is_finish)) < 2:
            raise ValueError("Finish head requires both finish and decision examples.")
        self.finish_model.fit(x, is_finish)

        finish_mask = labels != "DEC"
        finish_labels = labels[finish_mask]
        if len(finish_labels) and len(np.unique(finish_labels)) >= 2:
            is_sub = (finish_labels == "SUB").astype(int)
            self.sub_model.fit(x.loc[finish_mask], is_sub)
            self.sub_head_fitted_ = True
        else:
            self.sub_head_fitted_ = False
        return self

    def predict_proba(
        self,
        x: pd.DataFrame,
        *,
        fallback_sub_share: float = 0.20,
    ) -> pd.DataFrame:
        p_finish = self.finish_model.predict_proba(x)[:, 1]
        if self.sub_head_fitted_:
            p_sub_given_finish = self.sub_model.predict_proba(x)[:, 1]
        else:
            p_sub_given_finish = np.full(len(x), fallback_sub_share, dtype=float)

        p_sub = p_finish * p_sub_given_finish
        p_ko = p_finish * (1.0 - p_sub_given_finish)
        p_dec = 1.0 - p_finish

        out = pd.DataFrame({"KO": p_ko, "SUB": p_sub, "DEC": p_dec}, index=x.index)
        return out.div(out.sum(axis=1), axis=0)


@dataclass
class BinaryMarketModel:
    """Reusable learner for one binary timing/survival market."""

    name: str
    c: float = 0.25

    def __post_init__(self) -> None:
        self.pipeline = _binary_pipeline(self.c)
        self.feature_names_: list[str] | None = None

    def fit(self, x: pd.DataFrame, y: Sequence[int]) -> "BinaryMarketModel":
        y_arr = np.asarray(y, dtype=int)
        if len(np.unique(y_arr)) < 2:
            raise ValueError(f"{self.name} requires both outcome classes.")
        self.feature_names_ = list(x.columns)
        self.pipeline.fit(x, y_arr)
        return self

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        return self.pipeline.predict_proba(x)[:, 1]


def joint_outcome_probabilities(
    p_a_win: float,
    method_if_a_wins: Mapping[str, float],
    method_if_b_wins: Mapping[str, float],
) -> dict[str, float]:
    """Create six coherent fighter+method probabilities."""
    if not 0.0 <= p_a_win <= 1.0:
        raise ValueError("p_a_win must be within [0, 1].")

    def normalized(m: Mapping[str, float]) -> dict[str, float]:
        vals = {k: float(m[k]) for k in METHODS}
        if any(v < 0 for v in vals.values()):
            raise ValueError("Method probabilities cannot be negative.")
        total = sum(vals.values())
        if total <= 0:
            raise ValueError("Method probabilities must have positive mass.")
        return {k: v / total for k, v in vals.items()}

    a = normalized(method_if_a_wins)
    b = normalized(method_if_b_wins)
    p_b_win = 1.0 - p_a_win

    joint = {
        "A_KO": p_a_win * a["KO"],
        "A_SUB": p_a_win * a["SUB"],
        "A_DEC": p_a_win * a["DEC"],
        "B_KO": p_b_win * b["KO"],
        "B_SUB": p_b_win * b["SUB"],
        "B_DEC": p_b_win * b["DEC"],
    }
    total = sum(joint.values())
    return {k: v / total for k, v in joint.items()}


def fighter_double_chance(joint: Mapping[str, float]) -> dict[str, float]:
    """Derive fighter-specific method double chances from six joint outcomes."""
    return {
        "A_KO_OR_SUB": joint["A_KO"] + joint["A_SUB"],
        "A_KO_OR_DEC": joint["A_KO"] + joint["A_DEC"],
        "A_SUB_OR_DEC": joint["A_SUB"] + joint["A_DEC"],
        "B_KO_OR_SUB": joint["B_KO"] + joint["B_SUB"],
        "B_KO_OR_DEC": joint["B_KO"] + joint["B_DEC"],
        "B_SUB_OR_DEC": joint["B_SUB"] + joint["B_DEC"],
    }
