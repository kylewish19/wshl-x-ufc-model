# November 24 — finishing-conversion v9 and future history extension

## Verified execution

GitHub Actions run [45490332703](https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45490332703) completed successfully. Seven targeted tests passed, all 3 historical test cohorts were scored, and the original November 21 frozen source checksums were verified unchanged.

## Coherent challenger: first prospective observation

The existing November 21 lock was compared against the verified outcomes without any refitting or changing winner selections. Full audit: `reports/model_health/2026-11-24_COHERENCE_FIRST_PROSPECTIVE_MATCHED_COMPARISON.json`.

| View | Original exact | Winner/timing-aligned exact | Original log loss | Aligned log loss |
|---|---:|---:|---:|---:|
| Reference | 4/12 | 7/12 | 1.485161 | 1.249023 |
| Historical | 5/12 | 5/12 | 1.426407 | 1.328628 |
| Unified | 3/12 | 7/12 | 1.402727 | 1.242024 |

All three views improved six-way Brier and finish/nonfinish Brier on this card. Reference and Unified retained 11/12 winners, and both aligned views predicted 6 KO, 0 SUB, 6 DEC. Actual: 3 KO, 1 SUB, 8 DEC. Reference retained all 3 correct KOs and gained 3 correct decisions. No original winning-fighter selection was altered. Neither aligned view selected Albazi's submission.

This is just one prospective event, 12 unique decisive fights, not 36 observations from the three views. The earlier 40-fight reconstruction was retrospective, not a second prospective evaluation. The minimum 300-bout prospective gate remains; 288 further unique decisive bouts are required for that minimum. No model promotion.

## Data pipeline

- `data/results/ufcqatar_2026-11-21/fightingdata_round_stats_secondary_2026-11-24.csv`: 64 fighter-round rows. All 24 fighter totals reconciled to the previously stored Qatar totals for significant strikes landed/attempted, takedowns landed/attempted, control seconds and knockdowns.
- Sources: https://fightingdata.com/events/ufc-fight-night-prochazka-vs-stirling/ and the archived per-bout Cage Almanac UFCStats-derived pages. Both are secondary mirrors; agreement does not establish independent primary UFCStats verification. Total strikes, submission attempts, and reversals are not cross-checked by the six-field reconciliation.
- `src/wshlx_ufc/postevent_history_extension_v1.py`: explicit date-safe research extension from Nov 25 onward. Extends 8,871 base bouts to 8,896 with 13 UFC334 and 12 Qatar bouts, 24 decisive and 1 draw. Verified outcomes included; UFC334 provisional stats excluded. Qatar secondary totals require explicit opt-in; outcome-only default. Pinned source blobs and base checksums validated. New APIs expose training features/labels and future snapshots; original production archive and runners are unchanged. The round dataset is archived and reconciled, not yet a round-sequence prediction model.
- `tests/test_ufc_postevent_history_extension_v1.py` exercised actual source data and future cutoff guards.

## New finishing conversion research (v9)

`src/wshlx_ufc/finish_conversion_v9.py` adds observed prior winning/losing method distributions (8 features per fighter) plus prior KO/submission/decision conversion and exposure statistics (20 per fighter). The latter use recorded knockdown/no-knockdown opportunities, submission attempts and takedown/control access, including defensive analogues. No fabricated get-ups or current-fight observations. These associations are descriptive, not causal estimates of the effect of grappling or knockdowns.

`tools/benchmark_finish_conversion_v9.py`: fixed Winner v3 logistic57 head across arms, 2024/2025/2026 chronological test cohorts (511/513/488 bouts), regularization selected using only preceding validation year for tuned arms, fixed C=.20 legacy UFC38 comparator. The same historical cohorts have already been inspected in prior research. No sportsbook odds. The extended November data are not used in the historical comparison, so old results are not contaminated.

| Year | Legacy UFC38 fixed | Tuned UFC38 | Historical method mix54 | Conversion94 | Fixed winner correct |
|---|---:|---:|---:|---:|---:|
| 2024 | 168/511 | 167/511 | 176/511 | 173/511 | 310/511 |
| 2025 | 169/513 | 168/513 | 168/513 | 168/513 | 314/513 |
| 2026 retrospective | 157/488 | 146/488 | 153/488 | 147/488 | 303/488 |

| Year | Legacy log loss | Tuned baseline log loss | Mix54 log loss | Conversion94 log loss |
|---|---:|---:|---:|---:|
| 2024 | 1.604755 | 1.602408 | 1.585069 | 1.589286 |
| 2025 | 1.601160 | 1.596758 | 1.579594 | 1.582105 |
| 2026 | 1.628300 | 1.629273 | 1.615178 | 1.611966 |

The new features improved proper probability scores in all three cohorts compared with the legacy fixed-regularization head, but they did not produce robust gains in the primary exact-pick goal. 2026 exact submission hits: 12 legacy, 8 tuned baseline, 10 mix54, 9 conversion94. The simpler historical method-mix variant beats the full conversion variant on 2024 and 2026 exact hits. The tuning/feature changes should not be mistaken for a new production edge. This test isolates the UFC-only method head, not a direct head-to-head with the regional v5 or Reference production system.

## Decision

Keep all existing official winner and method locks. Continue the existing prespecified Coherent Reference and Unified prospective research, with native distributions retained as comparators. No retrospective promotion based on one good card. The newly tested v9 variants remain research only, without official picks, until a candidate demonstrates meaningful exact-outcome improvement. Next research priority: separately validate submission pathways and a matchup-aware finishing/decision model using independently supported prior round/position information and stronger baselines. Track timing, exact hits, proper scores and genuinely available FanDuel prices independently. Future model runs must explicitly opt into the new history interface; production runners have not yet been migrated. No guarantee of 70% exact or 2–5 flawless selections.
