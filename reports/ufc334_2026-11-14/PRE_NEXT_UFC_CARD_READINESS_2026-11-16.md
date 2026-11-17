# WSHL_X UFC — November 16 pre-next-card readiness audit

**Current date:** Monday November 16, 2026. **Next scheduled UFC:** Saturday November 21, UFC Fight Night: Prochazka vs Stirling, Doha, Qatar. Official UFC source: https://www.ufc.com/events .

**Governance:** This memo is POST-RESULTS analysis only. The Reference champion remains frozen as existing model; Historical and Unified remain shadow models. Original Stage A, Stage B, FanDuel odds, locked grading and videos were not changed. No new official betting wagers authorized.

## Completed and saved this turn

- UFC334 original Stage A / Stage B grading previously saved: 13 bouts, Reference 8-4 plus 1 draw, Historical 6-6 plus draw, Unified 7-5 plus draw. Reference exact winner+method only 1/12, Historical and Unified 3/12 each; original Stage A primary timing 9-4.
- Found full UFCStats-derived fight statistics on FightingData and Cage Almanac, despite direct UFCStats website returning 502. Captured 26 fighter fight-total rows, 32 columns (significant/total strikes attempted and landed, target, strike position, TD, KD, sub attempts, reversals, control); captured 72 fighter-round rows with significant strikes, TD, KD and control.
- All 72 fighter-round core counts sum to 26 published totals; all 26 fighter target and striking-position breakdown sums reconcile with significant-strike totals; 13 frozen matchup pairs and results crosschecked.
- Because direct primary UFCStats is inaccessible and some third-party sources disagree (Gane/Hokit sig strikes), the files are labelled **PROVISIONAL MIRROR-CROSSCHECKED** and default **NOT TRAINING-ELIGIBLE** until confirmed against a verified UFCStats source or formally approved equivalent.
- New code + CI tests enforce source status, outcome alignment, 13-bout identity, 26 totals/72 round consistency, and strict time leakage prevention.
- Ran a genuine pre-Nov14 method calibration shadow experiment: fitted existing two-offset MethodInterceptCalibrator on 153 earlier (through Nov7) causal method feedback rows, tested solely against archived Nov14 input and Nov14 held-out results. **Do not promote:** same exact fighter+method score 1/12; conditional-on-correct-reference-winner accuracy 1/8; conditional method Brier worsened from **0.7754** to **0.9948** and log loss **1.2247** to **1.6049**. A second known-actual-winner oracle diagnostic also worsened Brier 0.6214 -> 0.7677; not a deployable betting forecast. This is evidence against blindly adding a single global KO/DEC offset.
- Reproduction in tools/benchmark_ufc334_pre_nov14_method_offset_shadow.py and tests/test_ufc334_method_prior_only_shadow_holdout.py; shadow report reports/ufc334_2026-11-14/PRE_NOV14_METHOD_OFFSET_SHADOW_HOLDOUT.json. Original picks unchanged.

## Highest-priority adjustments TO TEST before predictions for Nov21

### Priority 0: Method/decision probabilities and coherent multi-market outputs

Two consecutive cards Nov7+Nov14, 26 decisive fights combined: **21 Reference top KO labels** but only **9 observed KO outcomes**; **3 DEC labels** versus **14 DEC outcomes**. Nov14 alone exact winner+method 1/12. This establishes repeated top-label selection error on these dated cohorts, but NOT a population calibration correction. Need compare proper class-specific log loss, Brier, reliability and method-specific recall on strictly chronological held-out events.

Historical method joint and Historical winner probabilities are from separately trained models/vintages. Original UFC334 fighter six-way joint vs standalone winner maximum discrepancies: **17.569 percentage points Historical** and **10.228pp Unified**. Before promoting exact-method or combined props, test a coherent shadow where six-way method masses equal the corresponding winner model marginal and both match a single fight-duration hazard. The original models should remain untouched, and the shadow must pass proper loss functions and chronological holdouts.

Do **not** hardcode additional decisions or run another global finish intercept correction: the 153-prior-row shadow got worse on UFC334 despite chronological validation.

