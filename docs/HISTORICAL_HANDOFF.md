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
