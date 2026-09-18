from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from wshlx_ufc.locks import freeze_payload, verify_lock, write_lock_once
from wshlx_ufc.timing import DiscreteTimeHazardModel, rounds_to_seconds


def test_round_threshold_seconds():
    assert rounds_to_seconds(0.5) == 150
    assert rounds_to_seconds(1.5) == 450
    assert rounds_to_seconds(2.5) == 750


def test_lock_is_hashed_and_immutable(tmp_path: Path):
    lock = freeze_payload({"event": "test", "predictions": [{"p": 0.6}]})
    path = tmp_path / "lock.json"
    write_lock_once(path, lock)
    assert verify_lock(path)
    with pytest.raises(FileExistsError):
        write_lock_once(path, lock)


def test_hazard_market_probabilities_are_coherent():
    x = pd.DataFrame(
        {
            "pace_diff": [0.1, -0.2, 0.4, -0.5, 0.2, 0.0],
            "grapple_diff": [0.4, 0.1, -0.2, 0.3, -0.4, 0.2],
        }
    )
    durations = [120, 900, 420, 700, 250, 900]
    scheduled = [900] * 6
    observed = [1, 0, 1, 1, 1, 0]

    model = DiscreteTimeHazardModel(bin_seconds=30, c=0.1).fit(
        x, durations, scheduled, observed
    )
    markets = model.market_probabilities(x.iloc[0], 900)

    assert 0 <= markets["GTD_YES"] <= 1
    assert markets["OVER_0.5"] >= markets["OVER_1.5"] >= markets["OVER_2.5"]
    assert np.isclose(markets["GTD_YES"] + markets["GTD_NO"], 1.0)
