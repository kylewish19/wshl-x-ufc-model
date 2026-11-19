# Historical handoff — 2026-09-15

This document preserves only the recoverable high-level state transferred into this repository.

## Clean current-model UFC sample

Through UFC Paris on September 5, 2026:

| Metric | Record |
|---|---:|
| Winner | 36-28 (56.3%) |
| Displayed method | 28-36 (43.8%) |
| Winner + displayed method | 15-49 (23.4%) |

Displayed method calls across the 64-fight clean sample:

- Predicted: 37 DEC / 25 KO / 2 SUB
- Actual: 21 DEC / 31 KO / 12 SUB

This supports a real submission-recall / decision-heavy concern. The response is **not** to force more submissions. The research target is to improve conditional access and finishing-pathway features.

## Paris timing snapshot

Directional grades recorded in the handoff:

- round totals: 33-11
- goes distance: 8-6
- round starts: 20-10

These are correlated market observations across 14 fights, not 64 independent wagers and not a profitability claim.

## v0.26 status

A prior workspace reportedly executed a v0.26 experimental residual method challenger, tests, and replay. Final archive saving and master-audit writeback were not completed and the workspace was later removed.

Therefore this repository does **not** claim to possess or reproduce the old trained v0.26 package. Any rebuild must get a new version/hash unless exact artifacts are later restored and verified.

## Preserved research lessons

- access before weapon
- distinguish takedown attempts from successful access/control
- account for opponent get-ups and counter-grappling
- model offensive-wrestling exposure that can create neck/back/scramble danger
- distinguish attempted volume from durable control
- track KO, SUB, and DEC recall separately
- do not use result labels as retroactive prefight features
- do not rewrite old locks after grading


## November 17, 2026 — evidence-first model reset

**START FUTURE DEVELOPMENT HERE:** `reports/model_health/2026-11-17_EVIDENCE_FIRST_MODEL_RESET.md`

- A reproducible full-history reference audit now covers 153 clean,
  reconstructed graded fights on 12 event dates Aug8–Nov7 and 12
  decisive UFC334 results; mixed-vintage combined 165 decisive
  examples: **100 winner correct; 49 exact fighter+method**.
- The cumulative 64→153 source archive has 8 exact prefix snapshots.
  Separate original Stage A sources matching the reference picks are
  present for **89 later clean fights**; the first 64 remain reconstructed
  historical grade snapshots, NOT separately timestamped Stage A files.
- Most concrete method weakness: **24 actual submission finishes,
  only 10 SUB class calls and only 2 class/selected-fighter correct**.
  No automatic SUB adjustment is promoted.
- Fixed early64-selected KO/TKO on the same fighter scored **30/89
  exact** on the subsequent 89, versus the model's **33/89**;
  incremental advantage is not convincing in this tiny, retrospectively
  explored sample.
- Recorded FanDuel Stage B selection accounting depends on Sep19
  ledger choice: final actionable 9–10, -0.1661u/14u vs original
  frozen 10–10, +0.6739u/14.5u. These are **alternative records**,
  NOT actual user wagers; no demonstrated market beating.
- Pinned historical 2021–2026 archive eligibility audit:
  **3,036** complete-stats fights, **2,544** dated 2021–2025
  possible training bouts, **492** 2026 already-observed retrospective
  fights, **21 draws** explicitly separated from the **3,015 decisive**
  win/loss labels. Data includes **568** UFC-debutant and **1,873**
  under-5-prior-UFC-bout matchups. Do NOT let the source's
  decision-*method* string convert a DRAW into a winner by decision.
  Direct first-party UFCStats provenance remains unverified.
- Negative post-UFC334 intercept, opponent-quality and finish-resistance
  challengers remain unpromoted, even if conditional-known-winner
  scores looked attractive. Coherent joint winner+timing is a separate
  prospective research sidecar, not the champion.
- **No model promotion or retraining is authorized until an event-
  chronological real selected-fighter test beats simple/reference
  baselines on proper scores and exact method; honor the existing
  >=300 prospective sample gate where applicable.**

**Reproduce and inspect:**
`src/wshlx_ufc/longitudinal_audit.py`,
`tools/audit_wshlx_ufc_history.py`,
`reports/model_health/2026-11-17_FULL_HISTORY_BASELINE_AUDIT.json`,
`src/wshlx_ufc/historical_training_eligibility.py`,
`reports/model_health/2026-11-17_2021_2026_TRAINING_ELIGIBILITY.json`.

