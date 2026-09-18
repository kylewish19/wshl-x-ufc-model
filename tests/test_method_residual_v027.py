import numpy as np
import pandas as pd

from wshlx_ufc.method_residual_v027 import (
    V027MethodResidualChallenger,
    V027_FEATURES,
)


def _frame(n=12):
    rng = np.random.default_rng(8)
    data = {c: rng.normal(size=n) for c in V027_FEATURES}
    data["winner_round3_retention"][0] = np.nan
    return pd.DataFrame(data)


def test_v027_residual_outputs_coherent_probabilities():
    x = _frame(12)
    methods = np.array(["KO", "SUB", "DEC", "KO", "DEC", "SUB"] * 2)
    p_ko = np.full(12, 0.30)
    p_sub = np.full(12, 0.20)
    p_dec = np.full(12, 0.50)

    model = V027MethodResidualChallenger(ridge=10.0).fit(
        x,
        actual_method=methods,
        baseline_ko=p_ko,
        baseline_sub=p_sub,
        baseline_dec=p_dec,
    )
    out = model.predict_proba(
        x,
        baseline_ko=p_ko,
        baseline_sub=p_sub,
        baseline_dec=p_dec,
    )

    assert list(out.columns) == ["KO", "SUB", "DEC"]
    assert np.all(out.to_numpy() >= 0)
    assert np.allclose(out.sum(axis=1), 1.0)


def test_v027_requires_all_frozen_features():
    x = _frame(12).drop(columns=[V027_FEATURES[0]])
    methods = np.array(["KO", "SUB", "DEC", "KO", "DEC", "SUB"] * 2)
    p_ko = np.full(12, 0.30)
    p_sub = np.full(12, 0.20)
    p_dec = np.full(12, 0.50)

    try:
        V027MethodResidualChallenger().fit(
            x,
            actual_method=methods,
            baseline_ko=p_ko,
            baseline_sub=p_sub,
            baseline_dec=p_dec,
        )
    except ValueError as exc:
        assert "missing v0.27 features" in str(exc)
    else:
        raise AssertionError("missing feature should have been rejected")
