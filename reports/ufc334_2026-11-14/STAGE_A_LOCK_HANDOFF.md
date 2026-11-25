# WSHL_X — UFC334 November 14 Stage A FROZEN BEFORE FANDUEL PROP PRICING

**Freeze status:** STAGE A frozen, fight-count 13, no sportsbook prices used in models, November 11, 2026.  
**Original lock:** `data/locks/ufc334_2026-11-14/stage_a_final_selection.json` (SHA256 embedded and verified by test).  
**Raw model output:** `data/locks/ufc334_2026-11-14/stage_a_model_raw_three_view.json`.  
**Audit:** `data/locks/ufc334_2026-11-14/stage_a_final_audit.json`.

**Card source:** https://www.ufc.com/event/ufc-334; replacement/cancellation https://www.ufc.com/index.php/news/updates-polymarket-ufc-334-gane-vs-hokit. The user's 12 unique lineup screenshots omitted Stephen Thompson vs Charles Radtke, included from official listing. Dober-Duncan and Harrison-Nunes screenshots were duplicates. Final count = 13, with two five-round titles.

**Odds exposure:** The screenshots showed preliminary moneyline prices. Those prices were not provided as inputs to any predictive model, nor used to flip a pick, assign risk tiers, or select timing. No FanDuel Stage B pricing analysis has yet occurred.

**Model vintages:** Reference v0.27 weights fitted through Sep 12 with fighter features through Nov7. Current challenger winner/method/timing fit through Nov7. Historical winner shadow refit through Nov7; historical method/timing components still fit only through Oct17. Unified ensemble blending weights fit from Oct17 OOF. No champion or challenger promotion, and no observed Nov14 results used.

## Three winner predictions on every fight

| # | Bout | Reference winner | Historical winner | Unified winner | Tier |
|---:|---|---|---|---|---|
| 1 | Evan Elder vs Samuel Sanches | Evan Elder 51.5% | Samuel Sanches 53.7% | Samuel Sanches 52.1% | PASS PASS |
| 2 | Alatengheili vs Juan Diaz | Juan Diaz 82.2% | Juan Diaz 72.9% | Juan Diaz 76.0% | PASS PASS |
| 3 | Macy Chiasson vs Bia Mesquita | Macy Chiasson 56.8% | Bia Mesquita 70.0% | Bia Mesquita 62.5% | PASS PASS |
| 4 | Jared Gordon vs Melquizael Costa | Melquizael Costa 66.7% | Melquizael Costa 77.4% | Melquizael Costa 74.5% | B SIDE |
| 5 | Donte Johnson vs Cesar Almeida | Donte Johnson 85.2% | Donte Johnson 76.5% | Donte Johnson 79.4% | C LEAN |
| 6 | Jim Miller vs Terrance McKinney | Terrance McKinney 74.2% | Terrance McKinney 79.1% | Terrance McKinney 77.7% | B SIDE |
| 7 | Drew Dober vs Chris Duncan | Chris Duncan 64.1% | Chris Duncan 76.9% | Chris Duncan 73.4% | C LEAN |
| 8 | Stephen Thompson vs Charles Radtke | Charles Radtke 63.6% | Charles Radtke 78.5% | Charles Radtke 74.5% | C LEAN |
| 9 | Bilal Hasan vs Luis Gurule | Bilal Hasan 54.1% | Bilal Hasan 65.7% | Bilal Hasan 62.3% | PASS PASS |
| 10 | Uros Medic vs Kevin Holland | Uros Medic 51.9% | Uros Medic 60.2% | Uros Medic 57.7% | PASS PASS |
| 11 | Caio Borralho vs Yousri Belgaroui | Caio Borralho 54.3% | Yousri Belgaroui 53.2% | Yousri Belgaroui 51.0% | PASS PASS |
| 12 | Kayla Harrison vs Amanda Nunes | Kayla Harrison 83.5% | Kayla Harrison 70.5% | Kayla Harrison 75.0% | PASS PASS |
| 13 | Ciryl Gane vs Josh Hokit | Ciryl Gane 72.6% | Josh Hokit 59.8% | Ciryl Gane 50.3% | PASS PASS |

Four matchups with winner disagreements: #1 Elder-Sanches, #3 Chiasson-Mesquita, #11 Borralho-Belgaroui, #13 Gane-Hokit. Preserve EVERY model's original forecast for prospective grading, even in PASS fights.

## Top method of victory from ALL THREE models, conditioned on EACH MODEL'S OWN selected fighter

