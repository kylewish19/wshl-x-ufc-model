# UFC 334 (2026-11-14) — prior-conversation recovery snapshot

**Recovery date:** 2026-11-12 (pre-event)
**Status:** RECOVERED CONVERSATION RECORD — **NOT** the original signed/hashed Stage A lock, a model artifact, a code run, or authorization to place wagers.
**Repository:** `kylewish19/wshl-x-ufc-model`
**Source:** Previous assistant outputs from the user's 2026-11-11 UFC 334 discussion (Stage A around 2026-11-11 23:00 UTC; Stage B around 2026-11-12 01:57 UTC), accessed through conversation-context retrieval on 2026-11-12.

## Critical continuity / integrity notes

1. The previous conversation reports that **13 bouts were analyzed and Stage A was frozen before FanDuel pricing**. We recovered the displayed winner/model-top-conditional-method/timing selections below. This snapshot does **not** recreate or overwrite the original lock.
2. We searched `main`, `feature/historical-conditional-rates`, and `post-edmonton-integration`. The original November 11 Stage A JSON, Stage B audit, hashes, generated simulations, and claimed November code/test results were **not verified** on any of those branches during the 2026-11-12 audit. The newest visible `main` commits concerned UFC Edmonton (Oct 17).
3. **Do not backdate this commit**, call this a full model rerun, claim a 10,000-trial simulation was run as part of recovery, invent missing numerical markets, or promote a shadow/challenger model. Do not overwrite old frozen records.
4. Stage A classifications reported: **2 SIDE, 3 LEAN, 8 PASS**. The per-fight assignment to these labels was not recovered. There were **six method/timing warnings**, whose exact per-fight content has not been recovered.
5. The prior report said the fighter data was updated through **2026-11-07**, while historical method/timing and Unified weights remained on an October 17 fitting basis. This is a *previous-conversation claim*, not independently reexecuted or validated model code in this recovery.
6. Winners and methods below reflect the **displayed original model predictions**, not price-based choices. **Method percentage is conditional on that model's predicted fighter winning**, not unconditional fighter+method probability. Timing column is a selection, **not a recovered timing probability**.

## Recovered Stage A displayed model table

| # | Bout | Reference — predicted winner, win p; leading conditional method | Historical — predicted winner, win p; leading conditional method | Unified — predicted winner, win p; leading conditional method | Displayed primary timing |
|---|---|---|---|---|---|
| 1 | Elder vs Sanches | Elder **51.5%**; KO/TKO **44.7%** | Sanches **53.7%**; KO/TKO **44.4%** | Sanches **52.1%**; KO/TKO **49.9%** | Over 1.5 rounds |
| 2 | Alatengheili vs Diaz | Diaz **82.2%**; SUB **53.6%** | Diaz **72.9%**; SUB **51.6%** | Diaz **76.0%**; SUB **53.5%** | Over 1.5 rounds |
| 3 | Chiasson vs Mesquita | Chiasson **56.8%**; KO/TKO **52.8%** | Mesquita **70.0%**; SUB **62.1%** | Mesquita **62.5%**; SUB **63.2%** | Over 1.5 rounds |
| 4 | Gordon vs Costa | Costa **66.7%**; KO/TKO **51.8%** | Costa **77.4%**; SUB **41.4%** | Costa **74.5%**; KO/TKO **36.9%** | Over 1.5 rounds |
| 5 | Johnson vs Almeida | Johnson **85.2%**; KO/TKO **65.0%** | Johnson **76.5%**; KO/TKO **37.1%** | Johnson **79.4%**; KO/TKO **47.8%** | GTD No |
| 6 | Miller vs McKinney | McKinney **74.2%**; KO/TKO **50.6%** | McKinney **79.1%**; KO/TKO **44.2%** | McKinney **77.7%**; KO/TKO **46.7%** | GTD No |
| 7 | Dober vs Duncan | Duncan **64.1%**; KO/TKO **37.8%** | Duncan **76.9%**; SUB **45.0%** | Duncan **73.4%**; SUB **39.6%** | Over 1.5 rounds |
| 8 | Thompson vs Radtke | Radtke **63.6%**; KO/TKO **54.3%** | Radtke **78.5%**; DEC **39.9%** | Radtke **74.5%**; KO/TKO **42.2%** | Over 1.5 rounds |
| 9 | Hasan vs Gurule | Hasan **54.1%**; KO/TKO **73.5%** | Hasan **65.7%**; KO/TKO **55.6%** | Hasan **62.3%**; KO/TKO **62.8%** | GTD No |
| 10 | Medić vs Holland | Medić **51.9%**; KO/TKO **48.9%** | Medić **60.2%**; KO/TKO **53.9%** | Medić **57.7%**; KO/TKO **52.3%** | GTD No |
| 11 | Borralho vs Belgaroui | Borralho **54.3%**; KO/TKO **49.8%** | Belgaroui **53.2%**; KO/TKO **51.0%** | Belgaroui **51.0%**; KO/TKO **57.8%** | Over 1.5 rounds |
| 12 | Harrison vs Nunes | Harrison **83.5%**; KO/TKO **40.0%** | Harrison **70.5%**; SUB **44.4%** | Harrison **75.0%**; SUB **42.1%** | Over 1.5 rounds |
| 13 | Gane vs Hokit | Gane **72.6%**; KO/TKO **72.8%** | Hokit **59.8%**; KO/TKO **51.7%** | Gane **50.3%**; KO/TKO **54.2%** | GTD No |

