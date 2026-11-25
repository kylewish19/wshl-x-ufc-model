# UFC Vegas 124 — complete frozen Stage B FanDuel price audit

**Saturday November 7, 2026; saved before scheduled 5pm ET prelims.**

**Stage B result: No official Top 5 +200 longshot and no official Top 5 −150 to +190 Best Bet can pass every documented gate at the screenshot quotes.** This is a deliberately conservative outcome under the user's adopted one-fight-across-categories policy, **not a claim there were no interesting prices**.

## Verification and audited sources

- Official all-28-made-weight UFC list: https://www.ufc.com/news/official-weigh-in-results-ufc-fight-night-cortes-acosta-vs-walker
- Source prices: **14 user-provided FanDuel screenshot sets**, `data/quotes/ufcvegas124_2026-11-07_fanduel_user_screenshots.json`.
- **378** transcribed quote prices, of which **350** correspond to modeled non-draw outcomes, and **28** are duplicated $+5000 draw offers across two market sections (our model has no draw-probability fit). The screenshot set contains no total-round O/U for Kondratavicius–Petroski or Nakamura–Schmid, and the main-event exact-round pricing was hidden under a collapsed menu; none was invented.
- All 14 frozen odds-blind picks unchanged; stage A file `data/locks/ufcvegas124_2026-11-07/stage_a_final_selection.json`.
- Full **378-outcome** quote-by-quote probabilities, bookmaker break-even, simple raw model EV, shadow stress checks and **explicit block reasons**: `data/locks/ufcvegas124_2026-11-07/stage_b_fanduel_full_price_audit.json`.
- Exact screenshot quote timestamp is **not independently authenticated**. No claim that these are still live prices or that a personal bet was placed. Model/price analysis was completed pre-event.

## Frozen winner model versus quoted FanDuel moneyline

*Raw model probability edge is NOT a calibrated value-bet guarantee.*

| # | Frozen winner | FanDuel ML | Model win P | Market break-even | Raw edge | Stage B decision |
|---:|---|---:|---:|---:|---:|---|
| 1 | Jonny Parsons | +188 | 66.2% | 34.7% | +31.4pp | PASS: only 1 prior UFC bout for each; Parsons 3+ years inactive |
| 2 | Seokhyeon Ko | -720 | 71.0% | 87.8% | -16.8pp | B-side but moneyline −720 requires 87.8% (model 71.0%) |
| 3 | Mantas Kondratavicius | -295 | 78.1% | 74.7% | +3.4pp | C lean; −295 outside range and 1 UFC bout for Mantas |
| 4 | Austin Bashi | -590 | 70.2% | 85.5% | -15.3pp | PASS: Calderon 0 UFC bouts, emergency replacement |
| 5 | Murtazali Magomedov | +100 | 71.5% | 50.0% | +21.5pp | PASS: 1 prior UFC bout each; method/finish conflict |
| 6 | Karine Silva | -220 | 57.5% | 68.8% | -11.3pp | C lean; −220 outside range; ML model below implied price |
| 7 | Gabriel Lorenco | +138 | 55.8% | 42.0% | +13.8pp | PASS: two shadows favor Petersen, unlike reference Lorenco |
| 8 | Keiichiro Nakamura | -360 | 62.4% | 78.3% | -15.8pp | PASS: 1 UFC bout each; method unvalidated |
| 9 | Mitch Raposo | +188 | 60.8% | 34.7% | +26.1pp | PASS: Degli UFC debut and regional-to-UFC transfer uncertainty |
| 10 | Nina Milosevic | -590 | 85.7% | 85.5% | +0.2pp | C lean; −590 outside range; one UFC fight and finish incoherence |
| 11 | Lucas Fernando | -340 | 52.4% | 77.3% | -24.9pp | PASS: near-coinflip reference and sparse Fernando experience |
| 12 | Elijah Smith | -330 | 59.5% | 76.7% | -17.2pp | C lean; −330 outside range; timing families disagree |
| 13 | Tatiana Suarez | -200 | 75.8% | 66.7% | +9.1pp | A− side, highest-supported raw value; −200 outside chosen range |
| 14 | Waldo Cortes Acosta | -230 | 63.8% | 69.7% | -5.9pp | PASS: shadows favor Walker, reference Cortes Acosta |

## Top 5 Longshots: +200 and higher

**0 of 5 approved**. Exact-method, fighter-specific double-chance, and finish-method families remain blocked by Stage A model/timing coherence failures; many tempting longshot odds involve a frozen research PASS, a UFC newcomer or an unsupported timing/model contradiction.

Notable **REJECTED** screenshots — these are *not* suggested wagers:

