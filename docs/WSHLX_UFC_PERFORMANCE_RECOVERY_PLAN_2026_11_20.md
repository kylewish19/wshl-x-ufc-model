# WSHL_X UFC — performance-recovery development contract (Nov 20, 2026)

**Purpose:** Turn WSHL_X UFC from retrospective experiments into a **reproducible, independently graded prospective prediction AND profitability system**. Four goals: improve winning-fighter accuracy, improve KO/SUB/DEC conditional on winner, build 0–5 selective exact opportunities without forced bets, and determine whether FanDuel prices offer positive long-run expected return.

**Scope:** Research branch `feature/historical-conditional-rates` only. Original November 21 Qatar Stage A and its separate Coherent, Winner v3, Winner v4, Method v5 and direct six v7 prior-to-event research locks MUST NOT CHANGE. Previous experiments already studied 2024–2026 outcomes and are not pristine future validation.

## Current evidence and non-negotiable baseline

- Archived historical Reference August–Nov 2026: **100/165 winners (60.6%)**, **49/165 exact fighter + method (29.7%)**. Only part of earlier reference archive was independently pre-event time-stamped; label its pedigree honestly.
- New historic feature/model variants (old years repeatedly examined): highest isolated observed exact ~**198/513 (38.6%)** in 2025 v7 bilateral; not continuously verified on future independent events.
- Historical exact pick models still frequently predict KO/DEC incorrectly, especially SUB. Adding more submissions by quota was already shown unreliable.
- Separately preregistered Nov21 original champion/three-view and new v3/v4/v5/v7 shadows exist. These are worth **future evaluation**, not late reshuffling.
- **70% exact all-card outcome accuracy** is aspirational. It requires winner accuracy at least 70%; if winner accuracy is 80% it requires methods right on **87.5% of correctly picked winners**. 2–5/2–5 perfect groups are aspiration, never a guaranteed claim.

## Workstream A — WINNER quality (research only)

1. Preserve opponent strength, actual UFC striking accuracy/defense, last-three/five history, worldwide pre-UFC professional records and time-frozen global Elo as separate feature families.
2. Audit actual identity and data age; two athletes with same name are NOT one fighter; an unmapped professional record is **missing**, not 0–0. Quarantine weak regional-fight source quality.
3. Candidate experiments: regularized mirrored logistic; limited-depth boosting; Bayesian/shrinkage winner ratings; style-specific clusters and nonlinear offensive-vs-defensive interactions *only if verified*.
4. **Pre-register each model's features and hyperparameters using older calendar periods exclusively**. Report paired winner hits, Brier, log loss and event-cluster bootstrap vs existing Historical and Unified on identical decisive bouts. Count era-specific/missing-UFC-info splits.
5. STOP and reject changes that only improve 2024/2025 or already-researched 2026; the final benchmark requires genuinely new pre-event-locked outcomes. No promoting based on a single UFC event or a few extra winning picks.

## Workstream B — METHOD after winning fighter

1. Independently measure **method-class recall when the fighter selection is correct**; track raw method class accuracy separately from exact six-state accuracy.
2. Candidate families: separate KO/SUB finishing and vulnerability rates, opponent takedown access/defense interactions, conditional KO/SUB/DEC multinomial, hierarchical finish vs decision, and direct six-outcome probability model.
3. Real time-lagged opponent resistance, knockdowns, submissions attempted, takedown entries, control, reversals and escape patterns may be used **only where actually observed**; never invent UFCStats get-up counts, injuries or backdated regional detailed stats.
4. Evaluate paired exact fighter+method hits, six-state Brier/log loss and confusion **for KO, SUB and DEC**, holding the winning-fighter head FIXED. A higher unconditional SUB prediction count isn't itself success.
5. Preserve correct fighter/method six-state numerical tie handling, deterministic single-thread runs and proper source SHA checks.

## Workstream C — SELECTIVE 0-to-5 exact picks

1. Do not mechanically take the highest winner-confidence five or force two picks. Evaluate all 11–14 fights; a card may have **zero eligible** exact outcomes.
2. Every model/selection policy must be independently preregistered before a bout. Build same-model, same-probability-range observed success only from PREVIOUS verified prospective results; never put current/future fights in historical reliability calibration.
3. Source/identity ambiguity and provisional fights are hard PASS regardless of numerical P. Model probabilities (especially large uncalibrated six-state forecasts) are NOT stated as certain exact outcomes.
4. Predeclared **research gate for testing, NOT an optimal betting guarantee**: >=300 unique previously prospectively locked/graded decisive fights, >=50 previous records in same exact-probability bucket, 95% Wilson lower bound >=55%, source identity verified. Rank up to five if and only if they pass. No retroactive threshold search after watching current event.
5. Track per card: number picked, % exact picks, **all-selected-perfect card rate for k=2,3,4,5**, abstentions, and lift against ranked-top-k and random eligible baselines on the SAME events. Void and pending NEVER counted as wins. A 100% target cannot be guaranteed.

