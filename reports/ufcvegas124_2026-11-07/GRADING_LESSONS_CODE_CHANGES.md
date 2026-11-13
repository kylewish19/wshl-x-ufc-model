# UFC Vegas 124 (2026-11-07) — Complete WSHL_X model grading, pricing, lessons and code changes

**Event:** Cortes Acosta vs Walker, 14 fights. **Graded:** November 8, 2026 (after all bouts). **Branch:** `feature/historical-conditional-rates`, NOT merged to main.  
**Sources:** Official UFC results https://www.ufc.com/event/ufc-fight-night-november-07-2026 ; UFC editorial https://jp.ufc.com/news/ufc-fight-night-cortes-acosta-vs-walker-results ; Fightful full-card outcomes https://www.fightful.com/mma/ufc-fight-night-cortes-acosta-vs-walker-results-11-7/ ; independent MMA Fighting https://www.mmafighting.com/fight-results/ufc .

## Final frozen model scorecard

| Model / forecast | Correct | Misses | Hit rate |
|---|---:|---:|---:|
| **Reference winner** (odds-blind champion v0.27) | **9** | 5 | **64.3%** |
| **Historical winner** (research shadow) | **11** | 3 | **78.6%** |
| **Unified winner** (research shadow) | **11** | 3 | **78.6%** |
| **Reference exact winner + method** | **5** | 9 | **35.7%** |
| **Historical exact own winner + method** | **7** | 7 | **50.0%** |
| **Unified exact own winner + method** | **8** | 6 | **57.1%** |
| **Primary timing forecast** (separate pre-fight research) | **10** | 4 | **71.4%** |

**Method conditional on a correctly selected winning fighter:** Reference **5/9 (55.6%)**, historical **7/11 (63.6%)**, unified **8/11 (72.7%)**. **Method class against actual outcome while ignoring wrong fighter** is a different, less meaningful diagnostic: reference 9/14, historical 10/14, unified 10/14. Do not claim those are exact winner+method wins.

### Correct winner and winner+method, every bout

| # | Actual | Reference winner | Historical winner | Unified winner | Reference exact | Hist exact | Unified exact |
|---:|---|---|---|---|:---:|:---:|:---:|
| 1 | Souza KO R1 4:16 | Parsons ✗ | Parsons ✗ | Parsons ✗ | ✗ | ✗ | ✗ |
| 2 | Ko DEC R3 5:00 | Ko ✓ | Ko ✓ | Ko ✓ | ✓ | ✓ | ✓ |
| 3 | Petroski KO R2 4:39 | Kondratavičius ✗ | Kondratavičius ✗ | Kondratavičius ✗ | ✗ | ✗ | ✗ |
| 4 | Bashi SUB R1 1:07 | Bashi ✓ | Bashi ✓ | Bashi ✓ | ✗ | ✓ | ✓ |
| 5 | Magomedov DEC R3 5:00 | Magomedov ✓ | Magomedov ✓ | Magomedov ✓ | ✗ | ✗ | ✗ |
| 6 | Silva DEC R3 5:00 | Silva ✓ | Silva ✓ | Silva ✓ | ✓ | ✓ | ✓ |
| 7 | Petersen KO R3 4:47 | Lorenco ✗ | Petersen ✓ | Petersen ✓ | ✗ | ✗ | ✓ |
| 8 | Schmid DEC R3 5:00 | Nakamura ✗ | Nakamura ✗ | Nakamura ✗ | ✗ | ✗ | ✗ |
| 9 | Raposo DEC R3 5:00 | Raposo ✓ | Raposo ✓ | Raposo ✓ | ✗ | ✓ | ✓ |
| 10 | Milošević KO R2 3:40 | Milošević ✓ | Milošević ✓ | Milošević ✓ | ✓ | ✓ | ✓ |
| 11 | Fernando DEC R3 5:00 | Fernando ✓ | Fernando ✓ | Fernando ✓ | ✗ | ✗ | ✗ |
| 12 | Smith KO R1 1:00 | Smith ✓ | Smith ✓ | Smith ✓ | ✓ | ✗ | ✗ |
| 13 | Suarez DEC R3 5:00 | Suarez ✓ | Suarez ✓ | Suarez ✓ | ✓ | ✓ | ✓ |
| 14 | Walker KO R3 2:27 | Cortes Acosta ✗ | Walker ✓ | Walker ✓ | ✗ | ✓ | ✓ |

### Each model's selected fighter CONDITIONAL method (not just reference fighter method)

