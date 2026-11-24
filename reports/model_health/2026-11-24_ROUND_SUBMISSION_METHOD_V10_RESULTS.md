# November 24 — Method v10 round and submission research

**Verified CI:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45492217530 — success, six targeted tests passed; complete historical comparisons and original frozen-source hash checks passed. Initial run 45492029261 failed because the source elapsed seconds are floats; corrected integer floor conversion, regression test for float durations, and shell pipefail now prevent this error being masked.

## Source and design
- Pinned historical UFCStats-derived archive through November 7, 2026, 8,871 supported bouts, same source SHA as v9.
- 42,310 parsed fighter-round rows after excluding two duplicate keys. 6,326 historical bouts had paired full-round data, 4,926 had the first two full rounds recorded. Coverage counts indicate matched round rows, not that every statistic was measured.
- Added 16 features per fighter, 32 per matchup: prior round coverage, first/later-round submission-attempt exposure on offense and defense, ground significant-strike shares, first-to-second full-round changes in own and opponent striking, own TD/submission activity and control, opponent control and submission activity.
- Incomplete rounds excluded; paired first/second full rounds only for changes. These are conditional associations, subject to survivor bias; not directly measured fatigue, get-ups, submission escapes or judge scoring.
- No target-fight observations enter features. Same calendar day frozen before updating. Missing parsed values are excluded from opportunity measures, not converted into observed zeroes.
- Fixed v3 symmetric logistic57 winner head across all arms, earlier-year conditional log-loss coefficient choice from .005/.025/.20, except legacy UFC38 fixed .20. 511/513/488 identical already-inspected chronological test bouts; no prospective credit. No odds or wager approvals.
- Round86 = prior method-mix54 plus 32 round features; round126 = round86 plus v9 conversion40. Hierarchical heads independently predict finish given winning fighter, then submission versus KO given finish and that fighter. Predict both possible winners before combining with fixed winner probability. All comparisons isolate UFC-only conditional method heads, not directly compare with v5 regional or production Reference.

## Exact fighter+method hit counts
| Arm | 2024 (511) | 2025 (513) | 2026 (488) |
|---|---:|---:|---:|
| Legacy UFC38 fixed C=.20 | 168 | 169 | 157 |
| Tuned UFC38 | 167 | 168 | 146 |
| v9 method mix54 | 176 | 168 | 153 |
| Hierarchical mix54 | 180 | 171 | 150 |
| Round mix86 | 172 | 177 | 158 |
| Hierarchical round86 | 175 | 172 | 157 |
| Round conversion126 | 167 | 168 | 152 |
| Identical winner hits, every arm | 310 | 314 | 303 |

## Mean six-state log loss (lower is better)
| Arm | 2024 | 2025 | 2026 |
|---|---:|---:|---:|
| Legacy UFC38 | 1.604755 | 1.601160 | 1.628300 |
| Tuned UFC38 | 1.602408 | 1.596758 | 1.629273 |
| v9 mix54 | 1.585069 | 1.579594 | 1.615178 |
| Hierarchical mix54 | 1.582818 | 1.583212 | 1.614961 |
| Round mix86 | 1.589366 | 1.584341 | 1.609649 |
| Hierarchical round86 | 1.583964 | 1.587599 | 1.612714 |
| Round conversion126 | 1.594881 | 1.588213 | 1.608753 |

## Exact submission hits
| Arm | 2024 | 2025 | 2026 |
|---|---:|---:|---:|
| Legacy UFC38 | 12 | 9 | 12 |
| Tuned UFC38 | 12 | 7 | 8 |
| v9 mix54 | 13 | 8 | 10 |
| Hierarchical mix54 | 11 | 6 | 9 |
| Round mix86 | 13 | 12 | 11 |
| Hierarchical round86 | 13 | 10 | 11 |
| Round conversion126 | 14 | 10 | 10 |

Round mix86 improves exact hits over the legacy fixed head in all three retrospective years, but the 2026 gain is only one bout and it loses four exact predictions in 2024 versus v9 mix54. Compared to v9 mix54 the exact differences are -4/+9/+5 and the logloss differences worsen 2024/2025 while improving 2026. Hierarchical round86 improves all three exact totals over the legacy or ties, but is less accurate than the single-stage round86 in 2025/2026. Submission hits remain very low relative to all actual submissions; in 2026 no new variant beats the legacy's 12 exact SUB hits. More features alone do not establish better prediction.

## Decision and next steps
- Retain round mix86 as an experimental candidate for further evaluation, no production replacement or claim of calibrated 70% exact; do not select winners from the same previously studied year results. No automatic prospective lock, no new wagers.
- Need sharper opponent-relative access/finish-resistance models and class-specific diagnostic calibration; inspect prior full-round submission opportunity and actual prior finish outcome distinctions. Consider predeclared evaluation of separate method ranking and submission probability calibration against simple method priors and regional v5 on identical cohorts. Do not change the original winner head just to make exact scores look better.
- Qatar 64-round supplemental CSV and Nov14/21 outcomes remain in the separate validated postevent extension. This historical v10 experiment used the Nov7 archive only; future runner integration and prospective v10 testing not yet implemented. Original Stage A/B and previous research sidecars unchanged. Coherent retains its separate 12-fight prospective record, gate 300 unique decisive fights.
- Full per-fight result CSV and JSON with paired event-bootstrap comparisons are preserved in the successful workflow artifact. Code: `src/wshlx_ufc/round_method_v10.py`, `tools/benchmark_round_method_v10.py`, `tests/test_ufc_round_method_v10.py`, `.github/workflows/ufc-round-method-v10.yml`.