| # | Reference: own pick method | Historical: own pick method | Unified: own pick method | Method/timing warning |
|---:|---|---|---|---|
| 1 | Evan Elder KO/TKO 44.7% | Samuel Sanches KO/TKO 44.4% | Samuel Sanches KO/TKO 49.9% | **BLOCK >15pp** (20.7pp) |
| 2 | Juan Diaz SUB 53.6% | Juan Diaz SUB 51.6% | Juan Diaz SUB 53.5% | **BLOCK >15pp** (33.6pp) |
| 3 | Macy Chiasson KO/TKO 52.8% | Bia Mesquita SUB 62.1% | Bia Mesquita SUB 63.2% | **BLOCK >15pp** (18.1pp) |
| 4 | Melquizael Costa KO/TKO 51.8% | Melquizael Costa SUB 41.4% | Melquizael Costa KO/TKO 36.9% | **BLOCK >15pp** (16.7pp) |
| 5 | Donte Johnson KO/TKO 65.0% | Donte Johnson KO/TKO 37.1% | Donte Johnson KO/TKO 47.8% | Below 15pp (12.5pp) |
| 6 | Terrance McKinney KO/TKO 50.6% | Terrance McKinney KO/TKO 44.2% | Terrance McKinney KO/TKO 46.7% | Below 15pp (7.3pp) |
| 7 | Chris Duncan KO/TKO 37.8% | Chris Duncan SUB 45.0% | Chris Duncan SUB 39.6% | **BLOCK >15pp** (17.8pp) |
| 8 | Charles Radtke KO/TKO 54.3% | Charles Radtke DEC 39.9% | Charles Radtke KO/TKO 42.2% | Below 15pp (11.8pp) |
| 9 | Bilal Hasan KO/TKO 73.5% | Bilal Hasan KO/TKO 55.6% | Bilal Hasan KO/TKO 62.8% | Below 15pp (5.1pp) |
| 10 | Uros Medic KO/TKO 48.9% | Uros Medic KO/TKO 53.9% | Uros Medic KO/TKO 52.3% | Below 15pp (1.3pp) |
| 11 | Caio Borralho KO/TKO 49.8% | Yousri Belgaroui KO/TKO 51.0% | Yousri Belgaroui KO/TKO 57.8% | **BLOCK >15pp** (16.0pp) |
| 12 | Kayla Harrison KO/TKO 40.0% | Kayla Harrison SUB 44.4% | Kayla Harrison SUB 42.1% | Below 15pp (8.0pp) |
| 13 | Ciryl Gane KO/TKO 72.8% | Josh Hokit KO/TKO 51.7% | Ciryl Gane KO/TKO 54.2% | Below 15pp (4.3pp) |

**Important:** Some models select opposite fighters. Method percentages are conditional on each respective model-selected fighter winning, not the actual unconditional probability of a winning fighter-by-method bet. For bet-price comparison, use the frozen six-way fighter+method joint distributions. Coherence warning flags method-joint finish probability differing by over 15 percentage points from simulated timing finish probability; these market families remain blocked from approval until reconciled.

## EXACTLY one locked timing forecast for every fight

| # | Exactly one frozen timing pick | Current timing P | Unified timing P | Minimum P |
|---:|---|---:|---:|---:|
| 1 | Over 1.5 rounds | 69.0% | 67.3% | 67.3% |
| 2 | Over 1.5 rounds | 76.4% | 75.1% | 75.1% |
| 3 | Over 1.5 rounds | 65.1% | 65.6% | 65.1% |
| 4 | Over 1.5 rounds | 67.3% | 68.7% | 67.3% |
| 5 | Fight goes distance NO | 63.0% | 59.0% | 59.0% |
| 6 | Fight goes distance NO | 61.6% | 62.4% | 61.6% |
| 7 | Over 1.5 rounds | 69.4% | 70.1% | 69.4% |
| 8 | Over 1.5 rounds | 65.6% | 64.4% | 64.4% |
| 9 | Fight goes distance NO | 61.3% | 62.3% | 61.3% |
| 10 | Fight goes distance NO | 74.4% | 71.9% | 71.9% |
| 11 | Over 1.5 rounds | 65.5% | 63.9% | 63.9% |
| 12 | Over 1.5 rounds | 65.7% | 69.2% | 65.7% |
| 13 | Fight goes distance NO | 81.0% | 79.2% | 79.2% |

Timing candidates were predeclared and ranked by the minimum of frozen current+unified timing probabilities (ties reference probability, then deterministic label). Only GTD Yes/No, standard O/U 1.5 and 2.5, and Round3 Starts Yes/No competed. Routine Round2 Starts Yes was excluded, and no available sportsbook line or price influenced the choice. **These forecasts are for grading, not automatically approved wagers.**

## Research governance

