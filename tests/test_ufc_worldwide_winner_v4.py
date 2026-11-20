"""Worldwide history, missingness, method types and outcome guard tests."""
import importlib.util
import math
from pathlib import Path
import numpy as np
import pytest

spec=importlib.util.spec_from_file_location(
 "wshlx_worldwinner_v4_tests",
 Path(__file__).resolve().parents[1]/"tools/benchmark_worldwide_mma_winner_v4.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def good():
    return {
      "known_nonUFC_decisive_prior":5,
      "known_nonUFC_wins_prior":3,
      "known_nonUFC_losses_prior":2,
      "known_nonUFC_recent3_decisive":3,
      "known_nonUFC_recent3_wins":2,
      "known_nonUFC_recent5_decisive":5,
      "known_nonUFC_recent5_wins":3,
      "known_nonUFC_KO_wins_prior":1,
      "known_nonUFC_SUB_wins_prior":1,
      "known_nonUFC_DEC_wins_prior":1,
      "known_nonUFC_KO_losses_prior":1,
      "known_nonUFC_SUB_losses_prior":1,
      "known_nonUFC_DEC_losses_prior":0,
      "known_nonUFC_bouts_prior_365d":1,
      "known_pro_mma_bouts_any_org_prior":7,
      "known_nonUFC_method_recorded":5,
    }

def test_new_features_are_preserved_not_guessed_and_stable_asof():
    x=m.features(good(),verified=True)
    assert len(m.EXTRA)==16 and m.FULL==73 and m.BASE==57
    assert x.shape==(16,) and np.isfinite(x).all()
    assert x[0]==pytest.approx(math.log1p(5))
    assert x[1]==pytest.approx(5/9)
    assert x[2]==pytest.approx(3/5)
    assert x[14]==1. and x[15]==0.
    missing=m.features(None,verified=False)
    assert missing[14]==0. and missing[15]==1.
    assert missing[1]==.5
    assert missing[0]==0.
    assert not np.array_equal(x,missing)

def test_no_impossible_prior_lose_win_method_counts():
    d=good()
    d["known_nonUFC_decisive_prior"]=4
    with pytest.raises(ValueError,match="inconsistency"):
        m.features(d,verified=True)
    d=good()
    d["known_nonUFC_method_recorded"]=6
    with pytest.raises(ValueError,match="coverage"):
        m.features(d,verified=True)

def test_study_has_same_exact_fighter_method_primary_target_and_no_odds():
    assert m.HEADS==(
        "winner_v3_logit57","winner_v4_logit73",
        "winner_v3_boost57","winner_v4_boost73")
    assert all(z in m.FOLDS[-1][0] for z in ("2026",))
