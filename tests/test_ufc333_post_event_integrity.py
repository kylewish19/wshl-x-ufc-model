"""Permanent regression gates for UFC333 post-event data and causal grading."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/ufc333_2026-10-24"
GRADE = ROOT / "data/grades/ufc333_2026-10-24_stage_a_grade.json"
FREEZE = ROOT / "data/locks/ufc333_2026-10-24/stage_a_final_selection.json"
CLEAN_OLD = ROOT / "data/results/clean_ufc_125_2026-10-17.csv"
CLEAN_NEW = ROOT / "data/results/clean_ufc_139_2026-10-24.csv"
WALK = ROOT / "reports/ufc333_2026-10-24/full_stats/method_walk_forward_comparison.json"
PRED = ROOT / "reports/ufc333_2026-10-24/full_stats/method_walk_forward_predictions.csv"


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_canonical_full_round_stats_complete_and_pinned():
    a = json.loads((RAW / "availability.json").read_text())
    assert a["upstream_commit"] == "5d6622ffc349a1d0c6dd25158d737a96b889a3e0"
    assert a["full_card_stats_available"] is True
    assert a["unique_result_bouts"] == a["unique_detail_bouts"] == a["unique_stat_bouts"] == 14
    assert a["fighter_round_stat_rows"] == a["expected_round_stat_rows_from_locked_outcomes"] == 62
    assert a["unexpected_pairs"] == []
    assert a["duplicate_fighter_round_keys"] == []
    source = read_csv(RAW / "ufc333_fight_stats.csv")
    assert len(source) == 62
    keys = [(r["BOUT"], r["ROUND"], r["FIGHTER"]) for r in source]
    assert len(keys) == len(set(keys))
    bouts = Counter(r["BOUT"] for r in source)
    assert len(bouts) == 14
    assert all(n > 0 and n % 2 == 0 for n in bouts.values())


def test_clean139_appended_without_rewriting_previous_history_or_freeze():
    old, new = read_csv(CLEAN_OLD), read_csv(CLEAN_NEW)
    assert len(old) == 125 and len(new) == 139
    assert new[:125] == old
    assert len({(r["event_date"], r["fight"]) for r in new}) == 139
    grade, frozen = json.loads(GRADE.read_text()), json.loads(FREEZE.read_text())
    assert len(grade["bouts"]) == len(frozen["fights"]) == 14
    for append, fight, g in zip(new[125:], frozen["fights"], grade["bouts"]):
        expected_method = fight["method"]["top_method_current"].replace("KO/TKO", "KO")
        assert append["event_date"] == "2026-10-24"
        assert append["fight"] == g["fight"]
        assert append["locked_pick"] == fight["official_reference_pick"]
        assert append["actual_winner"] == g["actual"]["winner"]
        assert append["displayed_method"] == expected_method
        assert append["actual_method"] == g["actual"]["method_class"]
        assert int(append["winner_correct"]) == int(append["locked_pick"] == append["actual_winner"])
        assert int(append["method_correct"]) == int(append["displayed_method"] == append["actual_method"])
        assert int(append["joint_correct"]) == (
            int(append["winner_correct"]) * int(append["method_correct"])
        )


def test_walkforward_folds_never_train_on_target_date_and_forecasts_normalize():
    report = json.loads(WALK.read_text())
    full = read_csv(CLEAN_NEW)
    for fold in report["folds"]:
        day = fold["test_date"][:10]
        before = sum(r["event_date"] < day for r in full)
        target = sum(r["event_date"] == day for r in full)
        assert fold["train_n"] == before
        assert fold["test_n"] == target
        assert before >= 24
    preds = read_csv(PRED)
    assert len([r for r in preds if r["event_date"] == "2026-10-24"]) == 14
    for r in preds:
        assert r["used_training_before_date_only"] == "True"
        for prefix in ("base", "cal", "access"):
            values = [float(r[f"{prefix}_{m}"]) for m in ("KO", "SUB", "DEC")]
            assert all(0 <= v <= 1 for v in values)
            assert abs(sum(values) - 1) < 1e-8


def test_post_event_shadow_governance_not_promoted():
    manifest = json.loads(
        (ROOT / "artifacts/ufc333_post_event_shadow/manifest.json").read_text()
    )
    assert manifest["population"]["feedback_clean_after"] == 139
    assert manifest["population"]["fights_in_causal_training"] >= 8781
    gov = manifest["governance"]
    assert gov["reference_changed"] is False
    assert gov["challenger_promoted"] is False
    assert gov["ufc333_stage_a_recomputed"] is False
    assert gov["future_shadow_trained"] is True
    assert manifest["method_displayed_across_versions"]["prior125"]["submission_recall"] == {
        "correct": 2, "actual_submissions": 22
    }