- **Stage A:** 13 reference winners, 13 historical winners, 13 unified winners; 13 own-fighter method predictions for EACH model; one selected timing forecast per fight; full six-way fighter-method and timing distribution retained, plus double chances in model artifact.
- **Research tiers:** 8 PASS fights; 5 non-PASS SIDE/LEAN. PASS cannot be silently turned into an official bet by attractive FanDuel prices.
- **Method vs timing coherence:** 6 fights flagged (#1, #2, #3, #4, #7, #11); maintain conservative method and round-family approval blocks.
- **Tape:** Public UFC previews and official identity updates were consulted. There is **no representation that continuous fight footage was watched in this environment**.
- **Price gate:** Stage B only after this lock; use FanDuel screenshots for +200-up Longshot research Top 5, −150 through +190 Best Bets Top 5. Same fight across tiers only if logically compatible, one selection per fight within a tier. Display up to five ranked candidates per tier but never fabricate or force five approved stakes. Research-only 1u hypothetical unit ROI stays separate from approved-bet ledger.
- **Recheck:** Official Nov13 weigh-ins, any fighter substitution or medical withdrawal BEFORE recommending Stage B markets. If card changes, record versioned addendum and DO NOT silently rewrite the original Stage A model predictions.
- **Grading:** Post Nov14, independently grade exact method and sides (including each challenger's own fighter), one timing selection each, both Top5 longshot/best hypothetical units and official approval units. NO hindsight selection.

### Exact KO / SUB / DEC conditional probabilities by model's OWN chosen winner

#### 1. Evan Elder vs Samuel Sanches

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Evan Elder | 44.7% | 21.3% | 34.0% |
| Historical: Samuel Sanches | 44.4% | 27.5% | 28.1% |
| Unified: Samuel Sanches | 49.9% | 22.6% | 27.5% |

#### 2. Alatengheili vs Juan Diaz

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Juan Diaz | 23.4% | 53.6% | 22.9% |
| Historical: Juan Diaz | 10.6% | 51.6% | 37.8% |
| Unified: Juan Diaz | 14.6% | 53.5% | 32.0% |

#### 3. Macy Chiasson vs Bia Mesquita

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Macy Chiasson | 52.8% | 9.6% | 37.6% |
| Historical: Bia Mesquita | 14.0% | 62.1% | 23.9% |
| Unified: Bia Mesquita | 16.5% | 63.2% | 20.4% |

#### 4. Jared Gordon vs Melquizael Costa

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Melquizael Costa | 51.8% | 22.0% | 26.1% |
| Historical: Melquizael Costa | 28.6% | 41.4% | 30.0% |
| Unified: Melquizael Costa | 36.9% | 33.7% | 29.4% |

#### 5. Donte Johnson vs Cesar Almeida

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Donte Johnson | 65.0% | 12.3% | 22.7% |
| Historical: Donte Johnson | 37.1% | 30.6% | 32.3% |
| Unified: Donte Johnson | 47.8% | 22.7% | 29.6% |

#### 6. Jim Miller vs Terrance McKinney

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Terrance McKinney | 50.6% | 15.0% | 34.5% |
| Historical: Terrance McKinney | 44.2% | 22.7% | 33.1% |
| Unified: Terrance McKinney | 46.7% | 19.5% | 33.7% |

#### 7. Drew Dober vs Chris Duncan

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Chris Duncan | 37.8% | 29.6% | 32.5% |
| Historical: Chris Duncan | 16.6% | 45.0% | 38.4% |
| Unified: Chris Duncan | 23.2% | 39.6% | 37.2% |

#### 8. Stephen Thompson vs Charles Radtke

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Charles Radtke | 54.3% | 10.4% | 35.4% |
| Historical: Charles Radtke | 34.8% | 25.3% | 39.9% |
| Unified: Charles Radtke | 42.2% | 18.6% | 39.2% |

#### 9. Bilal Hasan vs Luis Gurule

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Bilal Hasan | 73.5% | 10.7% | 15.9% |
| Historical: Bilal Hasan | 55.6% | 16.2% | 28.2% |
| Unified: Bilal Hasan | 62.8% | 14.1% | 23.1% |

#### 10. Uros Medic vs Kevin Holland

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Uros Medic | 48.9% | 5.6% | 45.6% |
| Historical: Uros Medic | 53.9% | 10.1% | 36.0% |
| Unified: Uros Medic | 52.3% | 8.1% | 39.6% |

#### 11. Caio Borralho vs Yousri Belgaroui

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Caio Borralho | 49.8% | 18.8% | 31.4% |
| Historical: Yousri Belgaroui | 51.0% | 9.7% | 39.3% |
| Unified: Yousri Belgaroui | 57.8% | 6.0% | 36.2% |

#### 12. Kayla Harrison vs Amanda Nunes

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Kayla Harrison | 40.0% | 36.4% | 23.7% |
| Historical: Kayla Harrison | 21.0% | 44.4% | 34.6% |
| Unified: Kayla Harrison | 27.3% | 42.1% | 30.6% |

#### 13. Ciryl Gane vs Josh Hokit

| Predictor (conditional on named fighter winning) | KO/TKO | Submission | Decision |
|---|---:|---:|---:|
| Reference: Ciryl Gane | 72.8% | 12.7% | 14.5% |
| Historical: Josh Hokit | 51.7% | 19.2% | 29.2% |
| Unified: Ciryl Gane | 54.2% | 22.4% | 23.4% |


