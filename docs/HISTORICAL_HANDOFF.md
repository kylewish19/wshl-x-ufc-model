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


## November 19, 2026 — winner v3 recent-form benchmark and prospective Qatar lock

**LATEST VERIFIED RESUME POINT:** `reports/model_health/2026-11-19_WINNER_V3_RECENT_FORM_AND_NOV21_PROSPECTIVE_SHADOW.md`.
- **New actual model development**: 19 UFC fight-date-exclusive prior significant-striking/defense, recent-3/5 form, TD accuracy/defense, streak/layoff/coverage variables added to previously audited 38 features. New `src/wshlx_ufc/winner_recent_form_v3.py` and `tools/benchmark_winner_recent_form_v3.py`; tests passed, [Actions run](https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44616520174), full forecasts in `wshlx-winner-v3-recent-form-2024-26` artifact.
- **Chronological same-method-head winner model comparison:** old regularized winner logistic 38 vs new logistic 57:
   - 2024 winner 309→310/511, exact fighter+method 169→168, six-class log loss 1.60769→1.60475.
   - 2025 winner 305→314/513, exact 170→169, six-class log loss 1.60652→1.60116.
   - 2026 retrospect winner 293→**303/488**, exact **145→157**, six-class log loss 1.63604→1.62830. Also winner Brier improved all three years; clustered winner/exact CIs still cross 0, no promotion or 60-70% claim.
   - Boosted 57 exact 175/511, 176/513,149/488, but six-class log loss slightly worse than old logistic each year; not a slam-dunk. All 2024–26 historical folds have already been seen in model development.
- **First independent new research-only prospective winner head** `logit_recent_57`, locked **2026-11-19T21:22:24.603880+00:00** on *existing* November 21 Qatar 12 fight lineup, [successful GitHub Actions](https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44618011906). File `data/shadow_locks/ufcqatar_2026-11-21/winner_v3_prospective_shadow.json`, source SHA checked against existing original Stage A AND separate Coherent pre-event lock. Original `stage_a_final_selection.json` and original `coherent_joint_pre_event_shadow.json` both UNCHANGED. All source UFC fight records through Nov7 only, no Nov14 results, no odds, no fabricated UFC wins for debutants.
- New primary research winner deviations from original Reference/Historical/Unified: **Gaziev KO/TKO instead of Teixeira**, **Aleksandre Topuria DEC instead of Luna**, **Almabayev SUB instead of Horiguchi Reference DEC**. Do not flip original picks. Max V3 pre-event exact-outcome P **~41%** (Stirling KO); no exact near-lock; 12th provisional Mitchell/Yousaf is 0/0 UFC data, winner P 50%, PASS.
- On archived 28 Oct24 and Nov7 fights: new V3 winner **17/28**, exact **11/28**; original Historical **20/28 winners**, **10/28 exact**, Unified **19/28 winners**, **11/28 exact**. No claims of independently beating old Historical's winner accuracy.
- **NEXT:** after Nov21, grade frozen new v3 vs original 3 models plus coherent sidecar on identical decisive outcomes, six-class score and proper winner/KO/SUB/DEC confusion, count unique future bouts once. Continue seeking legitimate date-verified regional MMA and positional grappling/get-up datasets, and wait for replicated prospective validation before promotion. Keep FanDuel Stage B separate, no authorized bets from research results.



## November 19, 2026 — source-matched worldwide MMA winner v4 and method v5 prospective locks

**LATEST FULL RESEARCH RESUME:**
- `reports/model_health/2026-11-19_WORLDWIDE_MMA_WINNER_V4_RESULTS_AND_NO_PROMOTION.md` — global pro-fight history and newer winner candidate, verified Actions https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44622662648.
- `reports/model_health/2026-11-19_WORLDWIDE_METHOD_V5_RESULTS_AND_PRE_EVENT_LOCK.md` — new fighter-specific conditional KO/SUB/DEC model, full comparative out-of-year historical scores, pre-event method-only Nov21 future-card SHA lock. Verified Actions https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44625645961.
- V4 complete data and pre-event lock GitHub Actions https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44623849723. V5 code `tools/benchmark_worldwide_method_v5.py`, future runner `tools/lock_ufcqatar_worldwide_method_v5_research.py`, tests `tests/test_ufc_worldwide_method_v5.py`, CI `.github/workflows/worldwide-mma-method-v5-research.yml`. Source profiler `tools/audit_worldwide_mma_history_v4.py` / source join test `tests/test_ufc_worldwide_mma_identity_v4.py`.

**Important source breakthrough:** Fight Canon public international MMA professional records, pinned exact released SQLite `db-2026-11-19-1934`, size 184770560, SHA `8185a2163b5f97071dbc4ec68667cceb43f5e321fadc38c26b5069303af4d949`. Reconciled identities by SAME original UFC fight date and BOTH opponents (not fighter name alone), matched 3,016/3,036 modern features; 20 ambiguous identities quarantined. 2026 had 110 newcomer pair matchups each with at least one fighter's 3+ known pre-UFC pro fights. Measured regional pro KO/SUB/DEC, past professional opponent data, recent form, with recorded source missingness. Reconstructed 2026 source vintage may retroactively backfill old results — not perfect historical snapshot.

