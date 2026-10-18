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
for both rows are calculated before either row's outcome is added to the rate history.
This prevents a subtle mirror-row leak.

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
8. accuracy, log loss, Brier score, and ROC-AUC reporting.

The model is a **shadow/research model** until it proves itself prospectively against the
current official winner model. A higher historical accuracy alone is not enough to
promote it.

## Current limitations / next enrichments

UFCStats does not natively provide every factor we care about. Historical ranking,
short-notice status, weight-miss context, full professional record, regional strength of
schedule, injury context, camp changes, and detailed opponent-quality features require
separate timestamped sources. They should be joined only when we can reconstruct them
as-of each fight without leakage.
