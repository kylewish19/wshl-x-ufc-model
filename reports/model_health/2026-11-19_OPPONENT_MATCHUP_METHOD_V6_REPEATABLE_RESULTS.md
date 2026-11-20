# WSHL_X UFC Method v6 — opponent-relative matchup finishing, nested coefficients and repeatability

**Historical evaluation November 19, 2026. Status: VERIFIED RESEARCH, NOT APPROVED FOR PRODUCTION OR ANY WAGER.**

**Execution 1, complete source/probability checks passed:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44627685201 .
**Execution 2, strict single-thread replay with 2 independent trainings and byte-for-byte forecast comparison passed:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44628426421 .

**Independent date-out-of-year forecast CSV SHA256 (both runs identical):** `491602026351188e294e07a331e195728d24ef3424c61b1f238575322401ecf9`. Artifacts `wshlx-opponent-relative-method-v6-nested-chronological-research` have full six-state forecasts/temporal fold results/coefficients. Code `tools/benchmark_opponent_matchup_method_v6.py`, tests `tests/test_ufc_opponent_matchup_method_v6.py`, workflow `.github/workflows/ufc-opponent-matchup-method-v6.yml`.

## What was missing from earlier v5 methods

The FIRST 38 UFC method predictors **already** included rival takedown defense, finish vulnerability, and fighter-vs-rival interactions. Therefore, don't falsely claim earlier model ignored opponents. V5 added only the selected winner's regional pro MMA record. New V6 separately adds:

- **Opponent pre-UFC pro MMA method record** (16 dimensions), so opponent KO losses and SUB losses can condition attacker's finish chances;
- Pre-fight recent 3-fight strike accuracy/absorption and wrestling activity for **both** candidates (19 each);
- Seven prespecified offensive-vs-defensive interaction proxies using those source-verified measures.
- Candidates: regional self-only 54 (same as v5); both regional histories 70; both recent UFC histories + regional 108; seven further interactions 115; and independent nonlinear 115. Original UFC-only 38 retained as control.

All values come from the SHA-pinned UFC archive and `db-2026-11-19-1934` FightCanon pro history with two-fighter matched identities. No current fight data entered predictors. Historical source may contain **retrospectively backfilled** past pro fights; this is not a newly discovered pristine time-stamped 2024 archive.

**Coefficient selection discipline:** 2024-test regularization chosen by 2023 conditional method log loss (train before 2023), 2025-test by 2024 (train before 2024), 2026-test by 2025 (train before 2025). Tried C = 0.005, 0.025, 0.10, 0.35. Prior-only validation chose **C=0.005** for all three expanded linear logistic architectures in all three years. New method models refit using all past data before test year. Full sample 2024 511, 2025 513, 2026 488 decisive fights, scored with same held-fixed independently trained winner head.

## Year-by-year comparison, fixed Winner v3 logistic-57

| Historical year | Method v5 54-feature exact | New v6 70 exact | New v6 108 exact | New v6 115 exact | 54 six-way log loss | 108 six-way log loss |
|---|---:|---:|---:|---:|---:|---:|
| 2024 (511 fights) | **177** | 177 | 167 | 170 | 1.59769 | **1.56741** |
| 2025 (513 fights) | 173 | 187 | **188** | 186 | 1.58895 | **1.57004** |
| 2026 (488 fights) | **158** | 153 | 155 | 153 | 1.61108 | **1.59644** |

New 108-feature model also **decreased correctly identified actual SUB method classes** versus v5: 2024 20→17 /83, 2025 16→12 /91, 2026 15→13 /84. A better overall six-way log loss does not imply better winning-fighter-plus-method selection. No global SUB forcing or quota was applied.

## With Winner v4 boosted 73 fixed

| Year | V5 54 exact | V6 70 exact | V6 108 exact | V6 115 exact | V6 boost115 exact |
|---|---:|---:|---:|---:|---:|
| 2024 | 178 | **180** | 166 | 169 | 165 |
| 2025 | 196 | **201** | **201** | 197 | 185 |
| 2026 | **158** | 155 | 154 | 152 | 149 |

The full combination still never achieves 40% exact consistently, versus the user target 60–70%. Each year winner head remains fixed within matched method comparisons and cannot explain method-head changes. Event-level bootstrapped intervals for v6 vs v5 exact improvements generally cross zero, including the 2026 regression.

**Important reproducibility investigation:** Earlier unrelated 2024/2026 boosted winner research artifacts produced 1–2 different winners on reruns while logistic models remained unchanged; p-values differed by up to about 1 percentage point for a few fights. Potential causes include multi-thread gradient fitting or dependency version drift (not yet causally established). This v6 workflow now enforces `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, and runs the **whole 1,512-bout forecast generation twice**, comparing exact CSV bytes. Both successful. This guards against incidental research rerun changes; does not retroactively change the earlier independently committed V4 or official card.

## Top-2/3/5 exact subsets

Across 2026's 38 eligible full 11–14-fight cards, top 5 by exact probability:
- V3 winner + 54 method: 74/190 exact, **0 perfect five-pick cards**.
- V3 winner + 108 method: 67/190 exact, **0 perfect five-pick cards**.
- V4 winner + 108 method: 71/190 exact, **0 perfect five-pick cards**.

This disproves the notion that merely adding more matchup variables or tuning logistic C allows reliably guaranteed five exact picks. Same previously used historical periods, not untouched future evidence.

## Decision

**No model promoted, no official picks altered, no additional FanDuel wagers approved.** November 21 original official Stage A, Coherent Challenger, independent V3, V4 and V5 research shadows remain unchanged. The next candidate should be a separately fitted genuinely **direct six-outcome** model with these bilateral professional fight histories rather than more tuning on v5 conditional probabilities. Build the new six-way learner with (i) mirrored fighter roles, (ii) only earlier-year coefficient selection, (iii) same original fighter/finish evaluations, (iv) exact-probability ranked selective sets, and (v) strict 2024–26 prior-researched retrospective disclaimer. Do not confuse more training samples, small Brier changes or 10,000 simulations with an independently validated 70% model.