All original Reference/Historical/Unified predictions, immutable Stage A/B
locks, 10k sims, consensus/editorial artifacts and FanDuel gates remain
**unchanged**. The next development action is a timestamped 2021–2025
pre-event feature matrix and rigorous baselines, **not another
post-card-picked correction**.


## November 17, 2026 — executed time-safe feature matrix and retrospective baselines

**START FROM LATEST VERIFIED RESEARCH RESULTS:** `reports/model_health/2026-11-17_EXECUTED_HISTORICAL_BASELINES.md` (GitHub Actions PASS: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44193866672).

- A full **8,871**-bout as-of-date fighter/opponent matrix and strictly separate post-event label table were generated, keyed and SHA-verified; historical data source remains pinned SECONDARY UFCStats-compatible, not first-party validated.
- **2021–2025:** 2,544 bouts (2,527 decisive, 17 draws), 212 events. **2026 retrospective:** 492 (488 decisive, 4 draws), 39 events. All 21 modern draws are excluded from binary labels.
- First non-trained 2026 winner benchmarks: 50/50 Brier **0.250000**, UFC-only pre-event Elo **0.246109** (56.76% correct), smoothed past-UFC win rate **0.242448** (60.25% correct). Six-class exact fighter+method: **23.57% / 23.36% / 25.61%**, respectively.
- DEC class moved from **49.98% of decisive training finishes** (2021–25) to **42.01% of 2026 decisive finishes**. KO/TKO rose from **32.33% to 40.78%**; submissions **17.69% to 17.21%**. Not sufficient to force method changes.
- 2026 outcomes have been inspected in prior research. This is **NOT** an unseen independent holdout. Reference/Historical/Unified have not yet been paired against these same 488 historical fights. Do not claim new-model gain, FanDuel edge or profitability.
- No production champion, Stage A/B original predictions, FanDuel approvals, sim weights or grading ledgers modified. Existing >=300 genuinely prospective observation guard remains.
- **Next exact work item:** join original time-frozen Reference/Historical/Unified picks by event date and stable fighter ID to the corresponding as-of baseline probabilities on the **same** bouts; keep reconstructed-only rows separate. Report paired event-cluster proper scores and finish-class recall; preregister prospective challengers only after that.


## November 17, 2026 — matched original Reference selection comparison

**LATEST EXACT RESUME POINT:** `reports/model_health/2026-11-17_MATCHED_REFERENCE_INTERPRETATION.md`. Verified CI https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44195202280, artifact `wshlx-historical-feature-baselines-research`. The runnable script is `tools/audit_matched_reference_baselines.py` and its output JSON is in the run artifact (`reports/model_health/2026-11-17_MATCHED_REFERENCE_BASELINES.json`).

- **153/153** archive fights joined exactly on event date and fighter pair to pre-event historical features/outcomes; no missing rows. One source name abbreviation (Stan vs Stanley Dorsainvil, Aug22 vs Gauge Young) is explicitly whitelisted after date/opponent/DEC-outcome corroboration, not fuzzy-matched.
- SAME-FIGHT winner selections: across the **153 reconstructed** grade rows, Reference **92**, smoothed past-UFC win-rate **83**, prior-only UFC Elo **82**; the original Stage A subset **89**: Reference **56**, win-rate **45**, Elo **45**; only **41** across three dates have timestamp evidence, where Reference **20**, win-rate **17**, Elo **22**. The paired 153-row event-bootstrap difference Reference minus win-rate has interval **-1.99pp to +14.74pp** (crosses zero).
- The displayed Reference has exact fighter+method **48/153**, **33/89**, **11/41**; same Reference fighter plus fixed recent-era DEC has **30/153**. The original full-history audit also documents same Reference fighter plus KO **50/153** and next-89 KO **30/89**, compared with displayed **33/89**. No method improvement has earned promotion.
- **DO NOT** claim Reference reliably beats Elo based on retrospective 153: the best timestamp-evidenced 41 has Elo 22/41 and Reference 20/41. The results were all studied previously, so they are not an unseen prospective experiment. Cross-vintage original probabilities are incomplete; no paired Reference-vs-baseline Brier comparison is authorized from the 153 selection ledger.
- Still no code/model promotion or odds, wager, Stage A/B, FanDuel or old grade changes. The **next research action** is to recover aligned original timestamped *probabilities* (not only winner decisions) and assess proper Brier/log-loss / six-class selected-fighter method and whole-event uncertainty, then build truly prospective frozen challenger evidence under >=300 observation rule.