**Winner research v4 boosted73 vs UFC-only boosted57, same conditional method:** 2024 winner 314→313/511 and exact 175→169/511; 2025 winner 316→330/513 and exact 176→187/513; 2026 retrospective winner 294→306/488, exact 150→163/488. Proves valuable additional coverage and retrospective gains in some years but regression in 2024, no robust model promotion or 70% claim.

**Method v5 regional multinomial54 vs old UFC-only multinomial38 (FIXED winner head):** with pre-locked V3 logistic57, exact 2024 168→177/511, 2025 169→173/513, 2026 157→158/488; actual submission-class recall 2024 12→20/83, 2025 12→16/91, 2026 12→15/84. Six-class logloss improved each. With V4 boosted73 winner fixed, exact 2024 169→180/511, 2025 187→196/513, 2026 163→159/488 (worse). All historical years previously inspected, no held-out future claim. Strongest cited still ONLY 196/513 ~38.2% exact, nowhere near full-card target. No 2-5 perfect exact bets proven.

**FOUR distinct preserved Nov21 pre-event sources:** Original 12-fight Reference/Historical/Unified Stage A and Coherent shadow, plus independent new V3, V4 and method-only V5 research sidecars, all original SHA checked UNCHANGED.
1. V3 future-only winner `data/shadow_locks/ufcqatar_2026-11-21/winner_v3_prospective_shadow.json`, `logit_recent_57`, first SHA lock Nov19 21:22 UTC, n12.
2. V4 full model independently locked `data/shadow_locks/ufcqatar_2026-11-21/worldwide_winner_v4_prospective_shadow.json`, primary `winner_v4_boost73`, Nov19 21:58:03 UTC, n12, exact P max 40%, source SHA pinned, research only.
3. V5 conditional method-only separately locked `data/shadow_locks/ufcqatar_2026-11-21/worldwide_method_v5_prospective_shadow.json`, Nov19 **22:09:16.786617 UTC**, primary `worldwide_MMA_multinomial54` (both possible winners), **winner P(A) exactly unchanged from first V3 lock**. Only Dom Mar Fan and Dan Hooker method projections change V3 KO→V5 DEC (same fighter picks). Exact P max Stirling KO 44.4%; ZERO wagers or near-lock claims. All 3 committed before Nov21 earliest prelim 15:00 UTC; no current-event result used. Mitchell/Yousaf provisional, unknown ID / no prior UFC, PASS.

**NEXT mandatory gate**: After Nov21 event, grade the original independently dated Reference, Historical, Unified, coherent, V3, V4, and V5 research models on the same unique decisive bout identities; compare winner, exact fighter+method, own selected method, six-class proper scores, class recall and event-level uncertainty. Draws/cancellations void. Preserve >=300 future decisive unique fight promotion guard (not 300 pre-examined retro records), no arbitrary model flip/percent target claim or FanDuel approvals. Further develop truly observed positional grappling stats from per-round cross-promotion data only if credible date-safe source; avoid inventing get-ups, injuries, ages. User objectives 60–70% exact full card and 100% small group are stretch goals, **NOT guaranteed or currently achieved**. Chat tool work is synchronous: never promise to independently return later without an automation.


## November 19, 2026 — new opponent-relative method v6, direct six v7, and worldwide opponent Elo winner v8

**LATEST FULL RESEARCH RESUME POINTS:**
- `reports/model_health/2026-11-19_OPPONENT_MATCHUP_METHOD_V6_REPEATABLE_RESULTS.md` — v6 38/54/70/108/115 features, opponent-regional-vulnerability and UFC recency, **nested previous-year coefficient tuning**, runner/test `tools/benchmark_opponent_matchup_method_v6.py`, `tests/test_ufc_opponent_matchup_method_v6.py`, CI https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44628426421 **PASSED twice with byte-identical per-fight forecast CSV**, SHA `491602026351188e294e07a331e195728d24ef3424c61b1f238575322401ecf9`. Strict single-thread numerical environment now enforced for this test.
- `reports/model_health/2026-11-19_DIRECT_SIX_WORLD_V7_PROPER_SCORE_AND_TIE_FIX.md` — v7 independently fit mirrored *all six fighter+method outcomes*, earlier-year C tuning, models 115-diff, 230-bilateral, boosted115 and explicit global-six vs winner-marginal selected method. Corrected post-bug CI https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44629780197; code `tools/benchmark_worldwide_direct_six_v7.py`, test `tests/test_ufc_worldwide_direct_six_v7.py`. **Important grading bug fixed**: 50/50 original winner P(A) could flip after six-class sum rounding 0.49999999999999994, producing two FALSE 2026 baseline winner hits; now tie guard and exact `score_six(p_a=original_p)` assert. Earlier prospective November21 locks NOT changed.
- `reports/model_health/2026-11-19_WORLDWIDE_OPPONENT_QUALITY_ELO_V8_RESULTS.md` — 371,109 completed global professional MMA fight outcomes, 179,959 fighter IDs, date-frozen opponent-quality Elo and opponent strength features for 3016/3036 two-fighter corroborated UFC matchups (20 unresolved); files `src/wshlx_ufc/worldwide_opponent_elo_v8.py`, `tools/benchmark_global_opponent_elo_v8.py`, `tests/test_ufc_worldwide_opponent_elo_v8.py`; passed https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44630737187; source pinned Fight Canon SHA unchanged. Retrospective source has possible historical backfills. No promotion.

