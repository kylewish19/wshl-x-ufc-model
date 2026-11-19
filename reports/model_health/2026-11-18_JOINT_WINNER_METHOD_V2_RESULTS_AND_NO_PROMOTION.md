# November 18 — Independent winner PLUS matchup-specific method v2: verified results and NO promotion

**Status: RESEARCH-ONLY TRAINED & VERIFIED; DID NOT IMPROVE EXACT WINNER+METHOD PICKS.**

Reproducible code: `src/wshlx_ufc/independent_winner_v2.py`, `tools/benchmark_joint_winner_finish_v2.py`, `tests/test_ufc_independent_joint_v2.py`, and workflow `.github/workflows/joint-winner-finish-v2-research.yml`.

Successful GitHub Actions run: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44430124994

Archive: `wshlx-independent-joint-winner-and-method-v2-research`, containing `reports/model_health/2026-11-18_joint_winner_finish_v2/joint_v2_evaluation.json` plus all pre-event-feature-derived date-ordered out-of-fold predictions in `all_date_fold_forecasts.csv`. Source is the verified pinned secondary UFCStats-compatible archive; no future fighter career stats allowed in a pre-fight feature.

## Motivation and identity

Finish v1's method model was tested using **a fixed, simple prior UFC winning-rate head**, which cannot demonstrate improvement in the fight winner. In this research follow-on, a separate **symmetric regularized logistic winner learner** uses bilateral past-only matchup feature differences (striking/submission/takedown/control/defense, pre-bout Elo and opponent quality, missingness/debutant counts) with mirrored fighter roles to enforce `P(A) + P(B) = 1`. Its standalone winner probabilities are combined with the unchanged prespecified Finish-v1 **multinomial**, hierarchical or historical-global method conditional distributions for **both possible winning fighters**. All six exact fighter+method probabilities sum to 1 and are compatible with the winner head.

Three independent winner heads (prior UFC win-rate, UFC-only past Elo and newly fitted symmetric logistic), 3 predeclared method heads (global prior, hierarchical, multinomial) were compared on identical date groups, not chosen after learning the evaluation outcomes. The winrate-vs-new-winner plus SAME multinomial method comparison isolates whether a freshly fitted winner model boosts exact picks.

## Full-year strictly date-ordered evaluation

Train 2021–23, test 2024 (511 decisive, 42 events); train 2021–24, test 2025 (513 decisive, 42 events); train 2021–25, test already-viewed 2026 through Nov 7 (488 decisive, 39 events). Entire past event dates exclusive; mirrored side identity checks and test assertions passed. 2026 **not** pristine; original source and architecture have already been researched.

| Year | Prior-winrate + multinomial winner hits | New winner + multinomial winner hits | Prior-winrate + multinomial exact hits | New winner + multinomial exact hits | Prior + multinomial six-class log loss | New + multinomial log loss |
|---|---:|---:|---:|---:|---:|---:|
| 2024 (511) | 313 (61.3%) | 309 (60.5%) | **170 (33.3%)** | 169 (33.1%) | 1.6295 | **1.6077** |
| 2025 (513) | 310 (60.4%) | 305 (59.5%) | **175 (34.1%)** | 170 (33.1%) | 1.6208 | **1.6065** |
| 2026 (488, retrospective) | 294 (60.2%) | 293 (60.0%) | **151 (30.9%)** | 145 (29.7%) | 1.6552 | **1.6360** |

**Direct verdict:** New symmetric winner head improves log loss and Brier, but **does NOT improve the designated main metric: fighter+method exact accuracy** in any of the three tested years. The user's full-card objective is unachieved. New hierarchical method combined with the learned winner head produces 165/511, 165/513 and 142/488 exact, also not better than the prior-rate + multinomial baseline.

Binary winner Brier prior vs new in 2026: **0.2424 vs 0.2333**. A better calibrated probability does not automatically produce a better winner choice at the 50% threshold or a more correct six-class top pick. In 2026 the new winner + multinomial classifies **12** of 84 submissions correctly versus **7** under the prior-rate winner + multinomial, but gets **6 fewer** overall exact outcomes: class-level improvements cannot substitute for exact-pick improvement.

## Same 28 original SHA-frozen matchup comparison, October 24 and November 7

| Model on identical fight identities | Winner correct | Exact fighter+method | Six-class log loss |
|---|---:|---:|---:|
| **Original Historical** | **20/28** | 10/28 | 1.5837 |
| Original Unified | 19/28 | 11/28 | **1.5693** |
| Original Reference | 17/28 | 8/28 | 1.6348 |
| New symmetric winner + multinomial | 15/28 | 10/28 | 1.6239 |
| Past Elo + multinomial | 16/28 | **12/28** | 1.6133 |
| Prior UFC winrate + multinomial | 12/28 | 10/28 | 1.6260 |

