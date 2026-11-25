# WSHL_X UFC — November 17 continuation: historical as-of feature rebuild

Status: RESEARCH-ONLY IMPLEMENTATION. No model fitted or promoted. All historic Stage A/B locks, Reference/Historical/Unified outcomes, FanDuel gates, and grading are unchanged.

## New code and reproducibility

- `src/wshlx_ufc/historical_feature_matrix.py` joins pinned past-only fighter and opponent-quality snapshots into one immutable-key row per fight. Every bout's feature cutoff is its event date **exclusive**, and all fights on a given date use only earlier dates. Winner/method/duration/draw labels are exported in a SEPARATE post-event table, keyed by stable bout SHA.
- `src/wshlx_ufc/historical_baselines.py` computes simple 2026 retrospective baselines: 50/50 winner, smoothed prior UFC winning percentage, and past-only UFC Elo. Each uses 2021–2025 method proportions for a coherent six-class fighter-plus-method baseline. It scores winner Brier/log-loss/accuracy, six-class Brier/log-loss/exact, and a paired event-cluster bootstrap Elo-vs-50/50 comparison.
- `tools/build_historical_feature_baselines.py` exports `pre_event_features.csv`, `post_event_labels.csv`, `matrix_manifest.json`, and `benchmark_results.json` to `reports/model_health/2026-11-17_historical_feature_baselines/` after executing the pinned historical archive.
- `tests/test_ufc_historical_feature_baselines.py` verifies same-date leakage protection, draw handling, separation of labels, missing-stat treatment, stable fighter identity, and inventory counts. `.github/workflows/historical-feature-baselines.yml` runs tests and publishes the output as an Actions artifact.

## Evidence boundaries

The pinned secondary UFCStats-compatible archive contains 2,544 bouts from 2021–2025 and 492 from 2026 as of Nov. 14, including 21 modern-window draws. Results already inspected during prior 2026 research cannot be advertised as unseen, independent validation. Original Reference/Historical/Unified forecasts have not yet been replayed on this exact same 2026 bout set. Better scores than 50/50 are not proof of better scores than our models.

Missing prior-fight performance rates remain null instead of artificial zero values. UFC debuts are marked uncertain. UFC Elo is not regional transfer skill. Measured reversals/control are not direct measured get-ups. Age/reach/height await temporally verified source metadata; timing-specific features await separate research. Real-money FanDuel ROI cannot be inferred from retrospective prices.

## Governed next steps

1. Confirm Actions generated both separated tables and recorded source CSV SHA256 hashes.
2. Check test-period event counts, method prevalence and paired event-bootstrap uncertainty.
3. Replay unchanged Reference/Historical/Unified predictions only where truly dated and identity matched. Compare the same fight-date samples, never combine incompatible data vintages.
4. Preregister any fresh challenger before prospective Stage A locks. Observe existing >=300 genuine prospective sample rule where applicable, and do not tune/push a champion from 2026 retrospective work.

Run: `pip install -e '.[dev]'`; `pytest -q tests/test_ufc_historical_feature_baselines.py`; `python tools/build_historical_feature_baselines.py`.

**Model promotion: NONE. Stage A/B/odds changes: NONE.**