## November 17, 2026 — original frozen three-view probability audit

**LATEST RESUME POINT:** `reports/model_health/2026-11-17_FROZEN_THREE_VIEW_PROBABILITY_INTERPRETATION.md`; CI https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44196129448. Script `tools/audit_frozen_three_view_probabilities.py` and full probability JSON in Actions artifact.

- Three SHA-linked, pre-event original final locks (Oct24, Nov7, Nov14): 41 bouts, 40 decisive, 1 draw. Edmonton Reference-only not pooled. Reference/Historical/Unified winner hits **25/26/26**, winner Brier **.233163/.223540/.222212**, exact own-selected fighter+method **9/13/14**, six-class log loss **1.638220/1.571287/1.561095**, SUB correct **0/3/3** of 4 actual. Three-event retrospective sample, not independent prospective validation.
- Same 28 Oct24/Nov7 bouts matched to past-only baselines: Reference/Historical/Unified winner Brier **.239178/.213633/.217474**; Elo **.239443**, prior UFC win rate **.245762**, 50/50 **.25**. Shadow winner-Brier bootstrap intervals against Reference cross zero.
- **Integrity veto:** among 41 bouts, native joint winner marginal differs from native winner head >1pp in Reference **0**, Historical **34**, Unified **33**. Max shadow gaps **17.57pp/10.23pp**. These are not coherent fighter+method pricing distributions. GTD Brier **.238074/.236604/.235771** on all 41, 22 observed full-distance bouts.
- No training, promotion, original model/lock, Stage A/B, odds or grading changes. No inference of betting advantage. NEXT: preregister a coherent research-only joint distribution with the same winner marginal, examine direct timing compatibility and score native/coherent/simple baselines on identical future locked predictions. Keep >=300 prospective observation guard; do not treat these historical rows as genuine new prospective evidence.


## November 18, 2026 — UFC Qatar original Stage A and first pre-event coherent lock

**LATEST LIVE-CARD RESUME POINT:** `reports/ufcqatar_2026-11-21/STAGE_A_FROZEN_AND_COHERENT_SHADOW_HANDOFF_2026-11-18.md`. Verified [GitHub Actions run](https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44402086325). Source final Stage A frozen **2026-11-18T21:31:31.338799+00:00**, separate research coherent shadow generated **2026-11-18T21:31:33.464944+00:00**; both committed to research branch before Nov21 first-fight start.

- User provided **11** matchups, independently matched to UFC event page. Late reported **John Mitchell vs Shoaib Yousaf** was included as explicitly **PROVISIONAL fight 12** and marked PASS after 0/0 prior UFC fights produced an extreme raw Reference 96.4% outlier; this is NOT a betting confidence.
- Original three-model Reference/Historical/Unified winner, selected-fighter method and full timing distributions came from the unchanged Nov7 model lineage and **actual 10,000 seeded simulations**. All raw/summary/final frozen source hashes verified. Original 11 Reference winners in order: Nurgozhay, Dom Mar Fan, Matthews, Albazi, Tallison Teixeira, Santiago Luna, Aliskerov, Horiguchi, Hooker, Kevin Vallejos, Navajo Stirling. No price inputs, no Nov14 UFC334 outcome fitting.
- Three unpromoted research coherence projections PER original model are now **pre-event SHA-frozen** in `data/shadow_locks/ufcqatar_2026-11-21/coherent_joint_pre_event_shadow.json`; NOT a fourth independent winner model. No bets authorized, no original picks rewritten.
- Stage A PASS: 1,3,4,6,8,9,12; winner disagreements: 3,4,8; method-vs-timing price-gate conflicts: 2,3,4,6,9,10. Only one primary timing market per bout; all other odds-blind timing probabilities preserved.
- NEXT: Nov20 weigh-in, official source confirmation/cancellation audit for extra bout, then **FanDuel-only Stage B**. After card, separately grade genuine first prospective coherent shadow fights (0/300 graded as of lock); use original immutable locks and audit uncertainty. Model promotion **NONE**.


## November 18, 2026 — independently trained matchup-specific Finish v1 research

**LATEST MODEL-DEVELOPMENT RESUME POINT:** `reports/model_health/2026-11-18_INDEPENDENT_FINISH_V1_RESULTS_AND_DECISION.md`. Successful research/tests/Chronological scoring [GitHub Actions](https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44424839095), artifact `wshlx-2026-11-18-independent-finish-v1-research`. All source, code, per-fight historical probabilities, independently fitted models, true submission-ranking diagnostics and proper scores are preserved there.