### Priority 1: Pre-fight opponent-quality and wrestling countermeasure features

Develop features ONLY from fights completed before each prediction date: quality-adjusted opposition (opponent UFC sample/strength), professional record strength separately from UFC quality, takedown and get-up success/opponent defense, sustained control and takedown attempts, significant-strike defense/absorption, knockdown durability, pace and round-by-round attrition, veteran vs newcomer uncertainty. Audit sparse 0–1 UFC-bout transfers.

Post-event examples motivating these pre-fight features: Elder 6/10 takedowns, 6:03 control vs Sanches; Gurule 2/5 TD, 6:19 control vs Hasan; Borralho 5/13 TD, 7:47 control vs Belgaroui; Radtke 2/7 TD, 4:47 control but only 11 significant strikes vs Thompson's 67; Gane 237 significant strikes and Hokit 3/30 takedowns. These are held-out explanatory labels, NOT valid Nov11 pre-fight inputs.

### Priority 1: Timing-hazard and format distinctions

Original UFC334 timing markets: Over 1.5 rounds 7-1 vs GTD NO 2-3; projected 7.57 expected finishes vs 5 actual. Five-round Gane-Hokit GTD No 81% was a big error. Evaluate method/timing alignment, 3-round vs 5-round survival, and opponent finish resistance under out-of-time evaluation. Do NOT infer profitable plays from hit rate without the FanDuel price gate.

### Priority 2: Odds and actual betting governance

Original Stage B researched 334 FanDuel screenshot quotes but approved zero bets. Best-five research 3-2 +1.4497 virtual units; longshots 1-4 -1.15u; combined 4-6 +0.2997 virtual units. All-quote diagnostic includes 293 scored correlated outcomes and 41 draw/unresolved rows. No official-betting ROI exists; no price data may enter Stage A. Do not remove independent calibration, quote freshness, weave-in, or method-family consistency gates to force a pick.

## Recommended acceptance criteria for any model promotion

1. Dataset source verified and tagged as post-fight; feature engineering explicitly lags to previous event, with fighter/opponent ID assertions. Never use UFC334 post-event stats as UFC334 prediction features.
2. Chronological walk-forward, by event date rather than random fight split, with exact winner+method, conditional method KO/SUB/DEC, 3v5 round hazard, winner Brier/logloss and model calibration. Stratify by opponent quality / new UFC experience, but do not overfit 12 outcomes.
3. New shadow must improve BOTH Brier and logloss over current baseline on multi-event holdouts, without material loss in submission recall, winner accuracy, or method/winner coherence. Preserve existing stricter 300 prospective observation promotion gate where applicable.
4. Bookmaker price gates stay separate; no stake approval based on retrospective model raw EV alone. Maintain all original frozen model cards as immutable grade references.
5. Treat event Nov21 training/Stage A lock separately. Today's research additions are preflight preparation, not Nov21 picks.

## Links to files and code

- data/raw/ufc334_2026-11-14/ufc334_complete_26_fighter_mirror_totals_PROVISIONAL.csv
- data/raw/ufc334_2026-11-14/ufc334_fighter_mirror_per_round_PROVISIONAL.csv
- data/raw/ufc334_2026-11-14/INGESTION_MANIFEST_PROVISIONAL.json
- src/wshlx_ufc/post_event_stats_audit.py
- reports/ufc334_2026-11-14/OFFICIAL_STATS_AVAILABILITY_AUDIT.md
- reports/ufc334_2026-11-14/PRE_NOV14_METHOD_OFFSET_SHADOW_HOLDOUT.json
- tools/benchmark_ufc334_pre_nov14_method_offset_shadow.py
- tests/test_ufc334_post_event_mirror_stats_integrity.py
- tests/test_ufc334_method_prior_only_shadow_holdout.py

**Current predictive model status: UNCHANGED. All post-event data, diagnostics and benchmark experiments live on the feature branch; not automatically merged into main.**


## November 16 continuation — 3-event coherent winner/method/timing research

