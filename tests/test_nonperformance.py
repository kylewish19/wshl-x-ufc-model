import pandas as pd
from wshlx_ufc.nonperformance import (
    apply_activity_recency,
    is_known_nonperformance_bout,
    is_nonperformance_method,
)


def test_known_injury_stoppage_is_nonperformance():
    assert is_known_nonperformance_bout(
        "UFC 323: Dvalishvili vs. Yan 2",
        "Alexandre Pantoja vs. Joshua Van",
    )


def test_dq_and_nc_are_nonperformance_methods():
    assert is_nonperformance_method("Disqualification (illegal knee)")
    assert is_nonperformance_method("DQ")
    assert is_nonperformance_method("No Contest")
    assert not is_nonperformance_method("Decision - Unanimous")


def test_activity_recency_can_override_performance_layoff():
    summary={"days_since_last":400.0}
    asof=pd.Timestamp("2026-10-10",tz="UTC")
    activity={"mahammadaliosmanli":pd.Timestamp("2026-09-26",tz="UTC")}
    apply_activity_recency(summary,"Mahammadali Osmanli",asof,activity)
    assert summary["days_since_last"] == 14.0