- **New prediction research code** `src/wshlx_ufc/finish_v1_research.py`: conditional fighter-specific finish vs DEC, SUB vs KO models, with pre-fight opponent-interaction features and separate full multinomial and nonlinear comparators. Both fighter orientations are forecast prospectively; actual winners are used ONLY in historical model fitting/evaluation. Not a Unified, consensus, or Coherent/IPF blend. **Winner-head fixed to a past UFC-winrate baseline for method-only comparisons**, not a new validated winner predictor.
- **Chronological evaluation:** train 2021-23 -> 2024 511 fights: global-prior **171** exact, hierarchical **166**, multinomial **170**; train through 2024 -> 2025 513: **155 / 172 / 175**; train through 2025 -> 2026 retrospective 488: **125 / 148 / 151**. Nonlinear did not consistently outperform. 2026 previously examined; NOT a new prospective holdout. Proper log-loss improved vs simple baseline, but 2024 **exact** degraded. No model promotion.
- **SUB is NOT fixed:** 2026 hierarchical still only **7/84** actual submission classes correct, despite ~**79.4 expected fight submissions vs 84 actual**. On model-selected-fighter SUB probability ranking, fixed top 10% of 2026 fights contained **11/49** exact submissions (22.4%) vs 10.2% overall base; 2024 **15/51** (29.4%), 2025 **16/51** (31.4%). Ranking diagnostic only, **NOT** official method picks or authorized bets.
- **Same two original Historical frozen events (28 bouts):** Original Historical normalized to same frozen winner head exact **10/28**, six-class log loss **1.5814**; new hierarchical **11/28, 1.5636**; new multinomial **12/28, 1.5596**. Neither new model predicted the method of either actual submission on those 28; Historical identified one. Two previously studied events do NOT prove better future model performance.
- **Next exact development gate:** build an independently source-verified future as-of feature adapter for this method model; before any eligible new card, preregister and timestamp original *research-only* future forecasts. Preserve original 11/21 Stage A and locked Coherent sidecar without modification; do not claim new independent 11/21 method predictions from historical scores. Later grade paired proper scores, exact fighter+method and sub call precision/recall with original Historical, Reference and Unified. Existing >=300 genuine prospective-observation policy stays intact. **No model/price/wager promotion.**


## November 18, 2026 — exact-outcome full-card and top-5 selection audit

**LATEST MODEL-SELECTION DEVELOPMENT RESUME POINT:** `reports/model_health/2026-11-18_TOP5_EXACT_SELECTION_RESULTS_AND_POLICY.md`; passed GitHub Actions https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44427740203. Source-verified code `tools/audit_finish_v1_top5_exact_selection.py` and generated `reports/model_health/2026-11-18_finish_v1_research/selection_top1_to5_diagnostic.json` in Actions research artifact. No original frozen predictions/odds/wagers/production models modified.

- User target **60–70% exact fighter + method across entire 11–14 bout card**, aspirational 100%; also desires 2–5 carefully selected extremely high-hit exact bets, but 100% cannot be guaranteed and need not force 2–5 picks when evidence doesn't clear strict gates.
- 117 11–14-decided-bout historical UFC cards (2024/2025/previously studied 2026, total 1,456) using independent research Multinomial Finish v1 + SAME fixed prior-UFC-win-rate winner head. Sort fights by highest of all six exact fighter+method P BEFORE reading outcomes. Top 1: **44/117 exact**, top 2: **88/234**, top 3: **132/351**, top 4: **169/468**, top 5: **212/585**. All selected correct on only **12/117** top-2 cards, **3/117** top-3 cards, **0/117** top-5 cards. The recent model cannot identify 2–5 near-certainties.
- Alternative rank the model's selected fighter+method by that exact P: Top 1 **46/117**, Top 3 **140/351**, Top 5 **223/585**, still 0/117 perfect top-5; rank the same exact pair by winner-only P: Top 1 **43/117**, Top 3 **135/351**, Top 5 **212/585**. Winner confidence is NOT exact-outcome confidence.
- Across all 1,512 date-ordered evaluated fights, Multinomial's biggest global six-cell probability is only **~51.3%**; only 1 fight >50%, none >55%. Do not manufacture 90–100% bet-lock confidence using the highest model rank.
- **NEXT:** maintain independent full-card exact score and separately top 1–5 selection quality + whole-parlay-perfect outcomes, use prospectively pre-locked probabilities and calibration, and permit **zero** selected bets when nothing passes independent source/odds/data/EV gates. Continue developing winner+method model together (winner accuracy bounds exact), with original Nov21 Stage A and coherent sidecar entirely untouched.


