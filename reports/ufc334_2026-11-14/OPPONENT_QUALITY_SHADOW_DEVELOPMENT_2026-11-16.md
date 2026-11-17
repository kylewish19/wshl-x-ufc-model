# Opponent Quality and UFC Finishing Predictions — November 16 Research Update

**Status: source/feature engineering completed; opponent-aware prediction upgrade NOT promoted.**

This work extends the post-UFC334 Stage A/B audit and existing six-way probability coherence challenger. It is **not** an official WSHL_X pick card or FanDuel wager authorization.

## What was added to GitHub

1. `src/wshlx_ufc/prefight_opponent_quality.py` — UFC-only, **past-only** opponent-rating / strength-of-schedule snapshots. An earlier opponent's rating is frozen at the date of the *earlier fight*, before its result, so future career success never inflates an old win. Results of a shared event date are applied only after all that date's pre-fight snapshots are frozen. Newcomers have neutral ratings and sparse-data flags.
2. `src/wshlx_ufc/opponent_quality_join.py` — strict accent-aware exact-identity matching of each of the 153 pre-Nov14 conditional method examples to its pre-bout fighter and opponent ratings. **153/153 matched (100%)**, zero unmatched fighter identities. Missing data would be explicit, not silently converted to bad defense.
3. `src/wshlx_ufc/opponent_aware_method_shadow.py` — a low-capacity, opponent-defense method experiment using bounded prior KO/SUB loss, striking defense, TD defense, recent finish rates and five-round format; missing prior stats shrunk toward neutral priors.
4. `src/wshlx_ufc/quality_aware_method_shadow.py` — five-way chronological ablation including new quality-of-opposition Elo and previous opposition quality features.
5. Research-specific CI runner `.github/workflows/quality-aware-method-shadow.yml`, and regression tests for identity, future-leakage, same-day blocking and chronological model selection.
6. Full machine-readable report: `reports/ufc334_2026-11-14/QUALITY_AWARE_METHOD_153_7FOLD_RESEARCH_RESULTS.json`.
7. Reproducible research run: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/43986253261 .

## Results: 89 held-out fights across seven successive event dates

All training uses **only earlier event dates**, starting with 64 training bouts from five events and evaluating Sep19, Sep26, Oct3, Oct10, Oct17, Oct24, and Nov7. Predictions remain **conditional on the already-known actual winning fighter** for this diagnostic; these are not exact fighter+method hits.

| Research candidate | Method correct | Method Brier ↓ | Method log loss ↓ |
|---|---:|---:|---:|
| Frozen causal historical baseline | 39/89 | 0.604224 | 0.973567 |
| Intercept-only conditional method calibration | **49/89** | 0.558746 | 0.915636 |
| Intercept + basic opponent defense | **49/89** | 0.558784 | 0.916460 |
| Intercept + quality-of-opposition | **49/89** | **0.558435** | **0.914664** |
| Intercept + opponent defense + quality | 48/89 | 0.558617 | 0.915742 |

### Interpretation

- A simple historical finishing-rate intercept correction drove most of the apparent 39→49 method improvement, not the opponent-defense factors.
- UFC-strength-of-opposition features produced **no extra correct method predictions** over intercept-only. Quality-only had tiny proper-score gains (Brier −0.000311, log loss −0.000972), far too small to justify promotion.
- Adding opponent-defense features to the quality model instead lost **one correct call** (49→48), with slightly worse log loss than intercept-only.
- The earlier separate fully 153-trained method calibration already **failed** when tested against the later UFC334 card (same exact fighter+method 1/12, worse proper method scores). This later-event rejection is more relevant than squeezing a tiny fit improvement out of already-examined history.
- KO-heavy versus decision-heavy events fluctuate: the Oct3 KO-heavy card provided 5 of the 10 intercept extra hits; the Oct24 decision-heavy card showed a clear score deterioration. Don't train a global assumption that a fight must finish.
- Every example is outcome-oriented to the actual winner, so none of the above measures whether the candidate selects the **correct fighter**. Exact fighter+method must combine pre-event winner selections with a truly pre-fight fighter-perspective feature builder and score both together.

## Technical cautions

- Archived UFCStats-compatible CSV is third-party historical data (through Nov7), **not proof of direct first-party UFCStats access**. This opponent-only Elo is a starting approximation; it does not cover opponent quality in international/regional fights before a UFC debut.
- Ratings are constructed solely from UFC win/loss/draw outcomes and reflect a simple deterministic Elo rule; ratings do not imply causal fight quality and are not bookmaker value forecasts.
- Fights on a shared date use **snapshots frozen before that date**; no future fight updates affect them.
- Historical conditional baselines are research reconstructions, not all contemporaneously frozen original betting/pick records.
- UFC334's separately collected 26 fighter totals and 72 fighter-round rows remain **provisional**, withheld from champion training pending source approval.
- No modifications were made to Reference/ Historical/ Unified production models, Stage A, Stage B, 10,000 simulations, frozen prior picks, FanDuel odds, or official betting decisions.

## Required next gate for any improvement

The next model-development test must use **fully pick-oriented** fighter/opponent features (not an actual-winner oracle), include defensive durability and get-up statistics from prior fights and strength-of-opposition **before the forecast date**, then compare proper scoring, exact fighter+method, submission recall and 3- vs 5-round timing on multiple untouched event dates. Keep the 300-prospective-observation promotion policy.

**Current status: opponent quality infrastructure passes tests, but there is NO demonstrated incrementally accurate opponent-aware method predictor to promote.**
