# UFC 334 — WSHL_X official Stage A and research-only Stage B post-event grade

Date: November 14, 2026. Verified outcomes: November 15. Original picks, pre-event prices, Stage A models, and Stage B gates are unchanged.

## Frozen winner + method scores

| Model | Winner W-L-D | Winner hit rate (12 decisive) | Exact fighter+method |
|---|---|---:|---:|
| reference | 8-4-1 | 66.7% | 1/12 (8.3%) |
| historical | 6-6-1 | 50.0% | 3/12 (25.0%) |
| unified | 7-5-1 | 58.3% | 3/12 (25.0%) |
| consensus | 7-5-1 | 58.3% | 3/12 (25.0%) |

D = majority draw, excluded from binary winner and exact method accuracy. Method means selected fighter AND finish, not finish class alone. Unified and consensus are related to Reference/Historical, not statistically independent models.

## Every fight

| # | Actual | Reference side/method | Historical | Unified | Exact R/H/U | Stage A timing |
|---:|---|---|---|---|---|---|
| 1 | Evan Elder DEC R3 | Elder KO (W) | Sanches KO (L) | Sanches KO (L) | L/L/L | OVER_1.5 (W) |
| 2 | Juan Diaz DEC R3 | Diaz SUB (W) | Diaz SUB (W) | Diaz SUB (W) | L/L/L | OVER_1.5 (W) |
| 3 | Bia Mesquita SUB R1 | Chiasson KO (L) | Mesquita SUB (W) | Mesquita SUB (W) | L/W/W | OVER_1.5 (L) |
| 4 | Melquizael Costa DEC R3 | Costa KO (W) | Costa SUB (W) | Costa KO (W) | L/L/L | OVER_1.5 (W) |
| 5 | Cesar Almeida KO R1 | Johnson KO (L) | Johnson KO (L) | Johnson KO (L) | L/L/L | GTD_NO (W) |
| 6 | Terrance McKinney KO R1 | McKinney KO (W) | McKinney KO (W) | McKinney KO (W) | W/W/W | GTD_NO (W) |
| 7 | Chris Duncan DEC R3 | Duncan KO (W) | Duncan SUB (W) | Duncan SUB (W) | L/L/L | OVER_1.5 (W) |
| 8 | Stephen Thompson KO R3 | Radtke KO (L) | Radtke DEC (L) | Radtke KO (L) | L/L/L | OVER_1.5 (W) |
| 9 | Luis Gurule DEC R3 | Hasan KO (L) | Hasan KO (L) | Hasan KO (L) | L/L/L | GTD_NO (L) |
| 10 | DRAW DRAW R3 | Medic KO (D) | Medic KO (D) | Medic KO (D) | D/D/D | GTD_NO (L) |
| 11 | Caio Borralho DEC R3 | Borralho KO (W) | Belgaroui KO (L) | Belgaroui KO (L) | L/L/L | OVER_1.5 (W) |
| 12 | Kayla Harrison SUB R4 | Harrison KO (W) | Harrison SUB (W) | Harrison SUB (W) | L/W/W | OVER_1.5 (W) |
| 13 | Ciryl Gane DEC R5 | Gane KO (W) | Hokit KO (L) | Gane KO (W) | L/L/L | GTD_NO (L) |

## Method failure

Reference top method across 13 bouts: 12 KO, 1 SUB, 0 DEC. Actual: 3 KO, 2 SUB, 7 DEC, 1 draw. Reference method hit just 1/12 exact (8.3%).
Expected early finishes from archived Reference timing: 7.57 of 13, compared with 5 actual.
Reference winner Brier/log loss 0.438256/0.638134; Historical 0.493312/0.689064; Unified 0.466531/0.662384. Lower is better.
Frozen Historical/Unified joint probabilities can differ substantially from their standalone winner forecasts: max discrepancy Historical 17.569pp, Unified 10.228pp. Do not treat these sixway method probabilities as independently validated exact betting probabilities.

## Fight diagnostics

1. Elder beat Sanches 30-26 x3. Reference held onto the UFC-experienced fighter; both shadows incorrectly preferred the debuting Sanches. All three favored KO method, while Elder won DEC.
2. Diaz beat Alatengheili UD. All three picked the winner, all three missed SUB vs DEC. Grappling skill does not guarantee a submission.
3. Mesquita submitted Chiasson by RNC in R1 3:23. Historical and Unified got exact method; Reference missed winner. The early finish defeated Over 1.5.
4. Costa beat Gordon UD. All models had Costa as winner, but method KO/SUB predictions failed. Grappling/time management and durability matter.
5. Almeida TKO'd Johnson in R1. Johnson was 85.2% Reference / 76.5% Historical / 79.4% Unified; strong false confidence against a veteran striker.
6. McKinney KO'd Miller in R1. All three got exact winner and method plus GTD NO timing. He missed weight Friday, AFTER Nov11 original Stage A freeze.
7. Duncan beat Dober UD. All three models got fighter, none the method. KO/SUB predictions consistently ignored the DEC route.
8. Thompson stopped Radtke via wheel-kick TKO in R3 at 2:54. All three winner views failed; Radtke ML and KO research plays also failed. Get-ups/long-range defensive striking require better emphasis.
9. Gurule beat Hasan by SD. All three winner models failed, as did GTD NO. Wrestling control, sustained pace, grappling defense and limited UFC sample are key diagnostic hypotheses.
10. Medić–Holland was a majority draw after a point deduction. Binary winner/method graded D/unscored, not a Medić loss. GTD NO timing lost.
11. Borralho beat Belgaroui UD. Reference winner correct, both shadows wrong. Tactical wrestling/quality-of-opponents weak spots; KO finish forecasts missed.
12. Harrison submitted Nunes R4. Winner all three correct, Historical and Unified exact SUB correct; Reference KO incorrect.
13. Gane beat Hokit UD over five rounds. Reference/Unified winner right, Historical wrong. Original GTD NO at 81.0% was a major duration mistake.

