# WSHL_X — global professional MMA opponent-strength Winner v8, dated Elo and exact-method evaluation

**Verified GitHub Actions:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44630737187 (all source, unit, winner, method, forecast hash checks passed).
**Complete forecasts:** workflow artifact `wshlx-global-professional-opponent-elo-winner-v8-research`, report `global_elo_winner_v8_results.json` and `global_professional_opponent_quality_elo_v8_forecasts.csv`.
**Code:** `src/wshlx_ufc/worldwide_opponent_elo_v8.py`, `tools/benchmark_global_opponent_elo_v8.py`, `tests/test_ufc_worldwide_opponent_elo_v8.py`, workflow `.github/workflows/ufc-global-opp-elo-v8-research.yml`.

**Result: important new source/feature class; inconsistent historical winner and exact improvement; NOT promoted, NOT a 70% fighter+method system, no wagering authority.**

## Problem being targeted

Adding a fighter's prior professional MMA 20–0 record without measuring the quality of opponents can produce overconfident projections against proven UFC fighters. Thus we built a truly chronological **all-professional-MMA opponent Elo** (not just UFC Elo) from Fight Canon's exact pinned `db-2026-11-19-1934` SQLite source, SHA256 `8185a2163b5f97071dbc4ec68667cceb43f5e321fadc38c26b5069303af4d949`.

- **371,109 historical professional MMA fights**, **179,959 fighter IDs**, 251 modern dated UFC event dates, **6,032 athlete-date rating snapshots**. Source 3,016/3,036 validated modern UFC matchup identity records, 20 quarantined unverified crosswalks. Same earlier history-source caveat: 2026 consolidated data may be retrospectively backfilled and cannot be represented as 2024-source-timestamped.
- Ratings initialized 1500, fixed K=24; on EACH event date a fighter's rating and opponent quality are frozen **before** any of that same-date's fights update ratings. Bout results/labels on the target date are NEVER features. Only verified professional W/L/draw results count; exclude unclear results, non-pro source records and future events. Unit tests cover same-date repeat fights and duplicate IDs.
- Four extra pre-fight features **for each candidate fighter**: global professional Elo relative to 1500, log prior professional bouts, average past opponent's Elo at the encounter (shrunk to 1500), average previously defeated opponent's pre-fight Elo (shrunk). This augments existing 73-feature UFC+regional model to **77**.
- Compare v4 regularized logistic73 versus v8 logistic77, and v4 small boosted73 versus v8 boosted77, on identical whole 2024–26 yearfolds. **SAME fighter-specific conditional regional method-v5 head** is fitted before each target year and used unchanged in all arms, so differences reflect winning-fighter model only. Exact fighter+method, winner Brier, six-way log loss, SUB class, 2–5 exact selection, paired event-cluster uncertainty tested.
- Additional source data does NOT amount to new untampered prospective events. All 2024–26 labels previously inspected, independent future prospective events still necessary. Coefficients here are prespecified (not post-hoc tuned to the result).

## Matched historical winner and exact outcomes, fixed regional Method v5

| Year | Original v4 logistic73 winners | New world Elo logistic77 winners | Original v4 logistic73 exact | New Elo logistic77 exact |
|---|---:|---:|---:|---:|
| 2024 (511) | 314 (61.4%) | **332 (65.0%)** | 175 (34.2%) | **190 (37.2%)** |
| 2025 (513) | 324 (63.2%) | 325 (63.4%) | 179 (34.9%) | **186 (36.3%)** |
| 2026 retrospective (488) | **304 (62.3%)** | 292 (59.8%) | **153 (31.4%)** | 147 (30.1%) |

2024 logistic77 vs73 improves winners by +18 and exact by +15; within-event bootstrap interval for 2024 winner gain roughly **+1.15 to +5.62 percentage points** and exact gain **+0.60 to +4.92pp**, but 2026 reversal is considerable (winners -12, exact -6). A small 2024 sample and three years already used for model development are not sufficient to promote.

| Year | Original v4 boosted73 winners | New world Elo boosted77 winners | Original boosted73 exact | New Elo boosted77 exact |
|---|---:|---:|---:|---:|
| 2024 (511) | 311 | **317** | 178 | **181** |
| 2025 (513) | **330** | 323 | **196** | 188 |
| 2026 retrospective (488) | 305 | **312** | 158 | **161** |

2026 boosted77 312/488 winners **63.9%**, exact 161/488 **33.0%**; 2025 regression 330→323 winners and 196→188 exact. Both 2026 winner+exact event-cluster bootstrap intervals for the incremental boosted77 model cross zero. The new 2026 boosted winner Brier improved from 0.23139→0.23044, but six-way method logloss modest 1.61523→1.61351, not enough to claim robust predictive superiority.

## Ability to identify five 100%-accurate picks

For boosted77 top five by exact fighter-method probability on eligible 11–14 fight historic full cards:
- 2024: 78/200 exact, **0 of 40** cards with all five exact;
- 2025: 81/195 exact, **0 of 39** cards with all five exact;
- 2026: 75/190 exact, **0 of 38** cards with all five exact.

The global Elo fighter-competition improvement does not solve the perfect 2–5-fight subset problem. There is no guarantee of any future fight's exact result.

## Real performance ceiling and decision

Highest new v8 candidate winner rate observed here is 65.0% in 2024; the highest new v8 candidate exact rate is 37.2% in 2024, although the unchanged v4 boosted control reached 196/513 (38.2%) in 2025. None approaches 70% complete fighter+method accuracy. A hypothetical 70% exact rate needs at least 70% winner accuracy AND nearly perfect method correctness at that level; a more realistic example is **80% correct winners with 87.5% correct method conditional on those winners**, neither demonstrated. The long-term target is aspirational; current historical probabilities cannot justify 100% certainty.

**No candidate promoted, no new wagers.** Earlier original Reference/Historical/Unified, Coherent, independent V3 winner, independent V4 winner and independent V5 method research sidecars from November 21 remain frozen and unmodified. Given escalating retrospective test re-use, the only defensible arbiter now is to register model candidates before future bouts and score matched new fights; stop optimizing until old development years happen to hit the requested percentage. Future source work can look for verified opponent-relative positional grappling, time-vintage fighter metadata and regional MMA scouting, but those improvements must earn promotion on fresh results.
