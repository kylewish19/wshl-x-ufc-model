# WSHL_X UFC — November 21 Prospective Coherence Shadow Readiness

**Research branch:** `feature/historical-conditional-rates`
**Event:** UFC Fight Night: Procházka vs Stirling, Doha, Qatar, **November 21, 2026**. Source: https://www.ufc.com/event/ufc-fight-night-november-21-2026
**Earliest scheduled bout window:** **10:00 AM EST = 15:00 UTC**. This is a **strict deadline** for the sidecar lock, not the main-card time.

## Current status: READY TO LOCK AFTER NORMAL STAGE A — NOT LOCKED YET

As checked November 16, there is **NO** `data/locks/ufcqatar_2026-11-21/stage_a_final_selection.json`, nor its corresponding `stage_a_model_raw_three_view.json`, on this research branch. The UFC's announced November 21 card is subject to fight-week changes; our normal complete card and three-model Stage A forecast must be collected and frozen **before** a new research shadow is permitted.

**No November 21 fighter winner, method or timing forecast was invented or published by this change.**

## Why a new strict research locking process was needed

The earlier `generate_coherent_joint_method_sidecar.py` was designed for development experiments and explicitly supports *post-event replays*, including synthetic past-time inputs in tests. Those replays can teach us about arithmetic but **cannot** be counted as prospective picks. The new code refuses to publish a prospective shadow after the UFC's earliest confirmed start, and it is independent of all actual fight results and FanDuel odds.

The research candidate is mathematically coherent, not a new trained outcome model. It preserves each existing view's raw forecast and projects six fighter-plus-method probability states:

1. **Raw archived**: the untouched six-way KO/SUB/DEC on fighter A and fighter B.
2. **Winner-aligned**: totals of A/B method outcomes are constrained to that exact model's separately frozen winner probabilities.
3. **Winner and direct timing aligned**: additionally constrain total KO+SUB mass to the same model's frozen direct `GTD_NO` probability (and all decision mass to `GTD_YES`).

All three original model views are now included: **Reference, Historical and Unified**. The original winner selections remain fixed, with the winner's top conditional KO/SUB/DEC method reported for each purely research variant. The 10,000 simulations, round-start, over/under and other timing forecasts **do not change**; only GTD outcome probabilities are used as a consistency constraint. The existing user-facing three-model consensus/video picks **do not change**.

## Exact live-lock protocol

1. **Run the normal full UFC Fight Night November 21 Stage A**: full fighter list, tape/research checks, 10,000 sims, Reference/Historical/Unified winner+method+timing outputs, odds-blind. Do not change the champion model or promote a challenger based on past UFC334 errors.
2. **Freeze Stage A in its own original files**, including the existing `stage_a_final_selection.json` and `stage_a_model_raw_three_view.json`, with raw SHA-256 integrity and `frozen_at_utc`. This pipeline does *not* generate or alter those files.
3. **Before Saturday November 21 at 15:00 UTC**, run the separately implemented tool from the feature branch:
   ```bash
   python tools/lock_prospective_coherence_shadow.py --event-slug ufcqatar_2026-11-21
   ```
   Alternatively, trigger the manual-only GitHub workflow `.github/workflows/lock-ufcqatar-nov21-coherent-shadow.yml` on the feature branch **if available through your repo's Actions settings**. GitHub may require a workflow definition on the default branch before manual dispatch is offered. The CLI remains the reference path. Do **not** bypass its time or source guards.
4. The tool checks the original **raw hash**, the entire original frozen file, the official event-time manifest, timestamp ordering, no-odds flags, original fighter identities, main-event pairing, all three original model winner selections and probabilities, six-way mass and GTD probability ranges. It writes a **new file exclusively**:
   `data/shadow_locks/ufcqatar_2026-11-21/coherent_joint_pre_event_shadow.json`.
   **Never overwrite it.** Commit this independent sidecar to GitHub *before the first fight* and preserve the Actions run / commit history as an externally dated proof. The post-event scorer recalculates every shadow probability from original SHA-verified inputs to detect tampering.
5. **Run original Stage B separately**, using FanDuel prices only, the same approved price/edge/coherence gates and the original locked Stage A card. The research shadow does **not** approve new wagers.
6. **After all fights and independently verified results**, prepare a complete, verified result source file (the scorer does not auto-fetch odds or outcomes). Run:
   ```bash
   python tools/grade_prospective_coherence_shadow.py --event-slug ufcqatar_2026-11-21 --verified-results path/to/ufcqatar_verified_results.json
   ```
   Each verified result row must supply `fight_no`, original `a` and `b` names in locked order, `winner` and `method` (KO/TKO, SUB, DEC; DRAW or NC explicitly excluded). File-level fields must include `event_slug`, `event_date`, `results_verified: true`, `results_source_url` and `verified_at_utc`. An incomplete or conflicting result card is rejected. Grade is stored in its own, previously nonexistent file:
   `data/shadow_grades/ufcqatar_2026-11-21/coherent_joint_post_event_grade.json`.
7. Keep separate cumulative prospective challenger logs; **no promotion** until the existing >=300 prospectively locked observation evaluation has passed proper scoring (six-way Brier/log loss), exact selected fighter+method, KO/SUB/DEC recall and the original winner/timing performance protection checks.

## Why this research candidate is worth testing, not automatically accepting

The October24/November7/November14 retrospective study on 40 decisive fights found a modest gain in six-way scores when enforcing winner *and* direct timing coherence, while adjusting fighter+method finish rates or adding opponent-quality/durability factors performed worse on the original chosen fighter. The coherence method was designed after seeing those events, so it remains **ineligible for a 'prospective accuracy' claim** until timestamped predictions are truly made before the first fight.

The three model views are correlated, particularly Unified with its contributing views. A 2-of-3 consensus is an editorial voting rule, not three independent statistical confirmations. No majority-consensus video/script change is made here.

## Files and governance

- `research/events/ufcqatar_2026-11-21.json` — official event date/start-time evidence and partial lineup warning.
- `src/wshlx_ufc/prospective_coherence.py` — strict lock checks and reproducible three-view projections.
- `tools/lock_prospective_coherence_shadow.py` — real-clock, exclusive-write research-only CLI.
- `.github/workflows/lock-ufcqatar-nov21-coherent-shadow.yml` — optional branch-only manual lock workflow; no automatic run.
- `src/wshlx_ufc/prospective_coherence_grade.py` — grade exact original selected fighter+method, true six-way proper scores, original direct GTD scores.
- `tools/grade_prospective_coherence_shadow.py` — result-verified, exclusive-write post-event scorer.
- `tests/test_ufc_prospective_coherence_lock.py`, `tests/test_ufc_prospective_coherence_grade.py` — sample old UFC334 **unit-test fixtures only**, never a genuine prospective UFC334 lock.

**Production status:** UNCHANGED — Reference champion, Historical and Unified original shadow models, all Stage A/B selections, all 10k simulations, FanDuel price rules and user-visible consensus/video content. No next-card bet, method or winner has been recommended by this research.