The original Historical method joint is not coherent with its separate winner head, so scores are descriptive of its native probabilities and method selections; the new candidate is coherent. Don't promote a newly trained winner model on better log loss while missing more winners than frozen Historical on these two selected events. The 28 outcomes were already inspected during prior model development, so this comparison provides **no independent prospective claim**.

## Meaningful next tasks (uncompleted)

1. **Fighter-record quality coverage audit** for winners and finish labels: debutants, <5 UFC bouts, no same-weightclass or relevant recent history, insufficient source round/control data, physical covariates and opponent grappling style missingness. Draw a clear line between observed UFCStats and unobserved get-ups/positional chains; add only legitimate timestamped supplementary data when available.
2. **Exact-pick error decomposition** on archived original frozen fight forecasts: winner-missed vs winner-right/method-missed, outcome class, score magnitude, data coverage and challenger vs original on the same bout. Most recent 40 three-view events are best provenance; 153 original Reference grade rows have mixed original-time provenance.
3. **Ablation-first training design:** remove/add source-verifiable feature families and evaluate sensitivity by whole event and out-of-year folds; never random train/test split, never rely only on overall method prevalence or blanket +SUB/-DEC.
4. **Prospective challenger lock** only if both selection accuracy and proper scoring show replicated improvement against Historical/Unified and on events not used in development. The >=300 genuine prospective observation gate remains for promotion; no arbitrary future model confidence or odds. No pre-Nov21 retrospective challenger picks can be called prospective if not locked before the bout.

**UNCHANGED:** Nov21 original Reference/Historical/Unified Stage A, independent timestamped coherence shadow, seeded 10,000 simulations, FanDuel-only Stage B, past grades and betting ledgers. **No model trained here is authorized for betting.**

The meaningful action now is NOT another random coefficient tweak. We have directly verified the proposed independent winner replacement fails to improve exact predictions. Focus on real missing matchup information, leakage-safe feature quality, error decomposition and new event-locked testing instead.


## Follow-up verified 2026 winner-vs-method failure decomposition

GitHub CI success https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44430725166. Reproducible `tools/audit_joint_v2_failure_decomposition.py`, `reports/model_health/2026-11-18_joint_winner_finish_v2/winner_method_failure_decomposition.json` in the Actions artifact. All 488 outcomes and pre-event bout/stat coverage joined by exact bout ID.

| Error type (2026, 488 decisive fights) | Prior-UFC-winrate + multinomial | Newly trained winner + multinomial |
|---|---:|---:|
| Wrong winning fighter | **194** | 195 |
| Correct winning fighter, wrong finishing method | **143** | 148 |
| **Correct exact fighter and method** | **151 (30.9%)** | 145 (29.7%) |
| Correct method GIVEN correct winner | **51.4%** | 49.5% |

For the newly trained winner+method challenger, 109/488 decisive contests featured a UFC debutant on at least one side: **26/109 exact (23.9%)**. Among the 181 where both had at least five prior UFC bouts: **57/181 exact (31.5%)**. On the 83 contests with calculated winner probability >=70%, only **28/83 exact (33.7%)**, despite **62/83 correct winning fighter**. This demonstrates that winner-side confidence is not fighter+method confidence, and UFC sample size matters without solving the core problem. No ranking/eligibility threshold has been refitted to these historical outcomes.

**Mathematical bottleneck:** At 294/488 winner accuracy, even **perfect** conditional methods would allow at most 60.25% exact across all fights. To actually reach 60% exact at this winner level would require almost 100% conditional method correctness. A 70% exact full-card target necessarily needs winner accuracy materially above 70% **and** very high conditional method accuracy. Neither has been demonstrated; do not raise confidence labels or sim counts to imply otherwise.

**Do not ignore outcome quality:** 2026's roughly 17% submissions are not a requirement for forced submission calls. This new winner+method combination identified 12/84 actual SUB classes as the top class—better than the fixed prior-winrate combination's 7/84—but still missed 6 more exact fight outcomes overall. Primary optimization remains all-six exact outcome quality, not SUB share.

**Next research focus:** critical data-quality and feature-family audit, particularly transferable pre-UFC/debutant form, valid age/reach/weight-class metadata at prediction time, opponent grappling access and actual get-ups where ethically/legitimately measurable, plus recency and injuries. Then one prespecified chronological ablation and matched exact-score comparison. The unplayed November 21 card's Stage A and locked coherent shadow remain UNCHANGED. No candidate approved for bets or promotion.
