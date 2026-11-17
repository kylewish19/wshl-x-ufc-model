# UFC 334 — lessons learned, code changes, and next-model audit queue

Post-event audit date: 2026-11-15. Event Nov14. Predictions and prices frozen Nov11. NO old locks, model coefficients, trained artifacts, or Stage B decisions were rewritten.

## Full grading is complete

- New immutable-source verified outcomes ledger: data/results/ufc334_2026-11-14_verified_outcomes.json (13 fights including a majority draw).
- New machine-readable complete model/method/timing and priced-research grade: data/results/ufc334_2026-11-14_all_models_grading.json.
- Public-facing internal score report: reports/ufc334_2026-11-14/STAGE_A_B_POST_EVENT_GRADE.md.
- Cross-card evidence audit: data/results/ufc334_2026-11-14_two_card_finish_class_diagnostic.json.
- New reusable post-event diagnostic code: src/wshlx_ufc/finish_class_diagnostics.py.
- Regression tests: tests/test_ufc334_post_event_grading_integrity.py (freeze hashes, source identity, 13 results, draw, 334 FanDuel quotes, 5+5 research-only settlements, two-card method bias).
- Stage B 0 official bets; separate virtual research list 3-2 (+1.4497u) and longshots 1-4 (-1.1500u). Combined 4-6 (+0.2997u). Nothing represented as real money staked.

## Model performance lessons (priority ranked)

### P0 — Repeated KO leading-method excess vs actual decisions

Nov7 decisive 14 fights: Reference selected top method KO10 / SUB1 / DEC3; actual KO6 / SUB1 / DEC7.
Nov14 decisive 12 fights: Reference selected top method KO11 / SUB1 / DEC0; actual KO3 / SUB2 / DEC7.
Combined 26 decisive fights: **21 KO top labels vs 9 actual KO; 3 DEC top labels vs 14 actual DEC**.
Reference exact fighter+method: Nov7 5/14 and Nov14 1/12 => 6/26 (23.1%) across these two dates. Reference winners 9/14 + 8/12 = 17/26 (65.4%). Therefore finish-method calibration is a substantially bigger observed problem than the basic fighter winner.
Important statistical caution: counted most-likely class labels, NOT a full method probability calibration. Must also use conditional-method class-specific Brier/log loss and realized frequencies by confidence bin.
**Do not silently flip finish-method picks to decisions or manually force a DEC share.** Require time-ordered out-of-sample recalibration comparison across more than these two cards.

### P0 — Shadow winner probability and joint method mass coherence

Frozen Historical shadow standalone winner forecasts vs six-outcome joint mass differ by as much as 17.569 percentage points; Unified by 10.228pp.
That arithmetic mismatch is a diagnostic/integration issue independent of who won the card. Future model candidate should enforce P(A KO)+P(A SUB)+P(A DEC)=P(A) and the equivalent for B, without inventing post-event probabilities.
Preserve the Nov11 original raw distributions. Repair the assembly/calibration in a *new challenger/shadow build*, rerun chronology-safe probability validation, and block exact-method betting families until coherent.

### P1 — Fighter opponent quality and defensive counter-matchups

- Johnson/Almeida: Reference Johnson win 85.2%, lost R1 TKO. Review strength of pre-UFC competition, opponent kickboxing quality and counter-striking defense, not just newcomer finish streak.
- Thompson/Radtke: all three winner models missed; Radtke pressure/grappling vs Thompson technical counter-striking and stand-ups. Review spacing, defensive wrestling, get-up frequency and how much control actually translates to winning rounds.
- Hasan/Gurule: underestimated ability to wrestle through rounds and neutralize explosive counters; fold non-UFC and UFC opponent competition level and fight-duration experience into OOF evaluations.
- Borralho/Belgaroui: Reference correct 54.3%, shadows wrong. Evaluate striking-only specialists against experienced wrestlers/multiphase MMA with actual takedown success and control.
- Elder/Sanches: inexperienced UFC newcomer with 0 prior UFC bouts got favored by shadow models while Elder won 30-26 x3. Apply evidenced uncertainty and minimum-information gates on new fighters; don't blindly use regional KO stats as UFC-level equivalence.

### P1 — Finish hazard and five-round championship pacing

