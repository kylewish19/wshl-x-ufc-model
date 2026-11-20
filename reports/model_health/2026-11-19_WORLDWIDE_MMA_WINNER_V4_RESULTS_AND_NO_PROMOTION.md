# WSHL_X — Worldwide Professional MMA Winner v4: source-verified cross-promotion data and chronological outcomes

**Research completed:** 2026-11-19. **Status: RESEARCH ONLY; NO winner or method model promoted, NO new bets or near-certainty claims.**

## Verified external data source

- Original third-party source: [Fight Canon](https://github.com/Jadevit/fight-canon-db), compiled from UFC Stats, Sherdog, PFL, Oktagon and other public historical sources; open SQLite database under source project MIT license.
- Immutable downloaded release asset `db-2026-11-19-1934/canon.db` (published 19:34:59 UTC), size **184,770,560 bytes**, SHA256 **`8185a2163b5f97071dbc4ec68667cceb43f5e321fadc38c26b5069303af4d949`**. Later updates to the external database must not silently replace this exact research source.
- Verified UFC fights by **same event day AND both competitors' names** against the pinned UFC historical results and source-linked Fight Canon IDs, not approximate name matching.
- All **3,071** source result rows for 2021–Nov7 (includes non-modeled bouts and NCs) matched exactly; 3,016 of **3,036** clean, modelable modern feature rows have independently verified external fighter IDs. The remaining **20** quarantine ambiguous crosswalk, including **two distinct professional fighters named Bruno Silva**. No inferred non-UFC histories for these rows.
- Of 2026 clean training universe, 110 modern bout rows have a UFC debutant; all 110 have at least one debutant with three or more *recorded* pre-UFC pro fights in the verified Fight Canon histories. This is **coverage**, not evidence of predictive correctness or certainty, and availability of 2026 snapshot means historical record backfills cannot be ruled out.
- Date-exclusive feature calculations use only completed pro MMA bouts with event dates **strictly BEFORE** the target UFC fight; source contains follow-up records and current event results, which are not input features. Matches are verified using UFC bout identities rather than outcome labels. Names alone never authorize a cross-promotion join.

**Reproducible research GitHub Actions:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44622662648 (successful, verified SHA + full 2024–26 chronological training). Artifact `wshlx-worldwide-regional-history-v4-identity-audit` includes source audits, dated pro records, complete predictions and bootstrap scoring.

**Actual files:** `tools/audit_worldwide_mma_history_v4.py`, `tools/benchmark_worldwide_mma_winner_v4.py`, `tests/test_ufc_worldwide_mma_identity_v4.py`, `tests/test_ufc_worldwide_winner_v4.py`, `.github/workflows/worldwide-mma-identity-v4-audit.yml`. All research on `feature/historical-conditional-rates`; NOT main, original 11/21 Stage A, new v3 prospective sidecar or Coherent model.

## World-MMA additional features

New matchup-relative data:
- Number of **prior non-UFC professional bouts**, wins/losses, smoothed prior cross-promotion win rate;
- Prior non-UFC 3- and 5-bout form, activity in last 365 days, total professional fight history including UFC;
- Past regional **KO/SUB/DEC victories and losses** where directly recorded (with method-source coverage), smoothed finish-mix rates;
- Crosswalk verified/missing flag; no evidence guessed for name-ambiguous fights.
- The 16 added regional features augment previous UFC 57, producing 73 matchup features. Fighter roles mirrored and training restricted to 2021+ events strictly before each test year.

All winner variants share the same multinomial **fighter-specific conditional KO/SUB/DEC method predictor**, trained only before test year, so accuracy improvements are directly attributable to changing winner head/features. Methods NOT yet fixed.

## Actual paired results — boosted tree winner head (same method)

| Historical year | Prior v3 boosted winners | Regional v4 boosted winners | Prior v3 exact fighter+method | Regional v4 exact |
|---|---:|---:|---:|---:|
| 2024 (511) | **314/511 (61.45%)** | 313/511 (61.25%) | **175/511 (34.25%)** | 169/511 (33.07%) |
| 2025 (513) | 316/513 (61.60%) | **330/513 (64.33%)** | 176/513 (34.31%) | **187/513 (36.45%)** |
| 2026 retrospective (488) | 294/488 (60.25%) | **306/488 (62.70%)** | 150/488 (30.74%) | **163/488 (33.40%)** |

2026 v4 boosted exact difference **+13/488 = +2.66pp** (event-cluster bootstrap 95% CI **~+0.21pp to +4.89pp** against same boosted v3); the original analysis has already studied 2026, so **this interval is descriptive uncertainty, not an untouched-future validation**. 2025 exact +11/513 (CI crosses 0). 2024 exact -6/511. No consistent reliable exact dominance.

2026 boosted winner difference +12/488 (62.70% vs 60.25%); event-cluster CI includes zero. 2026 v4 boosted winner Brier **0.23163** and six-outcome log loss **1.63296**, improved versus v3 boosted (**0.23365**, **1.63675**), but worse than the logistic v3 (**0.22981**, **1.62830**). Comparing to the strongest preexisting candidate matters.

## Linear logistic research control

| Historical year | v3 logistic winner hits | v4 logistic winner hits | v3 logistic exact | v4 logistic exact |
|---|---:|---:|---:|---:|
| 2024 (511) | 310 | 314 | **168** | 167 |
| 2025 (513) | 314 | 324 | 169 | **174** |
| 2026 (488) | 303 | 304 | **157** | 156 |

The linear regional learner barely changes exact in 2026 and is no superior to boosted in 2025–26. Blindly accepting a better Brier or greater winner accuracy without exact improvements remains disallowed.

## Finishing-method problem is STILL present

The 2026 boosted v4 was correct on only **9 of the 84 actual SUB method classes** (SUB recall ~10.7%), while the boosted v3 had 11/84. Even though exact total rose 150→163, submission recall regressed. In 2025 both boosted models identified **12/91** actual submission classes; in 2024 v4 10/83 vs v3 9/83. No globally forced more SUB predictions, and **no method victory model improvement proven here**.

For confidence selection, the v4 boosted **top-five exact P** ranking scored **79/200** in 2024 (40 cards, 1 perfect 5-pick card), **81/195** in 2025 (39 cards, zero perfect), and **71/190** in 2026 (38 cards, zero perfect). The model CANNOT reliably pinpoint a 100% accurate 2–5 exact-method set every event; the user goal is aspirational, not demonstrably met.

## Decision and next action

- **No production promotion.** Stronger pre-UFC regional source provides 16 meaningful features; v4 boosted candidate may merit separately pre-locked FUTURE card predictions, but does not clear target and historical 2024 evidence is mixed.
- **Original November 21 2026 Stage A and Coherent, plus previously independently locked Winner v3 are SHA-protected and unchanged**. Any additional Winner v4 research shadow must be locked with a separate file and timestamp before November 21 first fight, with fighter identity verification and novice PASS flags; never revise original locks or conceal missing newcomer identities.
- Actual next method-model research should use **opponent-specific conditional finish features including pro-fight method records**, not only winner replacement. Separate trainer and preregister direct 6-way comparisons. Source-fight-level ground/clinch/head damage and reversals are available in UFC Stats and could be added with prior-date masking; get-ups are still not directly counted by the original UFCStats archive.
- Promotion requires multiple truly fresh event-locked fights, comparison to Historical and Unified on same bout IDs and same betting cutoffs, properly calibrated six-outcome uncertainty and superior exact scores; existing >=300 genuine prospective observation rule remains.
- No wagering confidence can be upgraded to near 100% based on these 2024–26 retrospective folds, even with 10,000 simulations or new regional records.

**Outcome:** We improved information and discovered some predictive lift in winner accuracy in 2025/2026; we have **not** met or proven 60–70% full-card exact accuracy or 2–5 perfect fighter+method outcomes.
