# UFC — Opponent-Aware Method Research: 153-Fight Chronological Ablation

**Date:** November 16, 2026

**Decision: DO NOT PROMOTE.** The added opponent-specific defensive features failed to demonstrate incremental improvement over an intercept-only correction in a seven-event, 89-fight chronological evaluation. We must not mistake a general KO/decision-rate shift for an opponent-quality or get-up model.

## What was actually tested

An **odds-blind, causal, prior-to-fight** reconstructed method dataset contains **153 historical fights** from Aug 8–Nov 7, 2026, and **12 event dates**. Exactly the first five dates (64 fights) provide the initial training period. Subsequent dates are evaluated with an expanding training window: only events strictly **before** each tested event can fit the candidate.

The forecast is **KO/SUB/DEC conditional on the actual winning fighter**, a research/oracle diagnostic. The model is NOT shown the current result at inference, but the training/evaluation rows are explicitly constructed from the true winning fighter's perspective. Therefore **49/89 is NOT 49 correctly predicted fighter-plus-method parlays**, and is not an official UFC betting card.

Three comparable, fixed-rule alternatives:

1. Original historical causal pre-fight conditional-method baseline (no new model).
2. **Intercept only:** regularized finish-vs-decision logit shift plus regularized submission-vs-KO logit shift, using training outcomes strictly before each held-out date.
3. **Opponent features:** the same intercepts plus six bounded pre-fight finish features and five pre-fight submission features. Factors include prior opponent KO/sub loss rates, prior significant-strike defense, prior TD defense versus winner's TD rate, winner's prior finish rates, recent finish rates, and five-round format. Sparse or missing stats are shrunk toward neutral priors; missingness is not misinterpreted as defenselessness.

Both logit stages use fixed regularization **ridge 20**, intercept penalty **10**, with no random test split, no FanDuel odds, no fight-day/post-event features, and no selection of the best lambda on the held-out events.

## Seven held-out event results — 89 fights

| Conditional method forecast | Correct top method | Six-class (3-method) Brier ↓ | Log loss ↓ |
|---|---:|---:|---:|
| Pre-fight causal baseline | 39/89 (43.8%) | 0.604224 | 0.973567 |
| Intercept-only | **49/89 (55.1%)** | **0.558746** | **0.915636** |
| Intercept + opponent features | **49/89 (55.1%)** | 0.558784 | 0.916460 |

**Incremental opponent-feature contribution:** 0 extra correct classes, **Brier worse by 0.0000387**, log loss worse by **0.0008243** relative to the intercept-only comparator.

### By evaluation event

| Held-out event | Prior training fights | Original correct | Intercept correct | Opponent correct | Original Brier | Intercept Brier | Opponent Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sep 19 | 64 | 5/12 | 4/12 | 4/12 | 0.6393 | 0.6465 | 0.6473 |
| Sep 26 | 76 | 4/11 | 5/11 | 5/11 | 0.6738 | 0.6084 | 0.6078 |
| Oct 3 | 87 | 6/14 | 11/14 | 11/14 | 0.5295 | 0.4397 | 0.4382 |
| Oct 10 | 101 | 4/11 | 7/11 | 7/11 | 0.6145 | 0.5023 | 0.5014 |
| Oct 17 | 112 | 6/13 | 7/13 | 7/13 | 0.6807 | 0.5414 | 0.5387 |
| Oct 24 | 125 | 6/14 | 5/14 | 5/14 | 0.6607 | 0.7011 | 0.7050 |
| Nov 7 | 139 | 8/14 | 10/14 | 10/14 | 0.4587 | 0.4815 | 0.4826 |

The Oct 3 card, with **11 actual knockouts in 14 fights**, accounts for half of the ten additional correct labels from the intercept adjustment. The last two held-out dates did **not** show an opponent-specific probability-score benefit.

**Critical external challenge already documented:** an earlier all-153-trained intercept calibrator tested against genuinely later UFC334 Nov14 **failed**. Exact frozen Reference winner+method remained 1/12, and conditional Brier/log loss became worse. This separate opponent-feature ablation (through Nov7) does not supersede that negative later result.

## Missingness is a real training limitation

Among the 153 data rows, **21** are missing a range of prior defensive metrics, including historical opponent KO loss/striking defense. Opponent TD-defense has **31 missing** and winning fighter TD-defense **36 missing** values. Prior three-round-retention has **59–61 missing**. Naively treating missing defenses as 0 would wrongly make sparse, newcomer-heavy fighters appear extremely vulnerable. These features were shrunk toward neutral priors, but 153 fights cannot identify reliable nuanced effects across this missingness.

## Technical and causal limitations

- The source dataset reports causal, pre-event feature snapshots and pre-event conditional baseline probabilities; however, it is a reconstructed research archive, not the contemporaneous user-approved FanDuel/Stage A lock for every bout.
- Since the dataset is oriented from the **actual winner's perspective**, it cannot by itself test win-side identification. We still require a true pick-oriented feature feed for a usable fighter + method predictor.
- All candidates were specified after prior cards were inspected; the retrospective seven-date comparison is **development evidence**, not prospective validation.
- Ridge 20 is intentionally conservative. Very small opponent-feature coefficients mean the model mostly learns a blanket finish-rate shift—not credible opponent durability or skill interactions.
- The conditional method objective is not a wager strategy; the time-of-lock Stage A winner, timing, and Stage B FanDuel price gate remain unchanged.
- A prior 153-fight model calibration challenger **failed on UFC334** (its distinct held-out test), so the apparent 89-fight improvement is insufficient for promotion.

## Next *structural* work, in order

1. **Build leakage-safe opponent-strength-of-schedule and prior-quality-adjusted records.** Our current win/loss and last-five finish rates do not measure whether those results came against established UFC competition. Build from each opponent's strength **as known before that earlier fight**; never use their eventual career rating.
2. Collect legitimate opponent-specific wrestling defense, time spent underneath, get-ups, and ability to force rounds to completion, with availability/missingness flags. A single TD% and a vague KO history are insufficient.
3. Train the improved conditional method model strictly on winning-fighter-perspective data, but **evaluate its deployment alongside separately frozen winner selections**, ensuring incorrect picked winners can never receive an exact method credit.
4. Benchmark against **both** original pre-fight baseline and intercept-only challenger with event-grouped chronological out-of-time proper losses, submission recall and exact fighter+method.
5. Keep the coherent Historical/Unified winner+timing IPF sidecar unpromoted until prospective evaluation. Maintain existing 300-bout promotion gate and FanDuel-only price authorization.

## Reproducible implementation

- `src/wshlx_ufc/opponent_aware_method_shadow.py`
- `tests/test_ufc_opponent_aware_method_shadow.py`
- Source: `reports/ufcvegas124_2026-11-07/full_stats/clean153_causal_method_inputs.csv`

**Governance:** No model weights, fit artifact, original Stage A odds-blind card, 10,000 simulations, Stage B gate, or original FanDuel prices changed.