Reference predicted approximately 7.57 of 13 fights to end early, versus only 5. Stage A GTD NO 2-3 vs Over 1.5 rounds 7-1.
Gane-Hokit GTD No was 81.0% simulated yet the fight went 25 minutes; separate five-round heavyweight late-finish, full-distance, and matchup-specific pacing calibration.
Do not conflate exact method, fight-distance outcome and round-to-start markets. Enforce method-timing coherence warnings per original six blocked fights; no post hoc gate override.

### P1 — Unanimous model errors and ensemble dependence

All three views favored Johnson, Radtke and Hasan, and all three were wrong. Unified blends the other components, so 3/3 is not three independent confirmations.
Reference won 8/12 decisive fights versus Historical 6/12, Unified 7/12 and presentation consensus 7/12. No evidence this card supports promoting either shadow.
The original SIDE model pick tier went 2-0; LEAN went 1-2, PASS 5-2 plus draw. Small samples: evaluate confidence threshold calibration across previous events before changing risk gates.

### P2 — Fight-day context source checks

Terrance McKinney and Juan Diaz missed official weight on Nov13, after the Nov11 original Stage A lock. Never backfill or modify originally frozen inputs with post-lock information.
Future predeclared fight-day quality audit should flag missed weights, catchweights, opponent changes, late injury/news and lineup changes separately, producing a dated revised scenario only when compliant with odds-blind policy.

### P2 — FanDuel Stage B price realism

Radtke ML +126 and Radtke KO +480 showed purported raw edges but both lost; some inflated raw win probabilities are likely model risk, not bookmaker errors.
McKinney Round3 starts Yes +640 had a stated 50% shadow simulation chance while McKinney won R1. This was not our Stage A primary timing pick and illustrates possible bad survival hazard modeling.
Keep original zero-wager gate. Conservative calibrated probability bounds, model/market consistency, verified original screenshot timing and official weigh-ins must precede any future approval.
The 4-6 research-only 10-pick slate with +0.30u hypothetical net is too small/correlated to validate price-gate ROI. Report best/longshot independently and use original quotes, never current post-fight prices.

## Exact code and training status

**Code updates completed:** verified-result recording, all-view grader output, repeated cross-event finish-class diagnostic, and automated regression assertions in test suite. These are audit/diagnostic code changes, not recalibration or new winner picks.
**Predictive code/weights today:** unchanged. Reference remains champion, Historical and Unified remain shadows, Stage A and B preserved.
**Do not overfit:** there is repeated directionality in KO-vs-DEC top labels, but it is insufficient to fit a new probability correction without actual per-fighter/per-round stats and a chronological holdout.

## Mandatory follow-up before predictive change

1. Obtain official UFCStats fighter and per-round UFC334 records (striking, accuracy, TD, control, knockdowns, submission attempts) and review provenance. Do not claim them ingested until verified.
2. Assemble pre-fight causal opponent-quality and actual defense/get-up features WITHOUT introducing post-event stats as prediction inputs for the same fight.
3. Investigate six-class conditional method mass vs winner probability mismatch in Historical/Unified; fix forward only as versioned shadow and unit-test constraints.
4. Run chronological held-out experiments on (a) winner probabilities, (b) conditional method probabilities including decision, (c) timing/finish hazard incl five-round, (d) double chance coherence, with Brier/log-loss and exact hit rates.
5. Compare champion vs shadow across multiple event dates, repeat significant evidence before any promotion. Never use one card's 12 decisive outcomes alone to retrain confidence blindly.
6. Continue Stage A odds-blind, then FanDuel-only Stage B. Grade each frozen view and each odds-price research vs approved official bets as separate ledgers.

## Source links

https://www.cbssports.com/ufc/news/ufc-334-fight-card-ciryl-gane-josh-hokit-results-winners/
https://www.sherdog.com/news/news/UFC-334-Gane-vs-Hokit-playbyplay-results-round-scoring-203625
https://www.ufc.com/news/official-weigh-results-polymarket-ufc-334-gane-vs-hokit


## November 15 additional Stage B audit — all 334 archived quotes

Saved `data/results/ufc334_2026-11-14_all_334_fanduel_markets_settlement_diagnostic.json`
after the complete Stage A and Top5+Top5 grading. All originally displayed
FanDuel prices and betting-block decisions remain frozen. The retrospective
research scoring covers 293 supported quote outcomes (108 W/185 L),
excludes 24 unmodeled draw quotes, and leaves 17 draw-affected special
markets unresolved until the actual FanDuel settlement terms are verified.
This includes multiple complementary and correlated markets per fight,
**so the 108/185 count is NOT a pick-card hit rate or an actual-bet record**.

