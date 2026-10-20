import numpy as np
import pandas as pd

from wshlx_ufc.contextual_ensemble import (
    fit_contextual_binary_blend,
    fit_contextual_grouped_binary_blend,
    fit_contextual_multiclass_blend,
    grouped_binary_log_loss,
    rowwise_binary_logit_pool,
    rowwise_multiclass_log_pool,
)


def test_rowwise_binary_pool_endpoints():
    current = np.array([0.8, 0.2])
    historical = np.array([0.6, 0.4])
    assert np.allclose(rowwise_binary_logit_pool(current, historical, np.ones(2)), current)
    assert np.allclose(rowwise_binary_logit_pool(current, historical, np.zeros(2)), historical)


def test_rowwise_multiclass_pool_is_coherent():
    current = np.array([[0.7, 0.2, 0.1], [0.2, 0.3, 0.5]])
    historical = np.array([[0.5, 0.3, 0.2], [0.4, 0.2, 0.4]])
    out = rowwise_multiclass_log_pool(current, historical, np.array([0.7, 0.3]))
    assert out.shape == current.shape
    assert np.allclose(out.sum(axis=1), 1.0)
    assert np.all(out > 0)


def test_contextual_binary_fit_returns_valid_weights():
    frame = pd.DataFrame({"disagreement": [0.1, 0.2, 0.3, 0.4] * 8, "sparse": [0, 1, 0, 1] * 8})
    y = np.array([1, 0, 1, 0] * 8)
    current = np.array([0.7, 0.3, 0.65, 0.35] * 8)
    historical = np.array([0.6, 0.4, 0.55, 0.45] * 8)
    fit = fit_contextual_binary_blend(
        frame, y, current, historical, ["disagreement", "sparse"], l2=10.0
    )
    weights = fit.weights(frame)
    assert len(weights) == len(frame)
    assert np.all((weights > 0) & (weights < 1))
    assert fit.n == len(frame)


def test_contextual_multiclass_fit_returns_valid_weights():
    frame = pd.DataFrame({"js": np.linspace(0.01, 0.3, 30), "sparse": [0, 1, 0] * 10})
    y = np.arange(30) % 3
    current = np.tile(np.array([[0.6, 0.25, 0.15]]), (30, 1))
    historical = np.tile(np.array([[0.4, 0.35, 0.25]]), (30, 1))
    fit = fit_contextual_multiclass_blend(frame, y, current, historical, ["js", "sparse"], l2=10.0)
    w = fit.weights(frame)
    pooled = rowwise_multiclass_log_pool(current, historical, w)
    assert np.allclose(pooled.sum(axis=1), 1.0)
    assert np.all((w > 0) & (w < 1))


def test_grouped_binary_loss_equalizes_groups():
    y = np.array([1, 1, 0])
    p = np.array([0.9, 0.9, 0.1])
    groups = np.array(["a", "a", "b"])
    loss = grouped_binary_log_loss(y, p, groups)
    expected = (-np.log(0.9) + -np.log(0.9)) / 2
    assert np.isclose(loss, expected)


def test_contextual_grouped_binary_fit_runs():
    n_fights = 12
    rows = []
    y = []
    current = []
    historical = []
    groups = []
    for i in range(n_fights):
        for market in range(3):
            rows.append({"disagreement": 0.05 + 0.02 * market, "horizon": market / 2})
            outcome = int((i + market) % 2 == 0)
            y.append(outcome)
            current.append(0.65 if outcome else 0.35)
            historical.append(0.58 if outcome else 0.42)
            groups.append(f"f{i}")
    frame = pd.DataFrame(rows)
    fit = fit_contextual_grouped_binary_blend(
        frame,
        y,
        current,
        historical,
        groups,
        ["disagreement", "horizon"],
        l2=10.0,
    )
    assert fit.n == len(frame)
    assert np.all((fit.weights(frame) > 0) & (fit.weights(frame) < 1))
