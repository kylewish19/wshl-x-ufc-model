import numpy as np

from wshlx_ufc.method_calibration import MethodInterceptCalibrator


def test_intercept_calibrator_moves_systematic_finish_underprediction():
    actual = np.array(["KO", "KO", "SUB", "KO", "DEC", "KO", "DEC", "SUB"])
    ko = np.full(8, 0.25)
    sub = np.full(8, 0.10)
    dec = np.full(8, 0.65)
    m = MethodInterceptCalibrator(ridge=0.5).fit(
        actual_method=actual,
        baseline_ko=ko,
        baseline_sub=sub,
        baseline_dec=dec,
    )
    p = m.predict_proba(baseline_ko=ko, baseline_sub=sub, baseline_dec=dec)
    assert p[["KO", "SUB", "DEC"]].sum(axis=1).round(10).eq(1.0).all()
    assert p["DEC"].mean() < 0.65


def test_calibrator_is_low_capacity_and_finite():
    actual = np.array(["KO", "SUB", "DEC", "KO", "DEC", "SUB"])
    ko = np.array([.5, .2, .1, .6, .2, .2])
    sub = np.array([.1, .5, .1, .1, .1, .5])
    dec = 1 - ko - sub
    m = MethodInterceptCalibrator().fit(
        actual_method=actual,
        baseline_ko=ko,
        baseline_sub=sub,
        baseline_dec=dec,
    )
    assert np.isfinite(m.finish_offset_)
    assert np.isfinite(m.sub_offset_)
