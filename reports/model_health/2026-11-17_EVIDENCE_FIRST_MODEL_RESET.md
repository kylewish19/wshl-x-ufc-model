# WSHL_X UFC — Evidence-First Model Reset and Historical Performance Audit

**Audit date:** November 17, 2026  
**Repository:** `kylewish19/wshl-x-ufc-model` · research branch `feature/historical-conditional-rates`  
**Decision:** **NO NEW MODEL PROMOTION. NO REACTIVE METHOD ADJUSTMENTS.**

This is the deliberate reset after multiple months of changes failed to demonstrate a consistent predictive or betting advantage. All results below are recomputed from the repository's archived records and protected by automated regression tests. Historical data quality and original-versus-reconstructed provenance are explicitly separated.

## 1. What we actually have — not what we wish we had

| Evidence | Present | Caveat |
|---|---|---|
| Clean reference prediction/result ledger | **153 fights, 12 events, Aug 8–Nov 7** | Reconstructed historical *grading* table, not 153 independently source-timestamped bets |
| Original separate Stage A artifacts matching those rows | **89 of 153 fights, 7 events** | Four earlier original selection files lack complete freeze timestamps; existence/identity matches are not independently cryptographic proof of pre-event publication |
| First five earlier events | **64 fights** | Present in immutable cumulative grading snapshots, but no separate original Stage A selection file identified in this repository |
| Cumulative snapshots | **8 exact prefixes, 64→153** | Checked all eight snapshot files against the 153-row ledger without rewriting old rows |
| UFC 334 | **13 fights, 12 decisive + 1 draw** | Separately SHA-checked frozen Stage A/verified results; not part of the earlier 153-row training archive |
| Historical UFCStats-compatible full fight archive | **8,871 UFC bouts reported in earlier source audit** | Source is a pinned third-party compatible export; direct first-party provenance remains gated, and sparse/debutant data still matter |
| Fully archived fight cards before Aug 8 | **Not established by this repository audit** | Earlier conversations may have scores, but do not silently promote recollections to immutable historical pick locks |
| Stage B strategy-selection ledgers | **5 events with documented stakes/results** | Not proof of actual user-placed bets or a repeatable FanDuel market edge; missing/zero-approved cards stay outside totals |

**Required distinction:** An archived post-event result or a backfilled prediction row is not the same thing as a contemporaneously frozen, source-verifiable pre-fight forecast. We will track these data classes separately.

## 2. All 12 historical events: original clean reference record

| Event date | Decisive fights | Winner correct | Method CLASS correct | Exact selected fighter + method |
|---|---:|---:|---:|---:|
| Aug 8 | 12 | 9 | 4 | 3 |
| Aug 15 | 12 | 6 | 3 | 1 |
| Aug 22 | 13 | 6 | 6 | 3 |
| Aug 29 | 13 | 9 | 6 | 5 |
| Sep 5 | 14 | 6 | 9 | 3 |
| Sep 19 | 12 | 8 | 4 | 3 |
| Sep 26 | 11 | 9 | 5 | 4 |
| Oct 3 | 14 | 13 | 10 | 9 |
| Oct 10 | 11 | 6 | 8 | 6 |
| Oct 17 | 13 | 3 | 9 | 3 |
| Oct 24 | 14 | 8 | 6 | 3 |
| Nov 7 | 14 | 9 | 9 | 5 |
| **153-fight total** | **153** | **92 (60.1%)** | **79 (51.6%)** | **48 (31.4%)** |

The September 26 DQ and October 10 draw are excluded from this clean 153-row record; strict original event grading retains those outcomes separately. Original Stage A picks across seven later events matched the independently archived source fighter choices for every one of their **89** gradeable clean fights.

**UFC 334 separately:** among **12 decisive fights** (13 scheduled including draw), Reference went **8/12 winners**, **3/12 finish-method classes**, **1/12 exact selected fighter+method**. Do not present the draw as a binary loss.

**Combined, with important provenance/vintage caveat:** **165 gradeable decisive fights** across these 13 dated events, **100 winner picks (60.6%)**, **82 method classes (49.7%)**, **49 exact fighter+method (29.7%)**. The two eras are mixed, so this is a descriptive accumulated record **not** an out-of-time model-promotable score.

### Chronology is not proof of improvement