| # | Actual method | Reference model's own winner method | Historical model's own winner method | Unified model's own winner method | Accuracy trio R/H/U |
|---:|---|---|---|---|---|
| 1 | KO | KO | KO | KO | ✗ / ✗ / ✗ |
| 2 | DEC | DEC | DEC | DEC | ✓ / ✓ / ✓ |
| 3 | KO | KO | KO | KO | ✗ / ✗ / ✗ |
| 4 | SUB | KO | SUB | SUB | ✗ / ✓ / ✓ |
| 5 | DEC | SUB | SUB | SUB | ✗ / ✗ / ✗ |
| 6 | DEC | DEC | DEC | DEC | ✓ / ✓ / ✓ |
| 7 | KO | KO | DEC | KO | ✗ / ✗ / ✓ |
| 8 | DEC | KO | KO | KO | ✗ / ✗ / ✗ |
| 9 | DEC | KO | DEC | DEC | ✗ / ✓ / ✓ |
| 10 | KO | KO | KO | KO | ✓ / ✓ / ✓ |
| 11 | DEC | KO | KO | KO | ✗ / ✗ / ✗ |
| 12 | KO | KO | SUB | SUB | ✓ / ✗ / ✗ |
| 13 | DEC | DEC | DEC | DEC | ✓ / ✓ / ✓ |
| 14 | KO | KO | KO | KO | ✗ / ✓ / ✓ |

**Nuance:** On Lorenco vs Petersen and Cortes Acosta vs Walker the historical/unified models actually picked the **other fighter**, so their conditional winning method must be computed for **their selected fighter** from the 6-way pre-event joint distribution. The method chart previously displayed in conversation conditioned all three on the **reference-selected fighter**. This was rectified for fair exact winner+method grading in `tools/grade_ufcvegas124_all_locked_picks.py`; no prediction was changed.

**Probabilistic scoring (lower is better):**
- Winner multiclass Brier (two-outcome sum): reference 0.4591, historical 0.3932, unified 0.4051.
- Winner log loss: reference 0.6495, historical 0.5856, unified 0.5973.
- **6-class fighter+method Brier:** reference 0.7513, historical 0.6940, unified 0.6981.
- **6-class fighter+method log loss:** reference 1.4664, historical 1.4675, unified 1.4379.

The unified shadow led **exact hit rate and joint log loss**, while the historical shadow slightly led **joint Brier and winner Brier/log loss**. Therefore the exact-accuracy comparison does **NOT** establish the unified model as best calibrated on this tiny sample, and no trained model is promoted.

### Actual methods vs forecasts and submission learning

Actual **6 KO/TKO, 1 SUB, 7 DEC** across 14 bouts. The reference winner-side conditional-method top label was **10 KO, 1 SUB, 3 DEC**, overly KO-heavy relative to observed frequencies. The historical and unified shadows found Bashi submission while the reference guessed KO. For Magomedov all three models favored submission, but actual outcome was decision. Raposo was DEC, historical/unified expected DEC, reference expected KO. Lucas Fernando won DEC but all three expected KO. Elijah Smith KO in R1 validated reference KO while historical/unified expected SUB. The ONE observed submission is not enough to generalize recall gains; the baseline's severe historical submission-recall deficit still requires multi-card study.

### Single timing prediction per fight — separate pre-event research

**10–4 (71.4%)**, explicitly NOT an officially approved timing betting record and **not part of the initial odds-blind Stage A lock** (selection generated pre-fight after quotes were visible but using unpriced Stage A probability vectors). We did not choose retrospective winning markets.

| # | Single pre-event timing research forecast | Original FanDuel | Sim P (current/unified) | Settled |
|---:|---|---:|---|:---:|
| 1 | Fight goes distance NO | -186 | 67.6% / 63.1% | ✓ |
| 2 | Round 3 starts YES | -140 | 66.8% / 64.9% | ✓ |
| 3 | Fight goes distance NO | -590 | 57.2% / 58.3% | ✓ |
| 4 | OVER 1.5 rounds | -110 | 67.2% / 67.2% | ✗ |
| 5 | Round 3 starts YES | -128 | 65.1% / 68.1% | ✓ |
| 6 | Round 3 starts YES | -260 | 73.3% / 73.6% | ✓ |
| 7 | Fight goes distance NO | -205 | 68.2% / 69.8% | ✓ |
| 8 | Fight goes distance NO | -320 | 64.4% / 64.9% | ✗ |
| 9 | Round 3 starts YES | -168 | 62.7% / 60.5% | ✓ |
| 10 | OVER 1.5 rounds | +102 | 72.7% / 70.3% | ✓ |
| 11 | Fight goes distance NO | -174 | 59.1% / 64.8% | ✗ |
| 12 | Round 3 starts YES | -134 | 71.4% / 67.9% | ✗ |
| 13 | Round 3 starts YES | -460 | 71.0% / 73.7% | ✓ |
| 14 | Fight goes distance NO | -430 | 77.5% / 83.6% | ✓ |

