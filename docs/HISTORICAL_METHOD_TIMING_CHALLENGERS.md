# Historical Method + Timing Challengers

## Status

Research/shadow only. These models do not replace the preserved official UFC method or timing models.
Odds are excluded from prediction. Promotion requires prospective evidence and explicit authorization.

## Shared historical foundation

- 8,792 decided UFC fights through 2026-10-17
- 17,584 mirrored leakage-safe pre-fight fighter perspectives
- same-card outcomes are not visible to historical-rate encoders
- all historical fighter statistics are reconstructed as of the fight date
- 888 qualifying winner-rate buckets across 57 families
- 5,028 qualifying six-state method-rate buckets across 342 outcome/split families
- 375 timing-rate buckets across 75 target/split families

## Method challenger

The historical method challenger models one coherent six-state joint distribution:

- fighter A wins by KO/TKO
- fighter A wins by submission
- fighter A wins by decision
- fighter B wins by KO/TKO
- fighter B wins by submission
- fighter B wins by decision

Mirrored fighter rows are reconciled so A-WIN-KO equals B-LOSS-KO, etc. Winner probability,
KO/SUB/DEC fight-method probability, and winner+method probability therefore come from one
coherent simplex rather than multiplying unrelated probabilities.

Historical rate features are built separately for each six-state outcome and combined with
raw pre-fight stats, matchup differentials, and pre-declared interactions. A regularized
logistic model and histogram gradient boosting model are ensembled. Multiclass temperature
scaling is selected on validation only and frozen before the final test era.

### Correct method-market evaluation

Method bets are evaluated from marginal method probabilities:

- P(KO/TKO) = P(A KO/TKO) + P(B KO/TKO)
- P(SUB) = P(A SUB) + P(B SUB)
- P(DEC) = P(A DEC) + P(B DEC)

The largest individual winner+method cell is **not** used as the fight-method pick. This is
important because a method can have substantial probability split across both fighters.

### Chronological holdout

Untouched test era: 1,461 fights.

- joint winner+method accuracy: 34.91%
- winner accuracy from the six-state distribution: 62.56%
- top-method accuracy: 52.02%
- six-state log loss: 1.6014 vs 1.7918 uniform-six-state baseline
- six-state multiclass Brier: 0.7677
- three-method Brier: 0.5820
- calibration temperature: 1.0718

Method distribution on the test era:

| Method | Actual share | Mean model probability | Top-method share | Recall as top method |
|---|---:|---:|---:|---:|
| KO/TKO | 33.68% | 34.32% | 30.39% | 43.70% |
| Submission | 17.39% | 20.07% | 3.22% | 7.09% |
| Decision | 48.94% | 45.61% | 66.39% | 73.71% |

Interpretation: the model is **not** globally starving submission probability; its average
submission probability is actually slightly above the observed test frequency. The current
weakness is that submission is rarely the largest of the three method marginals. Therefore
we must not try to fix the old decision-heavy concern by artificially forcing more SUB top
picks. For betting, the probability and price matter even when SUB is the second-most-likely
method. Prospective tracking should grade both probability quality and official gated picks.

## Timing / round challenger

The historical timing challenger uses one orientation-invariant row per fight and feeds
historical conditional-rate features into the existing 30-second discrete-time hazard model.
The historical timing training window starts at 2001-01-01 to reduce distortion from early
UFC formats.

All markets are derived from one survival curve, which guarantees coherence between:

- over/under 0.5, 1.5, 2.5 rounds
- over/under 3.5 and 4.5 in five-round fights
- goes distance yes/no
- Round 2/3/4/5 starts yes/no
- exact finish Round 1/2/3/4/5

For example, Round 3 starting can never have a higher probability than Round 2 starting,
and exact-round finish masses plus distance survival are derived from the same hazard chain.

### Chronological holdout

Timing split after the 2001 cutoff:

- train: 5,768 fights
- validation: 1,338 fights
- untouched test: 1,400 fights

Selected calibrated test metrics:

| Market | Accuracy | Brier | Log loss | ROC-AUC |
|---|---:|---:|---:|---:|
| Goes distance | 59.86% | 0.2526 | 0.7534 | 0.6153 |
| Over 1.5 | 65.86% | 0.2279 | 0.6677 | 0.6205 |
| Over 2.5 | 58.29% | 0.2504 | 0.7356 | 0.6178 |
| Round 2 starts | 70.86% | 0.2003 | 0.5939 | 0.6314 |
| Round 3 starts | 59.50% | 0.2464 | 0.7164 | 0.6141 |
| Round 4 starts* | 57.97% | 0.2319 | 0.6511 | 0.6425 |
| Round 5 starts* | 64.49% | 0.2227 | 0.6308 | 0.6962 |

*Five-round subset only, n=138 in the test era.

Exact-round test ROC-AUC:

- Round 1 finish: 0.6314
- Round 2 finish: 0.5136
- Round 3 finish: 0.5437
- Round 4 finish*: 0.7115
- Round 5 finish*: 0.5911

High raw accuracy on late exact-round events is not treated as evidence of strong prediction
because those outcomes are rare. ROC-AUC, Brier/log loss, calibration, sample size, and
prospective performance must all be considered. The common-fight exact R2/R3 finish signal
is currently weak and should remain informational/shadow.

### Timing calibration

Validation chose a hazard temperature of 1.0375, very close to no adjustment. It improves
some validation metrics, but raw vs calibrated performance is mixed by market on the final
test era. Therefore there is no basis to declare one global timing calibration universally
superior. Raw and calibrated timing probabilities should remain separately visible during
prospective tracking until enough new cards accumulate.

## Operational rule for upcoming cards

For each new UFC card, run in parallel before odds:

1. preserved official/reference winner/method/timing models;
2. calibrated historical winner challenger;
3. six-state historical method challenger;
4. historical 30-second timing/survival challenger.

Lock all outputs before Stage B prices. After the event, grade models separately by market,
confidence/probability bucket, and calibration. Do not promote a historical challenger based
on retrospective performance alone.
