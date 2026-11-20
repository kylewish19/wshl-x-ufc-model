"""November 7 UFCStats data integrity and future-only model test gates.

Tests check post-fight data never rewrite frozen Stage A/Stage B/153 grades,
that all striking/grappling stat rows exist without inferred zero filling,
and that model selection uses genuine previous-date validation, not
backfitted November 7 wagering claims.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/raw/ufcvegas124_2026-11-07"
REPORT=ROOT/"reports/ufcvegas124_2026-11-07"
ART=ROOT/"artifacts/ufcvegas124_post_event_shadow"
CLEAN=ROOT/"data/results/clean_ufc_153_2026-11-07.csv"


def read(path):
    return json.loads(path.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_pinned_68_real_fighter_round_rows_not_synthetic():
    availability=read(RAW/"availability.json")
    assert availability["status"]=="UFCSTATS_ARCHIVED_SCRAPE_2026_11_08_FULL_CARD_VERIFIED"
    assert availability["full_card_stats_available"] is True
    assert availability["upstream_commit"]=="c742842f29466758fedc3906dbad28d6d320a8da"
    assert availability["unique_result_bouts"]==availability["unique_detail_bouts"]==availability["unique_stat_bouts"]==14
    assert availability["fighter_round_stat_rows"]==availability["expected_fighter_round_stat_rows"]==68
    assert not availability["validation_issues"]
    assert not availability["fighter_round_key_duplicates"]
    assert availability["observed_finish_methods"]=={"KO":6,"DEC":7,"SUB":1}
    assert availability["frozen_stage_a_sha256"]==sha(ROOT/"data/locks/ufcvegas124_2026-11-07/stage_a_final_selection.json")
    for filename,receipt in availability["source_csv_files"].items():
        f=RAW/filename
        assert f.is_file() and f.stat().st_size==receipt["bytes"] and sha(f)==receipt["sha256"]
    df=pd.read_csv(RAW/"ufcvegas124_fight_stats.csv")
    assert len(df)==68
    assert df["BOUT"].nunique()==14
    assert len(df[["BOUT","FIGHTER","ROUND"]].drop_duplicates())==68
    assert {"KD","SIG.STR.","TD","SUB.ATT","CTRL"}.issubset(df)
    assert df[["KD","SIG.STR.","TD","SUB.ATT","CTRL"]].notna().all().all()
    assert sum(df["ROUND"].eq("Round 1"))==28
    assert sum(df["ROUND"].eq("Round 2"))==22
    assert sum(df["ROUND"].eq("Round 3"))==18


def test_postevent_training_shadow_really_contains_verified_28_fighter_stats():
    m=read(REPORT/"full_stats/integration_report.json")
    assert m["status"]=="NOV7_FULL_STATS_INTEGRATED_FOR_POST_EVENT_FUTURE_ONLY_SHADOW_TRAINING"
    assert m["post_event_training_bouts"]==8807
    assert m["training_winner_rows"]==m["training_method_rows"]==m["training_timing_rows"]==8807
    assert m["new_full_stat_round_rows"]==68 and m["new_full_stat_fighter_rows"]==28
    assert m["new_causal_frozen_pred_rows"]==14
    assert m["causal_method_clean_feedback_rows"]==153
    assert m["post_event_last_date"].startswith("2026-11-07")
    assert m["frozen_stage_a_sha256"]==sha(ROOT/"data/locks/ufcvegas124_2026-11-07/stage_a_final_selection.json")
    assert m["graded_14_sha256"]==sha(ROOT/"data/results/ufcvegas124_2026-11-07_all_models_grading.json")
    assert m["clean_153_sha256"]==sha(CLEAN)
    assert m["governance"]["official_champion_v027_unmodified"] is True
    assert m["governance"]["model_promotion"] is False
    assert m["governance"]["data_stats_for_Nov7_are_postfight_only"] is True
    for obj in m["model_paths"].values():
        p=ROOT/obj["path"]
        assert p.is_file()
        assert sha(p)==obj["sha256"]
    stats=pd.read_csv(ROOT/"data/results/ufcvegas124_2026-11-07_fighter_full_stats.csv")
    assert len(stats)==28
    assert len(stats[["fight","fighter"]].drop_duplicates())==28
    assert stats["event_date"].eq("2026-11-07").all()
    assert stats["post_event_data_training_only"].all()
    assert stats[["sig_landed","sig_attempted","td_landed","td_attempted",
                  "kd_for","sub_att","ctrl_seconds"]].notna().all().all()
    assert np.all(stats["sig_landed"]<=stats["sig_attempted"])
    assert np.all(stats["td_landed"]<=stats["td_attempted"])


def test_no_same_card_lookahead_and_clean_prior_139_oof_unchanged():
    m=read(REPORT/"full_stats/integration_report.json")
    prior=pd.read_csv(ROOT/"reports/ufc333_2026-10-24/full_stats/clean139_causal_method_inputs.csv")
    full=pd.read_csv(REPORT/"full_stats/clean153_causal_method_inputs.csv")
    assert len(prior)==139 and len(full)==153
    assert list(prior.columns)==list(full.columns)
    pd.testing.assert_frame_equal(prior,full.iloc[:139].reset_index(drop=True),
                                  check_dtype=False,check_exact=False,rtol=1e-12,atol=1e-12)
    delta=full.iloc[139:]
    assert len(delta)==14
    assert delta["event_date"].astype(str).str.startswith("2026-11-07").all()
    assert np.allclose(delta[["base_KO","base_SUB","base_DEC"]].sum(axis=1),1,atol=1e-8)
    assert m["clean139_oof_untouched"] is True
    assert m["original_clean_139_oof_sha256"]==sha(ROOT/"reports/ufc333_2026-10-24/full_stats/clean139_causal_method_inputs.csv")
    assert len(pd.read_csv(CLEAN))==153
    assert len(pd.read_csv(CLEAN).query('event_date == "2026-11-07"'))==14


def test_historical_shadow_retrained_after_results_but_pre_nov7_pick_untouched():
    m=read(REPORT/"historical_shadow_refit.json")
    assert m["trained_through"]=="2026-11-07"
    assert m["eligible_for_predictions_starting"]=="2026-11-08"
    assert m["nov7_fights"]==14 and m["nov7_perspectives"]==28
    assert m["training_completed_fights"]==8832
    assert m["training_mirrored_fighter_perspectives"]==17664
    assert m["model"]["feature_count"]>10
    assert not any(re.search(r"(?:^win$|^method$|^fight_|^target_|^post_)",v.lower())
                   for v in m["model"]["feature_columns"])
    assert m["governance"]["original_historical_nov7_shadow_fitted_through_2026_10_17_unchanged"]
    assert m["governance"]["champion_v027_unchanged"]
    assert not m["governance"]["promotion_approved"]
    path=ROOT/m["model"]["fit_artifact_path"]
    assert sha(path)==m["model"]["fit_artifact_sha256"]
    for name in ("validation","test"):
        assert m["time_split_evaluation"][name]["n_fights"]>1000
        assert m["time_split_evaluation"][name]["log_loss"]>0
        assert 0<=m["time_split_evaluation"][name]["accuracy"]<=1


def test_longer_historical_oof_prevents_single_card_challenger_promotion():
    audit=read(REPORT/"challenger_generalization_audit.json")
    assert audit["older_winner_112_retrospective_comparison"]["current"]["n"]==112
    assert audit["older_winner_112_retrospective_comparison"]["historical"]["brier"]>audit["older_winner_112_retrospective_comparison"]["current"]["brier"]
    assert audit["older_winner_61_strict_walk_forward"]["current"]["n"]==61
    assert audit["older_method_88_retrospective_comparison"]["current"]["joint_accuracy"]>audit["older_method_88_retrospective_comparison"]["historical"]["joint_accuracy"]
    assert audit["prospective_paired_exact_method_mcnemar"]["unified"]["exact_p_value"]==pytest.approx(.375)
    assert not audit["candidate_promotion_gate"]["champion_promoted"]
    assert audit["candidate_promotion_gate"]["minimum_prospective_fights"]==300


def test_method_calibration_chronological_no_new_unvalidated_algorithm_promotion():
    s=read(REPORT/"full_stats/chronological_method_calibration_benchmark.json")
    assert s["method_feedback_rows"]==153
    assert s["total_chronologically_scored_bouts"]==116
    assert len(s["folds"])>=5
    assert s["metrics"]["historical_development_pre_nov7"]["cal"]["n"]==102
    assert s["metrics"]["nov7_chronological_reconstruction_not_official_frozen_picks"]["cal"]["n"]==14
    for fold in s["folds"]:
        assert fold["train_max_date"]<fold["date"]
    older=s["metrics"]["historical_development_pre_nov7"]
    assert older["cal"]["log_loss"]<older["base"]["log_loss"]
    assert older["cal"]["brier"]<older["base"]["brier"]
    assert older["v035_finish_access"]["log_loss"]>older["cal"]["log_loss"]
    assert older["v027_residual"]["brier"]>older["cal"]["brier"]
    assert not any(v["promoted"] for v in s["candidate_gates"].values())
    assert s["governance"]["original_frozen_nov7_unified_8of14_unchanged"] is True
    assert s["governance"]["no_current_event_training_in_its_own_fold"] is True
