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
