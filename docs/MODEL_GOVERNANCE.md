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

## Permanent UFC Stage B Top 5 + Top 5 straight-bet cards (effective 2026-11-07)

Stage B now has two independently graded FanDuel-only categories: **Top 5 Longshots** (American **+200 and longer**) and **Top 5 Best Bets** (American **−150 to +190**, inclusive). A fight may appear **at most once across both categories**, even under different methods, totals, fighters or props; maximum five eligible picks per category, never forced to five. **+191 to +199 and shorter than −150 are outside these two categories.**

Select only verified, timestamped, pre-fight FanDuel lines from the existing odds-blind frozen Stage A. Research, price, calibration, Stage A support, and market-family checks must all pass; preserve existing probability/method/timing gates. Rank gate-cleared candidates by **conservative expected value**, then edge and reliability, and enforce exclusive fight allocation across categories. **Price alone cannot flip Stage A or promote a PASS, and a new tier cannot bypass blocked method bets.**

After the card, grade W-L, units risked, net P/L and ROI for **each category separately**, with pushes/voids/pending distinguished. Recommendations are **not** evidence of actual wager placement. Three-leg parlays are optional research only, never a required Top-5 output. The new categories do **not** rewrite old official betting records.

See the executable specification and schema in [TWO_TIER_TOP5_FANDUEL_POLICY.md](TWO_TIER_TOP5_FANDUEL_POLICY.md), `src/wshlx_ufc/two_tier_card.py`, and `tests/test_two_tier_card.py`.

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
