import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import pytest

from wshlx_ufc.historical_data import build_prefight_perspective_rows


def synthetic_sources():
    events = pd.DataFrame({
        "EVENT": ["UFC Test 1", "UFC Test 2"],
        "URL": ["x", "y"],
        "DATE": ["January 01, 2020", "February 01, 2020"],
        "LOCATION": ["Las Vegas, Nevada, USA", "Las Vegas, Nevada, USA"],
    })
    results = pd.DataFrame({
        "EVENT": ["UFC Test 1", "UFC Test 2"],
        "BOUT": ["Alpha vs. Bravo", "Alpha vs. Bravo"],
        "OUTCOME": ["W/L", "L/W"],
        "WEIGHTCLASS": ["Lightweight Bout", "Lightweight Bout"],
        "METHOD": ["Decision - Unanimous", "KO/TKO"],
        "ROUND": [3, 2],
        "TIME": ["5:00", "1:30"],
        "TIME_FORMAT": ["3 Rnd (5-5)", "3 Rnd (5-5)"],
    })
    stats = pd.DataFrame({
        "EVENT": ["UFC Test 1", "UFC Test 1", "UFC Test 2", "UFC Test 2"],
        "BOUT": ["Alpha vs. Bravo"] * 4,
        "ROUND": ["Round 1"] * 4,
        "FIGHTER": ["Alpha", "Bravo", "Alpha", "Bravo"],
        "KD": [1, 0, 0, 1],
        "SIG.STR.": ["20 of 40", "10 of 30", "12 of 30", "18 of 35"],
        "TOTAL STR.": ["25 of 45", "15 of 35", "15 of 35", "21 of 40"],
        "TD": ["1 of 2", "0 of 1", "0 of 2", "1 of 1"],
        "SUB ATT": [0, 0, 0, 0],
        "CTRL": ["1:00", "0:30", "0:20", "1:10"],
    })
    fighters = pd.DataFrame({
        "FIGHTER": ["Alpha", "Bravo"],
        "HEIGHT": ["6' 0\"", "5' 10\""],
        "WEIGHT": [155, 155],
        "REACH": ["75\"", "71\""],
        "STANCE": ["Orthodox", "Southpaw"],
        "DOB": ["January 01, 1990", "January 01, 1985"],
    })
    return events, results, stats, fighters


def test_prefight_reconstruction_is_as_of_and_mirrored():
    frame = build_prefight_perspective_rows(*synthetic_sources())
    assert len(frame) == 4
    first = frame[frame.event == "UFC Test 1"]
    assert set(first.win) == {0, 1}
    assert set(first.ufc_fights) == {0.0}

    second_a = frame[(frame.event == "UFC Test 2") & (frame.fighter == "Alpha")].iloc[0]
    assert second_a.ufc_fights == 1
    assert second_a.ufc_win_pct == pytest.approx(1.0)
    assert second_a.reach_diff == pytest.approx(4.0)
    assert second_a.age_diff < 0
    assert second_a.rematch_number == 1
    assert second_a.previous_meeting_result == "win"


def test_current_fight_stats_do_not_enter_current_prefight_row():
    frame = build_prefight_perspective_rows(*synthetic_sources())
    first_a = frame[(frame.event == "UFC Test 1") & (frame.fighter == "Alpha")].iloc[0]
    assert pd.isna(first_a.sig_accuracy)
    second_a = frame[(frame.event == "UFC Test 2") & (frame.fighter == "Alpha")].iloc[0]
    assert second_a.sig_accuracy == pytest.approx(0.5)
