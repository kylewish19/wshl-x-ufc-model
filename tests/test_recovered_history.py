from pathlib import Path

import pandas as pd


def test_recovered_clean_ufc_ledger_matches_handoff_totals():
    path = Path("data/results/clean_ufc_64_2026-09-05.csv")
    frame = pd.read_csv(path)

    assert len(frame) == 64
    assert int(frame["winner_correct"].sum()) == 36
    assert int(frame["method_correct"].sum()) == 28
    assert int(frame["joint_correct"].sum()) == 15

    assert frame["displayed_method"].value_counts().to_dict() == {
        "DEC": 37,
        "KO": 25,
        "SUB": 2,
    }
    assert frame["actual_method"].value_counts().to_dict() == {
        "KO": 31,
        "DEC": 21,
        "SUB": 12,
    }


def test_each_clean_fight_is_unique():
    frame = pd.read_csv("data/results/clean_ufc_64_2026-09-05.csv")
    assert not frame.duplicated(["event_date", "fight"]).any()
