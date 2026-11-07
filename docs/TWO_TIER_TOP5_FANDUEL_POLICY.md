# WSHL_X UFC — permanent FanDuel Top 5 + Top 5 straight-bet policy

**Effective:** UFC Fight Night, November 7, 2026. **Scope:** UFC only.  
**Development branch:** `feature/historical-conditional-rates` until separately merged/approved.

## The two independent cards (same event)

| Card | American odds requirement | Maximum picks | Stake type |
|---|---|---:|---|
| **Top 5 Longshots** | **+200 or greater** | 5 | Individual straight bets |
| **Top 5 Best Bets** | **−150 through +190 inclusive** | 5 | Individual straight bets |

- **Same fight across categories is now ALLOWED only if both selections can win together.** For example, Fighter A ML as a Best Bet plus Fighter A KO/TKO as a Longshot is compatible; Over 1.5 rounds plus Fighter A by submission is compatible because a submission can happen after the Over threshold. **Fighter A ML plus Fighter B ML, Fighter B submission, or GTD Yes plus Fighter A KO/TKO are INCOMPATIBLE**, and the engine rejects these. A fight may appear at most once *within each category*, and at most twice *across both* if compatible.
- **Logical compatibility does not mean independent outcomes or low risk.** Two same-fight picks can both lose together, and concentration must be clearly disclosed rather than presented as two independent opportunities.
- Aim to **display five reviewed candidate opportunities per category when enough genuine FanDuel markets exist**, but show approved picks separately. A displayed **PASS / research-only** is never counted as a recommended bet, never recorded as official wager exposure, and cannot become a wager just to fill five. Each card still contains **0–5 officially qualified picks**. A mandatory 5/5 bet quota is not a goal.
- **+191 through +199** is intentionally outside both odds bands, as are prices shorter than −150. These odds are **not secretly rounded** into a band.
- Only **verified FanDuel** quoted prices are allowed. No substitute prices from DraftKings, BetMGM, prediction aggregators, screenshots of unrelated books, hypothetical listings, or fabricated lines.
- Every candidate price must be timestamped, must be available pre-fight, and must reference exactly the same frozen odds-blind Stage A card hash. **Price cannot modify Stage A predictions, sides or postures.**
- Pick ranking is **global across both categories**: highest **conservative-model expected value**, then edge, probability, evidence, stable candidate ID. A ranked candidate can share a fight with the opposite tier's selected market only if its exact structured win condition is compatible; duplicate and mutually exclusive outcomes are blocked. **No more than one officially selected market from a fight in each tier**. This ranking is not a guarantee of profitability.
- Outcomes MUST use the explicit validated `market_spec` metadata—do not infer compatibility from a vague market name. Supported types: fighter moneyline, fighter by method, fighter double chance, GTD Yes/No, total rounds Over/Under, round-to-start Yes/No and fight-ending method. **Unknown market shapes fail closed** until supported in code and tested. The current engine treats normal KO/TKO, SUB and DEC worlds; draw, DQ and technical-decision-special settlements are outside its scope.
- Each category may additionally show up to five **ranked_display** entries. Qualified bets have `OFFICIAL_TWO_TIER_STRAIGHT`; unqualified candidates are explicitly labeled `PASS_RESEARCH_ONLY_NOT_APPROVED_OR_BETTABLE` and include rejection reasons. The official W-L and ROI ledger includes **only** the selected bets, never WATCH/PASS display entries.
- An **official top-five pick** must also pass all documented research, market-family, price/edge, probability-calibration, and Stage A support gates. A fight with a high raw probability but sparse data can still be a **PASS**; a huge apparent EV is not enough. A candidate's conservative probability must be independently justified and at most its raw model probability—**no default/shrinkage invented after seeing the price.**
- Existing winner/method/timing protections remain in force, including the timed-market 12-percentage-point edge/sparse checks, currently blocked method-family pricing where method-vs-timing marginals are incoherent, and the price-alone-can't-flip-the-Stage-A-pick rule. **The new categories do not override or promote restricted props.** The 300-fight challenger promotion gate also remains unchanged.
- **Top 5** are each **straight bets**, not a disguised five-leg parlay. We may still show best straight, safest anchor, best value, and an **optional** two-leg parlay in the end-of-card summary. Three-leg parlays are **not automatically generated**.

## Workflow each UFC event

