# Model governance

## Champion / challenger

The preserved historical champions are references only until their exact executable artifacts are restored and verified:

- Winner: v0.3.1
- Conditional method: v0.4.0
- Round/timing: v0.3.1

New code in this repository begins as a **challenger**. A challenger is not called official merely because it performs well on a recently graded card.

## Weekly lifecycle

1. Collect and timestamp prefight data.
2. Build features using information available strictly before the bout.
3. Run champion and eligible shadow/challenger models.
4. Produce and hash a frozen prediction lock.
5. Only then inspect sportsbook prices for value analysis.
6. After the event, append official results.
7. Grade every frozen prediction and probability, including passes.
8. Diagnose errors by model layer.
9. Implement only justified changes.
10. Retrain a challenger on training data ending before its validation period.
11. Compare calibration, discrimination, class recall, log loss, Brier score, and stability.
12. Commit code/data-schema changes with an explicit lesson.
13. Preserve the old model and lock.

## Leakage rules

Never use the target fight result or any post-fight information as a feature.

Historical feature rows must be reconstructed as-of the fight date. Present-day career averages may not be copied backward into old fights.

Training folds for evaluation must respect chronology. Random train/test splits are not the primary model-selection evidence.

## Odds

Odds are not prediction features in the core fight models. Predictions are frozen first. Prices may be used afterward to calculate expected value and to decide whether a supported outcome is bettable.

## Tape

Tape is a separately logged evidence layer. Each source must be classified honestly as one of:

- continuous full fight
- highlights
- clip
- report/statistics
- unavailable

Do not encode a full-fight-review feature when only highlights or a recap were available.

## Promotion

Promotion requires prospective evidence and explicit authorization. Historical handoff policy required at least 300 newly locked prospective fights before model promotion; that rule remains in force unless deliberately revised in a future governance commit.

## Reproducibility

Actual fight-card simulation runs must save:

- model/version identifiers
- feature snapshot ID
- code commit SHA
- random seed
- trial count
- frozen probabilities
- generated market probabilities
- timestamp

A simulation or retraining run is not considered completed unless its output is saved.
