# November 19 — WSHL_X exact fighter+method Phase 2: data/ablation/six-way/selection findings

**Status:** VERIFIED historical research. **Not** a production model, Stage A change, or verified betting edge.

**Successful CI:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44432085423
**Artifact:** `wshlx-phase2-exact-outcome-research` includes `phase2_results.json`, all date-ordered six-state probability forecasts, SHA manifest and runner stdout.
**Files:** `tools/research_exact_outcomes_phase2.py`, `tests/test_ufc_exact_outcome_phase2.py`, `.github/workflows/ufc-phase2-exact-outcome-research.yml`.

## Goal that governs all design

Primary: **correct fighter AND method**, full 11–14-fight card aspiration 60–70% exact (100% stretch). Secondary: find 2–5 exceptionally dependable exact fighter+method selections **anywhere** on the card, not necessarily highest winner confidence and not obliged to force five. No 100% guarantee, no bet quota, no outcome-driven retrospective pick choice.

## New source audit

The existing pinned secondary UFCStats-compatible archive contains 8,871 completed historical fights. There are 3,036 UFC bouts in the 2021–Nov7 2026 window, of which 3,015 have decisive winner/method labels; 21 are draws, excluded from exact fighter+method scoring.

2026 (492 total, including four draws): 110 bouts with ≥1 UFC debutant, 310 with ≥1 fighter having fewer than 5 prior UFC fights. Average minimum fighter stats coverage about **77.6%**. These are substantial cold-start data limitations.

The existing pre-event feature matrix **did not contain** validated date-of-fight age, height, reach, prior same-division fight counts, recency/layoff, regional transfer history, injuries, nor directly observed get-ups. This is a feature omission, **not** a claim that the pinned raw data lack profiles. The pinned raw archive includes UFCStats-compatible physical profiles and bout divisions; a **separate source-verification and timing-sensitive enrichment experiment** is in progress. Do not invent historical physical attributes or regional credentials when unverified.

## 1. Historical feature-family ablation

Only previously recorded pre-fight features are used: own vs opponent UFC bouts/win rate/sample flags, past Elo/opponent strength, striking KD offense/defense, grappling takedown/submission/control offense/vulnerability, KO/sub survival and finish-resistance proxies. Controlled families were removed one at a time, using the same symmetric logistic winner and conditional multinomial method head; all hyperparameters fixed. Full **winner+method** outcomes evaluated year-ahead by whole-event date. 2026 is previously studied, not pristine.

| Candidate factorized method model | 2024 exact of 511 | 2025 exact of 513 | 2026 exact of 488 |
|---|---:|---:|---:|
| Full 38 pre-fight features | **169** | **170** | 145 |
| Remove opponent-quality features | 170 | 162 | 140 |
| Remove striking features | 169 | 154 | 141 |
| Remove grappling features | 171 | 162 | **148** |
| Remove two broad survival features | 170 | 166 | 145 |
| Only UFC experience, prior record and missingness | 168 | 152 | 131 |

Dropping grappling improves exact picks slightly in 2024 and 2026 but worsens six-state log loss on **all three years**: 2024 1.6077→1.6416; 2025 1.6065→1.6406; 2026 1.6360→1.6608. It also means **zero correct submission-class predictions** in every year, so it cannot be promoted. Removing striking or opponent-quality generally reduces probability quality too.

**No ablation reliably improves exact winner+method AND proper six-state probability metrics across all three years. Do NOT reinterpret this as permission to throw out grappling or boost KO globally.**

## 2. Direct six-outcome learning versus factorized six-outcome learning

Independent six-class conditional on bilateral fighter features, with mirrored A/B training examples and mirrored prediction averaging, was trained chronologically to predict A KO/SUB/DEC or B KO/SUB/DEC in one step. This is a genuinely new classifier architecture, not Coherent/IPF or the weighted Unified model.

| 2024/2025/2026 years | Factorized exact | Direct-six exact |
|---|---:|---:|
| 2024 511 fights | **169** | 168 |
| 2025 513 fights | **170** | 160 |
| 2026 488 (retrospective) | **145** | 143 |

**Direct-six did not outperform the factorized challenger on exact fighter+method accuracy.** Winner-only or method-only increases are not accepted in place of exact improvement; proper-score audit remains in full JSON. No model promotion.

## 3. Exact-pick reliable subset test, 11–14 decided bouts per card

Two predeclared procedures applied ONLY pre-event predictions: (a) baseline top 3 fighter+method by EXACT probability of the factorized model; (b) strict cross-model fighter+method agreement, ≥5 prior UFC bouts EACH, ≥80% historic stat coverage each, exact outcome probability at least 30% in both, and direct-six top-cell margin ≥5 percentage points. Strict selection chooses at most 5 and may choose **0 or 1**; no true results were consulted in choosing.

| Evaluation year | Card count | Baseline top 3 exact outcomes | Strict rule exact outcomes | Perfect strict subsets (2–5 selected) |
|---|---:|---:|---:|---:|
| 2024 | 40 | 42/120 (**35.0%**) | 38/82 (**46.3%**) | 4/27 |
| 2025 | 39 | 47/117 (**40.2%**) | 21/70 (**30.0%**) | 1/20 |
| 2026 retrospective | 38 | 42/114 (**36.8%**) | 23/75 (**30.7%**) | 3/24 |

The strict filter **fails to improve selection on two of three years**, and perfect-card rate for selected 2–5 remains poor. No 100% accuracy is claimed. The selected sample counts and card populations vary between rules; do not treat differences as causal without matched-fight analysis. All are retro model-development, not out-of-time future bets.

**Conclusion:** Neither high winner confidence, naive exact-score ranking, direct six-way model, nor a hard-coded evidence+consensus gate currently identifies dependable 2–5 exact picks.

## Next legitimate work

1. Complete source-hashed DOB, height/reach, weight-class and UFC layoff enrichment **without** current-vintage fighter stats leakage; separate invariant DOB vs possibly retrospectively revised reach and height. Test base vs context vs context+physical fields in 2024/2025/2026 chronology and report source coverage by year.
2. Candidate improvements must beat the strongest relevant *same-bout* Historical/Unified and prior-rate baselines in exact fighter+method + six-class scores, with proper event-level paired uncertainty and no submission collapse.
3. If trying trained exact-reliability selection, fit it on strictly PRIOR pre-event probability/outcome pairs only and evaluate on next years; allow abstention. Do not select per-fight thresholds after inspecting current card outcomes.
4. Prospective actual future Fight Night Stage A research challenger requires source-checked profiles and immutable pre-event predictions. Keep current November 21 Stage A and separate Coherent lock untouched. No new model/betting authority before future-event validation and the existing ≥300 prospectively gradeable fight policy.

**What has not improved:** The project has not demonstrated 60–70% full-card exact predictions, nor 100% correct 2–5 selection groups. A 60% winner hit rate mathematically caps full-card exact rate at 60% even with flawless methods. This research correctly found multiple negative paths instead of promoting a spurious backtest winner.
