# WSHL_X — prospective coherence evaluation plan
Registered November 17, 2026, ahead of the next unplayed UFC card. Research only; no model trained, promoted, or bet approved.

## Existing code to reuse (do not duplicate November 16 experiments)
- `src/wshlx_ufc/joint_coherence_shadow.py` — winner margin and joint winner+direct GTD probability projection.
- `src/wshlx_ufc/prospective_coherence.py`, `tools/lock_prospective_coherence_shadow.py` — frozen source verification and live UTC lock.
- `src/wshlx_ufc/prospective_coherence_grade.py`, `tools/grade_prospective_coherence_shadow.py` — immutable post-event grade.
- `reports/ufc334_2026-11-14/THREE_EVENT_COHERENT_METHOD_SHADOW_EXPERIMENT.md` — already-completed retrospective study. Historical exact 13/40 to 20/40, Unified 14/40 to 16/40 under winner+timing alignment; sample already examined. No prospective credit.
- `reports/ufcqatar_2026-11-21/PROSPECTIVE_COHERENCE_READINESS.md` — existing next-card protocol.

## Fixed evaluation design
On each future eligible UFC event, after original odds-blind Stage A and before the first fight, lock raw, winner-aligned, and winner+direct-GTD-aligned distributions for Reference, Historical, Unified. Preserve source checksums and externally dated commit or Actions evidence. Do not recreate locks after fights. No original predictions are replaced.

Primary research comparison: each model's winner+timing aligned joint vs its own native joint, with **mean six-class log loss** as primary proper score and mean six-class Brier as secondary. Winner-only alignment remains a diagnostic comparator; keep its results regardless of performance. All variants hold the corresponding frozen winner head and side fixed. Also record comparisons to the unchanged Reference on identical eligible fights. For future simple baseline comparisons, publish an independently source-pinned, pre-event baseline forecast with the same fighter identities before results; do not backfill a missing lock as prospective. Continue to report simple baselines only when authentically available.

Track exact selected fighter+method accuracy, KO/SUB/DEC class-wise and exact recall, native winner Brier/log loss and direct GTD scoring separately. Preserve draws/NC/DQ/cancellations as explicit non-gradeable categories for six-way scores; do not count them as losses or silently omit them. Timing is evaluated under its own eligibility rules. Count **unique decisive prospective bouts** once, never multiply by the number of variants, markets or models. Report event-level results and paired event-cluster uncertainty once sufficient independent events accrue. No promotion from a single event or any earlier retrospective results. Preserve the existing >=300 prospective-observation gate where applicable and documented comparison requirements before any promotion.

## Next eligible card
The existing archived UFC event manifest for Nov21 schedules earliest bouts at 15:00 UTC (10 AM Eastern); recheck actual official start and full current lineup before freezing. As of this registration the original Qatar Stage A freeze is absent; no next-card shadow exists. Current genuinely prospective observations for this protocol: **0**. Next action is normal Stage A followed by the existing real-clock sidecar lock before the first bout. If the deadline is missed, record the card as ineligible; no backdating.

No changes to Reference/Historical/Unified production probabilities, Stage A/B picks, simulations, FanDuel policy or prior grading. This registration is not a wager or a model promotion.