### First implementation committed Nov20

- `src/wshlx_ufc/forward_validation_v1.py`: strict six-state and exact grading, same-margin tie protection, 95% Wilson conservative history, 0–5 selected-card, verified FanDuel quote and exact outcome price checks, and perfect-group grading.
- `tests/test_ufc_forward_validation_v1.py`: all-match winner+method, incorrect method after correct winner, unavailable/future labels, source aliases, improper odds, no evidence, perfect-group VOID/PENDING and overstated selection size regressions.
- `tools/audit_ufcqatar_forward_selection_readiness.py`: SHA-verified, pre-first-fight ONLY Nov21 research selection readiness based on original Stage A and direct-six v7 lock.
- `.github/workflows/ufc-forward-selection-v1-audit.yml`: full CI, original source hashes, no model promotion, zero artificially manufactured bets. Run https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44758331722 completed successfully on Nov20 before additional quote-evidence test hardening.

**Expected Nov21 readiness:** without >=300 genuine previous prospective decisive model results, zero additional exact selections. This is a source/uncertainty guard, NOT evidence that no individual pick can be correct. The user-selected public video picks remain public predictions and are not automatically official FanDuel approved bets.

## Workstream D — VALUE, PRICING and VERIFIED profitability

1. Continue existing `src/wshlx_ufc/selection_policy.py`, `tools/build_ufc_two_tier_stage_b.py`, `tools/grade_ufc_two_tier_stage_b.py`, `tools/track_ufc_top5_research_units.py` without resetting their historic ledgers.
2. Research value tests must use **verified original FanDuel pre-bout odds** with archived evidence reference, sportsbook, quote timestamp, same fighter+method market identity and exact pre-event source hash. Never substitute DraftKings, an inferred price or an estimated closing line.
3. Use a **conservative empirically verified pre-event reliability lower bound**, not an uncalibrated raw model P, for candidate edge/expected profit. Review research without entering or approving any wager. Research model is not promoted to official Stage B by an attractive price alone.
4. Grade only externally verified market settlements, W/L/PUSH/VOID/PENDING separately. Track 1u-hypothetical and actually approved bets in separate ledgers; cumulative ROI, yield per bet, absolute P/L, profitable cards, closing-line value ONLY when genuinely archived FanDuel closing quotes exist.
5. Record realized returns and expected return distributions by odds band, market family, selection tier, fighter-history quality and event. Reject a potentially profitable strategy if the apparent edge disappears out of time.
6. Avoid high-stakes guarantees, locks, or unsustainably large accumulators as a substitute for credible single-bet edge.

## Gates, promotion, and execution order

**Immediately (before Nov21 first fight):** keep all existing locked model versions immutable; run new source/data selection QA and record NO fabricated FanDuel prices or bets; no late model selection changes.

**Nov21/after official settlement:** source-verifiably grade the SAME completed fights across original Reference/Historical/Unified, Coherent, v3, v4, v5 and v7 locks. Grade user-facing public video card separately if desired; never relabel it as the original model card. Do not train new model on result until prior grades are frozen and written.

**Next several UFC events:** accumulate unchanged pre-fight model forecasts and market source snapshots (where available), compare equally across winner, method, exact, six-state logloss/Brier, full-card perfect subset and FanDuel ROI.

**Model release gate:** require >=300 unique truly new decisive fights with independent pre-event registration for a candidate, not 300 repeatedly reexamined historical rows; insist on paired event-cluster evidence of stable improvement, no meaningful worsening in six-outcome proper scores, model calibration analysis, and real benefit over the current champion. Passing one good event or cherry-picking already-known favorites is NEVER promotion proof. Pre-register any threshold changes for *future* tests.

**Stop rule:** If 60–70% exact and perfect 2–5 groups cannot be demonstrated, remain candid; no number of rerun simulations makes impossible certainty an honest claim. The practical long-run goal is better calibrated decisions and sustainable positive-value **single bets** without manufacturing winners from past knowledge.

### Status Nov20, 2026

- **Research models and new source audits:** already implemented and versioned through v8; no proven new production accuracy advantage yet.
- **Forward validation and independent selection gate:** implemented, tested in GitHub Actions.
- **Actual 70% exact full card / guaranteed 2–5 perfect:** NOT achieved.
- **FanDuel profitability on Nov21:** UNVERIFIED until real market quotes and results, NOT claimed.
- **Original stage A and prospectively frozen research predictions:** remain untouched.
