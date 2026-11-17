"""No model is trained; audit whether recent data is even usable for one."""
from wshlx_ufc.historical_training_eligibility import audit_eligibility


def test_modern_historical_bouts_are_coherent_and_have_pre_event_features():
    r=audit_eligibility()
    m=r["modern_2021_2026"]
    assert r["full_archive_before_cutoff_bouts"]==8871
    assert r["full_archive_quality"]["complete_stat_bouts"]==8850
    assert m["total_bouts"]==m["training_bouts_2021_2025"]+m["retrospective_test_bouts_2026"]
    assert m["total_bouts"]==m["decisive_bouts"]+m["draws"]
    assert 1000<m["training_bouts_2021_2025"]<5000
    assert 100<m["retrospective_test_bouts_2026"]<1000
    assert 0<m["missing_either_stat_row"]<=r["full_archive_before_cutoff_bouts"]-8850
    assert m["any_ufc_debutant"]>0
    assert m["any_fighter_prior_ufc_bouts_under_five"]>m["any_ufc_debutant"]
    assert r["source_grade"].startswith("PINNED_THIRD_PARTY")
    assert r["labels_are_postfight_and_features_are_pre_event"]
    assert r["no_future_opponent_rating_or_result_features"]
    assert r["source_stats_missing_not_zero_filled"]
    assert r["direct_getups_not_observed"]
    assert r["retrospective_2026_already_seen_during_research_not_pristine"]
    assert r["new_model_trained_or_promoted"] is False
    assert r["no_stage_a_b_or_fanduel_quotations_modified"]


def test_year_by_year_source_bouts_partition_consistently():
    r=audit_eligibility()
    byyear=r["all_years"]
    assert sum(v["bouts"] for v in byyear.values())==8871
    for year,obj in byyear.items():
        assert obj["bouts"]==obj["decisive"]+obj["draws"]
        assert obj["bouts"]==obj["both_current_fight_stat_rows_available"]+obj["either_current_stat_missing"]
        assert obj["event_count"]>=1
        assert sum(obj["methods"].values())==obj["bouts"]
        assert 0<=obj["prior_evidence_any_debutant"]<=obj["bouts"]
        assert 0<=obj["prior_evidence_any_under_five_ufc_bouts"]<=obj["bouts"]
    assert 2021<=min(int(k) for k in byyear if int(k)>=2021)
    recent=[x for y,x in byyear.items() if 2021<=int(y)<=2026]
    assert sum(x["bouts"] for x in recent)==r["modern_2021_2026"]["total_bouts"]
