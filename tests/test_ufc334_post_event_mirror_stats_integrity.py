"""Post-event mirrored UFC334 totals are quarantined, reconciled and leak-proof."""
import csv
import json

import pytest

from wshlx_ufc.post_event_stats_audit import (
    MANIFEST, TOTALS, ROUNDS, audit_mirrored_ufc334_stats,
    postevent_feature_cutoff_guard,
)


def test_all_13_fights_26_totals_72_rounds_reconcile():
    result = audit_mirrored_ufc334_stats()
    assert result["total_fights"] == 13
    assert result["fighter_totals"] == 26
    assert result["fighter_rounds"] == 72
    assert result["fully_reconciled_core_stats"]
    assert not result["primary_ufcstats_access"]
    assert not result["training_authorized"]
    assert not result["stage_a_predictions_changed"]
    assert result["source_status"] == "PROVISIONAL_MIRROR_CROSSCHECKED"


def test_no_post_event_features_in_pre_event_predictions():
    with pytest.raises(ValueError, match="Post-event stats feature leakage"):
        postevent_feature_cutoff_guard(
            source_as_of="2026-11-16", prediction_date="2026-11-14")
    with pytest.raises(ValueError, match="Post-event stats feature leakage"):
        postevent_feature_cutoff_guard(
            source_as_of="2026-11-14", prediction_date="2026-11-14")
    postevent_feature_cutoff_guard(
        source_as_of="2026-11-14", prediction_date="2026-11-21")


def test_cannot_promote_mirror_data_by_changing_manifest_only(tmp_path):
    manifest = json.loads(MANIFEST.read_text())
    manifest["allow_training"] = True
    alternate = tmp_path / "manifest.json"
    alternate.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="post-event-only quarantine"):
        audit_mirrored_ufc334_stats(manifest_path=alternate)


def test_bad_round_sum_fails_before_training(tmp_path):
    with ROUNDS.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    headers = list(rows[0])
    rows[0]["sig_str_landed"] = str(int(rows[0]["sig_str_landed"]) + 2)
    path = tmp_path / "tampered_rounds.csv"
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="Round sums do not match"):
        audit_mirrored_ufc334_stats(rounds_path=path)


def test_bad_target_breakdown_fails(tmp_path):
    with TOTALS.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    headers = list(rows[0])
    rows[0]["head_sig_landed"] = str(int(rows[0]["head_sig_landed"]) + 1)
    path = tmp_path / "bad_fighter_totals.csv"
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="Striking target/position split"):
        audit_mirrored_ufc334_stats(totals_path=path)


def test_bad_event_date_fails(tmp_path):
    manifest = json.loads(MANIFEST.read_text())
    manifest["event_date"] = "2026-11-07"
    path = tmp_path / "other_event.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Mismatched events"):
        audit_mirrored_ufc334_stats(manifest_path=path)