**Interpretation:** Divergent model sides are intentionally preserved (for example, Elder/Sanches, Chiasson/Mesquita, Borralho/Belgaroui, Gane/Hokit). Never harmonize them after viewing sportsbook odds.

## Recovered Stage B summary — FanDuel ONLY

The prior Stage B assistant output reported **334 quoted prices checked, 310 supported by model probabilities, 24 excluded duplicate draw quotes without a supported draw model**. It reported **three initial numerical-screen survivors**, but calibration/verification safeguards failed or remained unresolved, so **ZERO official bets were approved**.

The **five research candidates** (NOT official wagers), in the earlier discussion's order:

| Candidate | FanDuel price |
|---|---:|
| Radtke moneyline | +126 |
| Dober vs Duncan — Over 1.5 rounds | -122 |
| McKinney KO/DEC double chance | +125 |
| Johnson KO/SUB double chance | +116 |
| Hasan vs Gurule — Over 1.5 rounds | +138 |

Longshot *research candidates only* recovered from the prior Stage B response: Radtke KO/TKO **+480**; Dober–Duncan GTD Yes **+285**; Miller–McKinney Round 3 starts Yes **+640**; Chiasson–Mesquita GTD Yes **+200**; Belgaroui KO/TKO **+470**.

No returns, stakes, entries, official bet count >0, or settled wager outcomes should be imputed from this list. Stage B odds do not amend Stage A selections. These were the prices reported in the earlier conversation, NOT current live quotes.

## Unrecovered data; explicit blocker for calling this the original complete lock

- Original full Stage A/Stage B machine-readable lock JSON and SHA-256 / original commit SHA
- Full two-sided method distributions, winner+method joint masses, double-chance probabilities, survival and timing probabilities, round-level distributions, Monte Carlo simulation samples/seeds
- Exact official per-fight SIDE/LEAN/PASS assignment, six individual research warnings, full evidence/tape log
- Stage B all-334 quote-level audit, individual model edges and EV, source price timestamps, individual numerical/calibration gate results
- Original claimed updated code, trained model binaries, test logs, or GitHub commit on November 11 (none independently verified in the checked branches)

## Next steps / governance

- Maintain this file as a provenance-labeled **pre-event recovery snapshot**. It can be compared with newly found originals later, but must not be silently represented as the original lock or its replacement.
- If original files are located, verify their actual SHA, timestamp, model versions, full 13-bout match, and any discrepancies. Preserve both records append-only.
- Preserve PR #1 and all challengers as SHADOW unless user explicitly authorizes promotion or merge.
- Prior conversation reported **no approved Stage B wagers**. Price review may be repeated prospectively only as a separately timestamped review, without modifying the previously displayed Stage A predictions.