Four primary timing misses: **Bashi O1.5 (R1 SUB), Nakamura–Schmid GTD NO (DEC), Elekana–Fernando GTD NO (DEC), Grant–Smith Round 3 starts YES (R1 KO)**. A high 10/14 hit count is not by itself a good priced strategy: several correct timing picks were heavy favorites (e.g. −590/−460/−430).

## Top Five + Top Five FanDuel: actual graded research-only 1-unit virtual exposure

**All ten were clearly designated PASS / research-only before the event.** The original official betting price gate approved **0 wagers, 0 official units staked, and NO official-bet ROI**. A separate simulated-1u ledger was pre-event frozen specifically to study our display candidates. The scores below are **hypothetical**, not proof of bets, dollars won or money risked.

### Top 5 Longshots (+200 or higher): 0–5, −5.00 hypothetical units, −100% ROI

| # | Longshot research pick | Original FanDuel | Result | Virtual P/L | 
|---:|---|---:|:---:|---:|
| 1 | Tatiana Suarez vs Virna Jandiroba: Fight goes distance NO | +240 | L | -1.00u |
| 2 | Austin Bashi vs Carlos Calderon: Fight goes distance YES | +230 | L | -1.00u |
| 3 | Mantas Kondratavicius vs Andre Petroski: Fight goes distance YES | +400 | L | -1.00u |
| 4 | Jose Delano vs Murtazali Magomedov: Murtazali Magomedov by SUB | +360 | L | -1.00u |
| 5 | Jonny Parsons vs Jose Souza: Jonny Parsons by KO_TKO | +460 | L | -1.00u |

### Top 5 Best Bets (−150 through +190): 2–3, −0.12 hypothetical units, −2.4% ROI

| # | Best Bet research pick | Original FanDuel | Result | Virtual P/L |
|---:|---|---:|:---:|---:|
| 1 | Jose Delano vs Murtazali Magomedov: Murtazali Magomedov ML | +100 | W | 1.00u |
| 2 | Jonny Parsons vs Jose Souza: Jonny Parsons ML | +188 | L | -1.00u |
| 3 | Mitch Raposo vs Marcos Degli: Mitch Raposo ML | +188 | W | 1.88u |
| 4 | Austin Bashi vs Carlos Calderon: OVER 1.5 rounds | -110 | L | -1.00u |
| 5 | Davey Grant vs Elijah Smith: Fight goes distance YES | +132 | L | -1.00u |

Combined **2–8, −5.12 virtual units on 10 hypothetical units of settled exposure (−51.2% ROI).** The three logically compatible same-fight pairs were nonetheless correlated: Magomedov ML W + SUB L (split); Parsons ML L + Parsons KO L; Bashi O1.5 L + Bashi GTD Yes L. Both Bashi selections failed together despite being logically compatible.

**Methodology:** One fixed 1u hypothetical straight on each displayed market at its EXACT original user-provided FanDuel snapshot odds. At +188 a W would produce +1.88u; L is −1u. At −110 a W produces +0.9091u; L is −1u. ROI uses W/L risk only. All grades derived from recorded market_specs + verified official winner/time/method. Neither the five longshots nor five best bets were a green-light to wager. NO hindsight re-ranking.

## Risk-tier diagnostics

Pre-event frozen reference research posture:
- **PASS: 4/8 winners (50%)**.
- **LEAN: 3/4 winners (75%)**.
- **SIDE: 2/2 winners (100%)**.
- Combined non-PASS **5/6 (83.3%)**.

This is encouraging directional evidence that the quality gate filtered some unreliable winner forecasts, not proof that the exact PASS threshold maximizes betting EV. The actual W-L in PASS does not retroactively convert excluded markets to approved picks.

## Historical cumulative clean reference ledger (legacy standard)

Preserved the 139 original graded fights without edits and appended 14 post-event rows into **`data/results/clean_ufc_153_2026-11-07.csv`**.

| Metric | Through 2026-10-24 (139) | Now including 2026-11-07 (153) |
|---|---:|---:|
| Reference winner hit rate | 83/139 (59.7%) | **92/153 (60.1%)** |
| Displayed winner-side method *class* correct ignoring side | 70/139 (50.4%) | **79/153 (51.6%)** |
| Actual correct winner + exact method together | 43/139 (30.9%) | **48/153 (31.4%)** |

