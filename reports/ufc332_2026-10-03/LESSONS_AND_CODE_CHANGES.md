# UFC 332 lessons and code changes

## Event grading

- Winner picks: **13-1 (92.9%)**
- Displayed method class: **10-4 (71.4%)**
- Exact winner + displayed method: **9-5 (64.3%)**
- Timing leans: **8-6 (57.1%)**
- Official Stage B wagers: **1-2, -0.743u on 2.00u risked**
- Official timing wagers across UFC 331 + UFC 332: **0-4, -2.75u**

## What changed

### Winner layer
No winner-model code change.

The winner reference and v0.32 shadow both went 13-1. The reference was still slightly better on Brier score and log loss, so there is no evidence-based reason to replace it.

### Method layer
No anti-decision correction and no new method feature rewrite.

UFC 332 displayed-method distribution was 11 KO / 0 SUB / 3 DEC, exactly matching the event's class distribution. The calibrated method shadow went 10-4 and clearly beat baseline and residual probability quality. Keep the calibrated layer as the leading method shadow and continue prospective validation.

### Timing / Stage B policy
Two concrete code changes were made in `src/wshlx_ufc/selection_policy.py`:

1. **Sparse timing promotion block**
   - O/U, GTD and round-start markets cannot become official wagers when either fighter has fewer than 2 prior UFC bouts.
   - They can still be generated, displayed, and graded as model-only timing leans.

2. **Timing stake probation**
   - Official timing wagers are 0-4 through UFC 332.
   - Until there are at least 20 graded official timing wagers **and** cumulative timing P/L is non-negative, timing stakes are capped at **0.25u**.
   - The existing 12 percentage-point model-vs-break-even gate remains unchanged. It is not raised after one additional card because that would risk overfitting.

## Tests

`tests/test_selection_policy.py` now includes explicit regression tests for:

- the existing 12-point timing edge threshold;
- blocking a large Wint-Armand-style timing edge when the UFC sample is 1 bout vs 0 bouts;
- allowing a qualifying timing edge when both fighters have adequate UFC evidence;
- enforcing the 0.25u timing probation cap;
- releasing the cap only after the prospective sample and P/L conditions are met.

The updated selection-policy test file passed **6/6 tests** in a clean local run.

## Next model step

UFC 332 results have been appended to the clean ledger (101 fights). Full-stat retraining should happen only after the event's complete UFC round-stat data is ingested causally. At that point:

- retrain the current full-stat shadow backbone;
- refit the method intercept calibrator including UFC 332;
- retrain the 30-second timing shadow;
- preserve the current winner reference unless the challenger beats it prospectively on calibration as well as accuracy;
- do not promote any challenger based on UFC 332 alone.
