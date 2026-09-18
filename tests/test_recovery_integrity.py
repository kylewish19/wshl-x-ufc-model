import hashlib
import json
from pathlib import Path


MANIFEST = Path("artifacts/v027_reconstruction/manifest.json")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def test_recovery_manifest_locks_current_population_and_status():
    m = json.loads(MANIFEST.read_text())

    assert m["status"] == "V0.27_RECONSTRUCTION_TRAINED_SHADOW"
    assert m["cutoff_exclusive"] == "2026-09-13T00:00:00+00:00"
    assert m["population"]["decisive_fights"] == 8707
    assert m["population"]["winner_training_rows"] == 8707
    assert m["population"]["conditional_method_training_rows"] == 8707
    assert m["population"]["timing_training_rows"] == 8707
    assert m["population"]["clean_feedback_rows"] == 64
    assert m["population"]["last_event_date"].startswith("2026-09-12")

    delta = m["post_august_feature_delta"]
    assert delta["winner_rows"] == 77
    assert delta["method_rows"] == 77
    assert delta["first_event_date"].startswith("2026-08-08")
    assert delta["last_event_date"].startswith("2026-09-12")

    assert m["promotion"]["authorized"] is False
    assert m["promotion"]["role"] == "shadow/reconstruction"
    assert m["promotion"]["prospective_fights_since_rebuild"] == 0


def test_v027_reconstruction_is_not_silently_promotable():
    m = json.loads(MANIFEST.read_text())
    bench = m["method_clean64_reconstruction_benchmark"]

    baseline = bench["chronology_baseline"]
    candidate = bench["chronology_candidate"]

    assert bench["chronology_evaluation_fights"] == 52
    assert candidate["accuracy"] == baseline["accuracy"]
    assert candidate["multiclass_brier"] > baseline["multiclass_brier"]
    assert candidate["log_loss"] > baseline["log_loss"]


def test_generated_artifact_hashes_match_manifest():
    m = json.loads(MANIFEST.read_text())
    paths = {
        "winner": Path("artifacts/v027_reconstruction/winner_reconstruction.joblib"),
        "method_baseline": Path("artifacts/v027_reconstruction/method_baseline_reconstruction.joblib"),
        "method_residual_v027": Path("artifacts/v027_reconstruction/method_residual_v027.joblib"),
        "timing": Path("artifacts/v027_reconstruction/timing_reconstruction.joblib"),
    }
    for key, path in paths.items():
        assert _sha256(path) == m["artifact_sha256"][key]


def test_post_august_feature_hashes_match_manifest():
    m = json.loads(MANIFEST.read_text())
    delta = m["post_august_feature_delta"]

    winner_path = Path(
        "data/features/reconstructed/prefight_winner_features_2026-08-02_to_cutoff.csv"
    )
    method_path = Path(
        "data/features/reconstructed/prefight_method_features_2026-08-02_to_cutoff.csv"
    )

    assert _sha256(winner_path) == delta["winner_delta_sha256"]
    assert _sha256(method_path) == delta["method_delta_sha256"]
