# WSHL-X Unified UFC Ensemble

## Goal

The final UFC decision layer should not force a manual choice between the existing
machine-learning models and the historical conditional-rate challengers. The unified
ensemble combines their pre-fight probability distributions while preserving every base
model underneath for diagnosis and grading.

The ensemble is **odds-blind**. Sportsbook prices remain Stage B inputs only.

## Why an ensemble instead of a fixed 70/30 rule

The weights are learned from frozen pre-fight predictions and completed outcomes. We do
not decide that the current model is worth 70%, or that historical conditional rates are
worth 30%, by intuition. A constrained chronological objective chooses the blend that
minimizes probability loss on prior frozen fights.

Because the clean prospective sample is still modest, the first ensemble is intentionally
low capacity: one global convex weight per modeling head. Dynamic matchup-specific gates
(age-gap-specific trust, debutant-specific trust, data-density-specific trust, etc.) are
future candidates only after the prospective sample is large enough to support them.

## Inputs

### Current/reference component

Use the probability that was **actually frozen before the event**. Do not rerun a modern
model backward and pretend that was the probability available at the time.

For the initial weight-learning window:

- UFC 331 — 2026-09-19
- UFC Vegas 121 — 2026-09-26
- UFC 332 — 2026-10-03
- UFC Vegas 122 — 2026-10-10

The model version is therefore allowed to evolve across the window; the frozen prediction
is the source of truth for what WSHL-X knew before that fight.

### Historical component

Use the historical challenger's **untouched chronological test-era prediction**. Do not
use a final model that was later refit on the fight being graded. This prevents the meta
learner from receiving a historical probability that already saw the answer.

### Reserved holdout

UFC Edmonton on **2026-10-17** is not used to choose the initial weights. It is the first
untouched event-level test of the unified architecture.

## Winner head

The current/reference winner probability and historical winner probability are pooled on
the log-odds scale:

`logit(p_final) = w * logit(p_current) + (1-w) * logit(p_historical)`

`w` is selected on the frozen training cards by minimum binary log loss over a constrained
grid from 0 to 1. The endpoint models are valid candidates, so the ensemble is never
forced to use both components when the training data says one should receive zero weight.

## Method head

Both inputs must be coherent six-state distributions:

- A by KO/TKO
- A by submission
- A by decision
- B by KO/TKO
- B by submission
- B by decision

The two distributions are combined by a geometric/log probability pool with one learned
convex weight. The result is normalized back to a six-state simplex, so winner, fight
method, winner+method and double-chance markets can all be derived from the same coherent
probabilities.

The current component uses the leading method layer that was actually frozen on each
card. UFC 331 predates the accepted low-variance method calibration, so its frozen
baseline is retained rather than being rewritten retrospectively.

## Timing / round head

The final production architecture blends the two **hazard curves**, not each sportsbook
market independently. Once the hazards are blended, one survival curve generates:

- Over/Under 0.5, 1.5, 2.5 and, for five-round fights, 3.5 and 4.5
- Goes the Distance Yes/No
- Round 2/3/4/5 Starts Yes/No
- exact finish-round probabilities

This prevents contradictions between correlated timing markets.

The initial timing weight must be learned from frozen market probabilities because the old
Stage A locks preserved market outputs rather than every underlying hazard bin. The same
global weight is then applied to hazard curves prospectively. This is an approximation
and remains shadow until it proves itself on future cards.

Timing weight fitting is **fight-balanced**: loss is averaged within each fight before it
is averaged across fights. Five-round fights therefore do not receive extra influence
merely because they expose R4 and R5 markets.

## Internal walk-forward validation

Before using all four training cards to choose the final weights, the build also performs
an internal walk-forward check when at least 20 prior frozen fights are available. In
practice this gives genuinely prior-only meta predictions on later cards in the training
window rather than reporting only an in-sample fitted score.

## Historical current-style OOF reconstruction update

The initial frozen-card ensemble weights were useful as a starting point but were learned
from a very small recent sample. A larger causal reconstruction was therefore built to
compare a historical reconstruction of the current/reference architecture against the
historical conditional challengers across UFC history.

The OOF reconstruction uses **7,935 aligned fights from 2008 through 2026**. Each calendar
year is predicted from models fit only on fights dated before that fold year. The global
ensemble weights are fit on OOF predictions through 2021, while 2022-2026 is held out as
a later-era evaluation block. The full procedure remains odds-blind.

The preferred global weights for **future shadow-only prospective testing** are:

- Winner: 30.0% current/reference, 70.0% historical
- Method: 37.5% current/reference, 62.5% historical
- Timing: 75.0% current/reference, 25.0% historical

These weights are stored in `data/unified/oof_global_unified_shadow.json`.

On the 2022-2026 evaluation block, the winner blend reached 62.44% accuracy versus 61.92%
for current/reference and 62.32% for historical. The exact winner+method blend reached
33.48% versus 31.99% for current/reference and 32.76% for historical. Timing accuracy was
64.29% for the blend versus 63.92% for current/reference and 63.75% for historical.

The historical component by itself retained better winner and method log loss than the
global blend on the later-era evaluation block, so these results do not justify claiming
that the blend dominates every probability-quality metric. The global blend is preferred
as the simple prospective shadow baseline because it improves pick accuracy while keeping
both model families represented and avoiding the unsupported complexity of a dynamic
context gate.

This OOF reconstruction is a development study, not a production promotion. The feature
families and architecture were designed with knowledge of later UFC history, so future
frozen prospective cards are still required before any official-model change.

## Promotion policy

The unified ensemble begins as **SHADOW ONLY**.

A strong Edmonton result is useful evidence, not promotion proof. The ensemble remains
separately graded against:

1. current/reference model;
2. historical conditional model;
3. unified model.

Promotion requires repeated prospective improvement in probability quality and pick
quality. A new layer must not be promoted because it fits one recent card.

## Future development after enough prospective fights

Once the clean unified ledger is substantially larger, candidate meta-features can be
researched without changing the current global-weight baseline:

- component disagreement magnitude;
- minimum UFC data coverage / debutant status;
- historical split sample size and uncertainty;
- age-gap and layoff extremity;
- five-round/title-fight context;
- weight-class-specific trust;
- method-specific access and vulnerability confidence;
- timing evidence density.

Any dynamic gate must be trained from chronological out-of-fold component predictions and
must beat the global-weight ensemble on unseen cards before adoption.