- **Nina Milosevic vs Cachoeira GTD YES +360**: current timing model 56.57% versus market 21.74% break-even, but Nina has just one UFC bout, and the method model and timing model disagree by 40.5 percentage points. This enormous raw edge is not a calibrated estimate.
- **Parsons KO/TKO +460**: model's raw six-way joint estimates 53.3%, but that matchup is a PASS because of extreme inactivity/UFC history sparsity, and all method markets are not promoted.
- **Gabriel Lorenco KO/TKO +250**: model reference leans Lorenco but two other winner models favor Petersen; research PASS and method-family block.
- **Davey Grant ML +265**: raw opposite-side win mass is 40.5% versus FanDuel break-even 27.4%, but this is the opposite of our frozen **Elijah Smith** selection. Price alone cannot switch the official side. 
- **Billy Elekana ML +275**: raw opposite-side probability 47.6% versus 26.7% market break-even; the frozen selection is Lucas Fernando with low 52.4% reference confidence and a PASS. A textbook warning against treating the enormous underdog raw gap as a validated wager.

## Top 5 Best Bets: −150 through +190

**0 of 5 approved.** The user's requested band does not contain the strongest frozen side prices (Suarez -200, Ko -720), and the other attractive priced predictions fail qualification.

Examples:

- **Jonny Parsons ML +188:** raw frozen winner P 66.2% versus 34.7% market implied. Still a **PASS**, not an official wager, because both UFC samples are exceptionally limited and Parsons has a 1,204-day UFC inactivity gap.
- **Mitch Raposo ML +188:** raw frozen P 60.8% versus 34.7% implied; **PASS** because Degli is a UFC debutant who may not transfer predictably from regional MMA. No automatic market-error free money.
- **Smith–Grant GTD YES +132:** timing sim P 62.22% vs 43.10% break-even, **but** independent method-joint finish probability exceeds timing finish probability by approximately **27.9pp**. The unified shadow GTD-yes estimate is 58.28%, still promising in isolation, but choosing only the optimistic timing family after seeing the price is not a valid calibrated edge. **BLOCKED.**
- **Suarez–Jandiroba GTD NO +240:** timing sim P 37.75% versus 29.41% implied; edge **8.3pp**, below existing **12pp** timing-edge requirement.
- **Ko–Turman GTD YES +110:** timing sim P 56.51% versus 47.62% implied; **8.9pp** edge, below the 12pp promotion gate; method/timing finish difference also exceeds 15pp.
- **Karine Silva–Fernandes O2.5 −190:** timing sim P 68.81% vs 65.52% implied; **3.3pp**, below the 12pp timing gate.

## Separate overall best straight-watch candidate (OUTSIDE two tiers)

**Tatiana Suarez Moneyline −200**, FanDuel snapshot:

- Frozen reference winner probability **75.8%**; historical-conditional shadow **72.5%**; unified shadow **73.5%**.
- FanDuel −200 requires **66.7%** success to break even. Reference raw edge **+9.1 percentage points**, model-estimated one-unit EV about **+0.137u** *if the reference estimate is calibrated*.
- The low model among the three is about **72.5%**, but this is a **shadow cross-check, not an audited probabilistic lower confidence bound**.
- Suarez remains the strongest odds-blind, well-supported side. However **−200 is explicitly outside the user's −150..+190 Top 5 category**. Mark as an **outside-range watch candidate only**, not as an official two-tier straight or guaranteed winner. Actual FanDuel quote needs reconfirmation before placing any wager.

### Why not force the old two-leg parlay?

- Suarez −200 is outside the new two-tier category but could be an overall stand-alone research candidate.
- Ko −720 needs 87.8% to break even but the frozen reference assigns only 71.0%. **Adding Ko to a Suarez parlay would worsen expected value**, so there is no defensible favorite two-leg or favorite three-leg this time. No safer anchor or longshot is promoted merely for a summary slot.

## Reproducibility, governance and next results grading

- Stage A's 14 winners and complete method/timing raw distributions are immutable and price-blind.
- Research PASS fights remain eligible for **post-fight winner-pick grading**, even though no bet was placed/promoted.
- Independent exact-method and round/timing warnings remain in the code; no challenger was trained/promoted in response to today's odds.
- Two separate new Top5 lists will be tracked in future events; **this event has zero officially selected bets and zero units at risk in these categories, not a 0% hit rate or a loss.**
- If new pre-fight FanDuel lines are supplied, produce a **versioned** Stage B amendment against the same frozen Stage A; never rewrite prices with hindsight.
- Code: `tools/audit_ufcvegas124_fanduel_stage_b.py`, `src/wshlx_ufc/two_tier_card.py`; tests: `tests/test_ufcvegas124_fanduel_stage_b_audit.py`.

> Stage B did not produce 10 bets because the user explicitly chose **no forced picks**, **no overlapping fights**, **model-supported value rather than raw edge inflation**, and **FanDuel only**.
