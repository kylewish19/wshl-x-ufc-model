import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from wshlx_ufc.historical_model import chronological_split, fit_historical_winner_model


def make_frame(n_fights=80):
    rows = []
    for i in range(n_fights):
        date = pd.Timestamp("2018-01-01") + pd.Timedelta(days=i * 7)
        younger_wins = i % 5 != 0
        for side in (0, 1):
            age_diff = -6.0 if side == 0 else 6.0
            win = int(younger_wins if side == 0 else not younger_wins)
            rows.append({
                "fight_id": f"f{i}", "date": date, "event": f"e{i}",
                "fighter": f"a{i}" if side == 0 else f"b{i}",
                "opponent": f"b{i}" if side == 0 else f"a{i}",
                "win": win,
                "age_diff": age_diff,
                "reach_diff": 2.0 if side == 0 else -2.0,
                "ufc_fights_diff": float((i % 7) - 3) * (1 if side == 0 else -1),
                "ufc_win_pct_diff": 0.1 if side == 0 else -0.1,
                "recent5_win_pct_diff": 0.2 if side == 0 else -0.2,
                "layoff_days_diff": -20.0 if side == 0 else 20.0,
                "sig_str_diff_diff": 0.8 if side == 0 else -0.8,
                "sig_accuracy_diff": 0.04 if side == 0 else -0.04,
                "sig_defense_diff": 0.03 if side == 0 else -0.03,
                "td_per15_diff": 0.5 if side == 0 else -0.5,
                "td_accuracy_diff": 0.05 if side == 0 else -0.05,
                "td_defense_diff": 0.05 if side == 0 else -0.05,
                "ctrl_sec_per_min_diff": 5.0 if side == 0 else -5.0,
                "kd_per15_diff": 0.2 if side == 0 else -0.2,
                "finish_win_rate_diff": 0.1 if side == 0 else -0.1,
                "ko_loss_rate_diff": -0.05 if side == 0 else 0.05,
                "stance_matchup": "Orthodox_vs_Southpaw" if side == 0 else "Southpaw_vs_Orthodox",
                "debut_status": "both_veterans",
                "fight_method": "KO_TKO" if i % 2 else "DEC",
            })
    return pd.DataFrame(rows)


def test_chronological_split_keeps_fights_together():
    df = make_frame(20)
    train, val, test = chronological_split(df)
    assert set(train.fight_id).isdisjoint(val.fight_id)
    assert set(train.fight_id).isdisjoint(test.fight_id)
    assert set(val.fight_id).isdisjoint(test.fight_id)


def test_model_fits_scores_refits_and_normalizes_matchup_probabilities():
    df = make_frame()
    bundle, metrics = fit_historical_winner_model(df)
    assert "fight_method" not in bundle.feature_columns
    assert 0 <= metrics["test"]["accuracy"] <= 1
    assert 0 <= metrics["test"]["brier"] <= 1
    assert metrics["test"]["n_fights"] > 0
    assert bundle.history_end == pd.to_datetime(df["date"]).max()

    future = df.tail(2).copy()
    future["fight_id"] = "future-fight"
    future["date"] = bundle.history_end + pd.Timedelta(days=7)
    probs = bundle.predict_proba(future)
    assert np.isclose(probs.sum(), 1.0)
    assert np.all((probs > 0) & (probs < 1))