**WARNING:** The legacy `method_correct` column grades the displayed METHOD CLASS independently of whether the chosen FIGHTER won. Do not label its 79/153 as exact method-bet wins. `joint_correct` 48/153 is the more relevant exact fighter+method metric. Three-model challengers are tracked prospectively in new separate JSON, NOT added to historical legacy champion ledger.

## Lessons learned — actionable but avoid single-card overfitting

1. **Winner challenger disagreement is highly important:** the reference failed on Petersen and Walker while both challengers correctly picked both sides. Investigate why reference v0.27 remains anchored to older coefficients and which matchup features dominate these two fights; validate on multiple chronological out-of-sample slates before promoting.
2. **One KO vs DEC bias can replace another:** current top method output tilted KO (10/14) compared with 6/14 observed KO. Historical/unified did better identifying Bashi SUB and Raposo DEC, but unified SUB on Elijah Smith and all models SUB on Magomedov missed. Calibrate **fighter-specific method conditioned on winning**, and keep class balance/true submission recall diagnostics separate from exact parlay outcomes.
3. **Finish timing families are not coherent:** the large raw GTD-YES +360 on Milošević–Cachoeira missed (KO R2). Bashi round timing missed (SUB R1). The 10/14 single timing forecasts show some useful information, but cannot justify overriding hard family-coherence or low-data betting restrictions. Do not let huge raw expected-value figures automatically create official longshots.
4. **Top 5 always full is NOT a profit target:** Longshot research 0–5, −5u. Five ranked opportunities per category can be shown for learning, but **do not force five real stakes**, and keep labels PASS. Same-fight compatibility is logically supported but highly correlated losses must be tracked.
5. **Model vintage must be transparent:** frozen raw model metadata shows champion v0.27 reconstructed fit through **2026-09-12** with fighter features updated to Oct 31, historical conditional shadow fitted through **2026-10-17** (NOT refit through Oct 31), and unified shadow using an Oct 17 source cutoff. Other method/timing shadows were fit through Oct 31. Before future slates, clearly log the precise FIT cutoff vs data feature availability; only retrain with verified completed bouts available at that time. No future-event leakage.
6. **After-event fighter and round statistics require separate ingestion:** These 14 verified winners/methods/finish seconds are valid for grading but are **not proof that UFCStats per-round knockdowns, significant strikes, takedowns, control, submission attempts or damage are available/imported**. Do not invent counts or add result-only placeholders into feature-rich training tables. Collect UFCStats when accessible, validate source provenance and per-fight/per-round totals, and run chronological train/test without lookahead.

## Actual code/files committed as part of this grading

- `data/results/ufcvegas124_2026-11-07_verified_outcomes.json` — documented final outcomes from official UFC event and independent media.
- `tools/grade_ufcvegas124_all_locked_picks.py` — deterministic full 14-fight grading, all three methods conditioned on **each model's own fighter**, 6-class log loss/Brier and two-outcome win scores, 14 fixed timing picks, both 5-slot virtual unit outcome ledgers, and clean 139→153 reference ledger update. SHA integrity checks fail closed if pre-fight artifacts change.
- `tests/test_ufcvegas124_postcard_grading.py` — regression for winner and method scores, 10–4 timing picks, exact 10 snapshot quotes, virtual units, pending/result provenance, cumulative ledger preservation, and re-computability.
- `data/results/ufcvegas124_2026-11-07_all_models_grading.json` — per-bout full data and model probability metrics.
- `data/results/ufcvegas124_2026-11-07_top5_verified_settlements.json` — tagged post-event verification for the exact 10 frozen watches.
- `data/results/ufcvegas124_2026-11-07_top5_research_unit_grade.json` — research-only 1u price/win/loss/net units and ROI, never official-bet P/L.
- `data/results/clean_ufc_153_2026-11-07.csv` — clean legacy champion result ledger extended chronologically without rewriting older entries.
- **NO** champion coefficient changes, shadow model promotion, odds re-fitting, unlocked predilection flips, or contamination of pre-event freeze.

### Next step

Collect remaining official **full UFCStats round and fighter totals** (pending verification); add only accurately sourced post-fight stats to future-only training tables. Compare challenger performance on another prospectively frozen card and a larger held-out sample; keep calibration, Brier/log loss, finish-type recall, and betting EV gates ahead of anecdotal hit-rate changes.

**This report is a complete after-event grade and lesson record, not a claim of profitable bets or fully integrated current post-fight feature data.**
