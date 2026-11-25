# WSHL_X — genuinely direct six-state worldwide MMA research v7, winner + method exact

**Verified historical CI:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44629780197 (success after explicit 50/50 float tie fix).
**Complete dated six-cell forecasts and scores:** GitHub Actions artifact `wshlx-direct-six-world-v7-full-chronological-research`.
**Code and tests:** `tools/benchmark_worldwide_direct_six_v7.py`, `tests/test_ufc_worldwide_direct_six_v7.py`, `.github/workflows/ufc-direct-six-world-v7-research.yml`.
**Status: research only; 70% exact and 2–5 perfect groups NOT achieved. No betting model promoted.**

The user prioritizes exact **winning fighter + KO/SUB/DEC class**, not submission count alone, and wants 2–5 exceptionally reliable exact picks from anywhere on each 11–14-fight card. Neither objective has been established by these tests.

## Architecture

Train six mutually exclusive fighter+method states **directly** rather than combining an independently trained winner head with a fighter-conditional method:
`A_KO_TKO,A_SUB,A_DEC,B_KO_TKO,B_SUB,B_DEC`.
Both participant orders are included for each dated historical fight with the corresponding first/second fighter outcome labels swapped. Predicting an event's two orientations and averaging with relabeling preserves side symmetry.

Candidate architectures:
- direct multinomial regularized logistic on 115 opponent-relative features (`direct_diff115`);
- direct multinomial logistic on ordered concatenation of both sides' 115 features (`direct_paired230`);
- direct HistGradientBoosting on 115 relative features (small depth/regularization).

The source is the exact FightCanon SHA256 `8185a2163b5f97071dbc4ec68667cceb43f5e321fadc38c26b5069303af4d949`, previously 3,016/3,036 verified UFC fight identities, plus original pinned UFCStats-compatible prior-only records; no current fight method leaks into training predictors. Training period starts 2021; 2024 results were trained on history strictly before 2024; 2025 before 2025; 2026 before 2026. For direct logistic **C selected using previous calendar validation year, not the target year** (2024 tests C=.005, 2025 C=.005, 2026 C=.025 for paired and difference). Small boost uses prespecified conservative depth/regularization. **All 2024–26 years have already been examined in previous WSHL_X experiments, so this is retrospective development, not pristine future holdout.**

Direct-six pick policy comparison is explicitly registered: global highest of all six outcome cells versus higher winner-marginal side, followed by its most likely method. Baselines are SAME-DATED v3-logistic57+Method v5 regional54 and v4-boost73+same Method v5. All classes graded with six-way log loss and Brier alongside exact hits, and 2/3/5 ranked exact subsets; event clusters are bootstrapped.

## Verified date-forward test results — direct paired230 with winner marginal method

| Year and fights | Direct paired230 winners | Direct paired230 exact | Factorized v3+v5 exact | Factorized v4+v5 exact | Direct 6-way log loss |
|---|---:|---:|---:|---:|---:|
| 2024 (511) | **314 (61.4%)** | 169 (33.1%) | **177** | **178** | **1.57196** |
| 2025 (513) | 324 (63.2%) | **198 (38.6%)** | 173 | 196 | **1.56814** |
| 2026 retrospective (488) | 304 (62.3%) | **161 (33.0%)** | 158 | 158 | **1.60653** |

Direct-paired six-way logloss BEAT both factorized baselines on all 3 dated periods (baseline v3+v5 1.59769,1.58895,1.61108). But 2024 exact 169 is BELOW both, and 2025/2026 gains are modest or unstable. On direct paired 230, choosing the **global** most likely outcome was not a better policy: exact 165/511,186/513,152/488 (versus 169,198,161 using winner marginal then method). A changed winner selection rule can make six-cell accuracy worse even if maximum probability was higher in the model.

Alternative architectures:
- direct difference115 winner-marginal exact 175/511, 163/513, 139/488; less reliable than direct bilateral.
- direct boosted115 winner-marginal exact 172/511, 167/513, 158/488; no strong exact improvement.
- Including significantly more bilateral data does NOT automatically yield 70%-exact wins; even at 2025's 198/513 exact, hit rate is just 38.6%.

### SUB and small selection groups

Direct paired winner-marginal correctly identified SUB **17/83 actual (2024)**, **12/91 (2025)**, **17/84 (2026)**. It did not solve SUB-class recall; cannot force submission quota or claim access to observed get-ups.

Top five direct paired exact-probability selections on 11–14-fight historical cards:
- 2024: **72/200** exact, 0/40 perfect five-pick groups;
- 2025: **82/195** exact, 1/39 perfect groups;
- 2026: **71/190** exact, 0/38 perfect groups.
Still no reliable way to guarantee all 2–5 exact predictions each UFC event.

### Critical grading bug found and fixed

In the first direct-six run, the baseline factorized winner probability of **exactly 0.5** was sometimes recomputed by summing three conditional method cells as `0.49999999999999994`, creating **two false winner-selection flips** in the 2026 evaluation. The bug is now fixed with a stable 1e-12 tolerance for only numerical 50/50 ties and an explicit assertion that recomputed factorized six-way exact/fighter grade equals the original `score_six(..., p_a=original_p_a)`. Unit tests cover near-ties, mirrors, direct-label mapping and draw exclusion. Corrected 2026 factorized comparison: V3 winner **303/488**, V4 winner **305/488**, exact **158/488** for both with Method v5. No frozen Nov21 records were edited. Code CI run https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44629780197 is post-fix.

## Research decision

**No promotion or official wagering action.** The bilateral six-state learner makes better probability estimates in historical periods, but exact winner+method choices remain around 33–39%, and no 100% 2–5 subset. Altering decision rules or searching many coefficient combinations using already studied events risks false discoveries. Keep Nov21 original Stage A, Coherent challenger, independently prospective winner v3, winner v4 and method v5 as originally frozen. Future genuine dated events, not revised old grades, are the decisive reproducibility test.
