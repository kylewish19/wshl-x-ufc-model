"""Export pinned as-of features and benchmark nontrained 2026 research baselines.

Usage: python tools/build_historical_feature_baselines.py
"""
from pathlib import Path
import json
from wshlx_ufc.historical_feature_matrix import export_matrix, load_matrix
from wshlx_ufc.historical_baselines import benchmark_fixed_baselines

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/model_health/2026-11-17_historical_feature_baselines"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    feature_rows, label_rows, manifest = load_matrix()
    benchmark = benchmark_fixed_baselines(feature_rows, label_rows)
    exported = export_matrix(OUT)
    if exported["feature_rows"] != manifest["feature_rows"]:
        raise AssertionError("Export row count changed between runs")
    (OUT / "benchmark_results.json").write_text(json.dumps(benchmark, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"export": str(OUT), "manifest": exported,
                      "benchmark": benchmark}, sort_keys=True, allow_nan=False))
    print("RESEARCH ONLY; NO MODEL TRAINED OR PROMOTED; NO STAGE A/B ALTERATIONS")


if __name__ == "__main__":
    main()
