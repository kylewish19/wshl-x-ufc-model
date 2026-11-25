"""Historical rebuild guards: same-day freeze, provenance, labels and scoring."""
from datetime import date
import pytest

from wshlx_ufc.prefight_finish_resistance import build_from_records
from wshlx_ufc.historical_feature_matrix import build_matrix, bout_id, bout_key, load_matrix
from wshlx_ufc.historical_baselines import benchmark_fixed_baselines


def _rec(when, a, b, outcome, method):
    return {
        "date": date.fromisoformat(when), "event": "UFC Test " + when,
        "a": a, "b": b, "result": outcome, "method": method,
        "elapsed_seconds": 435, "stats_a": None, "stats_b": None,
    }


def test_asof_matrix_same_date_freeze_labels_and_missingness():
    r = [
        _rec("2025-06-01", "Alice", "Bob", ("W", "L"), "KO_TKO"),
        _rec("2025-06-01", "Alice", "Charlie", ("D", "D"), "DEC"),
        _rec("2026-02-01", "Alice", "Darla", ("L", "W"), "SUB"),
    ]
    snaps, _ = build_from_records(r, as_of_exclusive="2026-11-14")
    features, labels = build_matrix(r, snaps)
    assert len(features) == len(labels) == 3
    assert features[0]["a_prior_ufc_bouts"] == 0
    assert features[1]["a_prior_ufc_bouts"] == 0  # same day has no leakage
    assert features[2]["a_prior_ufc_bouts"] == 2
    assert features[2]["a_ufc_prior_bouts"] == 2
    assert features[2]["a_ufc_prior_wins"] == 1
    assert features[0]["a_own_knockdowns_per15"] is None
    assert features[2]["a_own_knockdowns_per15"] is None  # missing stat rows not zero
    assert all("label" not in k and "winner" not in k for f in features for k in f)
    assert labels[0]["label_a_win"] == 1
    assert labels[1]["result_status"] == "DRAW"
    assert labels[1]["label_method"] is None  # source DRAW may encode DEC technique
    assert labels[2]["label_a_win"] == 0
    assert features[2]["data_partition"] == "retrospective_2026"


def test_matrix_rejects_inconsistent_or_missing_snapshot():
    r = [_rec("2025-06-01", "Alice", "Bob", ("W", "L"), "KO_TKO")]
    snaps, _ = build_from_records(r, as_of_exclusive="2026-11-14")
    with pytest.raises(ValueError, match="lack pre-event"):
        build_matrix(r, [])
    with pytest.raises(ValueError, match="Duplicate"):
        build_matrix(r, snaps + snaps)
    with pytest.raises(ValueError, match="Duplicate historical"):
        build_matrix(r + r, snaps)
    assert bout_id(bout_key("2025-06-01", "UFC Test", "Alice", "Bob")) == bout_id(bout_key("2025-06-01", "UFC Test", "Bob", "Alice"))


def test_baselines_do_not_treat_a_draw_as_training_or_test_label():
    r = [
        _rec("2021-06-01", "Alice", "Bob", ("W", "L"), "SUB"),
        _rec("2023-06-01", "Charlie", "David", ("D", "D"), "DEC"),
        _rec("2025-06-01", "Erin", "Frank", ("L", "W"), "KO_TKO"),
        _rec("2026-04-01", "Alice", "Erin", ("W", "L"), "DEC"),
        _rec("2026-04-02", "Frank", "Bob", ("D", "D"), "DEC"),
    ]
    snapshots, _ = build_from_records(r, as_of_exclusive="2026-11-14")
    features, labels = build_matrix(r, snapshots)
    report = benchmark_fixed_baselines(features, labels, bootstrap_samples=50)
    assert report["training_decisive_bouts"] == 2
    assert report["test_decisive_bouts"] == 1
    assert report["baseline_scores"]["coinflip"]["winner_brier"] == .25
    assert len(report["paired_event_bootstrap_elo_minus_coinflip_winner_brier_95pct"]) == 2
    assert report["no_challenger_trained"] and report["no_model_promotion"]


def test_actual_archive_history_count_and_separated_labels():
    features, labels, report = load_matrix()
    assert len(features) == len(labels) == 8871
    assert report["training_2021_2025"] == 2544
    assert report["retrospective_2026"] == 492
    assert report["draws_in_modern_window"] == 21
    assert len(set(f["bout_id"] for f in features)) == len(features)
    assert all(f["event_date"] == f["feature_as_of_exclusive"] for f in features)
    assert all("label" not in f for f in features)
    assert sum(l["result_status"] == "DRAW" and l["event_date"] >= "2021-01-01" for l in labels) == 21
