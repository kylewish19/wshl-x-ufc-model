# Historical Conditional Win-Rate Engine

## Purpose

This module adds a reproducible historical-baseline layer to the WSHL-X UFC workflow.
It does **not** turn descriptive UFC history into hand-written bonuses. It reconstructs
what was known before each fight, computes conditional rates from that history, and lets
machine-learning models decide how much predictive value those signals carry.

## Non-negotiable leakage rule

For fight `N`, every fighter-history field must be calculated from fights `< N` only.
The current fight's result, method, strikes, takedowns, control, or later career totals
cannot appear in its model features.

Two mirrored perspective rows are emitted per decided fight. Historical-rate encodings
for the entire event date are calculated before **any** result from that date is added to
the rate history. This prevents both mirrored-row leakage and same-card leakage and
matches the pre-card lock workflow used by WSHL-X.

## Data source

The builder consumes UFCStats-compatible CSV exports for:

- event/date/location
- fight result/method/scheduled format
- round-level fighter statistics
- fighter height/reach/stance/date of birth

The default downloader points at the maintained `Greco1899/scrape_ufc_stats` mirror.
The raw source is cached separately; derived rows retain fight/date identifiers so any
anomaly can be traced back to the source bout. Missing historical round-stat coverage is
tracked explicitly so absent statistics are not treated as zero performance.

Source-column matching prefers exact UFCStats headers and only uses punctuation/spacing
normalization when the normalized match is unique. This is specifically tested so
count columns such as `SIG.STR.` and `TD` can never be confused with percentage columns
such as `SIG.STR. %` and `TD %`.

When the public mirror is behind a completed UFC event, verified results-only supplements
can be added under `data/supplemental/results/`. A supplement is automatically ignored
once the upstream mirror contains an event on the same date, preventing duplicates. A
results-only supplement updates result-derived state while leaving unavailable detailed
round statistics missing until they are actually sourced.

## Split families

### Relative matchup splits

Age, reach, height, UFC experience, UFC win percentage, recent-five form, layoff,
significant-strike differential, significant-strike accuracy, significant-strike
defense, takedown rate, takedown accuracy, takedown defense, control, knockdown rate,
finish tendency, and KO-loss vulnerability.

### Absolute fighter-state splits

Age band, prior UFC fights, win/loss streak, layoff length, SLpM, SApM, striking
accuracy/defense, takedowns/15, takedown accuracy/defense, submission attempts,
knockdowns, control, finish share, KO-loss share, submission-loss share, prior five-round
experience, and prior title-fight experience.

### Context splits

Debutant/veteran status, previous UFC meeting result, five-round experience matchup,
title experience matchup, stance matchup, finish-profile matchup, weight class,
scheduled rounds, title fight, and rematch number.

### Pre-declared interaction splits

- age gap × UFC experience gap
- age gap × layoff gap
- age gap × KO vulnerability gap
- reach gap × striking differential gap
- takedown offense gap × takedown defense gap
- finish tendency gap × KO vulnerability gap
- stance matchup × reach gap
- weight class × finish-profile matchup
- scheduled rounds × five-round experience
- title fight × title experience
- prior meeting result × rematch number

These interactions are declared before looking at model results to reduce data-mining
and multiple-comparison bias.

## Rate output

Each qualifying bucket contains:

- sample size `n`
- wins
- conditional win rate
- 95% Wilson interval
- split/bucket definition

Default reporting suppresses tiny buckets. Published external benchmarks are kept under
`data/reference/published_conditional_rate_benchmarks.csv` for sanity checks, not as
training labels or manual bonuses.

## Machine-learning layer

`historical_model.py` builds an odds-blind historical winner shadow model:

1. chronological train/validation/test split by fight date;
2. past-only smoothed conditional-rate encodings;
3. raw pre-fight statistics and fighter-vs-opponent differentials;
4. pre-declared MMA interaction features;
5. regularized logistic regression benchmark;
6. nonlinear histogram gradient boosting model;
7. equal-weight probability ensemble;
8. mirrored fight probabilities normalized to a coherent two-outcome distribution;
9. probability calibration selected on the validation era only;
10. accuracy, log loss, Brier score, and ROC-AUC reporting for both raw and calibrated probabilities;
11. only after untouched test scoring, refit the saved shadow model on all completed history so the next card can use every available completed UFC fight.

The model is a **shadow/research model** until it proves itself prospectively against the
current official winner model. Historical accuracy alone is not enough to promote it,
and calibration metrics matter as much as raw pick percentage.

## Calibration policy: improve confidence without sacrificing discrimination

The first accepted calibration family is **positive logit-temperature scaling**. The
base winner learner is fit on the chronological training era. A single positive
temperature is selected by validation log loss on the next era. That temperature is then
frozen before the final historical test era is scored.

For raw probability `p`, calibration is:

`p_cal = sigmoid(logit(p) / T)` with `T > 0`.

This restriction is deliberate. A positive temperature is strictly monotonic and leaves
`p = 0.50` fixed. Therefore it cannot change:

- which fighter is picked to win at the 50% threshold;
- prediction ordering;
- ROC-AUC/discrimination, aside from floating-point noise.

It is allowed to change only **confidence**. When `T > 1`, extreme probabilities are
pulled toward 50%; when `0 < T < 1`, they become more confident. The validation period
chooses the value. Regression tests explicitly verify that winner accuracy and ROC-AUC
are unchanged by calibration. The untouched test period determines whether the improved
validation calibration generalizes.

More flexible methods such as Platt scaling or isotonic regression are not promoted just
because they improve in-sample calibration; they would first need chronological evidence
that they do not damage discrimination or matchup coherence.

## Current build snapshot — 2026-10-18

- 8,792 decided UFC fights reconstructed
- 17,584 mirrored pre-fight perspective rows
- history from 1994-03-11 through 2026-10-17
- public mirror current through 2026-10-10
- 13 verified 2026-10-17 Edmonton results added as a results-only supplement
- 57 conditional-rate families
- 888 qualifying conditional-rate buckets at the current minimum sample gates
- 37 repository tests passing before the calibration-specific regression tests were added

Pre-calibration chronological shadow-model baseline:

- validation: 60.22% accuracy, ROC-AUC 0.6523, Brier 0.2371, log loss 0.6727
- test: 63.08% accuracy, ROC-AUC 0.6557, Brier 0.2452, log loss 0.7334

The raw test accuracy and AUC show useful winner signal, but raw test log loss is worse
than the 0.6931 coin-flip log-loss baseline. That is the overconfidence/calibration
problem the temperature layer is designed to address. The calibrated build must preserve
the same winner accuracy/AUC while being judged on out-of-sample Brier score and log
loss. This model remains a shadow input regardless of the calibration result until it
proves itself prospectively under the repository promotion rules.

## Current limitations / next enrichments

UFCStats does not natively provide every factor we care about. Historical ranking,
short-notice status, weight-miss context, full professional record, regional strength of
schedule, injury context, camp changes, and detailed opponent-quality features require
separate timestamped sources. They should be joined only when we can reconstruct them
as-of each fight without leakage.