**Completed:** a frozen-data-only, reversible six-outcome method projection
using archived UFC333 (Oct24), UFC Vegas124 (Nov7), and UFC334 (Nov14)
Reference/Historical/Unified views. 41 fights total, 40 decisive scored
(majority draw held out of six-way method scoring).

- The **winner-only** probability reconciliation made proper historical and
  unified six-class scores slightly **worse** in the aggregate.
- Constraining **both** standalone winner and direct finish-vs-decision
  timing improved retrospective aggregate six-class Brier (Historical
  0.75678 -> 0.74242; Unified 0.76418 -> 0.73977) and mean log loss
  (Historical 1.57129 -> 1.56474; Unified 1.56110 -> 1.52524).
- Retrospective exact fighter+method went Historical **13/40 -> 20/40**
  and Unified **14/40 -> 16/40**. These are new post-event
  challenger calculations, NOT what the original models picked, NOT
  prospective results, and NOT an approved betting card.
- Historical's UFC334-specific Brier actually worsened 0.75093 -> 0.75321.
  Combined mathematical coherence is not guaranteed predictive improvement.
- The new IPF projection reconciles saved winner/finish margins to within
  ~1e-12 without retraining or changing original probabilities.
- **No promotion.** Development used knowledge of the three outcomes, so
  the next honest assessment must be prospective under a pre-event lock.
  Our existing independent 300-prospective-bout promotion gate remains.
- A new CLI now creates a **sidecar-only research artifact** from a
  separately frozen odds-blind Stage A card, verifying the raw SHA-256;
  source: `tools/generate_coherent_joint_method_sidecar.py`. Neither
  Stage A nor Stage B reads this candidate until a future, documented
  promotion after passing tests. Nothing is priced automatically.
- Research reports and full provenance:
  `reports/ufc334_2026-11-14/THREE_EVENT_COHERENT_METHOD_SHADOW_EXPERIMENT.md`,
  `reports/ufc334_2026-11-14/THREE_EVENT_COHERENT_METHOD_SHADOW_EXPERIMENT.json`.
  Code/tests:
  `src/wshlx_ufc/joint_coherence_shadow.py`,
  `tests/test_ufc_three_event_joint_coherence_shadow.py`,
  `tests/test_generate_coherent_joint_method_sidecar.py`.

**Next actual work still pending:** verify first-party UFCStats or formally approve
the reconciled provisional mirror, then build *pre-bout-only* strength-of-
competition, takedown defense/get-up, damage absorption and duration-survival
candidate features. Run date-separated evaluation; do not train on Nov14 stats
for Nov14 outcomes, and do not override FanDuel Stage B price gates.


## November 16 further checkpoint — opponent-strength feature implementation

New source-only code now computes history-safe UFC Elo / past defeated-
opponent strength at **time of each fight** (no future-success lookahead).
All **153/153** prior method cases matched their pre-bout snapshots.
Unit tests verify historical results cutoff, same-date grouping, no
outcome field used in the predictor and no fabricated missing identity.

A genuinely event-ordered **89-fight retrospective conditional-method
comparison** found no substantive opponent-specific incremental benefit:
baseline 39/89; intercept 49/89; basic defense 49/89; quality-only
49/89; quality plus defense 48/89. Slight quality-only Brier improvement
from 0.558746 to 0.558435 is not adequate for promotion. The previous
Nov14 held-out intercept failure also remains decisive.

**Next technical gate:** build a true **pre-fight predicted-fighter-oriented**
feature/prediction pipeline and benchmark exact winner+method plus
fight-duration proper scores, with opponent quality, defensive grappling,
damage resistance and submission skill against verified-strength opposition.
Do not report this conditional-actual-winner oracle as 49 winning
fighter+method bets. No model or Stage A/B changes.

Full source/tests/CI:
`reports/ufc334_2026-11-14/OPPONENT_QUALITY_SHADOW_DEVELOPMENT_2026-11-16.md`.


## November 16 final quality/model selection gate: **NOT PROMOTED**

