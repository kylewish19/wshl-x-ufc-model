"""Ensure unpicked UFC Oct31 event cannot become a fabricated official prediction."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/ufcvegas123_2026-10-31"
CLEAN = ROOT / "data/results/clean_ufc_139_2026-10-24.csv"
OBSERVED = ROOT / "data/results/ufcvegas123_2026-10-31_retrospective_only.csv"
FIGHTER_STATS = ROOT / "data/results/ufcvegas123_2026-10-31_fighter_stats.csv"
REPORT = ROOT / "reports/ufcvegas123_2026-10-31/retrospective/integration_report.json"
OFFLINE = ROOT / "reports/ufcvegas123_2026-10-31/retrospective/heldout_conditional_actual_winner_method.csv"


def csvrows(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_oct31_source_complete_and_rounds_not_fabricated():
    a = json.loads((RAW / "availability.json").read_text())
    assert a["upstream_commit"] == "3d4886d222e72be2c5336b49b98b721f5103d949"
    assert a["full_card_stats_available"] is True
    assert a["unique_result_bouts"] == a["unique_detail_bouts"] == a["unique_stat_bouts"] == 12
    assert a["fighter_round_stat_rows"] == a["expected_round_stat_rows_from_results"] == 64
    assert a["integrity_issues"] == a["round_key_duplicates"] == a["missing_stat_bouts"] == []
    assert a["result_methods"] == {"KO": 5, "SUB": 1, "DEC": 6}
    stat = csvrows(RAW / "ufcvegas123_fight_stats.csv")
    assert len(stat) == 64
    keys = [(r["BOUT"], r["ROUND"], r["FIGHTER"]) for r in stat]
    assert len(keys) == len(set(keys))
    assert len(set(x["BOUT"] for x in stat)) == 12
    doctor = [x for x in a["official_results"] if x["special_stoppage"]]
    assert len(doctor) == 2
    assert all(x["method_class"] == "KO" for x in doctor)
    # UFC event and UFCStats list R2 1:25; some UFC recap headers mistakenly say R3.
    armb = [x for x in a["official_results"] if "Kropschot" in x["bout"]]
    assert len(armb) == 1 and armb[0]["round"] == 2 and armb[0]["time"] == "1:25"


def test_oct31_cannot_count_as_official_bets_or_predictions():
    old = csvrows(CLEAN)
    unpicked = csvrows(OBSERVED)
    assert len(old) == 139
    assert len(unpicked) == 12
    assert not any(r["event_date"] >= "2026-10-31" for r in old)
    assert len({(r["event_date"], r["fight"]) for r in unpicked}) == 12
    for r in unpicked:
        assert r["event_date"] == "2026-10-31"
        assert r["has_frozen_stage_a"] == r["has_frozen_stage_b"] == "False"
        assert int(r["official_winner_prediction_count"]) == 0
        assert int(r["official_method_prediction_count"]) == 0
        assert r["evaluation_role"] == "RETROSPECTIVE_TRAINING_AND_RESEARCH_ONLY"
    classes = Counter(r["method"] for r in unpicked)
    assert classes == {"KO": 5, "DEC": 6, "SUB": 1}


def test_retrospective_fighter_stats_rows_have_full_both_sides():
    rows = csvrows(FIGHTER_STATS)
    assert len(rows) == 24
    groups = Counter(x["fight"] for x in rows)
    assert len(groups) == 12 and set(groups.values()) == {2}
    assert all(x["official_stats_fight_url"].startswith("http://ufcstats.com/fight-details/") for x in rows)


def test_future_shadow_artifacts_and_offline_conditional_model_gated():
    a = json.loads(REPORT.read_text(encoding="utf-8"))
    assert a["training"]["historical_performance_fights"] == 8793
    assert a["training"]["locked_feedback_unchanged"] == 139
    assert a["training"]["data_cutoff_exclusive"] == "2026-11-01"
    assert a["integrity"]["doctor_stoppages"] == 2
    assert a["integrity"]["fighter_bout_aggregates"] == 24
    assert a["integrity"]["aggregate_notice"].endswith(
        "NOT 151 officially predicted or graded fights."
    )
    assert not a["governance"]["official_prediction_record"]
    assert not a["governance"]["official_stage_a"]
    assert not a["governance"]["official_stage_b"]
    assert a["governance"]["official_profit_loss"] is None
    assert a["governance"]["clean139_ledger_untouched"] is True
    assert a["governance"]["model_promoted"] is False
    assert len(a["shadow_artifacts"]) == 5
    m = a["offline_conditional_method_reconstruction"]
    assert m["training_feedback_rows"] == 139
    assert m["training_max_date_before_test"].startswith("2026-10-24")
    assert m["status"] == "OFFLINE_RETROSPECTIVE_METHOD_CONDITIONAL_ON_OBSERVED_WINNER"
    assert all(m[name]["n"] == 12 for name in ("baseline", "calibrated", "submission_access"))
    preds = csvrows(OFFLINE)
    assert len(preds) == 12
    for r in preds:
        assert r["evaluation_role"] == m["status"]
        for key in ("base", "cal", "access"):
            probs = [float(r[f"{key}_{c}"]) for c in ("KO", "SUB", "DEC")]
            assert min(probs) >= 0
            assert max(probs) <= 1
            assert abs(sum(probs) - 1) < 1e-8