## November 18, 2026 — newly trained winner plus method failed to improve exact picks

**LATEST RESEARCH RESUME POINT:** `reports/model_health/2026-11-18_JOINT_WINNER_METHOD_V2_RESULTS_AND_NO_PROMOTION.md`; [fully verified Actions](https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44430725166). Trained code `src/wshlx_ufc/independent_winner_v2.py`, full chronological benchmark `tools/benchmark_joint_winner_finish_v2.py`, 2026 breakdown `tools/audit_joint_v2_failure_decomposition.py`, test `tests/test_ufc_independent_joint_v2.py`; complete per-fight research forecasts and results in run artifact `wshlx-independent-joint-winner-and-method-v2-research`.

- Directly tested whether replacing Finish v1's simple historical winrate winner head with an **independently trained fighter-relative symmetric logistic winner model** improves 6-outcome exact fighter+method with the same multinomial method conditional. **NO:** 2024 exact **170/511 old vs 169/511 new**, 2025 **175/513 vs 170/513**, 2026 retrospective **151/488 vs 145/488**. New winner probabilities have better Brier/log loss, but worse raw winner choice and exact choice. This is not promotion-worthy.
- Same 28 original SHA-locked Oct24/Nov7 fights: original Historical **20/28 winners, 10/28 exact**, original Unified **19/28 winners, 11/28 exact**. New independent winner+multinomial **15/28 winners, 10/28 exact**; no claims of outperforming proven locked views.
- 2026 decomposition new model: **195/488 wrong winner**, **148/488 right fighter but wrong method**, **145/488 exact**. Even among 83 fights with winner-confidence >=70% it made **62 correct winners but just 28 exact outcomes**. With at least one UFC debutant **26/109 exact (23.9%)**, versus both with >=5 UFC bouts **57/181 exact (31.5%)**. Sparse/missing UFC data are real issues; naive data gates do not repair core signal.
- **Important upper bound:** current historical ~60% winner hit rate caps full-card exact at 60% even if method prediction were perfect. The user wants 60–70% exact across every 11–14 fight card and a small near-perfect 2–5-fight subset; no existing research has proven such performance and no 100% group can be guaranteed.
- **Now** inspect date-as-of data missingness/transfer limitations, test source-valid new matchup features (not arbitrary coefficient/tally boosts), use year/event chronological ablations and compare all-six exact selections plus proper scores on same fights. No modification to original Nov21 Stage A, independent Coherent shadow, FanDuel Stage B, prior grades or prospectively frozen predictions. **No new model promoted.**


## November 19, 2026 — active four-part exact-outcome development (not promoted)

**LATEST DEVELOPMENT RESUME POINTS:**
- `reports/model_health/2026-11-19_PHASE2_EXACT_FEATURE_ABLATION_DIRECT_SIX_AND_SELECTION.md` (passed CI https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44432085423, artifact `wshlx-phase2-exact-outcome-research`).
- `reports/model_health/2026-11-19_PHYSICAL_WEIGHTCLASS_LAYOFF_SOURCE_RESULTS.md` (passed CI https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44433269497, artifact `wshlx-pre-event-profile-weightclass-layoff-research`).
- Selective historical meta gate: `tools/audit_learned_exact_reliability_gate.py`, added to `.github/workflows/ufc-phase2-exact-outcome-research.yml` to validate before claiming results.

**User's precise goals:** 60–70% full-card exact fighter+method (11–14 fights), aspire to 100%; find anywhere on card 2–5 unusually reliable exact picks, aspire perfect subsets but neither near-certainty nor forcing a fixed number of bets is justified.

