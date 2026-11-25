"""Export the historical challengers' untouched chronological test predictions.

These helpers intentionally reproduce the evaluation path rather than scoring with the
final all-history refit bundles.  They are used by the unified stacker so meta-weights
never learn from historical predictions that were trained on the fight being graded.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .calibration import fit_temperature_calibrator
from .historical_method_model import (
    _canonical,
    _ensemble as method_ensemble,
    _fit_estimators as fit_method_estimators,
    _fit_rate_encoders,
    _fit_temperature,
    _method_rate_encode_fit,
    _method_rate_encode_transform,
    _temperature_transform,
)
from .historical_model import (
    _fit_estimators as fit_winner_estimators,
    _pair_normalize,
    chronological_split,
)
from .historical_outcomes import METHOD_STATES, add_method_targets, add_timing_targets
from .historical_rates import PastOnlyRateEncoder, add_interaction_features
from .historical_timing_model import (
    HistoricalTimingBundle,
    MODEL_START_DATE,
    _encode_fit,
    _encode_transform,
    _fit_encoders,
    _fit_hazard,
    symmetric_timing_frame,
)


def winner_test_predictions(frame: pd.DataFrame) -> pd.DataFrame:
    train, val, test = chronological_split(frame)
    enc_train = PastOnlyRateEncoder()
    train_e = add_interaction_features(enc_train.fit_transform(train))
    val_e = add_interaction_features(enc_train.transform(val))
    enc_test = PastOnlyRateEncoder().fit(pd.concat([train, val], ignore_index=True))
    test_e = add_interaction_features(enc_test.transform(test))
    logistic, gb, features, _, _ = fit_winner_estimators(train_e)

    def ens(x: pd.DataFrame) -> np.ndarray:
        p1 = logistic.predict_proba(x[features])[:, 1]
        p2 = gb.predict_proba(x[features])[:, 1]
        return _pair_normalize(x, 0.5 * p1 + 0.5 * p2)

    raw_val = ens(val_e)
    calibrator, _ = fit_temperature_calibrator(val_e["win"], raw_val)
    p = calibrator.transform(ens(test_e))
    cols = [c for c in ("fight_id", "date", "event", "fighter", "opponent", "win") if c in test_e]
    out = test_e[cols].copy()
    out["historical_p_win"] = p
    return out.reset_index(drop=True)


def method_test_predictions(frame: pd.DataFrame) -> pd.DataFrame:
    work = add_method_targets(frame)
    work = work[work["method_target"].notna()].copy()
    train, val, test = chronological_split(work)

    train_e, train_outcome_enc, train_winner_enc = _method_rate_encode_fit(train)
    val_e = _method_rate_encode_transform(val, train_outcome_enc, train_winner_enc)
    train_e, val_e = add_interaction_features(train_e), add_interaction_features(val_e)
    logistic, gb, features, _, _ = fit_method_estimators(train_e)
    raw_val = method_ensemble(val_e, logistic, gb, features)
    mask = _canonical(val_e)
    temperature, _ = _fit_temperature(
        val_e.loc[mask, "method_target"], raw_val[mask], list(METHOD_STATES)
    )

    test_outcome_enc, test_winner_enc = _fit_rate_encoders(pd.concat([train, val], ignore_index=True))
    test_e = add_interaction_features(
        _method_rate_encode_transform(test, test_outcome_enc, test_winner_enc)
    )
    p = _temperature_transform(method_ensemble(test_e, logistic, gb, features), temperature)
    cols = [c for c in ("fight_id", "date", "event", "fighter", "opponent", "method_target", "fight_method", "win") if c in test_e]
    out = test_e[cols].copy()
    for i, state in enumerate(METHOD_STATES):
        out[f"historical_{state}"] = p[:, i]
    return out.reset_index(drop=True)


def timing_test_predictions(perspective_frame: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    targeted = add_timing_targets(perspective_frame, results)
    work = symmetric_timing_frame(targeted)
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work[work["date"] >= MODEL_START_DATE].copy()
    work = work.dropna(subset=["finish_seconds", "scheduled_seconds", "finish_observed"]).copy()
    work = work[work["scheduled_seconds"].isin([900.0, 1500.0])].copy()
    train, val, test = chronological_split(work)

    train_e, train_enc = _encode_fit(train)
    val_e = _encode_transform(val, train_enc)
    hazard, features = _fit_hazard(train_e)
    expanded_val, y_val = hazard._expanded_rows(
        val_e[features], val_e["finish_seconds"].to_numpy(),
        val_e["scheduled_seconds"].to_numpy(), val_e["finish_observed"].to_numpy(),
    )
    raw_h = hazard.pipeline.predict_proba(expanded_val)[:, 1]
    calibrator, _ = fit_temperature_calibrator(y_val, raw_h)

    test_encoders = _fit_encoders(pd.concat([train, val], ignore_index=True))
    test_e = _encode_transform(test, test_encoders)
    bundle = HistoricalTimingBundle(
        hazard_model=hazard,
        rate_encoders=test_encoders,
        feature_columns=features,
        history_end=pd.to_datetime(test["date"]).max(),
        hazard_temperature=calibrator.temperature,
    )
    rows = []
    for _, row in test_e.iterrows():
        scheduled = int(row["scheduled_seconds"])
        markets = bundle.market_probabilities_from_encoded(row, scheduled)
        rows.append({
            "fight_id": row["fight_id"],
            "date": row["date"],
            "scheduled_seconds": scheduled,
            "finish_seconds": float(row["finish_seconds"]),
            "finish_observed": int(row["finish_observed"]),
            "goes_distance": int(row["goes_distance"]),
            **{f"historical_{k}": float(v) for k, v in markets.items()},
        })
    return pd.DataFrame(rows)
