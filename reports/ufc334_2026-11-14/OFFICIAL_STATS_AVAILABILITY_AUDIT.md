# UFC 334 — post-event fight-stat source audit (Nov 15, 2026)

## Scope and integrity

Post-event results and model/Stage B grading are COMPLETE and independent of post-event performance features. This is a **data-availability audit**, not confirmation of a complete UFCStats import, model training, or review of continuous full-fight footage.

Attempted direct official UFCStats completed events URL: https://ufcstats.com/statistics/events/completed?page=all ; web fetch returned **502 Bad Gateway** on Nov 15. As a result, the official UFCStats fighter-by-fighter/per-round performance dataset was **NOT independently retrieved or ingested** in this run.

## Public alternative stat sources discovered

- MMA Index: https://www.mmaindex.com/events/ufc-334-2026-11-14 (13/13 fight totals listed; descriptive fighter stats, opponent striking and control).
- PropBetEdge: https://ufc.propbetedge.ai/events/ufc-334-2026-11-14 (13/13 fight totals, judges and per-bout summaries).
- UFCalendar: https://www.ufcalendar.com/events/ufc-2026-11-15/ciryl-gane-vs-josh-hokit (Gane/Hokit detailed fighter and per-round totals).
- Stats Fight: https://www.statsfight.com/schedule/ufc/ufc-334-gane-vs-hokit-41916/ (independently collected proprietary strike accounting, **not** the same definition as official UFCStats).
- Official results: https://www.ufc.com/index.php/news/polymarket-ufc-334-gane-vs-hokit-results (verified winners/method/round).

## Why a reconciliation step is mandatory

These sites do NOT automatically constitute identical official stats. For example **MMA Index and UFCalendar list Ciryl Gane at 237 significant strikes landed** against Josh Hokit, while **PropBetEdge lists 252** in its displayed fight totals. Stats Fight defines and counts strikes with its own criteria. These conflict or use different counting methods; do not quietly select the source that supports a desired model narrative.

Several provisional public totals have useful diagnostic hypotheses to check: MMA Index reports Borralho controlled Belgaroui for 7:47, Gurule controlled Hasan 6:19, Elder landed six takedowns, and Almeida registered two knockdowns. These are **NOT yet an official reconciled fighter-by-round dataset**; treat as source-reported leads for later validation.

## Rules for follow-on work

1. Retrieve official UFCStats per-fight and per-round striking, TD attempts/landed, control, knockdowns and submission attempts, with exact fight IDs and timestamps. Check source access.
2. Match every fighter ID, name, result, round and opponent to the 13 immutable frozen fight identities; reconcile totals with the official UFC scorecards and result sources.
3. Record original raw source and fetch hash, provenance and dates. Explicitly distinguish data captured **after** a card from features that would have been known **before** the card.
4. Create a versioned clean official dataset and review it before adding to historical training; do not leak the Nov14 result into predictions for Nov14.
5. Run an out-of-time method/finish calibration comparison across multiple cards before changing champion/shadow predictive weights.

**Current ingestion status: official UFCStats full post-event stats NOT ingested. Official outcome grade verified.**


---

## November 16 UPDATE — 13/13 UFCStats-derived mirrored fight summaries acquired

**Status change:** The November 15 statement that full performance stats were
not ingested was accurate at that time. On November 16, all **13 fights / 26
fighters** were transcribed from the two independently displayed UFCStats-derived
mirrors `FightingData` and `Cage Almanac`, with 72 fighter-round entries for
significant strikes, takedowns, control seconds and knockdowns.

- Full 26-fighter / 32-column data: `data/raw/ufc334_2026-11-14/ufc334_complete_26_fighter_mirror_totals_PROVISIONAL.csv`
- Round-level 72-row data: `data/raw/ufc334_2026-11-14/ufc334_fighter_mirror_per_round_PROVISIONAL.csv`
- Individual source links / validation restrictions: `data/raw/ufc334_2026-11-14/INGESTION_MANIFEST_PROVISIONAL.json`
- Source-audit code: `src/wshlx_ufc/post_event_stats_audit.py`
- Test coverage: `tests/test_ufc334_post_event_mirror_stats_integrity.py`

**What is now verified internally:** Every fighter's 72 fighter-round source
observations sum to the published 26 fight totals for each recorded round-level
core feature; per-fighter totals match the corresponding Cage Almanac UFCStats-
derived fight pages. Additional total strikes, submission attempts, reversals,
and strike placement/target totals were cross-checked and their component
sums validated. The original UFC 334 frozen matchup identities and official
fight results still agree.

**What is NOT established:** direct first-party UFCStats access; a complete
official first-party round-by-round export for all detailed strike locations;
independent reconciliation of other aggregators that disagree (notably
PropBetEdge's Gane-Hokit significant-strike counts). This remains a marked
**PROVISIONAL MIRROR-CROSSCHECKED** dataset, `allow_training = false`,
not automatically merged into champion model training.

Once the direct source or an explicitly approved mirror-data fallback is
validated, the stats can be added as *historical outcomes after Nov14* for
the Nov21 and later UFC cards. They **cannot** be backdated into the Nov11
prediction inputs or used to refit the champion without chronological tests.
