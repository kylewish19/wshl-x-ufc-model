# WSHL_X UFC — Full-card 60–70% exact and selective 2–5 exact-pick audit

**Registration/evaluation date:** November 18, 2026. **Status: Research-only; NO new model or Stage A/B promotion.**

**User's explicit goals:** strive for 100% correct exact fighter + victory method on every UFC fight, target 60–70% across typical 11–14-fight cards, and identify 2–5 especially reliable exact combinations. Do not misinterpret this as a mandate for more submissions, more KOs, or a 70% method-only target. A 100% hit rate on 2–5 bets cannot be promised; a high-confidence winner is not the same as a high-probability exact outcome.

## Verified source, method, and reproducibility

- Runner: `tools/audit_finish_v1_top5_exact_selection.py`; generated metrics JSON `reports/model_health/2026-11-18_finish_v1_research/selection_top1_to5_diagnostic.json`.
- Verified Actions CI (tests + year-ordered model training + submission ranking + exact top 1–5): https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44427740203 .
- Downloadable Actions artifact `wshlx-2026-11-18-independent-finish-v1-research` includes original source-date-ordered 2024–2026 predictions and results. No actual wager records involved.
- Same original independent **Multinomial Finish v1** model for the main table. It is NOT a production model, and its winner head in this experiment is an unchanged past-UFC-winrate baseline; hence do not equate its scores with Reference or Unified.
- 117 distinct dated UFC cards with 11–14 decided bouts (1,456 bouts) from the 2024, 2025, and inspected 2026 research evaluation vintages. Per-card top K is chosen by the existing PRE-result probability for an exact fighter+method event; reveal results only after ranking. Ties broken by immutable source bout ID.
- Some original cards with one or more draws can have fewer scored decisive bouts and are excluded from the 11–14 decided-bout main dashboard. Source years are historical research, NOT 117 pristine future prospective event locks. Data source is the pinned secondary UFCStats-compatible archive.

## Actual observed outcomes under all-six-outcome max-probability selection

| Per-card rank | Across-card exact hits | Hit rate | ALL selected hit, of 117 cards |
|---|---:|---:|---:|
| Top 1 | 44/117 | 37.6% | 44/117 |
| Top 2 | 88/234 | 37.6% | 12/117 |
| Top 3 | 132/351 | 37.6% | 3/117 |
| Top 4 | 169/468 | 36.1% | 1/117 |
| Top 5 | 212/585 | 36.2% | **0/117** |

Comparison of TOP selection strategies (same fights, identical underlying method probabilities):
- Rank model's own winning fighter + most likely conditional method by that **exact outcome probability**: Top1 **46/117 (39.3%)**, Top3 **140/351 (39.9%)**, Top5 **223/585 (38.1%)**, perfect Top5 cards **0/117**.
- Rank the same original winner+method pairs by **winner-only probability**: Top1 **43/117 (36.8%)**, Top3 **135/351 (38.5%)**, Top5 **212/585 (36.2%)**; perfect Top5 cards **0/117**.
- Selecting the GLOBAL most likely one of all six cells is theoretically optimal for accurately calibrated exact six-way probabilities, but on this historical research model its full-card exact performance was inferior to selecting the winner head first. This is diagnostic evidence of six-class calibration/model issues, not proof that two-stage selection is universally superior. Compare both against pristine pre-event forecasts later.
- **Risk of spurious overconfidence:** Across all **1,512** evaluated fights (including cards not in 11–14 subset) the new Multinomial method+winner model gave **only 1 fight** any exact outcome probability >0.50 and **none >0.55**. Maximum exact single-event probability **~51.30%**. An exact outcome labelled "90% lock" from this current model is not justified.

## What these results mean / concrete new workflow

The current trained model does not distinguish 2–5 exact outcomes per card with anything resembling 90–100% reliability. Do not impose an arbitrary 2–5 wager quota. No global SUB/KO/DEC target counts, no coefficient/temperature boosts to create fake certainty, no claims that 10,000 Monte Carlo trials repair weak base probabilities.

**Separate THREE outputs in every future Stage A candidate (without affecting existing official locks):**
1. **Full-card exact forecast:** one top fighter+method prediction for every matchup; always grade ALL decisive bouts (also grade winner head, native probabilities, and method confusion separately).
2. **Top-1 through Top-5 exact-probability ranking:** rank calibrated six-outcome exact P, compare (a) global maximum and (b) selected-winner conditional maximum and (c) winner-only confidence on chronological, identity-matched fights. Track actual hit rates, whole-subset-perfect card fractions, distribution of displayed probability vs observed precision, and event-cluster uncertainty. Rankings are diagnostics; not automatically wager recommendations.
3. **Bet-eligible subset:** only AFTER corroborated prefight evidence, data-density/coherence confidence and independently verified real FanDuel quotes clear the already-document selection and EV/price gates. If ZERO clear, output zero authorized exact-combo bets, not forced 2–5 "locks." Avoid same-fight correlated double inclusion.

**Model development objective:** maximize exact selected fighter+method accuracy while also requiring a strong six-class proper-score and calibration benchmark, not simply more winner confidence or method-label prevalence. Refit a source-verified, fighter-vs-opponent specific method and *winner head* against transparent historical baselines; evaluate on whole-event chronological folds, test pre-registered prospectively, and preserve >=300-fight prospective promotion rule where applicable.

**Pre-existing November 21 original Stage A and Coherent Challenger are unchanged and independently frozen.** This backtest is historical analysis only; it does not retroactively create November 21 Finish-v1 selections or approval for any FanDuel bets.
