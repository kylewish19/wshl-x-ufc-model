# WSHL_X UFC Complete Card Record Audit — consolidated through Paris

**Original audit date:** 2026-08-23  
**Recovered/consolidated:** 2026-09-18  
**Rule:** append-only. The August 23 conclusions are preserved; Shanghai and Paris are deltas. Historical locks are never rewritten.

## Original August 23 audit boundary

The original audit identified 11 UFC events and 139 completed bouts, but only 37 fights across the August 8, August 15 and August 22 cards had exact final current-process locks suitable for the clean headline record.

Original clean 37-fight totals:

| Measure | Record |
|---|---:|
| Winner | 21-16 (56.8%) |
| Displayed method | 13-24 (35.1%) |
| Winner + displayed method | 7-30 (18.9%) |
| Raw v0.4 method with actual winner supplied | 15-22 (40.5%) |
| Raw v0.4 winner + method | 8-29 (21.6%) |
| Official promoted method bets | 0-1 |

Older April-through-August-1 cards remain historical context only because their evidence mixes old process versions, partial pick maps, aggregate-only grades, and the unresolved UFC 329 version conflict.

## Original clean cards

| Date | Event | Fights | Winner | Displayed method | Winner + displayed method |
|---|---|---:|---:|---:|---:|
| 2026-08-08 | Gamrot vs Salkilld | 12 | 9-3 | 4-8 | 3-9 |
| 2026-08-15 | UFC 330 Makhachev vs Machado Garry | 12 | 6-6 | 3-9 | 1-11 |
| 2026-08-22 | Hernandez vs Rodrigues | 13 | 6-7 | 6-7 | 3-10 |
| **Subtotal** |  | **37** | **21-16** | **13-24** | **7-30** |

## Append-only delta — UFC Shanghai — 2026-08-29

- Finalized fights: **13**
- Winner: **9-4 (69.2%)**
- Displayed method: **6-7 (46.2%)**
- Winner + displayed method: **5-8 (38.5%)**
- Raw v0.4 method with actual winner supplied: **6-7**
- Raw v0.4 winner + method: **5-8**
- Official promoted method wagers: **0**
- v0.18 totals: **23-18**
- Goes distance: **5-8**
- Round starts: **14-14**
- Models retuned/promoted by the grade itself: **No**

Clean cumulative after Shanghai:

| Measure | Record |
|---|---:|
| Winner | 30-20 |
| Displayed method | 19-31 |
| Winner + displayed method | 12-38 |
| Raw actual-winner method | 21-29 |
| Raw winner + method | 13-37 |
| Official method wagers | 0-1 |

## Append-only delta — UFC Paris Hooker vs Parnasse — 2026-09-05

**Original Stage A lock:** `90d03447e12f7e4c41bb9856f465e51cc91ed14ece794960ac0604fe80fc702b`

- Finalized fights: **14**
- Winner: **6-8 (42.9%)**
- Displayed method type: **9-5 (64.3%)**
- Winner + displayed method: **3-11 (21.4%)**
- Raw v0.4 method with actual winner supplied: **8-6**
- Raw v0.4 winner + method: **3-11**
- Explicit finishing round, ignoring winner/method: **1-4**
- Winner + method + finishing round: **0-5**
- Round totals: **33-11**
- Goes distance: **8-6**
- Round starts: **20-10**
- Official wager ledger: **0 wagers, 0 units risked**
- Models promoted by this result: **No**

Paris timing detail:

| Market group | Grade |
|---|---:|
| O/U 0.5 | 13-1 |
| O/U 1.5 | 9-5 |
| O/U 2.5 | 9-5 |
| O/U 3.5 | 1-0 |
| O/U 4.5 | 1-0 |
| Round 2 starts | 10-4 |
| Round 3 starts | 8-6 |
| Round 4 starts | 1-0 |
| Round 5 starts | 1-0 |

These timing rows are correlated observations from 14 fights. They are not 88 independent wagers and are not a profitability claim.

