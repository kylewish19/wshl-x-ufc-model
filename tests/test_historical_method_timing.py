import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from wshlx_ufc.historical_method_model import _pair_cohere, _temperature_transform
from wshlx_ufc.historical_outcomes import METHOD_STATES, add_method_targets, add_timing_targets
from wshlx_ufc.historical_timing_model import _weight_context, symmetric_timing_frame


def _pair_frame():
    common = {
        "fight_id": "f1", "date": pd.Timestamp("2025-01-01"), "event": "UFC Test",
        "weight_class": "Light Heavyweight Bout", "scheduled_rounds": 3,
        "title_fight": 0, "rematch_number": 0,
    }
    return pd.DataFrame([
        {**common, "fighter": "Alpha", "opponent": "Beta", "win": 1, "fight_method": "KO_TKO",
         "age": 28.0, "opp_age": 34.0, "reach": 76.0, "opp_reach": 72.0,
         "ufc_fights": 5.0, "opp_ufc_fights": 8.0, "finish_win_rate": .8, "opp_finish_win_rate": .5,
         "ko_loss_rate": .1, "opp_ko_loss_rate": .4, "sub_loss_rate": .1, "opp_sub_loss_rate": .1,
         "kd_per15": .8, "opp_kd_per15": .2, "sapm": 2.5, "opp_sapm": 4.0,
         "sub_att_per15": .1, "opp_sub_att_per15": .3, "layoff_days": 120., "opp_layoff_days": 220.},
        {**common, "fighter": "Beta", "opponent": "Alpha", "win": 0, "fight_method": "KO_TKO",
         "age": 34.0, "opp_age": 28.0, "reach": 72.0, "opp_reach": 76.0,
         "ufc_fights": 8.0, "opp_ufc_fights": 5.0, "finish_win_rate": .5, "opp_finish_win_rate": .8,
         "ko_loss_rate": .4, "opp_ko_loss_rate": .1, "sub_loss_rate": .1, "opp_sub_loss_rate": .1,
         "kd_per15": .2, "opp_kd_per15": .8, "sapm": 4.0, "opp_sapm": 2.5,
         "sub_att_per15": .3, "opp_sub_att_per15": .1, "layoff_days": 220., "opp_layoff_days": 120.},
    ])


def test_method_targets_are_fighter_specific():
    out = add_method_targets(_pair_frame())
    assert out.loc[0, "method_target"] == "WIN_KO_TKO"
    assert out.loc[1, "method_target"] == "LOSS_KO_TKO"


def test_pair_coherence_and_temperature_preserve_event_ordering():
    classes = list(METHOD_STATES)
    raw = np.array([
        [.35, .08, .17, .16, .06, .18],
        [.15, .07, .18, .38, .07, .15],
    ])
    coherent = _pair_cohere(_pair_frame(), raw, classes)
    assert np.allclose(coherent.sum(axis=1), 1.0)
    for meth in ("KO_TKO", "SUB", "DEC"):
        wi, li = classes.index(f"WIN_{meth}"), classes.index(f"LOSS_{meth}")
        assert np.isclose(coherent[0, wi], coherent[1, li])
        assert np.isclose(coherent[0, li], coherent[1, wi])
    calibrated = _temperature_transform(coherent, 1.8)
    assert np.array_equal(np.argmax(coherent, axis=1), np.argmax(calibrated, axis=1))
    assert np.allclose(calibrated.sum(axis=1), 1.0)


def test_timing_features_are_orientation_invariant_and_light_heavyweight_is_205():
    frame = _pair_frame()
    a = symmetric_timing_frame(frame)
    b = symmetric_timing_frame(frame.iloc[::-1].reset_index(drop=True))
    numeric = [c for c in a.columns if c.startswith(("pair_", "gap_abs_"))]
    assert np.allclose(a[numeric].to_numpy(dtype=float), b[numeric].to_numpy(dtype=float), equal_nan=True)
    pounds, women = _weight_context(pd.Series(["Light Heavyweight Bout", "Women's Flyweight Bout", "Heavyweight Bout"]))
    assert pounds.tolist() == [205.0, 125.0, 265.0]
    assert women.tolist() == [0.0, 1.0, 0.0]


def test_timing_targets_treat_decisions_as_censored_and_finishes_as_events():
    frame = pd.concat([_pair_frame(), _pair_frame().assign(fight_id="f2", fighter=["Gamma", "Delta"], opponent=["Delta", "Gamma"], fight_method="DEC", win=[1, 0])], ignore_index=True)
    results = pd.DataFrame([
        {"EVENT": "UFC Test", "BOUT": "Alpha vs. Beta", "WEIGHTCLASS": "Light Heavyweight Bout", "METHOD": "KO/TKO", "ROUND": 2, "TIME": "1:00", "TIME_FORMAT": "3 Rnd (5-5-5)"},
        {"EVENT": "UFC Test", "BOUT": "Gamma vs. Delta", "WEIGHTCLASS": "Lightweight Bout", "METHOD": "Decision - Unanimous", "ROUND": 3, "TIME": "5:00", "TIME_FORMAT": "3 Rnd (5-5-5)"},
    ])
    out = add_timing_targets(frame, results)
    ko = out[out.fight_id.eq("f1")].iloc[0]
    dec = out[out.fight_id.eq("f2")].iloc[0]
    assert ko.finish_observed == 1.0 and ko.finish_seconds == 360.0
    assert dec.finish_observed == 0.0 and dec.finish_seconds == 900.0
    assert dec.goes_distance == 1.0