**Critical observed results:**
- V6 with fixed v3 logistic57 winner, old v5 method54 exact **177/511, 173/513, 158/488**, new v6 both-recent108 exact **167/511, 188/513, 155/488**; six-cell logloss *improved in all 3 years* but exact fell 2024 and 2026, SUB class also decreased. The new larger features are NOT stable improvements. Fixed v4 boosted73 similarly old v5 178/511,196/513,158/488 vs new108 166/511,201/513,154/488.
- V7 direct paired230 with winner-marginal-and-method selection exact **169/511 2024, 198/513 2025, 161/488 2026**; winner **314/511,324/513,304/488**; six-logloss **1.57196,1.56814,1.60653** lower than factorized v3+v5, but 2024 exact lower than baseline. Choosing globally highest six-class cell produced fewer exact results (165,186,152). Top 5 perfect exact groups 2024 **0/40**, 2025 **1/39**, 2026 **0/38**; not remotely dependable perfect 2-5 fights.
- V8 winner global opponent Elo adds *opposition quality*, not raw regional wins, on fixed method v5. Logistic73→logistic77 winner **314→332/511 2024**, **324→325/513 2025**, **304→292/488 2026**; exact **175→190/511**, **179→186/513**, **153→147/488**. 2024 improvements, 2026 clear regression. Boosted73→boosted77 winner **311→317/511**, **330→323/513**, **305→312/488**; exact **178→181/511**, **196→188/513**, **158→161/488**. Neither model consistently better. 2026 top5 0/38 perfect groups.

**Development governance:** The user's 70% exact full-card goal and 2–5 perfectly exact picks EACH card remain NOT achieved. Even the best isolated retrospective cohort in these new studies has only **198/513 exact (38.6%)** and the highest novel winner cohort **332/511 (65.0%)**, on DIFFERENT models/years and already-inspected data; not complementary evidence of a single 70% model. At 65% winner accuracy, 70% full-card exact is mathematically IMPOSSIBLE even if every conditional method were correct. In general 80% winners would require **87.5%** correct conditional methods for 70% exact. Current scores do not justify near-100% exact confidence on 2–5 picks.

**NEXT REAL VALIDATION (not yet performed, not asynchronous promised):** Nov21 unique decisive bout results become available only after event. Match by fighter/date identity and grade independently frozen official Reference/Historical/Unified, Coherent, winner v3, winner v4 and method v5 sidecars. V6/V7/V8 were researched after original locks and have **no prospectively frozen Nov21 predictions**, so never pretend they were independently locked before results or count their retrospective performance toward the project >=300 unique prospectively evaluated fight gate. Further source exploration can continue, but STOP selecting research candidates because they make already-seen 2026 exact outcomes look good. Future model change needs actual fresh pre-event registered forecasts, fighter/method and six-state Brier/log loss with paired event-cluster error bars, not any number of post hoc coefficient tweaks or simulations. No code here touches Reference production, FanDuel Stage B, official November21 selection, or previously committed research forecasts.


## November 19, 2026 — separate DIRECT six-state v7 Nov21 prospective research lock

**LATEST VERIFIED AND ACTIONED USER DECISION**: Keep original Reference/Historical/Unified odds-blind Stage A and original Coherent challenger exactly frozen. Preserve independently prospectively locked V3 Winner, V4 Winner, and V5 Method. Add **ONE** distinct new prospective shadow for November21: independent direct-six outcome model V7, NOT further model voting or addition of v6/v8 to original betting card. All no-betting and odds-blind.