Paris fight ledger:

| Fight | Locked winner | Actual winner | Displayed | Actual | Side | Method | Joint |
|---|---|---|---|---|---:|---:|---:|
| Delphine Benouaich vs Sofia Montenegro | Sofia Montenegro | Delphine Benouaich | DEC | SUB | L | L | L |
| Matthieu Duclos vs Luis Felipe Dias | Luis Felipe Dias | Matthieu Duclos | KO | KO | L | W | L |
| Nora Cornolle vs Klaudia Sygula | Klaudia Sygula | Nora Cornolle | DEC | DEC | L | W | L |
| Michael Aljarouj vs Fabia Sintes | Michael Aljarouj | Fabia Sintes | DEC | DEC | L | W | L |
| Nathaniel Wood vs Pavel Andrusca | Nathaniel Wood | Pavel Andrusca | DEC | DEC | L | W | L |
| Oumar Sy vs Modestas Bukauskas | Oumar Sy | Modestas Bukauskas | KO | KO | L | W | L |
| Mario Pinto vs Ryan Spann | Mario Pinto | Mario Pinto | KO | KO | W | W | W |
| Morgan Charriere vs Felipe Lima | Felipe Lima | Felipe Lima | DEC | DEC | W | W | W |
| Losene Keita vs Muhammad Naimov | Losene Keita | Losene Keita | DEC | KO | W | L | L |
| Kurtis Campbell vs Trevor Peek | Kurtis Campbell | Kurtis Campbell | DEC | SUB | W | L | L |
| Daniil Donchenko vs Punahele Soriano | Daniil Donchenko | Daniil Donchenko | KO | DEC | W | L | L |
| Michael Page vs Nursulton Ruziboev | Michael Page | Michael Page | DEC | DEC | W | W | W |
| Fares Ziam vs Axel Sola | Fares Ziam | Axel Sola | DEC | KO | L | L | L |
| Dan Hooker vs Salahdine Parnasse | Dan Hooker | Salahdine Parnasse | KO | KO | L | W | L |

## Certified clean record through Paris

| Event date | Fights | Winner | Displayed method | Winner + method |
|---|---:|---:|---:|---:|
| 2026-08-08 | 12 | 9-3 | 4-8 | 3-9 |
| 2026-08-15 | 12 | 6-6 | 3-9 | 1-11 |
| 2026-08-22 | 13 | 6-7 | 6-7 | 3-10 |
| 2026-08-29 | 13 | 9-4 | 6-7 | 5-8 |
| 2026-09-05 | 14 | 6-8 | 9-5 | 3-11 |
| **Total** | **64** | **36-28 (56.3%)** | **28-36 (43.8%)** | **15-49 (23.4%)** |

Additional clean totals:
- Raw actual-winner method: **29-35**
- Raw winner + method: **16-48**
- Historical official method wagers: **0-1**
- Displayed class counts: **37 DEC / 25 KO / 2 SUB**
- Actual class counts: **21 DEC / 31 KO / 12 SUB**

The class-count gap supports investigating submission/finish localization and access features. It does **not** authorize manually increasing finish predictions.

## Canonical machine-readable ledger

The repository file `data/results/clean_ufc_64_2026-09-05.csv` is the machine-readable clean ledger. Automated tests require:
- exactly 64 fights;
- 36 winner hits;
- 28 method-type hits;
- 15 exact winner+method hits;
- predicted 37/25/2 DEC/KO/SUB;
- actual 21/31/12 DEC/KO/SUB.

## Update contract

1. Add exactly one final fight-day lock per completed fight.
2. Keep winner, method-only, winner+method, timing, double chance and wager grades separate.
3. Never count shadow-model duplicates as extra picks or wagers.
4. Never backfill a missing old prediction from a known result.
5. Append grades after results; never rewrite the original prediction.
6. Record code/data changes separately from result labels.
7. A post-card lesson does not become "machine learned" until executable code/features are fitted and saved.