**What has been executed:** 
1. Audited the actual pinned feature matrix (8,871 bouts, 3,036 modern 2021-26, 3,015 decisive; 2026 110 UFC-debutant bouts and 310 bouts with a fighter under five UFC bouts). Existing matrix was missing age/reach/height/division-specific UFC experience/layoff/regional form/getups. Source archives DO contain pinned 2026 fighter profiles and fight divisions.
2. Six predeclared feature-family ablations, fit through prior years and scored 2024/25/26: baseline factorized exact **169/511, 170/513, 145/488**; remove grappling **171/511, 162/513, 148/488**, but six-class log loss worsens every year and all correct SUB classifications collapse to zero. No feature-family deletion earned promotion.
3. Newly fitted symmetric direct-six-outcome model versus factorized exact same fights: direct6 **168/511, 160/513, 143/488**; underperforms exact full-feature factorized in each year. Do not promote.
4. Pre-declared 2–5 anywhere-on-card strict exact-consensus+UFC evidence filter: 2024 **38/82** exact (46.3%); 2025 **21/70** (30%); 2026 **23/75** (30.7%). It did NOT reliably improve picks; perfect 2–5 subsets **4/27,1/20,3/24** card dates. Higher confidence winner ≠ higher exact result.
5. New truly source-hashed DOB age on event day, previous UFC layoff and same-weightclass UFC experience from date-locked fight histories, plus 2026-vintage height/reach snapshots. **All 3,036 modern feature-bout identities joined**, no ungrounded aliases. One ambiguous repeated SAME-date source pair (Sakuraba–Silveira, legitimate 1997 same-night rematch) was quarantined because date+pair cannot identify two separate bouts; no modern rows lost. Vintage caveat for physical profile revisions is explicit.
6. Factorized full-profile exact 2024 **182/511**, 2025 **185/513**, but 2026 **136/488** versus original **145/488**; in 2026 full-profile winner picks improved 293→301 but exact degraded 145→136. Historical 2024/25 gains DO NOT transfer into 2026, so no new predictive model improvement proven.

**Next step:** specifically investigate metadata regime shift, debutants, age/reach missingness and division moves; then investigate a source-timestamped prospective feature adapter for independently locked FUTURE research challenger picks, and only promote with valid out-of-time paired winner+method and six-outcome scores. Current 2026 historical year already researched, not pristine. Physical reach/height from 2026 source isn't a verified as-of 2024 profile. Keep FanDuel-only Stage B separately. **NO CHANGE** to original November 21 Stage A, independently locked Coherent Challenger, model weights, price gates, old grading, or officially selected bets; no new model promoted.



## November 19, 2026 — trained exact-pick selection gate failed and source-vintage error localized

**FINAL RESEARCH RESUME POINT:** The two up-to-date reports are `reports/model_health/2026-11-19_PHASE2_EXACT_FEATURE_ABLATION_DIRECT_SIX_AND_SELECTION.md` and `reports/model_health/2026-11-19_PHYSICAL_WEIGHTCLASS_LAYOFF_SOURCE_RESULTS.md`. Latest phase2 CI with saved 2025/2026 learned selective classifier: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44434146283, artifact `wshlx-phase2-exact-outcome-research` with `trained_selective_gate_2025_2026.json` included.

- **Learned meta selection failed:** trained logistic on PREVIOUS year/date-fold exact probability/coverage/agreement features. On 2025 cards: top3 **41/117** exact vs same model's exact-probability ranking **47/117**; on 2026: **40/114 vs 42/114**. Top 5 similarly did not improve. 60% estimated-accuracy threshold + both fighters 5+ UFC prior fights led to **1 missed pick on 39 cards (2025)** and **0 picks on 38 cards (2026)**. No 2–5 selection group cleared; no new bettor reliability demonstrated.
- **2026 physical-feature failure localization:** 488 dated decisive outcomes, factorized full-profile versus old 38-field exact: **136 vs145**. The main regression is decisions (65 vs86 exact), despite 56 vs47 KO and 15 vs12 SUB exact. Both fighters 5+ UFC prior fights: exact **44/181 vs57/181**. This is not merely a debutant sparsity problem. Winner head improved 301 vs293, exact declined 136 vs145.
- Data metadata 1997 same-day key issue is a LEGITIMATE Sakuraba vs Marcus Silveira rematch on the same UFC Japan card, not a fabricated duplicate. The research context builder quarantines one ambiguous date/event/pair identity, with zero losses in modern 3,036 matches. Current DOB and reach vintage is a later pinned 2026 snapshot; do not label reach historical-as-of verified.
- **No promotion, no betting approvals, no retroactively invented Nov21 Finish v1/v2 predictions.** Nov21 original Stage A and Coherent shadow hashes unchanged, all prior grades untouched. Next code actions should diagnose prior event date coverage, physically meaningful and verified fighter data, actual position/grappling access (not counterfeit get-ups), plus fresh truly prospective source-locked challenger and event-cluster paired six-state scoring. Current 2024–2026 backtests are already development evidence; 300-fight promotion guard remains for genuine prospective outcomes.
