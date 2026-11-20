import numpy as np

from wshlx_ufc.unified_ensemble import (
    binary_logit_pool,
    blend_hazards,
    fit_binary_blend,
    fit_grouped_binary_blend,
    fit_multiclass_blend,
    markets_from_hazards,
    multiclass_log_pool,
    resample_hazards,
)


def test_binary_pool_endpoints_and_midpoint():
    current = np.array([0.8, 0.3])
    historical = np.array([0.6, 0.4])
    assert np.allclose(binary_logit_pool(current, historical, 1.0), current)
    assert np.allclose(binary_logit_pool(current, historical, 0.0), historical)
    mid = binary_logit_pool(current, historical, 0.5)
    assert np.all((mid > np.minimum(current, historical)) & (mid < np.maximum(current, historical)))


def test_binary_weight_fit_prefers_better_component():
    y = np.array([1, 1, 0, 0, 1, 0])
    current = np.array([.82, .74, .22, .18, .68, .30])
    historical = np.array([.55, .52, .48, .45, .53, .49])
    fit = fit_binary_blend(y, current, historical)
    assert fit.weight_current >= 0.75
    assert fit.loss <= min(fit.current_loss, fit.historical_loss) + 1e-12


def test_grouped_binary_fit_counts_fights_not_markets():
    # Fight f1 has many duplicated current-friendly markets; f2 has one strong
    # historical-friendly market. Group balancing prevents raw market count from
    # letting f1 dominate simply because it exposes more props.
    y = np.array([1, 1, 1, 1, 1, 0])
    current = np.array([.8, .8, .8, .8, .8, .7])
    historical = np.array([.6, .6, .6, .6, .6, .1])
    groups = np.array(["f1", "f1", "f1", "f1", "f1", "f2"])
    raw = fit_binary_blend(y, current, historical)
    grouped = fit_grouped_binary_blend(y, current, historical, groups)
    assert grouped.n == 2
    assert grouped.weight_current < raw.weight_current


def test_multiclass_pool_is_coherent_and_fit_can_choose_history():
    y = np.array([0, 1, 2, 0])
    current = np.array([
        [.40, .35, .25], [.45, .30, .25], [.40, .35, .25], [.38, .37, .25]
    ])
    historical = np.array([
        [.75, .15, .10], [.15, .70, .15], [.15, .15, .70], [.65, .20, .15]
    ])
    pooled = multiclass_log_pool(current, historical, .4)
    assert np.allclose(pooled.sum(axis=1), 1.0)
    fit = fit_multiclass_blend(y, current, historical)
    assert fit.weight_current <= .25
    assert fit.loss <= min(fit.current_loss, fit.historical_loss) + 1e-12


def test_hazard_resampling_preserves_survival():
    h60 = np.array([.19, .36])
    h30 = resample_hazards(h60, 60, 30)
    assert len(h30) == 4
    s60 = np.prod(1.0 - h60)
    s30 = np.prod(1.0 - h30)
    assert np.isclose(s60, s30)


def test_blended_hazards_create_coherent_markets():
    current = np.full(30, .02)
    historical = np.full(30, .03)
    blended = blend_hazards(current, historical, .6)
    markets = markets_from_hazards(blended, 900, bin_seconds=30)
    assert 0 <= markets["GTD_YES"] <= markets["OVER_2.5"] <= markets["OVER_1.5"] <= 1
    assert markets["ROUND_2_STARTS_YES"] >= markets["ROUND_3_STARTS_YES"]
    total = sum(markets[f"FINISH_ROUND_{r}"] for r in (1, 2, 3)) + markets["GTD_YES"]
    assert np.isclose(total, 1.0)
