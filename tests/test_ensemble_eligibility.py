import pandas as pd

from wshlx_ufc.ensemble_eligibility import (
    filter_lock_payload,
    pair_key,
    unsupported_pairs_by_date,
)


def test_nonstandard_outcome_is_excluded_without_touching_normal_fights():
    frame = pd.DataFrame([
        {"date": "2026-09-26", "fighter": "Mahammadali Osmanli", "opponent": "Ilimbek Akylbek", "fight_method": "OTHER"},
        {"date": "2026-09-26", "fighter": "Ilimbek Akylbek", "opponent": "Mehemmed-Eli Osmanli", "fight_method": "OTHER"},
        {"date": "2026-09-26", "fighter": "Alpha", "opponent": "Beta", "fight_method": "DEC"},
    ])
    unsupported = unsupported_pairs_by_date(frame)
    assert pair_key("Mahammadali Osmanli", "Ilimbek Akylbek") in unsupported["2026-09-26"]
    assert pair_key("Mehemmed-Eli Osmanli", "Ilimbek Akylbek") in unsupported["2026-09-26"]

    payload = {"fights": [
        {"a": "Mahammadali Osmanli", "b": "Ilimbek Akylbek"},
        {"a": "Alpha", "b": "Beta"},
    ]}
    filtered, excluded = filter_lock_payload(payload, card_date="2026-09-26", unsupported=unsupported)
    assert filtered["fights"] == [{"a": "Alpha", "b": "Beta"}]
    assert excluded == ["Mahammadali Osmanli vs Ilimbek Akylbek"]
    assert len(payload["fights"]) == 2  # frozen input is not mutated


def test_supported_methods_do_not_create_exclusions():
    frame = pd.DataFrame([
        {"date": "2026-10-03", "fighter": "A", "opponent": "B", "fight_method": "KO_TKO"},
        {"date": "2026-10-03", "fighter": "B", "opponent": "A", "fight_method": "KO_TKO"},
        {"date": "2026-10-03", "fighter": "C", "opponent": "D", "fight_method": "SUB"},
        {"date": "2026-10-03", "fighter": "E", "opponent": "F", "fight_method": "DEC"},
    ])
    assert unsupported_pairs_by_date(frame) == {}


def test_accented_and_ascii_fighter_names_share_identity():
    assert pair_key("Ernesta Kareckaitė", "Melissa Gatto") == pair_key(
        "Ernesta Kareckaite", "Melissa Gatto"
    )
