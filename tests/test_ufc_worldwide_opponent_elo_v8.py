"""World MMA chronological opponent Elo, same-day freeze and anti-leakage."""
from collections import defaultdict
import math
import numpy as np
import pytest
from wshlx_ufc.worldwide_opponent_elo_v8 import (
    day_updates,state,score,K_FACTOR,INITIAL,FIELDS
)

def cases():
    return [
        {"date":"2026-11-05","fight_id":101,"a":1,"b":2,"p_a_win":1.},
        {"date":"2026-11-05","fight_id":102,"a":1,"b":3,"p_a_win":0.},
    ]

def test_worldwide_elo_same_day_matches_frozen_previous_fighter_ratings():
    s=defaultdict(state)
    d=cases()
    day_updates(d,s)
    # For athlete1 two same-day bouts use unchanged initial rating:
    # one win +12 and one loss -12 => zero net change.
    assert s[1]["elo"]==pytest.approx(1500.)
    assert s[2]["elo"]==pytest.approx(1488.)
    assert s[3]["elo"]==pytest.approx(1512.)
    assert s[1]["n"]==2
    assert s[1]["wins"]==1
    assert s[1]["opponents"]==pytest.approx(3000.)
    # Opponent-average backoff is unbiased for two new same-quality bouts.
    v=score(s[1])
    assert v[0]==pytest.approx(0)
    assert v[1]==pytest.approx(math.log1p(2))
    assert v[2]==pytest.approx(0)
    assert v[3]==pytest.approx(0)
    assert len(v)==len(FIELDS)==4

def test_knockouts_not_fabricated_as_elo_or_assigned_two_ids():
    s=defaultdict(state)
    with pytest.raises(ValueError,match="duplicate"):
        day_updates([{"fight_id":1,"a":1,"b":1,"p_a_win":1.,
                      "date":"2026-01-01"}],s)
    with pytest.raises(ValueError,match="duplicate"):
        day_updates([{"fight_id":1,"a":1,"b":2,"p_a_win":1.},
                     {"fight_id":1,"a":3,"b":4,"p_a_win":0.}],s)

def test_draw_has_zero_movement_with_equal_prior_ratings_and_zero_win_count():
    s=defaultdict(state)
    day_updates([{"fight_id":1,"a":10,"b":20,"p_a_win":.5}],s)
    assert s[10]["elo"]==pytest.approx(1500)
    assert s[20]["elo"]==pytest.approx(1500)
    assert s[10]["n"]==s[20]["n"]==1
    assert s[10]["wins"]==0
    assert s[20]["wins"]==0
