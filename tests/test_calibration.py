import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score

from wshlx_ufc.calibration import TemperatureCalibrator, fit_temperature_calibrator


def test_temperature_preserves_order_auc_and_winner_threshold():
    y = np.array([0, 0, 1, 1, 0, 1, 1, 0])
    p = np.array([0.08, 0.30, 0.55, 0.92, 0.40, 0.70, 0.62, 0.22])
    q = TemperatureCalibrator(2.0).transform(p)

    assert np.array_equal(np.argsort(p), np.argsort(q))
    assert np.isclose(roc_auc_score(y, p), roc_auc_score(y, q))
    assert accuracy_score(y, p >= 0.5) == accuracy_score(y, q >= 0.5)
    assert np.all((q > 0) & (q < 1))


def test_temperature_is_symmetric_for_mirrored_fight_probabilities():
    p = np.array([0.81, 0.19])
    q = TemperatureCalibrator(1.8).transform(p)
    assert np.isclose(q.sum(), 1.0)
    assert q[0] > 0.5


def test_fit_temperature_reduces_overconfidence_without_auc_loss():
    # Predictions rank every example correctly but are intentionally too extreme.
    y = np.array([0, 0, 0, 1, 1, 1, 0, 1, 0, 1])
    p = np.array([0.001, 0.02, 0.08, 0.92, 0.98, 0.999, 0.45, 0.55, 0.35, 0.65])
    calibrator, report = fit_temperature_calibrator(y, p)
    q = calibrator.transform(p)

    assert calibrator.temperature > 0
    assert report["calibrated_log_loss"] <= report["raw_log_loss"] + 1e-12
    assert np.isclose(report["raw_roc_auc"], report["calibrated_roc_auc"])
    assert np.isclose(roc_auc_score(y, p), roc_auc_score(y, q))
