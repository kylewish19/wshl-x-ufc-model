# WSHL_X UFC — permanent FanDuel Top 5 + Top 5 straight-bet policy

**Effective:** UFC Fight Night, November 7, 2026. **Scope:** UFC only.  
**Development branch:** `feature/historical-conditional-rates` until separately merged/approved.

## The two independent cards (same event)

| Card | American odds requirement | Maximum picks | Stake type |
|---|---|---:|---|
| **Top 5 Longshots** | **+200 or greater** | 5 | Individual straight bets |
| **Top 5 Best Bets** | **−150 through +190 inclusive** | 5 | Individual straight bets |

- **No fight may appear more than once across both lists**, regardless of market, athlete, prop, outcome, or category. Examples: a fighter-by-KO +250 longshot excludes the same fighter's ML −125, an opponent ML, any fight total, and any round prop from **both** lists. Each card may have **0–5 picks**. A weekly 5/5 quota is **not** a goal.
- **+191 through +199** is intentionally outside both odds bands, as are prices shorter than −150. These odds are **not secretly rounded** into a band.
- Only **verified FanDuel** quoted prices are allowed. No substitute prices from DraftKings, BetMGM, prediction aggregators, screenshots of unrelated books, hypothetical listings, or fabricated lines.
- Every candidate price must be timestamped, must be available pre-fight, and must reference exactly the same frozen odds-blind Stage A card hash. **Price cannot modify Stage A predictions, sides or postures.**
- Pick ranking is **global across both categories** to resolve same-fight conflicts: highest **conservative-model expected value**, then probability edge, conservative probability, model evidence quality, stable candidate ID. The highest *eligible* market claims its fight; the other category cannot include that matchup. Each list caps at five. This ranking is not a guarantee of profitability.
- An **official top-five pick** must also pass all documented research, market-family, price/edge, probability-calibration, and Stage A support gates. A fight with a high raw probability but sparse data can still be a **PASS**; a huge apparent EV is not enough. A candidate's conservative probability must be independently justified and at most its raw model probability—**no default/shrinkage invented after seeing the price.**
- Existing winner/method/timing protections remain in force, including the timed-market 12-percentage-point edge/sparse checks, currently blocked method-family pricing where method-vs-timing marginals are incoherent, and the price-alone-can't-flip-the-Stage-A-pick rule. **The new categories do not override or promote restricted props.** The 300-fight challenger promotion gate also remains unchanged.
- **Top 5** are each **straight bets**, not a disguised five-leg parlay. We may still show best straight, safest anchor, best value, and an **optional** two-leg parlay in the end-of-card summary. Three-leg parlays are **not automatically generated**.

## Workflow each UFC event

1. **Stage A:** research each matchup, run current reference plus shadow/challenger predictions, record all winner/method/round/total/GTD/double-chance probabilities, risk gates and 10,000-simulation artifacts as applicable; freeze the odds-blind card before reading prices.
2. **Stage B:** read verified and timestamped **FanDuel** lines. Produce a list of proposed markets. Check market-family calibration, moneyline support, opponent history, contradictions, edge and conservative model EV, and pre-fight availability. Apply the two-tier algorithm and **one-fight-only** constraint. Save the Stage B card without rewriting Stage A.
3. **After UFC:** verify the actual result and each selected market's settlement; grade **Top 5 Longshots** and **Top 5 Best Bets** **separately**, preserving their selection IDs and pre-event odds. Record W, L, PUSH, VOID, PENDING, risk in units, net units won/lost, and ROI. Also report combined total but don't blur the categories.
4. **Cumulative tracking:** aggregate the independently graded categories over time, no hindsight swaps, no additional hypothetical winnings attributed to actual user wagers, and no assumptions about whether a recommendation was personally placed.

## Example input/output tooling

- Selection engine: `src/wshlx_ufc/two_tier_card.py`
- Freeze CLI: `tools/build_ufc_two_tier_stage_b.py`
- Independent grading CLI: `tools/grade_ufc_two_tier_stage_b.py`
- Cumulative independent W-L/units/ROI: `tools/summarize_ufc_two_tier_results.py`
- Unit/regression tests: `tests/test_two_tier_card.py`

The freeze CLI requires a real, exact Stage A SHA256 and a quotes JSON file. Each candidate must contain:

```json
{
  "candidate_id": "example-unique-id",
  "fighter_a": "Fighter One",
  "fighter_b": "Fighter Two",
  "market": "Fighter One ML",
  "market_family": "moneyline",
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

### Independent grading and accounting

- At American **+200**, a 0.25u W earns **+0.50u** and an L loses **−0.25u**.
- At American **−150**, a 0.25u W earns approximately **+0.167u**, and an L loses **−0.25u**.
- **PUSH/VOID** return the stake and add 0u net; **PENDING** cannot count as losses. Settled-risk ROI is net units divided by total W/L stakes risked; push/void/pending are excluded from settled-risk denominator.
- Document picks and outcomes separately. **Recommendations are not proof the user wagered.**
- Keep official category W-L and ROI separate from (a) frozen Stage A all-fights record, (b) model-only forecasts on PASS bouts, (c) hypothetical 2-leg or 3-leg parlays, and (d) the unpicked retrospective UFC October 31 card.

## November 7 transition

The full November 7 Stage A card is frozen at `data/locks/ufcvegas124_2026-11-07/stage_a_final_selection.json`. This policy applies to its **future, verified FanDuel Stage B price card**, but **no Nov7 Top5 selections, prices or outcomes are created by this policy commit**. Exact-method props remain blocked under the current Nov7 method-vs-timing coherence audit until prospective validation supports a change.

**Go/no-go:** Empty lists are correct if there are no qualified offers. Never choose a +200 longshot or −150 to +190 selection merely to reach five.
