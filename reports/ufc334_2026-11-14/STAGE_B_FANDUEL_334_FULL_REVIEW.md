# UFC 334: Gane vs Hokit — FanDuel Stage B full pre-fight price audit

**Date of screenshots:** November 11, 2026 (precise UTC capture timestamp unknown). **Fight date:** November 14, 2026. **Sportsbook:** FanDuel exclusively (user screenshots, not real-time API).  
**Status:** Completed all-price research audit, **five research candidates in each category; zero approved wagers**. Do not interpret the raw model probabilities as fully calibrated betting probabilities.  
**Original freeze and provenance:** Stage A 13-fight lock [here](https://github.com/kylewish19/wshl-x-ufc-model/blob/feature/historical-conditional-rates/data/locks/ufc334_2026-11-14/stage_a_final_selection.json), price audit [here](https://github.com/kylewish19/wshl-x-ufc-model/blob/feature/historical-conditional-rates/data/locks/ufc334_2026-11-14/stage_b_all_334_fanduel_prices_audit.json), 5+5 research watchlist [here](https://github.com/kylewish19/wshl-x-ufc-model/blob/feature/historical-conditional-rates/data/locks/ufc334_2026-11-14/stage_b_top5_ranked_research_review_compatible_cross_tier.json), 1u hypothetical pending ledger [here](https://github.com/kylewish19/wshl-x-ufc-model/blob/feature/historical-conditional-rates/data/locks/ufc334_2026-11-14/stage_b_top5_research_units_pending.json).

## Sources and completeness

- **13 unique bouts accounted for. 334 FanDuel prices transcribed, 310 modeled, 24 unmodeled duplicate +5000 draw quotes.**
- **Alatengheili vs Juan Diaz (#2):** only two ML quotes (+265, −370) shown; zero method/timing/double-chance markets were invented.
- **12 other fights:** 10 fights with 27 prices per set, both five-round championship fights with 31 prices per set.
- Both title fights' **exact-round betting** accordion remained collapsed. No nonexistent exact-round prices were filled.
- O/U thresholds vary by fight. Miller–McKinney is **0.5**, Harrison–Nunes is **3.5**, and Gane–Hokit is **2.5**; these exact original FanDuel lines, not guessed alternative totals, were audited.
- Original Stage A winner, method, primary timing and 10,000 simulation forecasts remain unchanged. Earlier fight lineup thumbnails did display general ML prices, but no market odds were input to predictive code.
- **Pre-Nov13 weigh-ins:** No official weigh-in results were available at the time of this Nov11 snapshot. Independently check current fighter availability and live FanDuel odds before any real wager.

## Moneyline / three-model comparison — all 13 fights

| # | Fight | Screenshot ML (A / B) | Reference pick | Historical pick | Unified pick | Stage A |
|---:|---|---|---|---|---|---|
| 1 | Evan Elder vs Samuel Sanches | +102 / -130 | Evan Elder 51.5% | Samuel Sanches 53.7% | Samuel Sanches 52.1% | PASS |
| 2 | Alatengheili vs Juan Diaz | +265 / -370 | Juan Diaz 82.2% | Juan Diaz 72.9% | Juan Diaz 76.0% | PASS |
| 3 | Macy Chiasson vs Bia Mesquita | +220 / -295 | Macy Chiasson 56.8% | Bia Mesquita 70.0% | Bia Mesquita 62.5% | PASS |
| 4 | Jared Gordon vs Melquizael Costa | +285 / -400 | Melquizael Costa 66.7% | Melquizael Costa 77.4% | Melquizael Costa 74.5% | SIDE |
| 5 | Donte Johnson vs Cesar Almeida | -174 / +136 | Donte Johnson 85.2% | Donte Johnson 76.5% | Donte Johnson 79.4% | LEAN |
| 6 | Jim Miller vs Terrance McKinney | +158 / -205 | Terrance McKinney 74.2% | Terrance McKinney 79.1% | Terrance McKinney 77.7% | SIDE |
| 7 | Drew Dober vs Chris Duncan | +134 / -172 | Chris Duncan 64.1% | Chris Duncan 76.9% | Chris Duncan 73.4% | LEAN |
| 8 | Stephen Thompson vs Charles Radtke | -162 / +126 | Charles Radtke 63.6% | Charles Radtke 78.5% | Charles Radtke 74.5% | LEAN |
| 9 | Bilal Hasan vs Luis Gurule | -1200 / +630 | Bilal Hasan 54.1% | Bilal Hasan 65.7% | Bilal Hasan 62.3% | PASS |
| 10 | Uros Medic vs Kevin Holland | -156 / +122 | Uros Medic 51.9% | Uros Medic 60.2% | Uros Medic 57.7% | PASS |
| 11 | Caio Borralho vs Yousri Belgaroui | -162 / +126 | Caio Borralho 54.3% | Yousri Belgaroui 53.2% | Yousri Belgaroui 51.0% | PASS |
| 12 | Kayla Harrison vs Amanda Nunes | -196 / +152 | Kayla Harrison 83.5% | Kayla Harrison 70.5% | Kayla Harrison 75.0% | PASS |
| 13 | Ciryl Gane vs Josh Hokit | -188 / +144 | Ciryl Gane 72.6% | Josh Hokit 59.8% | Ciryl Gane 50.3% | PASS |


**Four official winner-model disagreement matchups**: Elder–Sanches; Chiasson–Mesquita; Borralho–Belgaroui; Gane–Hokit. Several model probabilities strongly diverge from FanDuel, especially Radtke vs Thompson and Hasan vs Gurule. Those discrepancies can reflect model errors or feature gaps rather than pure value. Do not assume the sportsbook is wrong.

## Top 5 Best Bets price category (−150 through +190 inclusive)

These are the most relevant **ranked RESEARCH** picks, **NOT five approved wagers**. A 1u research shadow will be graded only after the card. Method and timing family restrictions remain enforceable.

| Rank | Market | FanDuel | Reference raw P | Unified raw P | Book breakeven | Why still PASS |
|---:|---|---:|---:|---:|---:|---|
| 1 | Stephen Thompson vs Charles Radtke: Charles Radtke ML | +126 | 63.6% | 74.5% | 44.2% | Independent price and probability calibration not yet verified |
| 2 | Drew Dober vs Chris Duncan: OVER 1.5 rounds | -122 | 69.4% | 70.1% | 55.0% | method timing finish marginals disagree over 15pp |
| 3 | Jim Miller vs Terrance McKinney: Terrance McKinney KO_OR_DEC | +125 | 63.1% | 54.7% | 44.4% | fighter method double chance or fight end model not independently validated |
| 4 | Donte Johnson vs Cesar Almeida: Donte Johnson KO_OR_SUB | +116 | 65.9% | 55.9% | 46.3% | fighter method double chance or fight end model not independently validated |
| 5 | Bilal Hasan vs Luis Gurule: OVER 1.5 rounds | +138 | 58.5% | 57.8% | 42.0% | frozen stage a fight PASS research only; sparse less than two prior UFC fights for one side |


## Top 5 Longshots price category (+200 and higher)

**Research only; do not auto-bet.** Some apparent huge EV signals are artifacts of sparse, inconsistent, or uncalibrated method/timing probabilities. Ranks reflect considered research value, NOT maximum raw EV.

| Rank | Market | FanDuel | Reference raw P | Unified raw P | Book breakeven | Why still PASS |
|---:|---|---:|---:|---:|---:|---|
| 1 | Stephen Thompson vs Charles Radtke: Charles Radtke by KO_TKO | +480 | 34.5% | 28.0% | 17.2% | fighter method double chance or fight end model not independently validated |
| 2 | Drew Dober vs Chris Duncan: Fight goes distance YES | +285 | 51.9% | 52.5% | 26.0% | method timing finish marginals disagree over 15pp |
| 3 | Jim Miller vs Terrance McKinney: Round 3 starts YES | +640 | 50.7% | 50.1% | 13.5% | Independent price and probability calibration not yet verified |
| 4 | Macy Chiasson vs Bia Mesquita: Fight goes distance YES | +200 | 46.0% | 46.8% | 33.3% | frozen stage a fight PASS research only; method timing finish marginals disagree over 15pp |
| 5 | Caio Borralho vs Yousri Belgaroui: Yousri Belgaroui by KO_TKO | +470 | 30.9% | 27.4% | 17.5% | frozen stage a fight PASS research only; fighter method double chance or fight end model not independently validated; method timing finish marginals disagree over 15pp |


### Same-fight double exposure: independently validated logical compatibility

1. **Radtke ML +126** (Best) and **Radtke KO/TKO +480** (Longshot) can both win if Radtke wins by KO/TKO. Strongly correlated.
2. **Dober–Duncan Over 1.5 −122** (Best) and **GTD YES +285** (Longshot) can win together if the fight reaches a decision. Both can fail if the fight ends early.
3. **McKinney KO/TKO OR Decision +125** (Best) and **Round 3 Starts YES +640** (Longshot) can both win when McKinney wins by decision or by KO after Round 3 has begun. Compatible, but the simulated timing +640 line is **NOT** the original Stage A primary timing pick.

The pair validator checks typed contracts against supported 3-round MMA results; it does not treat the two outcomes as probabilistically independent.

## Why not officially approve apparent huge price edges?

The complete raw numeric screening found **exactly three** potentially qualifying markets under simple price/edge/source/posture rules, *before the final validated-calibration and freshness gate*:

| Candidate | Screenshot price | Reference raw | Unified raw | Critical concern |
|---|---:|---:|---:|---|
| Charles Radtke ML | +126 | 63.6% | 74.5% | Opposes book favorite; no independently validated conservative error range / fresh price verification |
| Miller–McKinney GTD YES | +900 | 38.4% | 37.6% | Timing model known to overestimate unlikely long survival; **not** original primary timing pick |
| Miller–McKinney Round 3 Starts YES | +640 | 50.7% | 50.1% | Extreme disagreement with book; model timing-calibration uncertainty |

**Zero official bets approved** because the minimum of two model probabilities is not a statistically validated lower confidence bound; source/line freshness, weight/day-of validity and market-family calibration are not cleared. Method, double chance and fight end require extra family coherence; serious method-vs-timing discrepancies persist in #1, #2, #3, #4, #7, #11.

**Do not fill five actual wagers per tier merely to make the card look complete.** Five *research* slots per tier are filled, but the official betting record is **0 bets, 0 units staked, ROI not applicable**, not “0–10” and not −10u.

## Frozen timing versus later price candidate distinction

The Stage A lock contains **exactly one primary timing prediction per each of the 13 bouts**. Grade these 13 later independent of a separately ranked Stage B timing market. This matters for #6 Miller vs McKinney: the odds-blind primary timing forecast was **GTD NO**, while an alternate priced research longshot is **Round 3 Starts YES +640**. Both can technically happen if the bout lasts into R3 and ends by stoppage, but neither can be retroactively substituted for the other on the Stage A grading ledger.

## Forward grading records

- The Top 5 Longshots and Top 5 Best Bets will each be tracked individually at **1.00 hypothetical unit per selection**, original FanDuel price, result, net virtual units and ROI, WITHOUT implying any wager was placed.
- Current **PRE-EVENT** research record: Best 0–0 (5 PENDING), Longshots 0–0 (5 PENDING); **0.00u settled**, ROI N/A, because NO outcomes exist yet.
- The original source cards are hashed, and any verified post-card settlements must reference those hashes. Do not replace a losing candidate or change a pre-event quote afterward.
- Additionally, all 13 Unified shadow fighter+top conditional-method selections are prospectively retained in Stage A for grading, including *one unpriced fight (#2)* so the all-fights exact-method hit rate is not biased by available prop quotes. If a separate price study is used, it may cover only the 12 genuinely quoted lines and must NOT invent a #2 price.
- Follow-up after Saturday: verify 13 actual winners, methods, rounds and settlements; grade the three winner models and 13 odds-blind timing picks; independently settle both research Top5 cards; add official UFCStats and new training rows only after verified results, backtest modifications prospectively.

**Final source:** [Full 334 line audit](https://github.com/kylewish19/wshl-x-ufc-model/blob/feature/historical-conditional-rates/data/locks/ufc334_2026-11-14/stage_b_all_334_fanduel_prices_audit.json), [frozen research ranks](https://github.com/kylewish19/wshl-x-ufc-model/blob/feature/historical-conditional-rates/data/locks/ufc334_2026-11-14/stage_b_top5_ranked_research_review_compatible_cross_tier.json). No official Top5 bet was published as confirmed playable on this screenshot-only, pre-weigh-in snapshot.
