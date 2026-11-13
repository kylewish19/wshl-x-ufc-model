# UFC Vegas 124 — WSHL_X complete odds-blind Stage A freeze

**Event:** UFC Fight Night: Waldo Cortes Acosta vs Johnny Walker  
**Date:** Saturday, November 7, 2026, Meta APEX, Las Vegas  
**Status:** Frozen research-reviewed Stage A, odds blind; Friday official weigh-in verification incomplete at freeze. **Not a FanDuel bet card.**

## Sources and chronology

- UFC current official event page: https://www.ufc.com/event/ufc-fight-night-november-07-2026
- Official fighter-by-fighter preview: https://www.ufc.com/news/fight-by-fight-preview-ufc-fight-night-cortes-acosta-vs-walker
- Official change notice: https://www.ufc.com/news/updates-ufc-fight-night-cortes-acosta-vs-walker
- Official live weight source: https://www.ufc.com/news/official-weigh-in-results-ufc-fight-night-cortes-acosta-vs-walker
- November 4 news confirming Calderon replacing injured Brennan: https://www.mmafighting.com/ufc/519393/ufc-vegas-124-adds-replacement-fighter-on-4-days-notice
- **14 bouts** verified with current UFC official card. The old Bonfim–Brady headline is off the card; Cortes Acosta–Walker is the 5-round main event. All others scheduled 3 rounds.
- No FanDuel or other sportsbook prices entered Stage A.
- No continuous fight-film playback was completed; evidence is reported honestly as UFC preview/stats/result research, not tape viewed.

## Executed model stack (do not conflate data through with training through)

1. **Frozen reference winner:** v0.27 reconstructed, coefficients fitted through September 12, 2026; pre-bout fighter history features updated through *October 31*.
2. **Current baseline method, calibrated method, residual method, winner comparison, 30-sec timing models:** post-Oct31 future-only shadow artifacts trained through October 31; 139 actual frozen graded feedback fights, plus 12 Oct31 **unpicked training-only** fight results in historical features.
3. **Historical conditional winner/method/timing shadow:** model coefficients still fitted through **October 17**, NOT Oct31. The competing source snapshot was updated before Nov7 as available; this is not a newly retrained historical model.
4. **OOF-unified research shadow:** previous fixed OOF weights: current winner 0.30, method 0.375, timing 0.75. Not reoptimized or promoted.
5. Current 14-fight reference **joint outcomes and timing each drawn 10,000 times** per bout. Unified joint and timing also **10,000 trials** each. Saved, seeded artifacts, not conversational guessed probabilities.

## Frozen winner selections and research posture

| # | Matchup | Frozen reference winner | Win P | Historical winner | Unified winner | Stage A |
|---|---|---|---:|---|---|---|
| 1 | Jonny Parsons–Jose Souza | Parsons | 66.2% | Parsons | Parsons | PASS: both thin sample, Parsons 3+ yr layoff |
| 2 | Seokhyeon Ko–Wellington Turman | **Ko** | **71.0%** | Ko | Ko | **B SIDE**: Turman inactivity |
| 3 | Mantas Kondratavicius–Andre Petroski | Kondratavicius | 78.1% | Kondratavicius | Kondratavicius | C LEAN: one UFC bout; Petroski wrestling |
| 4 | Austin Bashi–Carlos Calderon | Bashi | 70.2% | Bashi | Bashi | PASS: Calderon 0 UFC, four-day replacement |
| 5 | Jose Delano–Murtazali Magomedov | Magomedov | 71.5% | Magomedov | Magomedov | PASS: both 1 UFC fight, SUB uncertainty |
| 6 | Karine Silva–Gabriella Fernandes | Karine Silva | 57.5% | Karine Silva | Karine Silva | C LEAN: small edge, Fernandes form |
| 7 | Gabriel Lorenco–Thomas Petersen | Lorenco | 55.8% | **Petersen** | **Petersen** | PASS: debutant, model disagreement |
| 8 | Keiichiro Nakamura–Ollie Schmid | Nakamura | 62.4% | Nakamura | Nakamura | PASS: 1 UFC bout each |
| 9 | Mitch Raposo–Marcos Degli | Raposo | 60.8% | Raposo | Raposo | PASS: Degli debutant 13-win streak |
| 10 | Priscila Cachoeira–Nina Milosevic | Milosevic | 85.7% | Milosevic | Milosevic | C LEAN despite raw 85.7%: one UFC bout |
| 11 | Billy Elekana–Lucas Fernando | Fernando | 52.4% | Fernando | Fernando | PASS: near 50/50, 1-bout Fernando |
| 12 | Davey Grant–Elijah Smith | Smith | 59.5% | Smith | Smith | C LEAN: historical 83% vs reference 59% |
| 13 | Tatiana Suarez–Virna Jandiroba | **Suarez** | **75.8%** | Suarez | Suarez | **A− SIDE**: sufficient UFC samples |
| 14 | Waldo Cortes Acosta–Johnny Walker | Cortes Acosta | 63.8% | **Walker** | **Walker** | PASS: heavyweight transition, short notice, disagreement |