In 127 settled quotes with positive uncalibrated raw model EV, 43 settled W
and 84 L. Mean raw selected-outcome probability was 44.38% versus a
33.86% observed event frequency in this highly correlated sample. This is
an exploratory warning that non-calibrated raw EV selection can mislead,
not proof of a calibrated 10.5 percentage-point population bias.
Only chronological, matchup-clustered, market-specific probability
calibration and return simulations may support adjusting Stage B gates.

**Code changes this event remain recording/diagnostic/testing only.
There is still no champion, shadow weight, market gate, or original prediction
change.**


## November 16 additional data and method challenger follow-up

**UFC334 performance stats acquired and validated — PROVISIONAL secondary mirrors.**
We now have **13/13 fights, 26 fighter totals (32 columns) and 72 fighter-round
records**, sourced from UFCStats-derived FightingData and Cage Almanac mirrors.
Round sig-strike, takedown, knockdown and control sums agree with fighter totals;
strike target/position aggregates also reconcile. Direct first-party UFCStats
still returns 502 and a third-party feed differs on Gane/Hokit strike totals.
The manifest enforces `allow_training=false` until approved source
reconciliation. See
`data/raw/ufc334_2026-11-14/INGESTION_MANIFEST_PROVISIONAL.json`,
`src/wshlx_ufc/post_event_stats_audit.py` and the accompanying regression tests.

**Actual prior-only method correction experiment was run, and rejected.**
The existing `MethodInterceptCalibrator` was fitted on exactly **153 earlier
causal graded fights through November 7**, with the Nov14 UFC334 predictions
and results held completely out of fitting. Its prospective-style shadow
retained only **1/12** correct Reference fighter+method combinations;
on the eight correctly predicted Reference winners, method probability
Brier **worsened 0.7754 → 0.9948** and method log loss **worsened
1.2247 → 1.6049**. No improvement in top-label method accuracy. It was
**NOT promoted**; no champion coefficients, predictions, or previously
frozen outputs changed. The clean holdout study and reproducer live at
`reports/ufc334_2026-11-14/PRE_NOV14_METHOD_OFFSET_SHADOW_HOLDOUT.json`
and `tools/benchmark_ufc334_pre_nov14_method_offset_shadow.py`.
The linked tests pass.

**Before the Nov21 UFC card:** prioritize validating primary UFCStats (or
formal mirror approval), training only on previous-event stats, designing a
coherent six-way method/winner *shadow* (currently max discrepancies 17.569pp
Historical, 10.228pp Unified), adding opponent-quality/defensive
wrestling/decision-survival features from PRIOR fights, and testing 3- versus
5-round timing hazard out of time. Do not blindly force extra decisions or
relax Stage B FanDuel edge/quote/coherence gates. Full checklist:
`reports/ufc334_2026-11-14/PRE_NEXT_UFC_CARD_READINESS_2026-11-16.md`.

**Code status:** diagnostic/testing and held-out experiment code added,
but no predictive model promoted, original locks untouched and Stage B
unchanged.


## November 16 continuation — coherent six-method shadow prototype added

Built `src/wshlx_ufc/joint_coherence_shadow.py` and regression tests to
repair **probability arithmetic** in a *parallel, non-promoted candidate*
using iterative proportional fitting. Original Stage A odds-blind files
are hash verified, not rewritten. A standalone pre-fight sidecar generator
is in `tools/generate_coherent_joint_method_sidecar.py`.

Across 40 decisive fights from Oct24/Nov7/Nov14, combined winner+timing
constraints improved retrospective six-way Brier/log loss for both Historical
and Unified, and exact fighter+method research counts Historical 13/40->20/40,
Unified 14/40->16/40. By contrast winner-only projection worsened scores.
Historical's Nov14 subset also worsened, and the idea was devised after
looking at these dates: **no honest prospective success has yet been
demonstrated, no model promoted, no official wagers authorized.**

Next run this as an isolated, frozen shadow on the future UFC card. Source
checks and 300-prospective-observation promotion requirements still apply.
Full reproducible report:
`reports/ufc334_2026-11-14/THREE_EVENT_COHERENT_METHOD_SHADOW_EXPERIMENT.md`.
