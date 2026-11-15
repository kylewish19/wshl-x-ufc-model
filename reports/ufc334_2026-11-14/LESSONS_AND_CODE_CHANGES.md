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
