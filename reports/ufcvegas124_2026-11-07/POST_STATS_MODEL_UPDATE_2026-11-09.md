# WSHL_X UFC — November 7 post-card UFCStats learning, model refresh and promotion verdict

**Recorded:** November 9, 2026 (after the November 7 event).  
**GitHub working branch:** `feature/historical-conditional-rates`; **champion/main not promoted**.  
**Event:** UFC Fight Night: Cortes Acosta vs Walker — 14 fights.

## Executive conclusion

The five-point post-card plan was **executed**: source data gathered and validated, training data and shadow artifacts updated, reference/historical/unified generalization investigated against earlier held-out tests, fighter-specific method calibration alternatives backtested, and a conservative promotion decision made.

**The decision is NO PROMOTION at this time.** The Nov7 unified shadow made 11/14 winner picks and 8/14 correct exact winner+method picks, versus 9/14 and 5/14 for the reference. However, older chronological evidence does not establish a repeatable unified advantage. **The code now includes new trained future-only models. The existing champion remains unchanged pending prospective evidence.**

## Step 1: collect all fight statistics — COMPLETE

- Pinned source: [Greco1899 UFCStats scrape](https://github.com/Greco1899/scrape_ufc_stats/tree/c742842f29466758fedc3906dbad28d6d320a8da), refresh commit `c742842f29466758fedc3906dbad28d6d320a8da` created Nov 8, 2026 18:04 UTC.
- Source classification: **archived third-party scrape originally sourced from UFCStats.com**, NOT a claim of direct live UFCStats connectivity.
- All six source CSVs saved at `data/raw/ufcvegas124_2026-11-07`, plus four event-specific slices and a per-file SHA256/availability manifest.
- Results cross-checked against `data/results/ufcvegas124_2026-11-07_verified_outcomes.json`, which cites official UFC.com results.
- Validated **14/14 full fights, 68/68 fighter-round records, 28 fighter-fight aggregates**, exact KD, landed/attempted significant strikes, TD, submission attempts and control time fields; **zero integrity errors**.
- Independent source validation includes unique fight identities, rounds by bout, non-negative KD/SUB values, reasonable control time and landed ≤ attempted. Invalid or missing stats cause the ingest to fail closed.
- Key record: `data/raw/ufcvegas124_2026-11-07/availability.json`.
- Code: `tools/gather_ufcvegas124_full_stats.py` + GitHub Actions workflow.

## Step 2: integrate and train without lookahead — COMPLETE, SHADOW ONLY

- Canonical historical data integration: `tools/integrate_ufcvegas124_full_stats.py`, `reports/ufcvegas124_2026-11-07/full_stats/integration_report.json`.
- Existing performance-backbone architecture built **8,807 decided UFC fights** as fighter-matchup winner, winner-conditional method, and timing rows.
- Exported **28 Nov7 fighter-fight full-stat aggregates**: `data/results/ufcvegas124_2026-11-07_fighter_full_stats.csv`.
- Preserved preexisting **139** causal method-feedback observations, appended exactly **14** Nov7 records using baseline method probabilities actually frozen BEFORE Nov7; conditional method rows use the known outcome winner **only for post-event calibration training**, never as retrospective betting predictions.
- New saved `clean153_causal_method_inputs.csv` (153 rows) with verified KO/SUB/DEC labels. Note: the October 31 **unpicked** event remains present in the broad performance-stat backbone while excluded from the **139+14 official-pick feedback ledger**.
- Fitted and serialized **five new post-Nov7 future-only shadows** (winner, conditional-method baseline, method intercept calibrator, method residual, 30-second timing hazard), saved under `artifacts/ufcvegas124_post_event_shadow/`. Artifact SHA256 recorded.
- Refitted historical-conditional winner shadow through Nov7 with **17,664 mirrored fighter perspectives from 8,832 completed source fights** in `artifacts/ufcvegas124_post_event_historical/`. That broader historical pipeline's inclusion policies differ from the 8,807-fight v0.27 backbone; **do not equate the two population counts**.
- New historical model retrospective chronological held-out test: **1,467 fight pairs**, accuracy **63.29%**, probability Brier **0.2365** and log loss **0.6762**. This is not Nov7's original pre-event shadow or a head-to-head champion evaluation.
- Historical source alias controls preserve distinct Anthony Romero identities and normalize the known Kai Kamaka and Zach Reese aliases without modifying raw CSVs.
- All new model artifacts are **eligible to be considered for events after Nov7 only**. Neither old pre-event pick lock nor 153 officially graded results were modified.

## Step 3: investigate better Nov7 challenger performance — COMPLETE DIAGNOSTIC, NOT PROVEN

**Original truly frozen Nov7**:

| Metric | Reference | Historical shadow | Unified shadow |
|---|---:|---:|---:|
| Winners | 9/14 | 11/14 | 11/14 |
| Exact own fighter + method | 5/14 | 7/14 | 8/14 |
| Winner 2-class Brier (sum) | 0.4591 | 0.3932 | 0.4051 |
| Joint 6-class log loss | 1.4664 | 1.4675 | 1.4379 |

The two winner disagreement fights, Petersen and Walker, were predicted correctly by Historical+Unified but missed by Reference. Exact paired two-sided McNemar **p = 0.50** for those two winner differences, insufficient to claim generalization.

**Older OOF development evidence** from `reports/contextual_unified_through_2026-10-17/diagnostic.json`:

| Older cohort | Reference / current | Historical | Unified |
|---|---:|---:|---:|
| 112-fight winner Brier (single-outcome convention) | **0.2318** | 0.2731 | No historical development benefit shown |
| 61-fight walk-forward winner accuracy | **62.3%** | 60.7% | Global 62.3% |
| 88-fight exact winner+method accuracy | **40.9%** | 26.1% | Global 39.8% |

These older sample sizes and metrics have **different evaluation populations and conventions** from Nov7. Don't naively combine their numbers into a prospective overall ROI or W-L. The unified model's promising Nov7 8/14 exact method score warrants continued shadow testing, NOT promotion based on a single card.

Artifact: `reports/ufcvegas124_2026-11-07/challenger_generalization_audit.json`.

## Step 4: improve and backtest fighter-specific methods — MODEL REFRESH COMPLETE, CANDIDATE TESTED

The updated future-only `ConditionalMethodModel`, `MethodInterceptCalibrator`, and `V027MethodResidualChallenger` were refit with completed Nov7 UFCStats / the expanded **153-record causal method-feedback corpus**. We also ran new **date-scoped, train-prior-only** walk-forward tests on baseline, intercept calibration, v0.27 residual, and v0.35 finish-access methods. The sampled 102 older test bouts were kept separate from Nov7's 14 later method checks.

| Method predictor (known-winner conditional diagnostic) | Older 102 Brier ↓ | Older 102 log loss ↓ | Older 102 method accuracy |
|---|---:|---:|---:|
| Uncalibrated baseline | 0.6264 | 1.0036 | 43.1% |
| **Intercept-calibrated** | **0.5650** | **0.9277** | 54.9% |
| Feature residual v0.27 | 0.6342 | 1.0071 | 49.0% |
| Finish-access v0.35 | 0.5758 | 0.9494 | 55.9% |

**Interpretation:** Existing low-complexity intercept calibration demonstrably improves Brier and log loss over the uncalibrated baseline on this walk-forward set. The alternative feature-based method corrections **do not beat intercept calibration on both probability metrics** despite isolated classification gains. No feature-based method architecture is promoted. The conditional SUB recall sample remains too small to claim a fix to historical submission errors.

Nov7 method diagnostic conditioned on actual winning fighter from frozen pre-event baseline probabilities is **NOT a pre-fight side+method betting card**. The original unified frozen 8/14 outcome remains unchanged.

Artifacts: `reports/ufcvegas124_2026-11-07/full_stats/chronological_method_calibration_benchmark.json`, `.../chronological_method_calibration_predictions.csv`.

## Step 5: promotion verdict — NOT APPROVED; future prospective testing required

- **Official reference v0.27 remains the champion**. No coefficient overwrite, model promotion, unapproved method or GTD bet activation, new bookmaker price substitution, or Stage A/Stage B revision.
- Historical, current refreshed, and unified competitor weights must remain **labeled shadows**, tested on additional event-frozen future slates. All new Nov7-informed artifacts may only be used to forecast fights **after** Nov7.
- Historical challenger **300 genuinely prospectively graded fights** promotion policy remains in force; neither one 14-fight event nor retrospective historical fitting clears that gate.
- Timing/method family coherence restrictions and FanDuel conservative price checks must stay enabled.
- The next UFC Stage A runner must **explicitly load/version** these future-only refreshed shadow artifacts and freeze picks before prices are seen; this ingestion alone is **not** proof an older event-specific runner automatically points to the new model paths.
- Keep grading winner, method, timing and the two FanDuel Top5 categories independently; maintain official (approved) and hypothetical research ledgers separately.

## Regression checks and integrity

- `tests/test_ufcvegas124_full_stats_future_only.py` verifies every source CSV SHA, 14 fights, 68 real round rows, 28 real fighter aggregates, no missing same-day populations, preserved 139-row original pre-event OOF, append-only 153 feedback, full artifact hashes, historical shadow chronology, baseline and method candidate proper scores, and no unapproved promotion.
- Earlier `tests/test_ufcvegas124_postcard_grading.py` retains the original 14-fight grading.
- All files are on `feature/historical-conditional-rates`, with the trained artifacts as separate research builds. Existing champion and betting locks are not overwritten.
- This is a substantial **real data + code + model training update**, not merely a prose lessons note. It is also **not** a claim that any new model has passed strict prospective qualification for official betting.

**Next step for WSHL_X:** On the next card, freeze the unchanged reference plus versioned refreshed challenger probabilities, evaluate each shadow's winner and own-fighter method picks prospectively, and keep hard method-timing coherence and price gates until the validation evidence justifies change.