- **Verified new lock report:** `reports/model_health/2026-11-19_NOV21_INDEPENDENT_DIRECT_SIX_V7_LOCK.md`. Run [GitHub CI #44633002610](https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44633002610) all stages PASSED, Git commit succeeded.
- **New immutable v7 research sidecar:** `data/shadow_locks/ufcqatar_2026-11-21/worldwide_direct_six_v7_prospective_shadow.json`. Strict predates Nov21 earliest 15:00 UTC fight; actual lock **2026-11-19T22:55:36.469296+00:00**. Validates SHA of ORIGINAL 6 previous frozen source files before prospective write. Original bets, stages and previously locked data never changed.
- **PRIMARY prespecified** `direct_paired230` symmetrical bilateral 230-feature regularized logistic six-state A/B by KO/SUB/DEC, selected `winner_marginal_method` policy; C=.025 chosen on 2025 validation train 2021–24, fit all 3,015 historical decisive fights before Nov21 (source through Nov7), 2025 coefficients before Nov21 fight outcomes. Not direct global max cherry-picking.
- **New v7 11/21 exact picks:** Nurgozhay KO/TKO **source identity UNVERIFIED PASS, implausible 79.8% exact numeric probability**; Dom Mar Fan KO; Jake Matthews DEC; Albazi DEC; Gaziev KO; Santiago Luna DEC; Ikram Aliskerov DEC; Asu Almabayev SUB (winner 50.1%); Brian Ortega DEC (winner 50.7%); Kevin Vallejos KO; Navajo Stirling KO (unvalidated 59.3% exact); Mitchell KO **PROVISIONAL unverified both identities AUTO-PASS**. See report for full 12 fighter names, odds-blind probabilities and per-fight quality flags. Research model's apparently high numeric probabilities are NOT demonstrated credible bet confidence/calibration and must not override identity or original pass gates.
- **V6 and V8** had retrospective 2024–26 mixed performance and NO preregistered Nov21 research sidecar; do not pretend they have frozen 11/21 picks or add them to Stage B simply to make a consensus. New v7 is research-only, not a newly promoted production model, no bets approved. After card, compare independently locked model-specific exact hit on SAME genuinely future unique decisive fights; minimum 300 prospective evidence gate still applies. No guarantee of 70% exact card or perfect 2–5 exact selections.


## November 20, 2026 — four-part performance recovery roadmap and prospective exact selection audit

**LATEST IMPLEMENTED USER-APPROVED RESEARCH DIRECTION:** Four tracks: improve winning fighter accuracy, improve conditional KO/SUB/DEC, identify 0–5 unusually reliable exact outcomes anywhere on an 11–14 fight card **without forcing any**, and separately verify long-run FanDuel-only positive expected-value/ROI. No guarantees of 70% exact outcomes or perfect 2–5.

- Full implementation/criteria roadmap: `docs/WSHLX_UFC_PERFORMANCE_RECOVERY_PLAN_2026_11_20.md`.
- Audited initial results: `reports/model_health/2026-11-20_FORWARD_SELECTION_AND_FANDUEL_AUDIT_INITIAL_RESULTS.md`.
- Production-safe **new forward-only research code**: `src/wshlx_ufc/forward_validation_v1.py` (proper six-state exact+winner grades, 95% Wilson lower bound calibration from genuinely prospectively PREVIOUS graded fights, 0–5 exact selection without forcing any, fighter identity/provisional PASS, evidence/timestamp/source-check FanDuel-only price-implied break-even and conservative EV, perfect-group W/L/VOID/PENDING).
- Nov21 runtime `tools/audit_ufcqatar_forward_selection_readiness.py`; tests `tests/test_ufc_forward_validation_v1.py`, `tests/test_ufc_qatar_forward_readiness_v1.py`; CI `.github/workflows/ufc-forward-selection-v1-audit.yml`.
- Verified **GitHub Actions PASS** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44758880936, **19 tests passed**. This checked 12 Nov21 independently locked v7 fighter+method previews against original frozen Stage A SHA, **NO prior truly prospective matched model cohort yet**, **zero eligible new exact wagers**, no FanDuel market source uploaded; 0 official bet approvals. These are honest research PASS decisions, not a loss of the user's media selections.
- New research eligibility thresholds predeclared, NOT guaranteed profitable: >=300 unique previously prospective independently graded decisive fights for same registered model, >=50 before-target same predicted exact probability bucket, 95% Wilson lower bound >=55%, verified source athlete identities, up to five picks; lower-bound FanDuel edge and expected unit return >=5pp/5% for price research if and only if real quotes exist. Separate official Stage B gates unchanged and not bypassed. Future 300 fights must NOT come from repeatedly reexamined 2024–26 retrospective data.
- All original Nov21 Reference/Historical/Unified, Coherent, prospective v3, v4, v5 and v7 files remain UNMODIFIED. No future results are supplied yet and no code can promise to run later without user's request or automation.
- After Nov21 verified official results: prospective grade EVERY previously pre-event frozen model arm on same decisive fights, separately public video card if wanted; track winner, method correct conditional on winner, six-state proper logloss/Brier, 2–5 selected-group perfect flags and, IF real FanDuel verified prices supplied, expected return and cumulative ROI. Use future-only evaluation to decide which NEW model features/architectures deserve promotion. Current 70% exact and perfect 2–5 aims remain not achieved.


## Nov 24, 2026 — UFC Qatar RESULTS GRADED: original winners 11/12 and Coherent R/U 7/12 exact

**LATEST STATE, VERIFIED AND SAVED:** UFC Fight Night Prochazka vs Stirling took place Nov21. All 12 matchups ended in decisive results: **8 DEC, 3 KO/TKO, 1 SUB**. Fight-by-fight results sourced from published 2026-11-21 Sports Illustrated MMA and UFCStats-derived [Cage Almanac](https://cagealmanac.com/events/ufc-fight-night-prochazka-vs-stirling-cbf69f), corroborated 2026-11-24. Store only new dated results, do NOT alter any original pre-event fighter/method/timing probability or original research sidecar.

**RUN SUCCESS:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45488023126 (pytest all PASS, SHA verifications, deterministic 12-bout grade, GitHub commit/artefact). New primary files:
- `data/results/ufcqatar_2026-11-21/verified_event_results_2026-11-24.json`: official actual 12 winners, methods, finish rounds/times and public source links.
- `data/results/ufcqatar_2026-11-21/ufcstats_derived_postevent_fight_totals_2026-11-24.json`: independent 12-bout / 24-fighter UFCStats-derived actual significant/total strikes, takedowns, submissions, reversals, knockdowns, control and per-fight source URL. TOTALS only, per-round detail linked online not yet manually ingested. THESE ARE POSTEVENT LABELS AND CAN NEVER BE USED AS 11/21 PREDICTOR FEATURES.
- `data/grades/ufcqatar_2026_11_21_all_frozen_models_and_public_card_grade.json`: complete per-fight 10 original/research registered view exact grade plus originally locked primary timing outcomes and separate public mixed-market user card. SHA checks all original Reference/Historical/Unified, Coherent and prospective v3/v4/v5/v7.
- `tools/grade_ufcqatar_2026_11_21_frozen_models.py`, `tests/test_ufc_qatar_2026_11_24_grade.py`, `.github/workflows/ufc-qatar-2026-11-24-all-frozen-grade.yml`, `reports/model_health/2026-11-24_UFC_QATAR_ALL_LOCKED_MODELS_GRADE.md`.
- Full actionable observed fight stats diagnosis `reports/model_health/2026-11-24_UFC_QATAR_STATS_METHOD_FAILURE_AND_LESSONS.md`.

**FINAL 12-fight EXACT and winner grades (all previously frozen):**
- Original Reference **11/12 winners (91.7%), 4/12 exact**. Original 11 excluding late Mitchell/Yousaf **10/11 winners, 3/11 exact**.
- Original Historical **10/12 winners, 5/12 exact**.
- Original Unified **11/12 winners, 3/12 exact**.
- Coherent Reference winner/timing-aligned **11/12 winners, 7/12 exact (58.3%)**, Coherent Historical **10/12 & 5/12**, Coherent Unified **11/12 & 7/12**. Coherent is an original SHA-frozen, model-derived 6-cell probability postprocessor with NO independently trained fourth winner and no bet authorization. First original 11 Coherent R/U 6/11 exact 54.5%. Cannot claim 58.3% future accuracy or late choose a model by best grade.
- Winner v3 primary **8/12 winners, 3/12 exact**. Winner v4 primary **9/12, 4/12 exact**. Conditional Method v5 frozen V3 winner **8/12, 5/12 exact**. Direct Six v7 **8/12, 5/12 exact**. New v3/v4 degraded winner selections compared to original 11/12. Cannot promote.
- Original timing PREPRICING selected primary markets **10/12 correct**, two misses GTD NO on Gaziev/Teixeira and Cannonier/Aliskerov, both decisions. This is NOT a 10/12 FanDuel profit claim.
- User public WSHL_X video card (12 selected KO/DEC/SUB-doublechance and one GTD) **6/12 correct**; not same as original model picks, and no verified FanDuel quote/stakes/ROI to grade profit.

**MAIN DIAGNOSIS:** Original odds-blind Reference already selected winning fighter on 11/12, but predicted KO on **10/12**, while just 3 KOs occurred and 8 fights went to judges. Coherent R/U moves needed methods toward DEC and wins 7 exact on SAME 11 winners. One event not enough for release; compare multiple fresh prelocked events, 6-state logloss/Brier and calibrated selective bet ROI. User objective 70% full-card exact / perfect selected 2-5 remains NOT proven.

**Fight-specific verified outcomes:** Mar Fan DEC 4/9 TD, 6:01 control vs Motta; Abdullayev DEC 5/7 TD, 9:02 control vs Matthews; Albazi SUB R3 after 7/10 TD, 6:19 control; Teixeira DEC 47–15 sig vs Gaziev, zero knockdowns, mostly body/leg targeting; Luna DEC 142–65 sig vs Topuria; Aliskerov DEC 4/6 TD 6:55 control and 3 SUB attempts, not finish; Almabayev 7/9 TD 9:43 control yet Horiguchi DEC by judges; Hooker DEC 146–70 sig and zero KD vs Ortega; Vallejos DEC while Sterling TD 1/12, no KD; Stirling KO, Nurgozhay KO and Mitchell KO (last remains original betting PASS, UFC debut matchup). Full 24-fighter detailed actual fight totals in separate source above.

**DON'T OVEREACT:** No predictive coefficient changes, no global KO/DEC quota, and no new model promotion justified from one card. After grading preserved, source postfight stats are available as HISTORICAL data for FUTURE cards dated after Nov21; ensure future-only training. Evaluate opponent-specific takedown-to-control-to-scorecard pathways, striking power vs conversion to knockdown/finish, SUB reach vs completion, late fatigue, and original timed-market calibration in independent dated tests. Keep user Stage B FanDuel only; real ROI remains unverified. Data and grading correctness upgrades ARE committed, but not a claimed predictive miracle.


## Nov 24, 2026 — Coherent proper-score audit, updated historical input, and finishing-conversion v9

**Verified CI success:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45490332703, 7 targeted tests passed; all three retrospective cohorts scored; SHA checks verified original November21 frozen Stage A and all research sidecars unchanged.

**First prospective Coherent comparison:** `reports/model_health/2026-11-24_COHERENCE_FIRST_PROSPECTIVE_MATCHED_COMPARISON.json`. Native vs winner+timing alignment: Reference exact 4/12→7/12, six-class logloss 1.485161→1.249023; Historical 5/12→5/12, 1.426407→1.328628; Unified 3/12→7/12, 1.402727→1.242024. All improved six-Brier and finish Brier, original winner selections preserved. Reference retained all three correct KOs and gained three correct decisions. Neither aligned Reference nor Unified predicted a SUB. Only ONE prospective event, 12 unique decisive bouts; remaining minimum 288 of 300. Earlier 40-bout reconstruction remains retrospective; no promotion.

**New round source:** `data/results/ufcqatar_2026-11-21/fightingdata_round_stats_secondary_2026-11-24.csv` (64 fighter-round rows). Independently reconciled the recorded secondary mirror sums for 24 fighter totals across six fields (significant strikes landed/attempted, TD landed/attempted, control seconds, KD) against archived Cage Almanac totals. Both derive from UFCStats; not independent primary verification. Total strikes, sub attempts, reversals not independently cross-checked by this round dataset.

**Real research data pipeline implementation:** `src/wshlx_ufc/postevent_history_extension_v1.py` with pinned sources and future-only date cutoff >=2026-11-25; 8871→8896 completed bouts, 25 additions (24 decisive+1 draw). UFC334 results-only due to provisional statistics gate. Qatar results-only default; full secondary totals require explicit opt-in, with cross-check of six fields and other fields single-source. `future_research_matrix` and `future_research_snapshots` tested on real archive. Production runners are NOT migrated and original source is untouched; this explicit research interface must be used for later study. New round rows are saved, not yet used to train a temporal-round model.

**Method v9 experimental research:** `src/wshlx_ufc/finish_conversion_v9.py`, `tools/benchmark_finish_conversion_v9.py`, tests `tests/test_ufc_finish_conversion_v9.py` and `tests/test_ufc_postevent_history_extension_v1.py`. Fixed Winner v3 logistic57 across all arms; prior outcome-method mix for both fighters, offensive/defensive observed KD/submission/takedown-control opportunity conversion and sample counts, no causal/get-up/current-fight inference. Coefficients selected using preceding-year validation only. Chronological 2024/25/26 tested on 511/513/488 already-studied bouts. Legacy UFC38 fixed C=.2 exact 168/169/157; tuned UFC38 167/168/146; new history mix54 176/168/153; full conversion94 173/168/147. Conversion94 lower six-way logloss in all three years versus legacy, but 2026 exact and submission accuracy degraded; no robust exact improvement or promotion. UFC-only baseline comparison, not a claim to beat regional v5 or original Reference. Full report: `reports/model_health/2026-11-24_FINISH_CONVERSION_V9_AND_HISTORY_EXTENSION_RESULTS.md`.

**NEXT:** Retain original Stage A/B and prospective Coherent R/U locks across new cards. Work on submission-specific pathways and opponent-adjusted finishing versus decision probability from prior round/position features, evaluated against strongest comparable models. Do not keep a worse 94-feature model simply because it has more statistics. V9 remains unpromoted; 70% exact and perfect 2–5 sets not established. No invented FanDuel pricing, actual ROI or new bets.


## Nov 24, 2026 — Method v10: prior-round submission and pace features

**Latest actual research:** `reports/model_health/2026-11-24_ROUND_SUBMISSION_METHOD_V10_RESULTS.md` and [successful CI](https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45492217530). Six targeted tests, real 511/513/488 historical bout comparisons, source SHA verification; all passed. Initial archive run failed because floating elapsed seconds were passed into range; fixed full-round integer conversion plus regression and pipefail.

- `src/wshlx_ufc/round_method_v10.py` parses pinned November7 archive 42,310 round-fighter rows, excludes two duplicate keys. 6,326 bouts with matched full rounds, 4,926 with first two full rounds. 16 features per fighter, including earlier/later submission exposure, ground-striking share, paired-full-round changes in offense and opponent performance, sample counts. Whole-date frozen, partial rounds excluded, missing observed stats not filled with zero. Conditional on reaching rounds; not directly observed fatigue, getups or escapes.
- `tools/benchmark_round_method_v10.py`, `tests/test_ufc_round_method_v10.py`, `.github/workflows/ufc-round-method-v10.yml`. Same fixed v3 logistic57 winner probabilities in all arms; prior-year tuning only. Compare UFC-only methods on already-inspected retrospective cohorts, not prospective.
- Exact hits 2024/25/26: legacy38 168/169/157; tuned38 167/168/146; v9 mix54 176/168/153; hierarchical54 180/171/150; single-stage round86 **172/177/158**; hierarchical round86 175/172/157; round126 167/168/152. Single-stage round86 improves 4/8/1 over legacy, but loses 4 in 2024 vs v9 mix54, and proper logloss vs mix54 worsens first two years. Exact SUB for round86 13/12/11 vs legacy12/9/12 and v9 mix54 13/8/10. No stable dominance or promotion. 2026 round86 exact 32.4%, still far below objective.
- Next: sharpen class-specific submission probabilities and opponent-specific grappling resistance, verify meaningful gains over comparable strong regional v5 and historical mix54. Retain round86 only as research candidate. Future integration of November14/21 extended data and prospective v10 runner not yet implemented. Existing Coherent registered 12 unique forward fights; do not count these 1,512 reexamined bouts toward prospective gate. No changes to frozen official predictions or FanDuel Stage B. Target accuracy and flawless groups remain unproven.


## Nov 24, 2026 — opponent-adjusted Method v11

Verified final strict-source run https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45494717295 (7 targeted tests passed, all source checks and original frozen lock SHA verified). Full report `reports/model_health/2026-11-24_OPPONENT_ADJUSTED_METHOD_V11_RESULTS.md`. New files `src/wshlx_ufc/opponent_adjusted_method_v11.py`, `tools/benchmark_opponent_adjusted_method_v11.py`, tests and workflow `.github/workflows/ufc-opponent-adjusted-method-v11.yml`.
- 45 new features (prior opponent-relative KO/SUB/KD/submission attempts/TD-control access residuals and exposure counts, bounded historical UFC Elo weighting, matchup proxies). Prior-date frozen, not current-bout outcomes; not causal/direct get-ups. Regional v5 and v10 round86 controls on identical fixed v3 winner probabilities, 1,512 already studied test bouts.
- **Important data flaw discovered:** legacy aggregate stats parser may coerce missing fields into zeros. Strict new raw-round access loader avoids that for V11 only, 8,672 both-complete bouts/8,871, 950 missing individual fighter-field totals, 2 duplicate round keys excluded. Earlier run with legacy input superseded. Legacy comparators unchanged; broader parser audit remains.
- Exact 2024/25/26: regional v5 fixed54 **177/173/158**, tuned regional54 172/182/157, bilateral70 177/187/153, round86 172/177/158, regional-round118 170/183/156, adjusted83 172/171/151, adjusted163 167/184/151, hierarchical163 167/183/157. Winner fixed 310/314/303. Best combined bilateral70 517/1512=34.2%, no stable gain over v5; adjusted full163 improves proper scores but exact regresses. Exact SUB v5 19/15/12 vs adjusted163 14/13/13. No promotion, no new official predictions or bets, no prospective credit. Existing 300 unique fight gate unchanged.
- Next: avoid another indiscriminate feature expansion; audit inherited missing-stat encoding, prespecify probability blend/calibration and top-k selection research with strong comparators and real future locks. Nov14/21 extension has not yet been integrated into V11 or V10 runners. Keep Coherent Reference/Unified prospective comparisons, original champion and Stage B unchanged. 60–70% exact and flawless 2–5 goals remain unproven.


## Nov 24, 2026 — method ensemble v12 and top-k selection

Verified CI run https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45495483749; three targeted tests passed; source v11 corrected artifact and frozen Qatar source SHA checked. Report `reports/model_health/2026-11-24_METHOD_ENSEMBLE_V12_AND_TOPK_RESULTS.md`; code `src/wshlx_ufc/method_ensemble_v12.py`, benchmark `tools/benchmark_method_ensemble_v12.py`, tests and workflow `.github/workflows/ufc-method-ensemble-v12.yml`.
- Six method-only inputs with fixed v3 logistic57 winner probability; 2024 OOF 511 trains 2025 test 513, 2024+25 OOF 1024 trains 2026 test 488. Previously examined historical years, NOT prospective. No Reference/Coherent matching historical forecast input. Equal, learned simplex, strongly shrunk groups (limited UFC history, higher grappling activity proxy, established, unknown) and temperature. No verified weight class specialization. Temperature fitted on same earlier meta-training cohort.
- Exact hits 2025/26: v5 173/158, bilateral70 187/153, round86 177/158, regional-round118 183/156, adjusted163 184/151, hierarchical163 183/157, equal blend 186/155, learned global/group/calibrated all 184/154. Best combined equal 341/1001 (34.1%), only one more than best components. No reliable gain. All fixed winners 314/303. No promotion.
- Across 77 eligible 11–14 decisive-bout historical cards, equal top2 65/154, 11 perfect; top3 93/231, 6 perfect; top4 125/308, 2 perfect; top5 153/385, zero perfect. Regional v5 top2 70/154, 16 perfect; top3 100/231, 5 perfect; top4 125/308, zero; top5 155/385, zero. Bilateral70 one perfect top5 group. Forced rankings are retrospective diagnostics, not betting recommendations or prospective calibrated selections.
- Next: focus on actual future runner integration of verified Nov14/21 extension, identity QA, limited prospectively registered model arms, and broader legacy missing-stat parser audit. No repeated feature/weight optimization on same past fights solely to chase target. Coherent Reference/Unified 12 unique prospective bouts, remaining 288 to minimum 300. Original locks and FanDuel Stage B unchanged; no real ROI or 60–70% exact / perfect group target established.


## Nov 24, 2026 — strict history and future runner integration

Verified CI https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45497258904; 7 targeted tests, matched input experiment, original frozen source SHA passed. Report `reports/model_health/2026-11-24_STRICT_HISTORY_AND_FUTURE_RUNNER_RESULTS.md`. New strict complete-case adapter `src/wshlx_ufc/strict_history_inputs_v1.py`, benchmark `tools/benchmark_strict_history_v1.py`, future runner `tools/run_future_updated_history_research.py`, tests and workflow `.github/workflows/ufc-strict-history-input-v1.yml`.
- 8,871 pinned bouts; legacy complete both-side 8,850, strict 8,672; 178 quarantined, 2 duplicate round keys excluded. Control missing/invalid 398 fighter-field totals, six other required fields 184 each. All labels retained; both-complete numeric changed 0; **modern feature/form rows changed 0**. No evidence missing-stat flaw caused modern prediction failures in these tested heads. Four matched v3 arms legacy/strict winner/method all identical: 310/314/303 winners; 168/169/157 exact; logloss 1.604755/1.601160/1.628300. No promotion.
- Future runner now actually fits legacy and strict v3 comparators on extended Nov14/21 outcomes, 3,039 decisive since 2021, 8,896 total historical bouts. Outcome-only default, Qatar detailed stats explicit secondary opt-in; Nov14 provisional stats excluded. Real-data hypothetical fixture fit/query tested, prior counts increased, coherent six-state probabilities, zero bets. No real event predictions made. Requires caller-verified lineup with URL, future date before first fight, no overwrite, lineup SHA; caller attestation and name matching not independent source/identity verification. Source vintage Nov21, must refresh. Same-day execution blocked. Not a migration of Reference/Coherent or other experimental heads.
- Next: genuine upcoming-event lineup/source and identity QA, limited predeclared research arms plus original Stage A/Coherent, independent prospective grades; no more indiscriminate retrospective model variations. Coherent 12 unique prospective bouts, minimum 300 unchanged. FanDuel Stage B untouched; no target accuracy or ROI achieved.


## Nov 24, 2026 — updated method panel and December 5 readiness

# Nov 24 — Future research panel integration and UFC Riyadh readiness

## Completed
- Official event source checked Nov24: https://www.ufc.com/event/ufc-fight-night-december-05-2026 — Adesanya vs Magomedov, Dec5, scheduled prelims 10:00 EST / 15:00 UTC, main card 13:00 EST / 18:00 UTC. 14 listed bouts; not a final confirmed fight-week roster. Draft `research/lineups/ufcriyadh_2026-12-05_draft_2026-11-24.json` deliberately fails live lineup attestation; no odds copied or used, no real card picks generated.
- `tools/run_future_updated_method_panel.py` trains updated legacy and strict v3, Round86 and Regional v5 on 3039 decisive UFC outcomes since 2021, including Nov14/21 results. Round86 and v5 use exactly the legacy-updated v3 winner probabilities, not the original Reference winner head. Round86 uses historical method mix and prior round features with C chosen on 2025 validation only. Regional v5 retains audited regional source results through Nov7, not a refreshed worldwide history. Added 25 UFC rows may use previously vetted regional crosswalk candidates or missing-identity encodings; no invented histories. Unmatched regional query pair receives no v5 prediction. Future query snapshots added to v9 conversion and v10 rounds without appending synthetic outcomes.
- Outcomes-only default, optional cross-checked 64 Qatar round-fighter rows plus secondary fight totals. Round-specific submission attempts and ground strikes absent from this supplement, explicitly null. Existing v10 full-round paired change calculations require complete relevant fields; do not claim full Qatar round-level training coverage. Nov14 provisional details still excluded.
- Dedicated integration CI run https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45498793872: 10 targeted tests passed, actual extended data and pinned regional source, hypothetical in-memory pairing only, matched winner marginals, draft blocked, no backdating, supplemental fields not fabricated; frozen original November source hashes verified. Later commit isolates external-DB tests from normal unit suite and requires them in dedicated CI, run 45498857222. Hash checks confirm unchanged files, not independently verified pre-event chronology.
- Draft identity readiness (artifact and `tools/audit_riyadh_draft_lineup_readiness.py`): 23 of 28 exact normalized UFC name candidates and prior dated regional crosswalk candidates; Akbar Abdullaev, Ivan Gnizditskiy, Mahammadali Osmanli, Modestino Rodrigues unmatched; Bruno Silva same-name ambiguity. All 28 require independent source/identity review. Counts do NOT mean 23 verified identities or debut status for unmatched names. No forecasts/approved wagers.
- Production Reference/Historical/Unified still use previous archive/artifacts in event-specific Stage A runner; no production migration claimed. Coherent generic CLI available but requires new frozen original Stage A and time manifest. Next: source/identity verification, production artifact and input freshness audit (winner, method and timing), prepare new event-specific Stage A and freeze actual card only after verifying lineup. Keep original model unchanged as comparison; updated data versions must be independently labeled. Verify genuinely prospective commit/artifact chronology before counting toward 300-bout gate; in particular prior Nov21 v7 chronology unresolved, do not count as independently prospective merely from recorded timestamp or SHA. No model promotion, new bets, or profitability proof.

## Files
`src/wshlx_ufc/finish_conversion_v9.py`, `src/wshlx_ufc/round_method_v10.py` (query extensions), `tools/run_future_updated_method_panel.py`, `tools/audit_riyadh_draft_lineup_readiness.py`, `tests/test_ufc_updated_method_panel.py`, `.github/workflows/ufc-future-updated-method-panel.yml`, official lineup draft. Production and original locks unmodified.
