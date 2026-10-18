import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import pytest

from wshlx_ufc.historical_rates import (
    DEFAULT_SPLITS,
    PastOnlyRateEncoder,
    conditional_rate_table,
    comprehensive_conditional_rate_tables,
)


def test_age_bucket_and_wilson_table():
    spec = next(s for s in DEFAULT_SPLITS if s.name == "age_gap")
    df = pd.DataFrame({"age_diff": [-11, -11, -7, 7], "win": [1, 0, 1, 0]})
    t = conditional_rate_table(df, spec)
    r = t[t.bucket == "younger_10+"].iloc[0]
    assert r.n == 2
    assert r.win_rate == pytest.approx(0.5)
    assert 0 <= r.ci_low <= r.win_rate <= r.ci_high <= 1


def test_past_only_encoder_does_not_leak_mirrored_fight_result():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-02-01", "2020-02-01"]),
        "fight_id": ["f1", "f1", "f2", "f2"],
        "age_diff": [-6, 6, -6, 6],
        "win": [1, 0, 0, 1],
    })
    enc = PastOnlyRateEncoder(specs=[next(s for s in DEFAULT_SPLITS if s.name == "age_gap")], alpha=0)
    out = enc.fit_transform(df)
    f1 = out[out.fight_id == "f1"]
    assert list(f1.hist_age_gap_wr) == [0.5, 0.5]
    f2 = out[out.fight_id == "f2"]
    assert f2.hist_age_gap_n.min() == 1


def test_comprehensive_tables_include_categorical_splits():
    df = pd.DataFrame({
        "age_diff": [-6, 6] * 20,
        "win": [1, 0] * 20,
        "debut_status": ["veteran_vs_debutant", "debutant_vs_veteran"] * 20,
    })
    t = comprehensive_conditional_rate_tables(df, min_n=1)
    assert "age_gap" in set(t.split)
    assert "debut_status" in set(t.split)
