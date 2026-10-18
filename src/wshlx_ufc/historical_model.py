"""Leakage-aware historical UFC winner model.

This module intentionally keeps a transparent logistic benchmark next to a nonlinear
hist-gradient-boosting model.  The ensemble is evaluated chronologically; random train/
test splits are not used for official metrics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .historical_rates import PastOnlyRateEncoder, add_interaction_features


LEAKAGE_COLUMNS = {
    "win", "winner", "winner_side", "method", "result", "outcome", "postfight",
    "fight_sig_landed", "fight_sig_attempted", "fight_td_landed", "fight_td_attempted",
    "fight_kd", "fight_sub_att", "fight_ctrl_sec",
}


@dataclass
class NumericModelWrapper:
    """Expose a full-frame predict_proba API around a numeric-column pipeline."""

    def __init__(self, model: object, cols: list[str]) -> None:
        self.model = model
        self.cols = list(cols)

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(x[self.cols])


@dataclass
class HistoricalModelBundle:
    logistic: object
    gradient_boosting: object
    rate_encoder: PastOnlyRateEncoder
    feature_columns: list[str]
    numeric_columns: list[str]
    categorical_columns: list[str]
    train_end: pd.Timestamp
    validation_end: pd.Timestamp

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        x = add_interaction_features(self.rate_encoder.transform(frame))
        x = x.reindex(columns=self.feature_columns)
        p1 = self.logistic.predict_proba(x)[:, 1]
        p2 = self.gradient_boosting.predict_proba(x)[:, 1]
        return 0.5 * p1 + 0.5 * p2


def _feature_columns(frame: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    excluded_exact = LEAKAGE_COLUMNS | {
        "date", "fight_id", "event", "fighter", "opponent", "fighter_a", "fighter_b",
        "url", "source_url",
    }
    cols = []
    for c in frame.columns:
        low = c.lower()
        if c in excluded_exact:
            continue
        if (
            low.startswith("post_") or low.endswith("_post") or "result_after" in low
            or "method" in low or low.startswith("fight_")
        ):
            continue
        cols.append(c)
    numeric = [c for c in cols if is_numeric_dtype(frame[c])]
    categorical = [c for c in cols if c not in numeric]
    return cols, numeric, categorical


def _preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        [
            (
                "num",
                Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]),
                numeric,
            ),
            (
                "cat",
                Pipeline([
                    ("impute", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore")),
                ]),
                categorical,
            ),
        ],
        remainder="drop",
    )


def chronological_split(
    frame: pd.DataFrame,
    *,
    train_frac: float = 0.70,
    validation_frac: float = 0.15,
    date_col: str = "date",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by unique fight dates so mirrored rows never cross partitions."""
    if not (0 < train_frac < 1 and 0 <= validation_frac < 1 and train_frac + validation_frac < 1):
        raise ValueError("invalid chronological split fractions")
    work = frame.copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    dates = np.array(sorted(work[date_col].dropna().unique()))
    if len(dates) < 3:
        raise ValueError("need at least three distinct fight dates")
    train_i = max(1, min(len(dates) - 2, int(np.floor(len(dates) * train_frac))))
    val_i = max(train_i + 1, min(len(dates) - 1, int(np.floor(len(dates) * (train_frac + validation_frac)))))
    train_end = dates[train_i - 1]
    val_end = dates[val_i - 1]
    train = work[work[date_col] <= train_end].copy()
    val = work[(work[date_col] > train_end) & (work[date_col] <= val_end)].copy()
    test = work[work[date_col] > val_end].copy()
    return train, val, test


def evaluate_probabilities(y: Iterable[float], p: Iterable[float]) -> dict[str, float]:
    yy = np.asarray(list(y), dtype=float)
    pp = np.clip(np.asarray(list(p), dtype=float), 1e-6, 1 - 1e-6)
    metrics = {
        "n_rows": float(len(yy)),
        "accuracy": float(accuracy_score(yy, pp >= 0.5)),
        "log_loss": float(log_loss(yy, pp, labels=[0, 1])),
        "brier": float(brier_score_loss(yy, pp)),
    }
    metrics["roc_auc"] = float(roc_auc_score(yy, pp)) if len(np.unique(yy)) == 2 else np.nan
    return metrics


def fit_historical_winner_model(frame: pd.DataFrame) -> tuple[HistoricalModelBundle, dict[str, dict[str, float]]]:
    """Fit logistic + nonlinear models with time-respecting historical-rate features."""
    if "win" not in frame:
        raise KeyError("expected binary target column 'win'")
    train, val, test = chronological_split(frame)

    # Training encodings are past-only, grouped by fight. Validation and test use only
    # information available before their partitions.
    enc_train = PastOnlyRateEncoder()
    train_e = add_interaction_features(enc_train.fit_transform(train))
    val_e = add_interaction_features(enc_train.transform(val))

    # After validation is scored, validation outcomes may become history for test.
    enc_test = PastOnlyRateEncoder()
    enc_test.fit(pd.concat([train, val], ignore_index=True))
    test_e = add_interaction_features(enc_test.transform(test))

    features, numeric, categorical = _feature_columns(train_e)
    prep = _preprocessor(numeric, categorical)
    logistic = Pipeline([
        ("prep", prep),
        ("model", LogisticRegression(max_iter=3000, C=0.5, class_weight="balanced")),
    ])
    logistic.fit(train_e[features], train_e["win"].astype(int))

    # HistGradientBoosting does not accept sparse one-hot output. Keep it on numeric
    # features only; this also makes it a useful independent model family.
    gb_numeric = [c for c in numeric if c in train_e]
    gb = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", HistGradientBoostingClassifier(
            learning_rate=0.045,
            max_iter=350,
            max_leaf_nodes=15,
            l2_regularization=1.5,
            min_samples_leaf=25,
            random_state=19,
        )),
    ])
    gb.fit(train_e[gb_numeric], train_e["win"].astype(int))

    gb_wrapped = NumericModelWrapper(gb, gb_numeric)

    def ens(x: pd.DataFrame) -> np.ndarray:
        return 0.5 * logistic.predict_proba(x[features])[:, 1] + 0.5 * gb_wrapped.predict_proba(x[features])[:, 1]

    metrics = {
        "validation": evaluate_probabilities(val_e["win"], ens(val_e)),
        "test": evaluate_probabilities(test_e["win"], ens(test_e)),
    }
    bundle = HistoricalModelBundle(
        logistic=logistic,
        gradient_boosting=gb_wrapped,
        rate_encoder=enc_test,
        feature_columns=features,
        numeric_columns=numeric,
        categorical_columns=categorical,
        train_end=pd.to_datetime(train["date"]).max(),
        validation_end=pd.to_datetime(val["date"]).max(),
    )
    return bundle, metrics
