# WSHL_X Finish Model v1 — Independently Trained Matchup-Specific Method Challenger

**Date:** November 18, 2026
**Status:** RESEARCH-ONLY TRAINED + HISTORICALLY EVALUATED; **NOT PROMOTED**.
**Verified CI:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44424839095
**Artifact:** `wshlx-2026-11-18-independent-finish-v1-research` (complete fitted model bundle, yearly per-fight probabilities, source-checked original 28-bout comparisons, outcome labels and submission ranking metrics).

## What is actually new, and what is not

This is an **independently trained fighter-specific METHOD predictor**, not a fourth independent winner model and not an IPF/coherent edit of Unified. The initial evaluation deliberately **holds the winner head fixed** at a past-UFC-winrate baseline to isolate incremental method information. A future comparison can attach the same method predictions to frozen Reference/Historical winner heads, but this development alone does **not** demonstrate a new winner-prediction advantage.

Training and inference use only date-lagged UFCStats-compatible features:
- relative UFC experience/win history, pre-event UFC Elo/opponent quality;
- historic knockdown generation/absorption, KO survival;
- submission attempts, takedown production, control generated/absorbed;
- opposing takedown defense and submission-threat survival;
- fighter-offense x opponent-vulnerability interactions and debutant/missing-data flags.

No directly observed get-ups, regional competition, verified prefight division, height, age or reach measurements are invented. Source remains a pinned **secondary** UFCStats-compatible archive.

Four method variants trained/evaluated in parallel without searching parameter grids:
1. **Global prior:** 2021-to-before-test KO/SUB/DEC proportions, identical regardless of fighter (benchmark).
2. **Hierarchical (new):** independently fitted logistic P(finish|selected fighter wins) and P(SUB|finish, selected fighter wins); infer both possible winner sides, coherent six states.
3. **Multinomial (new):** independently fitted regularized 3-class KO/SUB/DEC conditional on each candidate winner, same matchup features.
4. **Nonlinear (diagnostic):** fixed-capacity low-depth regularized gradient-boosting finish and submission heads.

All models output P(A KO/SUB/DEC, B KO/SUB/DEC). Correct evaluation uses the **model-selected fighter**, never the real-life winner as an oracle. Missing UFC samples are flagged, not falsely interpreted as observed losses or observed zero performance. The fixed rate winner head is identical across variants.

## Strict date-ordered methodology

- Training **2021–2023 (1,503 decisive)** -> 2024 evaluation (**511** decisive bouts).
- Training **2021–2024 (2,014 decisive)** -> 2025 evaluation (**513** decisive bouts).
- Training **2021–2025 (2,527 decisive)** -> 2026 research evaluation (**488** decisive bouts through Nov 7).

2026 has been viewed, discussed and used in past WSHL_X development. Consequently **2026 is explicitly retrospective, NOT a pristine holdout**. The 2024/2025 years are chronologically source-leakage-safe for the current method builds, but are historical development/evaluation, not independently source-locked future predictions. Draws are excluded from binary winner+method scoring and are never converted to DEC.

## Exact fighter + method; unchanged rate-based winner head on each row

| Year | Global prior exact | Hierarchical exact | Multinomial exact | Nonlinear exact |
|---|---:|---:|---:|---:|
| 2024 / 511 | **171 (33.5%)** | 166 (32.5%) | 170 (33.3%) | 163 (31.9%) |
| 2025 / 513 | 155 (30.2%) | 172 (33.5%) | **175 (34.1%)** | 167 (32.6%) |
| 2026 / 488 (already inspected) | 125 (25.6%) | 148 (30.3%) | **151 (30.9%)** | 146 (29.9%) |

Mean six-class log loss (lower better):

| Year | Global prior | Hierarchical | Multinomial | Nonlinear |
|---|---:|---:|---:|---:|
| 2024 | 1.6661 | **1.6265** | 1.6295 | 1.6306 |
| 2025 | 1.6951 | **1.6207** | 1.6208 | 1.6308 |
| 2026 retrospective | 1.7279 | 1.6536 | 1.6552 | **1.6533** |

**Crucial failure:** 2024 exact outcomes are **worse** for all three trained challengers than the simple fixed method! The loss improvement alone does not prove the user's desired exact pick improvement. 2026 selected-fighter exact is only approximately **30%**, still far from the desired reliability.

## Is submission selection fixed? NO

Actual submissions / single-class SUB predictions / correct class on same date-fold:
- **2024:** 83 actual; hierarchical 33 SUB calls, **11** right; multinomial 39 calls, **12** right.
- **2025:** 91 actual; hierarchical 21 SUB calls, **10** right; multinomial 29 calls, **11** right.
- **2026:** 84 actual; hierarchical 20 SUB calls, **7** right; multinomial 19 calls, **7** right.

Thus 2026 hierarchical argmax **submission recall 7/84 = 8.3%** even with a separate submission head; do **not** claim the longstanding SUB problem is solved. However, its 2026 probabilistic expected number of fight submissions is **79.4 vs 84 actually observed**: accurate-looking overall prevalence does not make the highest-probability SINGLE method a correct submission selection. Overconfident forced category flips could worsen accuracy.

