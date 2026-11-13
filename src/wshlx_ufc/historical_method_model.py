"""Historical conditional-rate challenger for fighter-specific UFC method outcomes.

The target is a coherent six-state joint distribution:
WIN_KO_TKO, WIN_SUB, WIN_DEC, LOSS_KO_TKO, LOSS_SUB, LOSS_DEC.
That lets winner, fight method, and winner+method probabilities all come from one simplex
instead of being multiplied from independently calibrated models.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .historical_model import NumericModelWrapper, chronological_split
from .historical_outcomes import METHOD_STATES, add_method_targets
from .historical_rates import (
    PastOnlyRateEncoder,
    add_interaction_features,
    all_conditional_rate_tables,
    categorical_conditional_rate_tables,
    interaction_conditional_rate_tables,
)

METHOD_MARKETS = ("KO_TKO", "SUB", "DEC")


def _temperature_transform(probabilities: np.ndarray, temperature: float) -> np.ndarray:
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-9, 1.0)
    q = np.power(p, 1.0 / float(temperature))
    return q / q.sum(axis=1, keepdims=True)


def _multiclass_nll(y: pd.Series | np.ndarray, probabilities: np.ndarray, classes: list[str]) -> float:
    """Cross-entropy using the explicit probability-column order supplied by caller."""
    yy = np.asarray(y, dtype=str)
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-12, 1.0)
    lookup = {c: i for i, c in enumerate(classes)}
    indices = np.asarray([lookup[v] for v in yy], dtype=int)
    return float(-np.mean(np.log(p[np.arange(len(yy)), indices])))


def _fit_temperature(y: pd.Series, probabilities: np.ndarray, classes: list[str]) -> tuple[float, dict[str, float]]:
    yy = y.astype(str).to_numpy()
    raw = _multiclass_nll(yy, probabilities, classes)
    best_t, best_loss = 1.0, raw
    for t in np.geomspace(0.50, 4.0, 121):
        q = _temperature_transform(probabilities, float(t))
        loss = _multiclass_nll(yy, q, classes)
        if loss < best_loss - 1e-12:
            best_t, best_loss = float(t), loss
    return best_t, {"temperature": best_t, "raw_log_loss": raw, "calibrated_log_loss": best_loss}


def _model_classes(model: object) -> list[str]:
    if hasattr(model, "classes_"):
        return list(model.classes_)
    if hasattr(model, "named_steps"):
        return list(model.named_steps["model"].classes_)
    if hasattr(model, "model") and hasattr(model.model, "named_steps"):
        return list(model.model.named_steps["model"].classes_)
    raise AttributeError("Could not locate fitted class labels")


def _aligned_probabilities(model: object, x: pd.DataFrame, classes: list[str]) -> np.ndarray:
    raw = model.predict_proba(x)
    fitted = _model_classes(model)
    out = np.zeros((len(x), len(classes)), dtype=float)
    for j, c in enumerate(classes):
        if c in fitted:
            out[:, j] = raw[:, fitted.index(c)]
    s = out.sum(axis=1, keepdims=True)
    return np.divide(out, s, out=np.full_like(out, 1 / len(classes)), where=s > 0)


def _pair_cohere(frame: pd.DataFrame, probabilities: np.ndarray, classes: list[str]) -> np.ndarray:
    """Average mirrored evidence into one six-state event distribution per fight."""
    p = np.asarray(probabilities, dtype=float).copy()
    idx = {c: i for i, c in enumerate(classes)}
    out = p.copy()
    ids = frame["fight_id"].astype(str).to_numpy()
    for fight_id in pd.unique(ids):
        pos = np.flatnonzero(ids == fight_id)
        if len(pos) != 2:
            continue
        i, j = int(pos[0]), int(pos[1])
        event = np.zeros(len(classes), dtype=float)
        for meth in METHOD_MARKETS:
            wi, li = idx[f"WIN_{meth}"], idx[f"LOSS_{meth}"]
            event[wi] = 0.5 * (p[i, wi] + p[j, li])
            event[li] = 0.5 * (p[i, li] + p[j, wi])
        event = np.clip(event, 1e-12, None)
        event /= event.sum()
        out[i] = event
        swapped = event.copy()
        for meth in METHOD_MARKETS:
            wi, li = idx[f"WIN_{meth}"], idx[f"LOSS_{meth}"]
            swapped[wi], swapped[li] = event[li], event[wi]
        out[j] = swapped
    return out


def _method_rate_encode_fit(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, PastOnlyRateEncoder], PastOnlyRateEncoder]:
    out = frame.copy()
    winner_encoder = PastOnlyRateEncoder()
    wr = winner_encoder.fit_transform(frame, target="win")
    extra = [c for c in wr.columns if c.startswith("hist_")]
    out[extra] = wr[extra]
    encoders: dict[str, PastOnlyRateEncoder] = {}
    additions: list[pd.DataFrame] = []
    for state in METHOD_STATES:
        target = f"target_{state.lower()}"
        enc = PastOnlyRateEncoder(alpha=20.0, prior=float(pd.to_numeric(frame[target], errors="coerce").mean()))
        z = enc.fit_transform(frame, target=target)
        cols = [c for c in z.columns if c.startswith("hist_") and c.endswith("_wr")]
        if cols:
            rename = {c: c.replace("_wr", f"_{state.lower()}_rate") for c in cols}
            additions.append(z[cols].rename(columns=rename))
        encoders[state] = enc
    if additions:
        out = pd.concat([out, *additions], axis=1)
    return out.copy(), encoders, winner_encoder


def _method_rate_encode_transform(frame: pd.DataFrame, encoders: dict[str, PastOnlyRateEncoder], winner_encoder: PastOnlyRateEncoder) -> pd.DataFrame:
    out = frame.copy()
    wr = winner_encoder.transform(frame)
    extra = [c for c in wr.columns if c.startswith("hist_")]
    out[extra] = wr[extra]
    additions: list[pd.DataFrame] = []
    for state, enc in encoders.items():
        z = enc.transform(frame)
        cols = [c for c in z.columns if c.startswith("hist_") and c.endswith("_wr")]
        if cols:
            rename = {c: c.replace("_wr", f"_{state.lower()}_rate") for c in cols}
            additions.append(z[cols].rename(columns=rename))
    if additions:
        out = pd.concat([out, *additions], axis=1)
    return out.copy()


def _fit_rate_encoders(frame: pd.DataFrame) -> tuple[dict[str, PastOnlyRateEncoder], PastOnlyRateEncoder]:
    winner = PastOnlyRateEncoder().fit(frame, target="win")
    encoders: dict[str, PastOnlyRateEncoder] = {}
    for state in METHOD_STATES:
        target = f"target_{state.lower()}"
        prior = float(pd.to_numeric(frame[target], errors="coerce").mean())
        encoders[state] = PastOnlyRateEncoder(alpha=20.0, prior=prior).fit(frame, target=target)
    return encoders, winner


TARGET_PREFIXES = ("target_",)
TARGET_COLUMNS = {"method_target", "fight_method", "finish_seconds", "scheduled_seconds", "finish_observed", "finish_r1", "survive_450", "survive_750", "goes_distance"}


def _feature_columns(frame: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    excluded = TARGET_COLUMNS | {"win", "date", "fight_id", "event", "fighter", "opponent"}
    cols: list[str] = []
    for c in frame.columns:
        low = c.lower()
        if c in excluded or low.startswith(TARGET_PREFIXES) or low.startswith("fight_") or low.startswith("post_") or low.endswith("_post"):
            continue
        cols.append(c)
    numeric = [c for c in cols if is_numeric_dtype(frame[c])]
    categorical = [c for c in cols if c not in numeric]
    return cols, numeric, categorical


def _preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    return ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ], remainder="drop")


def _fit_estimators(frame: pd.DataFrame) -> tuple[object, NumericModelWrapper, list[str], list[str], list[str]]:
    features, numeric, categorical = _feature_columns(frame)
    y = frame["method_target"].astype(str)
    logistic = Pipeline([
        ("prep", _preprocessor(numeric, categorical)),
        ("model", LogisticRegression(max_iter=4000, C=0.35, class_weight="balanced")),
    ])
    logistic.fit(frame[features], y)
    gb_numeric = [c for c in numeric if c in frame]
    gb = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", HistGradientBoostingClassifier(
            learning_rate=0.04, max_iter=325, max_leaf_nodes=15,
            l2_regularization=2.0, min_samples_leaf=35, random_state=23,
        )),
    ])
    gb.fit(frame[gb_numeric], y)
    return logistic, NumericModelWrapper(gb, gb_numeric), features, numeric, categorical


def _ensemble(frame: pd.DataFrame, logistic: object, gb: object, features: list[str]) -> np.ndarray:
    classes = list(METHOD_STATES)
    p1 = _aligned_probabilities(logistic, frame[features], classes)
    p2 = _aligned_probabilities(gb, frame[features], classes)
    return _pair_cohere(frame, 0.5 * p1 + 0.5 * p2, classes)


def _canonical(frame: pd.DataFrame) -> np.ndarray:
    return ~frame["fight_id"].astype(str).duplicated(keep="first").to_numpy()


def _method_marginals(p: np.ndarray, classes: list[str]) -> np.ndarray:
    cols = []
    for meth in METHOD_MARKETS:
        cols.append(p[:, classes.index(f"WIN_{meth}")] + p[:, classes.index(f"LOSS_{meth}")])
    return np.column_stack(cols)


def evaluate_method_probabilities(frame: pd.DataFrame, probabilities: np.ndarray) -> dict[str, float]:
    classes = list(METHOD_STATES)
    mask = _canonical(frame)
    f = frame.loc[mask].copy()
    p = probabilities[mask]
    y = f["method_target"].astype(str).to_numpy()
    pred = np.asarray(classes, dtype=object)[np.argmax(p, axis=1)]

    winner_true = np.char.startswith(y.astype(str), "WIN_")
    win_cols = [classes.index(c) for c in classes if c.startswith("WIN_")]
    winner_pred = p[:, win_cols].sum(axis=1) >= 0.5

    method_true = np.asarray([v.split("_", 1)[1] for v in y], dtype=object)
    method_probs = _method_marginals(p, classes)
    method_pred = np.asarray(METHOD_MARKETS, dtype=object)[np.argmax(method_probs, axis=1)]

    y_onehot = np.zeros_like(p)
    method_onehot = np.zeros_like(method_probs)
    for r, label in enumerate(y):
        y_onehot[r, classes.index(label)] = 1.0
        method_onehot[r, METHOD_MARKETS.index(method_true[r])] = 1.0

    out = {
        "n_fights": float(len(f)),
        "joint_accuracy": float(np.mean(pred == y)),
        "winner_accuracy": float(accuracy_score(winner_true, winner_pred)),
        "method_accuracy": float(np.mean(method_true == method_pred)),
        "log_loss": _multiclass_nll(y, p, classes),
        "multiclass_brier": float(np.mean(np.sum((p - y_onehot) ** 2, axis=1))),
        "method_brier": float(np.mean(np.sum((method_probs - method_onehot) ** 2, axis=1))),
    }
    for j, meth in enumerate(METHOD_MARKETS):
        actual = method_true == meth
        key = meth.lower()
        out[f"actual_{key}_share"] = float(actual.mean())
        out[f"pred_{key}_share"] = float((method_pred == meth).mean())
        out[f"mean_prob_{key}"] = float(method_probs[:, j].mean())
        out[f"recall_{key}"] = float(np.mean(method_pred[actual] == meth)) if actual.any() else np.nan
    return out


@dataclass
class HistoricalMethodBundle:
    logistic: object
    gradient_boosting: object
    outcome_rate_encoders: dict[str, PastOnlyRateEncoder]
    winner_rate_encoder: PastOnlyRateEncoder
    feature_columns: list[str]
    history_end: pd.Timestamp
    calibration_temperature: float = 1.0

    def predict_joint_probabilities(self, frame: pd.DataFrame) -> pd.DataFrame:
        x = _method_rate_encode_transform(frame.copy(), self.outcome_rate_encoders, self.winner_rate_encoder)
        x = add_interaction_features(x)
        for c in self.feature_columns:
            if c not in x:
                x[c] = np.nan
        p = _ensemble(x, self.logistic, self.gradient_boosting, self.feature_columns)
        p = _temperature_transform(p, self.calibration_temperature)
        return pd.DataFrame(p, columns=list(METHOD_STATES), index=frame.index)

    def market_probabilities(self, frame: pd.DataFrame) -> pd.DataFrame:
        joint = self.predict_joint_probabilities(frame)
        out = joint.copy()
        out["WIN"] = joint[[c for c in METHOD_STATES if c.startswith("WIN_")]].sum(axis=1)
        out["LOSS"] = 1.0 - out["WIN"]
        for meth in METHOD_MARKETS:
            out[f"FIGHT_{meth}"] = joint[f"WIN_{meth}"] + joint[f"LOSS_{meth}"]
        return out


def fit_historical_method_model(frame: pd.DataFrame) -> tuple[HistoricalMethodBundle, dict[str, dict[str, float]]]:
    work = add_method_targets(frame)
    work = work[work["method_target"].notna()].copy()
    train, val, test = chronological_split(work)

    train_e, train_outcome_enc, train_winner_enc = _method_rate_encode_fit(train)
    val_e = _method_rate_encode_transform(val, train_outcome_enc, train_winner_enc)
    train_e, val_e = add_interaction_features(train_e), add_interaction_features(val_e)
    logistic_eval, gb_eval, features_eval, _, _ = _fit_estimators(train_e)
    raw_val = _ensemble(val_e, logistic_eval, gb_eval, features_eval)
    mask_val = _canonical(val_e)
    temperature, cal_report = _fit_temperature(val_e.loc[mask_val, "method_target"], raw_val[mask_val], list(METHOD_STATES))
    calibrated_val = _temperature_transform(raw_val, temperature)

    test_outcome_enc, test_winner_enc = _fit_rate_encoders(pd.concat([train, val], ignore_index=True))
    test_e = add_interaction_features(_method_rate_encode_transform(test, test_outcome_enc, test_winner_enc))
    raw_test = _ensemble(test_e, logistic_eval, gb_eval, features_eval)
    calibrated_test = _temperature_transform(raw_test, temperature)

    metrics = {
        "validation": evaluate_method_probabilities(val_e, calibrated_val),
        "test": evaluate_method_probabilities(test_e, calibrated_test),
        "raw_validation": evaluate_method_probabilities(val_e, raw_val),
        "raw_test": evaluate_method_probabilities(test_e, raw_test),
        "calibration": cal_report,
        "uniform_six_state_log_loss": float(np.log(6.0)),
    }

    full_e, final_outcome_enc, final_winner_enc = _method_rate_encode_fit(work)
    full_e = add_interaction_features(full_e)
    logistic, gb, features, _, _ = _fit_estimators(full_e)
    bundle = HistoricalMethodBundle(
        logistic=logistic,
        gradient_boosting=gb,
        outcome_rate_encoders=final_outcome_enc,
        winner_rate_encoder=final_winner_enc,
        feature_columns=features,
        history_end=pd.to_datetime(work["date"]).max(),
        calibration_temperature=temperature,
    )
    return bundle, metrics


def method_conditional_rate_tables(frame: pd.DataFrame, min_n: int = 30) -> pd.DataFrame:
    work = add_method_targets(frame)
    parts: list[pd.DataFrame] = []
    for state in METHOD_STATES:
        target = f"target_{state.lower()}"
        for table in (
            all_conditional_rate_tables(work, target=target, min_n=min_n),
            categorical_conditional_rate_tables(work, target=target, min_n=min_n),
            interaction_conditional_rate_tables(work, target=target, min_n=max(40, min_n)),
        ):
            if len(table):
                z = table.copy()
                z["outcome"] = state
                z = z.rename(columns={"wins": "events", "win_rate": "event_rate"})
                parts.append(z)
    if not parts:
        return pd.DataFrame()
    cols = ["outcome", "split", "bucket", "n", "events", "event_rate", "ci_low", "ci_high", "description"]
    return pd.concat(parts, ignore_index=True)[cols]