1. **Stage A:** research each matchup, run current reference plus shadow/challenger predictions, record all winner/method/round/total/GTD/double-chance probabilities, risk gates and 10,000-simulation artifacts as applicable; freeze the odds-blind card before reading prices.
2. **Stage B:** read verified and timestamped **FanDuel** lines. Produce a list of proposed markets. Check market-family calibration, moneyline support, opponent history, contradictions, edge and conservative model EV, and pre-fight availability. Apply the two-tier algorithm and **no same-tier duplicates / no incompatible cross-tier outcomes** constraint. Save the Stage B card without rewriting Stage A.
3. **After UFC:** verify the actual result and each selected market's settlement; grade **Top 5 Longshots** and **Top 5 Best Bets** **separately**, preserving their selection IDs and pre-event odds. Record W, L, PUSH, VOID, PENDING, risk in units, net units won/lost, and ROI. Also report combined total but don't blur the categories.
4. **Cumulative tracking:** aggregate the independently graded categories over time, no hindsight swaps, no additional hypothetical winnings attributed to actual user wagers, and no assumptions about whether a recommendation was personally placed.

## Example input/output tooling

- Selection engine: `src/wshlx_ufc/two_tier_card.py`
- Freeze CLI: `tools/build_ufc_two_tier_stage_b.py`
- Independent grading CLI: `tools/grade_ufc_two_tier_stage_b.py`
- Cumulative independent W-L/units/ROI: `tools/summarize_ufc_two_tier_results.py`
- Logical market compatibility engine: `src/wshlx_ufc/market_compatibility.py`
- Unit/regression tests: `tests/test_two_tier_card.py`

The freeze CLI requires a real, exact Stage A SHA256, a quotes JSON file, and **scheduled_rounds (3 or 5)** for each verified Stage A fight. Every candidate must contain typed market-spec metadata:

```json
{
  "candidate_id": "example-unique-id",
  "fighter_a": "Fighter One",
  "fighter_b": "Fighter Two",
  "market": "Fighter One ML",
  "market_family": "moneyline",
  "market_spec": {"kind": "moneyline", "side": "a"},
  "american_odds": 200,
  "model_probability": 0.43,
  "conservative_probability": 0.39,
  "evidence_quality": 0.8,
  "stake_units": 0.25,
  "sportsbook": "FanDuel",
  "quoted_at_utc": "2026-11-07T12:00:00Z",
  "researched_before_start": true,
  "gates": {
    "stage_a_supported": true,
    "research": true,
    "price": true,
    "calibration": true,
    "market_family": true
  }
}
```

**This is purely a schema example, not a real fighter, market, FanDuel quote or recommendation.** Each gate must actually be substantiated before being marked true.

Candidates in between price bands, with non-positive conservative EV, or failing any gate are **rejected with a reason**; no substitute value picks are invented.

### Compatibility examples

| Top 5 Best Bets | Top 5 Longshots | Can both settle as W? | Rule |
|---|---|---|---|
| Fighter A ML | Fighter A by KO/TKO | **YES** | Same winner, one specified method |
| Over 1.5 rounds | Fighter A by submission | **YES** | Fight can go past 7:30 and end by submission |
| GTD NO | Fighter A by KO/TKO | **YES** | Finish necessarily ends fight early |
| Fighter A ML | Fighter B ML | **NO** | Opposing winners |
| Fighter A ML | Fighter B by submission | **NO** | Opposing winners |
| GTD YES | Fighter A by KO/TKO | **NO** | Decision versus stoppage |
| Under 1.5 rounds | Round 3 Starts YES | **NO** | Contradictory clock conditions |

The typed support explicitly checks whether *some supported fight outcome* satisfies both contracts. It does **not** infer that both outcomes will often occur, nor that the joint payout has positive EV. Same-fight bets can double losses, so report correlated exposure.

### Independent grading and accounting

- At American **+200**, a 0.25u W earns **+0.50u** and an L loses **−0.25u**.
- At American **−150**, a 0.25u W earns approximately **+0.167u**, and an L loses **−0.25u**.
- **PUSH/VOID** return the stake and add 0u net; **PENDING** cannot count as losses. Settled-risk ROI is net units divided by total W/L stakes risked; push/void/pending are excluded from settled-risk denominator.
- Document picks and outcomes separately. **Recommendations are not proof the user wagered.**
- Keep official category W-L and ROI separate from (a) frozen Stage A all-fights record, (b) model-only forecasts on PASS bouts, (c) hypothetical 2-leg or 3-leg parlays, and (d) the unpicked retrospective UFC October 31 card.

## November 7 transition

The full November 7 Stage A card is frozen at `data/locks/ufcvegas124_2026-11-07/stage_a_final_selection.json`. This policy applies to its **future, verified FanDuel Stage B price card**, but **no Nov7 Top5 selections, prices or outcomes are created by this policy commit**. Exact-method props remain blocked under the current Nov7 method-vs-timing coherence audit until prospective validation supports a change.

**Go/no-go:** Empty lists are correct if there are no qualified offers. Never choose a +200 longshot or −150 to +190 selection merely to reach five.