## New ranked-submission diagnostic (not betting advice)

Sort the DATE-OUT-OF-FOLD fights by predicted P(**the model-selected fighter wins by submission**), descending. Take the fixed top 10% based on scores alone; AFTERWARDS count actual exact fighter+SUB.

| Year | Selected-fighter exact SUB base rate across all fights | Hierarchical top-decile exact SUB | Multinomial top-decile |
|---|---:|---:|---:|
| 2024 | 48/511 = **9.4%** | **15/51 (29.4%)** | 13/51 (25.5%) |
| 2025 | 56/513 = **10.9%** | **16/51 (31.4%)** | 14/51 (27.5%) |
| 2026 retrospective | 50/488 = **10.2%** | **11/49 (22.4%)** | 11/49 (22.4%) |

The model recognizes SOME matchup-specific submission risk in probability ranking even when it rarely predicts SUB as the single top class. This is a diagnostic insight, not an approved SUB pick policy or a proven positive-EV strategy. In 2026 **38 of those 49 highest-ranked submissions still lost**; sportsbook price and real selected outcome probability would need independent calibration before any bet could be considered. Rank-based retrospective calibration and precision can change on future cards.

**Do not** redefine the official method pick from KO/DEC to SUB merely because it appears on a research top-decile list.

## Direct apples-to-apples comparison with archived Historical on 28 fights

Original SHA-checked UFC 333 and Nov 7 Vegas 124 Historical forecasts are aligned by exact date and fighter identity. All method candidates are attached to the **same original Historical winner probabilities** here (not their weaker rate winner head). Historical native six-state has its own winner-marginal inconsistency, so the winner-normalized variant is the relevant equal-winner comparator.

| Method family, same frozen Historical winner head | Exact fighter+method | Six-class log loss |
|---|---:|---:|
| Original Historical native method | 10/28 | 1.5837 |
| Original Historical method normalized to original winner marginal | 10/28 | 1.5814 |
| Simple earlier-era global method prior | 11/28 | 1.5726 |
| New hierarchical | 11/28 | 1.5636 |
| New multinomial | **12/28** | **1.5596** |
| New nonlinear | 9/28 | 1.5581 |

Both new logistic variants fail to identify either of the **two** actual submissions as their highest-probability method in this 28-bout matched subset; the Historical model correctly called one. **Two events cannot establish superiority**, especially when the dates were already examined in earlier research and candidate development.

## Model policy now

- **Production champion:** original Reference. Historical and Unified remain existing shadows; Coherent sidecar retains its original independently timestamped Nov 21 lock. NEVER rewrite it.
- **New independent method challenger:** all code and fitted-through-2025 research artifacts now archived, but **no new Nov 21 predictions are claimed or invented**, no code is plugged into the user's original three-model Stage A, and no FanDuel pricing is authorized.
- **Candidate status:** Multinomial has stronger exact counts on 2025/2026 and matched 28; Hierarchical has marginally better 2024/2025 log loss and stronger SUB risk ranking. **Neither dominates every meaningful metric.**
- **Rejected as promoted improvement:** nonlinear complexity has not shown consistent gains; do not automatically tune coefficients to a recent loss or force SUB rates.
- Preserve the 300 genuinely prospective observation promotion gate, and require meaningful event-cluster proper score and exact fighter+method improvements **against the actual frozen Historical AND Reference/Unified**, with SUB precision/recall protection.
- The next implementation task is an **as-of independent prospective fighter-identity/feature query adapter**, with legitimate UFC-only history available BEFORE the event, then source-hashed new research-only predictions locked before a future fight card. Do not fake a forward Elo rating from a current opponent's future record or copy current-career stats backward.
- Additional verified pre-bout weight class/3- vs 5-round schedule, grappling position/get-up video data and prior regional form may be useful, but cannot be added without legitimate as-of provenance. The model has no evidence of reliable sportsbook ROI.

## Reproduce

Code:
- `src/wshlx_ufc/finish_v1_research.py`
- `tools/benchmark_matchup_finish_v1.py`
- `tools/audit_finish_v1_submission_ranking.py`
- `tests/test_ufc_finish_v1_research.py`
- `.github/workflows/finish-v1-research.yml`

Output artifact from successful Actions 44424839095:
- `reports/model_health/2026-11-18_finish_v1_research/evaluation.json`
- `yearly_test_forecasts.csv`
- `matched_28_original_predictions.csv`
- `submission_ranking.json`
- `finish_v1_train_through_2025_RESEARCH_ONLY.joblib`

The historical source SHA256 is `f5b316d5e745bd89da921b2c9711ec9209c2fa39dcbcd80bcb063b62d9175bcb`. CI ran tests, full chronological benchmark, 28-bout source alignment, output digest checks, and submission ranking. **No model promotion, odds influence, changed 10,000 simulations, altered previous predictions, or rewritten betting records.**