- First five events (64 fights): **36/64 winners (56.3%)**, **28/64 method classes (43.8%)**, **15/64 exact (23.4%)**.
- Next seven events (89 fights): **56/89 winners (62.9%)**, **51/89 methods (57.3%)**, **33/89 exact (37.1%)**.
- UFC 334 alone: **1/12 exact** after the apparently stronger later 89. The history shows extreme event-to-event volatility, including **13/14 winners on Oct 3** versus **3/13 on Oct 17**.

These data do **not** support a claim that successive code updates caused the apparent early-to-late increase. Model vintages, fight conditions, opposition and volatility all changed; the evaluation process was not prospectively controlled.

## 3. Basic benchmark: does our complicated method model beat something simple?

Within the **first 64 fights**, the actual finish-method plurality was **KO/TKO: 31**, versus decision 21 and submission 12. If one chooses this *simple fixed method* using the first 64 **only**, then applies it to each **same model-selected fighter** for the next 89:

| Next 89 fights, unchanged fighter pick | Exact fighter+method |
|---|---:|
| Model's displayed method | **33/89 (37.1%)** |
| Fixed KO/TKO method selected from earlier 64 | **30/89 (33.7%)** |

**Three extra correct methods over 89 fights is not compelling proof of a sophisticated predictive advantage.** This is a retrospective sanity check, not a preregistered prospective strategy and not an odds-aware betting baseline.

Over the **full 153 retrospective records**, the displayed method went **48/153 exact** versus **50/153** exact for always choosing KO/TKO with the same locked fighter. The latter uses the full historical sample and is **not** an honest out-of-time performance claim; it emphasizes how little demonstrated incremental method edge is currently visible.

### Submission identification is an actual, measurable weakness

| Actual victory method | Occurrences | Model calls of that class | Correct method class | Correct fighter + that method |
|---|---:|---:|---:|---:|
| KO/TKO | 80 | 82 | 51 | 30 |
| Submission | **24** | **10** | **2** | **2** |
| Decision | 49 | 61 | 26 | 16 |

**Submissions are the largest identifiable classification weakness:** only **2 of 24 actual submissions** were identified by the recorded displayed method, and the first 64 historical rows identified **zero** of their 12 submission finishes. This is a better-falsifiable research question than reacting to whatever finish type dominated the last card. However, do **not** blindly increase submission probabilities; a later complete selected-fighter test must show improved proper scoring and exact outcomes.

## 4. FanDuel Stage B: do we actually have betting evidence?

The source contains five dated events with selected strategy stakes/results. September 19 has **two mutually exclusive histories**: its initial frozen selections, and its after-recheck final actionable selections.

| Alternative strategy-accounting treatment | Strategy picks | Risked | Strategy net | Strategy ROI |
|---|---:|---:|---:|---:|
| **After-recheck actionable Sep 19** plus other events | **9–10** | 14.0u | **−0.1661u** | **−1.19%** |
| **Originally frozen Sep 19** plus other events | **10–10** | 14.5u | **+0.6739u** | **+4.65%** |

**Do not add both.** Neither reflects a verified personal bet slip/bankroll; this is only a documented selection-grade record, with a tiny sample. UFC 333 Oct 24 has no frozen Stage B official card in the repo; Nov 7 and Nov 14 have zero approved stakes; their hypothetical research/top-five/virtual profits are excluded from this financial table.

We still do **not** have systematic evidence that Stage B clears FanDuel closing lines or produces a statistically repeatable post-vig value advantage. Raw model EV forecasts and retrospective virtual top-five units are not realized ROI.

## 5. Why earlier improvements did not hold

The research after UFC 334 established several distinct negative results:

1. **Global finish-rate and method intercept corrections** could improve a KO/SUB/DEC label **when the winning fighter was already known**, but worsened exact real selected-fighter predictions and six-class probability scores.
2. **Opponent-quality, UFC Elo and defensive-wrestling additions** produced little or no incremental improvement over a simple intercept correction in out-of-time *conditional-winner* method scores; selected-fighter tests then worsened.
3. **Knockdown/control/submission survival features** were successfully reconstructed, but their first selected-fighter method challenger did **not** improve exact outcomes. Reversals and control are not direct observed get-ups.
4. **Coherent winner+method+direct fight-distance projection** improved some three-event retrospective scores and remains a *mathematical integrity challenger*, **not** a demonstrated prospective edge.
5. We previously mixed distinct objects under the word *method accuracy*: method class ignoring fighter, conditional class given actual winner, global six-way top cell, selected fighter's conditional top method, and authorized fighter+method bets. Every future report must distinguish these explicitly.

