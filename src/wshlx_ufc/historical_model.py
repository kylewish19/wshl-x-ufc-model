"""Leakage-aware historical UFC winner model.

This module keeps a transparent logistic benchmark next to a nonlinear histogram
gradient-boosting model. Evaluation is chronological; random train/test splits are not
used for official metrics. After untouched validation/test scoring, the saved shadow
bundle is refit on all completed history for future predictions.
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


def _pair_normalize(frame: pd.DataFrame, probabilities: np.ndarray) -> np.ndarray:
    """Force mirrored matchup probabilities to sum to one within each fight.

    The two model perspectives are fitted independently, so raw probabilities can be
    slightly incoherent (for example 0.58 and 0.47). Converting raw probabilities to
    logits and softmax-normalizing within a fight preserves relative model confidence
    while producing a coherent two-outcome probability distribution.
    """
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
    if "fight_id" not in frame.columns or len(p) != len(frame):
        return p
    out = p.copy()
    ids = frame["fight_id"].astype(str).to_numpy()
    for fight_id in pd.unique(ids):
        pos = np.flatnonzero(ids == fight_id)
        if len(pos) != 2:
            continue
        logits = np.log(p[pos] / (1 - p[pos]))
        logits -= np.max(logits)
        weights = np.exp(logits)
        out[pos] = weights / weights.sum()
    return out


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
    history_end: pd.Timestamp

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        x = add_interaction_features(self.rate_encoder.transform(frame))
        x = x.reindex(columns=self.feature_columns)
        p1 = self.logistic.predict_proba(x)[:, 1]
        p2 = self.gradient_boosting.predict_proba(x)[:, 1]
        return _pair_normalize(frame, 0.5 * p1 + 0.5 * p2)


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


def _fit_estimators(encoded: pd.DataFrame) -> tuple[object, NumericModelWrapper, list[str], list[str], list[str]]:
    features, numeric, categorical = _feature_columns(encoded)
    prep = _preprocessor(numeric, categorical)
    logistic = Pipeline([
        ("prep", prep),
        ("model", LogisticRegression(max_iter=3000, C=0.5, class_weight="balanced")),
    ])
    logistic.fit(encoded[features], encoded["win"].astype(int))

    gb_numeric = [c for c in numeric if c in encoded]
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
    gb.fit(encoded[gb_numeric], encoded["win"].astype(int))
    return logistic, NumericModelWrapper(gb, gb_numeric), features, numeric, categorical


def chronological_split(
    frame: pd.DataFrame,
    *,
    train_frac: float = 0.70,
    validation_frac: float = 0.15,
    date_col: str = "date",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by unique fight dates so mirrored rows and same-day cards stay together."""
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
    """Evaluate chronologically, then refit the shadow winner model on full history."""
    if "win" not in frame:
        raise KeyError("expected binary target column 'win'")
    train, val, test = chronological_split(frame)

    # Training encodings only use prior fight dates. Validation is frozen against
    # training history; test is frozen against training + validation history.
    enc_train = PastOnlyRateEncoder()
    train_e = add_interaction_features(enc_train.fit_transform(train))
    val_e = add_interaction_features(enc_train.transform(val))

    enc_test = PastOnlyRateEncoder()
    enc_test.fit(pd.concat([train, val], ignore_index=True))
    test_e = add_interaction_features(enc_test.transform(test))

    logistic_eval, gb_eval, features_eval, _, _ = _fit_estimators(train_e)

    def ens(x: pd.DataFrame) -> np.ndarray:
        p1 = logistic_eval.predict_proba(x[features_eval])[:, 1]
        p2 = gb_eval.predict_proba(x[features_eval])[:, 1]
        return _pair_normalize(x, 0.5 * p1 + 0.5 * p2)

    metrics = {
        "validation": evaluate_probabilities(val_e["win"], ens(val_e)),
        "test": evaluate_probabilities(test_e["win"], ens(test_e)),
    }
    metrics["validation"]["n_fights"] = float(val_e["fight_id"].nunique())
    metrics["test"]["n_fights"] = float(test_e["fight_id"].nunique())
    metrics["baseline"] = {"coinflip_log_loss": float(np.log(2.0)), "coinflip_brier": 0.25}

    # Evaluation remains untouched above. Now refit a deployment/shadow bundle on all
    # completed history, with each training row still encoded strictly from prior dates.
    final_encoder = PastOnlyRateEncoder()
    full_e = add_interaction_features(final_encoder.fit_transform(frame))
    logistic, gb_wrapped, features, numeric, categorical = _fit_estimators(full_e)

    bundle = HistoricalModelBundle(
        logistic=logistic,
        gradient_boosting=gb_wrapped,
        rate_encoder=final_encoder,
        feature_columns=features,
        numeric_columns=numeric,
        categorical_columns=categorical,
        train_end=pd.to_datetime(train["date"]).max(),
        validation_end=pd.to_datetime(val["date"]).max(),
        history_end=pd.to_datetime(frame["date"]).max(),
    )
    return bundle, metrics