## Timing

| Frozen timing view | W | L |
|---|---:|---:|
| Stage A original | 9 | 4 |
| 2-of-3 consensus research | 8 | 5 |

Original Over 1.5: 7-1. Original GTD NO: 2-3. Consensus altered Johnson-Almeida timing from successful GTD NO to unsuccessful Over 1.5; original lock remains separate.

## Stage B — frozen FanDuel quote research cards

334 archived price quotes (310 modeled, 24 draws unmodeled). **0 official wagers, 0 official stakes, no official ROI.** This is a separate 1-unit hypothetical settlement of two 5-pick lists, using original November 11 FanDuel screenshots.

### top 5 best bets: 3-2, 1.4497u, 29.0% virtual ROI

| Original pick | FanDuel | W/L | Virtual 1u P/L |
|---|---:|---|---:|
| 8: Charles Radtke ML | +126 | L | -1.0000u |
| 7: OVER 1.5 rounds | -122 | W | 0.8197u |
| 6: Terrance McKinney KO_OR_DEC | +125 | W | 1.2500u |
| 5: Donte Johnson KO_OR_SUB | +116 | L | -1.0000u |
| 9: OVER 1.5 rounds | +138 | W | 1.3800u |

### top 5 longshots: 1-4, -1.1500u, -23.0% virtual ROI

| Original pick | FanDuel | W/L | Virtual 1u P/L |
|---|---:|---|---:|
| 8: Charles Radtke by KO_TKO | +480 | L | -1.0000u |
| 7: Fight goes distance YES | +285 | W | 2.8500u |
| 6: Round 3 starts YES | +640 | L | -1.0000u |
| 3: Fight goes distance YES | +200 | L | -1.0000u |
| 11: Yousri Belgaroui by KO_TKO | +470 | L | -1.0000u |

Combined 4-6, 0.2997u, 3.0% hypothetical ROI. Do not equate research ROI with profitability or actual bets. A single +285 Duncan GTD YES success drove this total.

## Governance and data quality

- Original Stage A and Stage B files preserved byte-for-byte. No winner/method/timing prediction retroactively rewritten.
- McKinney and Juan Diaz missed weight Nov13; do not retroactively insert those features in Nov11 lock. Make any future fight-day update a distinct pre-registered pre-fight run.
- Current grading supports audited results, but not complete official UFCStats per-round/fighter ingestion. Do not claim those statistics have been imported.
- Prior UFC Vegas 124 already showed Reference KO top-method excess. Conduct walk-forward calibration study across multiple cards before adjusting champion method probabilities. Separate winner from conditional method and timing; assess decision survival and round hazards.
- Historical and Unified six-class method/winner mismatches need explicit corrected shadow outputs and tests, never overwriting originals.
- The Stage B price gate correctly kept 0 approved wagers despite questionable raw market edges; quote freshness and validated conservative calibration still required.

## SHA-256 provenance
- Original Stage A: fda4e7d5636174eb14114a1cabd55c804aae1c3e7de41bb0b12791b46920740a
- Original raw Stage A models: 13aeb532c5fddd5ec3cdc003ac7500a231addc45e34b45b7aebc38c5c241270d
- Original Stage B price audit: de50106f116d1931413c51518cfeafb0e4c8f2a51f0e54ff83edb682aef0d4d2
- Original Stage B research watchlist: 0bd97214a1da9877a9000001593fd4dba4334509b5809f8453e3dae3f707f0be

## Verified external results
- https://www.ufc.com/index.php/news/polymarket-ufc-334-gane-vs-hokit-results
- https://www.cbssports.com/ufc/news/ufc-334-fight-card-ciryl-gane-josh-hokit-results-winners/
- https://www.sherdog.com/news/news/UFC-334-Gane-vs-Hokit-playbyplay-results-round-scoring-203625
- https://sports.yahoo.com/mma/live/ufc-334-live-results-gane-vs-hokit-updates-round-by-round-scoring-for-tonights-title-doubleheader-191500505.html
- https://www.mmafighting.com/ufc/521306/ufc-334-video-stephen-wonderboy-thompson-retires-with-spinning-wheel-kick-knockout-over-charles-radtke
- https://www.ufc.com/news/official-weigh-results-polymarket-ufc-334-gane-vs-hokit