No failed challenger is promoted because of its attractive backfit, and every negative experiment is retained for reproducibility.

## 6. New development contract — what happens before another model update

### Phase A — data provenance and model-health baseline (CURRENT)

Keep fixed source hashes and a structured, dated prediction/outcome/quote ledger: `event_id`, `bout_id`, fighter identities, prediction-generated UTC, feature-as-of cutoff, source availability, exact fighter-side probabilistic markets, outcome method and duration, draw/NC/DQ handling, FanDuel quote capture time, and *whether the wager was approved and actually placed*. Don't merge reconstructed labels with original real pre-fight snapshots.

**Completed now:** reproducible 153-grade / UFC334 audit, exact cumulative prefixes, 89 source-pick matches, fixed-method sanity baseline, method confusion and separate Stage B alternatives.

### Phase B — robust historical training rebuild (NOT YET COMPLETE)

Inventory which of the ~8,871 pinned historical UFC bouts have verified identities, method labels, timed rounds, significant/total strikes, takedowns/attempts, control, knockdowns, and source timestamps. Keep fights with unreliable/missing data tagged; do not turn absent data into zero performance.

Build one strictly pre-event fighter-and-opponent feature table with *only past fights*, prior UFC sample counts, opponent-quality-adjusted performance, reach/age, durability, grappling access and round survival. Start with a recent **2021–2026** training horizon plus documented sensitivity tests to older events; include debuts and regional transfer uncertainty explicitly. Use chronological **whole-event** train/test splits, never random bout splits or future opponent careers.

### Phase C — transparent benchmarks and objective promotion gates

Before another change, register and test these baselines: current Reference, existing Historical/Unified, 50% fighter coin flip, simple fixed-method KO/DEC/SUB, original no-vig market favorite/price probability **when real FanDuel source data exists**, and simple calibrated logistic/gradient-boosting challenger only after reliable features exist.

Score distinct objectives: binary winner Brier/log loss, selected fighter+method **six-outcome** log loss/Brier and exact method, class-wise SUB/KO/DEC precision/recall, direct GTD and 3/5-round timing hazards, confidence bucket reliability, and genuine approved-price ROI **net of vig**, not fabricated retrospective odds.

Promote **nothing** from in-sample or repeated tiny post-card tests. Require preregistered, pre-fight frozen and meaningful multiple-event holdouts; respect the project's existing **≥300 prospective-observation guard** where applicable. New challengers should beat the unchanged Reference with paired event-cluster uncertainty analysis, without deteriorating submission recall or winner integrity. Keep FanDuel Stage B fully separate and veto plays that fail provenance/calibration/edge gates.

### Phase D — disciplined future weekly process

- **Before fights:** freeze original Stage A and unchanged model views; optionally lock a distinct research candidate with timestamp and source hashes; Stage B uses real FanDuel prices and approval status only.
- **After fights:** append verified outcomes; grade all models and officially approved bets **without retraining or rewriting original locks**; record errors by *fighter*, *finish*, and *timing* categories.
- **Only after sufficient evidence:** merge a model/code change with a documented version number, before/after proper scores and a signed evaluation manifest. No weekly forced flips or hand-tuned submission/decision weights.

**Near-term priority:** submission identification and winner-calibration reliability, backed by clean historical features and fixed, truly held-out benchmarks. Do not infer that more model complexity alone will improve bets.

## 7. Reproduce and verify

- **Script:** `python tools/audit_wshlx_ufc_history.py`
- **Core validation:** `src/wshlx_ufc/longitudinal_audit.py`
- **Regression tests:** `pytest -q tests/test_ufc_longitudinal_audit.py`
- **Evidence JSON:** `reports/model_health/2026-11-17_FULL_HISTORY_BASELINE_AUDIT.json`
- **CI evidence:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44189206559
- **Raw old historical ledger:** `data/results/clean_ufc_153_2026-11-07.csv`
- **UFC334 separate grade:** `data/results/ufc334_2026-11-14_all_models_grading.json`

**Confirmed:** No Reference/Historical/Unified production predictions, frozen Stage A/B data, wager approvals, FanDuel quote locks, training weights or 10,000-simulation models have been changed by this audit.