We now **graded the fighter each frozen Stage A model actually chose**,
instead of retrospectively conditioning on the actual winner. Three events
(UFC333 Oct24, Vegas124 Nov7, UFC334 Nov14), 40 decisive fights, 1 draw.
Using separately saved winner marginals with original within-side method
proportions, exact winner+method fell for quality-only candidate:
Reference **9/40 -> 6/40**, Historical **13/40 -> 12/40**, Unified
**14/40 -> 11/40**. Six-way Brier and log-loss also got worse.
Even intercept-only fit worsened probability scoring for all three
model families. Source:
`reports/ufc334_2026-11-14/TRUE_SELECTED_FIGHTER_METHOD_BENCHMARK_2026-11-16.md`.

Development action: **REJECT method intercept/quality adjustments**.
Keep strength-of-opposition features as *unpromoted research*.
The next meaningful challenger should address opponent-specific
finishing resistance, defensive grappling, get-ups and high-quality
opponent exposure using only prior fights, and it must be scored against
*originally selected fighters* across prospective locks. Maintain
no-odds Stage A / FanDuel Stage B separation, original 10k sims and
no-model-promotion governance.


## November 16 — finishing-resistance post-research decision

The pinned UFCStats-compatible historical archive is now audited for prior
fighter KO/sub resistance, KD faced, defended submission attempts inferred
only as *threat bouts without submission defeat*, takedowns conceded,
control allowed, and survival vs fighters with earlier documented UFC
finishing records. **There is no verified direct get-up count** in the
source, and 27 abnormal legacy round-format matches need further review.
For the pre-Nov14 UFC334 query, 25/26 fighters had prior UFC stats.

In a true originally-picked-fighter three-event test (40 decided outcomes,
with one draw excluded), this challenger **worsened** exact
winner+method and six-class proper scores across all three original
model families. Reference baseline 9 vs challenger 6 exact,
Historical 13 vs 12, Unified 14 vs 13.

**Do NOT promote this resistance method shadow.** Keep the useful
historical statistics as research-only features and preserve all original
three-model winner, method, timing and FanDuel Stage A/B gates. The
mathematically coherent winner+timing IPF sidecar remains a distinct,
unpromoted candidate, pending a truly pre-event frozen prospective card
and the original >=300 observation promotion guard.

See:
`reports/ufc334_2026-11-14/FINISH_RESISTANCE_2026-11-16_RESULTS_AND_DECISION.md`.


## November 16 — READY pre-event coherence lock pathway

**Verified upcoming event:** UFC Fight Night: Procházka vs Stirling,
November 21, 2026, Doha, Qatar. UFC's advertised prelims begin
**10:00am EST / 15:00 UTC**. Official event:
https://www.ufc.com/event/ufc-fight-night-november-21-2026

There is **no original frozen three-view Nov21 Stage A** in this research
branch as of this audit. No original or coherent-shadow Nov21 picks have
been generated. A new timestamp-gated locking protocol, unit tests,
manual-only workflow, and post-event separate research grading code are
ready **but will not run before normal Stage A**.

Source and protocol:
`reports/ufcqatar_2026-11-21/PROSPECTIVE_COHERENCE_READINESS.md`.
Source event manifest:
`research/events/ufcqatar_2026-11-21.json`.
Live lock:
`tools/lock_prospective_coherence_shadow.py`.
Safe source:
`src/wshlx_ufc/prospective_coherence.py`.
Post-event scorer:
`src/wshlx_ufc/prospective_coherence_grade.py`.

The pre-event sidecar independently includes **all three frozen views**
(Reference, Historical, Unified), with the untouched raw six-way method
probability, a winner-only-marginal projection, and a winner+direct
GTD_NO-marginal coherence projection. All original winner selections
and other timing prop markets stay unchanged. The script verifies
official event start, original frozen Stage A SHA, fighter identities
and all three original winner probabilities, refuses to write after
the 15:00 UTC earliest-start deadline and NEVER overwrites a shadow lock.
The grader verifies the frozen source and recalculates all probabilities
before independently scoring exact fighter+method and six-way Brier/log loss.

**Status: preparation only, research sidecar not locked yet.** Normal
Stage A/B, all FanDuel gates, reference champion, Historical/Unified
shadows, 10k simulations and official bets completely unchanged.