No research-driven winner flips. Reference picks remain recorded even for PASS bouts so post-event grading assesses all 14.

## Descriptive method and timing — NEVER confuse the two probability definitions

The **conditional method probabilities** in the Stage A selection mean: P(method **given the selected fighter wins**). They are *not* probabilities that a bet on fighter+method pays. The latter requires P(fighter wins **and** method), stored separately in the six-way joint file.

- The top conditional selected-fighter method is KO/TKO in 10 fights, DEC in 3, SUB in 1. It is descriptive, **not an official method bet list**. The earlier 139-fight ledger exposed extremely weak submission recall; do not force a KO-to-SUB flip.
- **Zero official exact-method promotions** this card.
- Best independent timing model over-2.5 probability on more experienced non-sparse pairings: Karine Silva–Fernandes **68.8%**, Grant–Smith **66.5%**, Suarez–Jandiroba **66.2%**, Ko–Turman **61.7%**. Candidate model outputs only, not playable until market-family calibration and FanDuel pricing gates.
- For 5-round Cortes Acosta–Walker, the timing hazard makes **GTD NO 77.5%** and **Under 2.5 57.5%** in current 10k simulations, but reference/unified outright disagree on the winner, so the fight remains a PASS for winner bets. Do not confuse GTD and selected-side KO rates.

## Critical mathematical model integrity finding

The reference *six-way winner×method* model and independent *30-second timing hazard* frequently disagree about the total finish probability. This is **not merely a pick miss**; these independent probabilities cannot simultaneously describe one coherent distribution.

The separate odds-blind pre-price audit found:

- **10/14** fights with absolute disagreement above **15 percentage points** between joint-model probability of a finish and timing-hazard GTD NO.
- **Two exact fighter-finish outcome probabilities exceed the hazard probability that the entire fight finishes**, mathematically incompatible within a single joint model:
  - **Magomedov by SUB:** exact reference joint **50.3%**, hazard GTD NO **45.3%**; method-model total finish **77.2%** versus hazard **45.3%**.
  - **Milosevic by KO:** exact reference joint **69.2%**, hazard GTD NO **43.4%**; method-model total finish **83.9%** versus hazard **43.4%**.
- Model-family inconsistency is most severe on multiple UFC-sparse fighters, including those two. **Do not price the direct exact-method outcomes as betting edges.**
- A separate mathematical-only **IPF-coherence shadow** was developed and saved. It preserves winner probabilities, timing GTD yes/no, and conditional KO/SUB fractions; it is **not a predictive calibration proof** and **not promoted**. Its adjusted probabilities are not automatically bettable.
- All exact-method wager price gates are blocked until prospective tests of coherence and calibration support reopening them. Independent timing props require their own market-family tests.

Audit: `data/locks/ufcvegas124_2026-11-07/stage_a_coherence_audit.json`.  
Shadow: `data/locks/ufcvegas124_2026-11-07/stage_a_coherence_shadow.json`.

## Stage B readiness and allowed process

- Frozen lock: `data/locks/ufcvegas124_2026-11-07/stage_a_final_selection.json`.
- Freeze audit: `data/locks/ufcvegas124_2026-11-07/stage_a_final_audit.json`.
- Raw full three-view and 10k simulation outputs: `data/locks/ufcvegas124_2026-11-07/stage_a_model_raw_three_view.json`.
- **Weigh-in status:** official UFC page had no complete independently verifiable 28-athlete weights in available results when locked. Check official scale readings, any misses, injuries, cancellations before selecting FanDuel plays. Any material changes need an explicitly timestamped amendment; never overwrite the frozen raw.
- **Stage B FanDuel only**: obtain actual prices, break-even probability, documented probability calibration and EV/edge gate, market availability, bankroll/stake limit. Passing price gates cannot retroactively change the frozen side or convert a PASS into a prior official side bet.
- Highest-quality pre-price **straight candidate**: Suarez; other SIDE candidate: Ko. A hypothetical two-leg *research* combination is Suarez + Ko, **not officially recommended or priced** until the FanDuel implied probabilities and parlay risk are reviewed.
- Do not treat the 139 clean previously graded fights plus 12 unpicked Oct31 outcomes as 151 official prediction grades. The 300 newly frozen prospective-fight promotion gate remains unchanged.

## Reproducibility and learning

Research and CI preserved all previous UFC333 and Oct31 original artifacts. New Nov7 scripts and tests:
- `tools/run_ufcvegas124_stage_a.py`
- `tools/finalize_ufcvegas124_stage_a.py`
- `src/wshlx_ufc/coherence.py`
- `tools/audit_ufcvegas124_market_coherence.py`
- `tests/test_ufcvegas124_stage_a_integrity.py`

Every future card should test *fight-level* method recall, calibration, sparse/UFC debutant reliability and counter-grappling access rather than applying a blind event-wide KO/DEC correction.
