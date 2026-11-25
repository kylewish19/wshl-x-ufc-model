"""Prior-only method calibration is reproducible, and UFC334 remains held out."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/benchmark_ufc334_pre_nov14_method_offset_shadow.py"


def load():
    spec = importlib.util.spec_from_file_location("ufc334_method_shadow_repro", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_prior_only_fitted_153_then_heldout_334_matches_report():
    module = load()
    result = module.compute()
    assert result["prior_fit_rows"] == 153
    assert result["fit_max_date"] == "2026-11-07"
    assert result["original_exact_correct"] == 1
    assert result["shadow_exact_correct"] == 1
    assert result["no_model_promotion"] is True
    assert len(result["rows"]) == 12
    assert len([x for x in result["rows"] if x["reference_winner_correct"]]) == 8
    assert abs(result["finish_offset"]-0.6729356972592578)<1e-8
    assert abs(result["sub_offset"]-(-0.4294005334331203))<1e-8
    given = result["correct_reference_winner_method"]
    assert given["shadow"]["mean_brier"] > given["baseline"]["mean_brier"]
    assert given["shadow"]["mean_logloss"] > given["baseline"]["mean_logloss"]
    assert given["shadow"]["top_accuracy"] == given["baseline"]["top_accuracy"] == 0.125
    oracle = result["known_winner_conditional_method_oracle"]
    assert oracle["shadow"]["mean_brier"] > oracle["baseline"]["mean_brier"]
    assert oracle["shadow"]["top_accuracy"] < oracle["baseline"]["top_accuracy"]


def test_report_stored_properly_and_is_experiment_not_stage_a_relock():
    module = load()
    # This also compares all metrics to the immutable shadow report.
    module.main()
