# UFC 333 → Vegas 124 → UFC 334: TRUE Selected-Fighter Method Backtest

**Audit date:** November 16, 2026. **Research-only experiment: NO PREDICTIVE MODEL PROMOTED.**

## Core improvement in this benchmark

Earlier method studies conditioned on the **actual winning fighter** and reported KO/SUB/DEC accuracy for that fighter. That is useful for diagnosing method probabilities but it **cannot** demonstrate correct winner-plus-method bets: we do not know who wins in advance.

This new challenger instead:

1. Loads each of three source **frozen odds-blind Stage A cards**, verifies the model-raw SHA-256 against the immutable final selection, and takes each model's already selected fighter. No post-event override or winner switch is permitted.
2. For each *predicted* fighter **and their opponent**, creates causal historical UFC opponent-strength snapshots using events strictly before that card. No current-event results, actual winners or FanDuel prices can enter model inputs.
3. Uses the original model's own six-way KO/SUB/DEC distribution conditional on each fighter winning, **combined with the separately saved model winner marginal**; the Historical/Unified original archives have known winner-vs-method marginal inconsistencies, so this is a specifically labelled *reconciled comparison*, not an overwrite of their archived original.
4. Separately fits an intercept-only finish/submission adjustment and an intercept plus opponent-quality adjustment on the **153 causal historical method-feedback examples**; at Oct 24 only the first **125** examples could train, at Nov 7 **139**, and at Nov 14 **153**, strictly prior to each date.
5. Grades the result as **exact selected fighter AND method**, as well as true six-outcome joint Brier and log-loss. Wrong fighter always means wrong exact fighter+method, even if the method class was guessed correctly. The Medić–Holland draw is excluded from six-way method losses (it has no binary winner/method state).

All three pre-event outputs were frozen at the time; these new variants were developed **after** the events, so the result is *retrospective development evidence*, not genuinely pre-registered prospective validation.

## Across 40 decisive fights (41 bouts including one draw)

| Model | Version | Exact fighter+method | 6-state Brier ↓ | 6-state log-loss ↓ | Winner correct |
|---|---|---:|---:|---:|---:|
| **Reference** | Frozen original (coherent) | **9/40** | **0.82084** | **1.63822** | 25/40 |
| Reference | Intercept only | 6/40 | 0.88842 | 1.79524 | 25/40 |
| Reference | Historical opponent-quality correction | 6/40 | 0.88940 | 1.79519 | 25/40 |
| **Historical** | Frozen original (coherent marginals) | **13/40** | **0.75924** | **1.58457** | 26/40 |
| Historical | Intercept only | 13/40 | 0.80107 | 1.67189 | 26/40 |
| Historical | Historical opponent-quality correction | 12/40 | 0.80232 | 1.67333 | 26/40 |
| **Unified** | Frozen original (coherent marginals) | **14/40** | **0.76488** | **1.56636** | 26/40 |
| Unified | Intercept only | 13/40 | 0.81626 | 1.67837 | 26/40 |
| Unified | Historical opponent-quality correction | 11/40 | 0.81733 | 1.67916 | 26/40 |

**Decisive finding:** all three models became *worse* on Brier and log-loss under the adjustment. Exact fighter+method fell 9→6 Reference, 13→12 Historical, and 14→11 Unified for the quality candidate. The intercept-only version likewise worsened/reference degraded. Their winner counts remained fixed by design.

### Per-event exact fighter+method accuracy

| Model | Event | Frozen | Intercept | Opponent quality |
|---|---|---:|---:|---:|
| Reference | UFC 333 Oct 24 | 3/14 | 1/14 | 1/14 |
| Reference | Vegas 124 Nov 7 | 5/14 | 4/14 | 4/14 |
| Reference | UFC 334 Nov 14 | 1/12 | 1/12 | 1/12 |
| Historical | UFC 333 Oct 24 | 3/14 | 3/14 | 2/14 |
| Historical | Vegas 124 Nov 7 | 7/14 | 7/14 | 7/14 |
| Historical | UFC 334 Nov 14 | 3/12 | 3/12 | 3/12 |
| Unified | UFC 333 Oct 24 | 3/14 | 2/14 | 2/14 |
| Unified | Vegas 124 Nov 7 | 8/14 | 8/14 | 7/14 |
| Unified | UFC 334 Nov 14 | 3/12 | 3/12 | 2/12 |

## Why the previous conditional-metrics improvement did not survive

On the same reconstructed 153-row *actual-winner conditional-method* dataset, intercept-only method classification had improved from 39/89 to 49/89, and opponent-quality features slightly improved Brier over intercept-only. This improvement **does not transfer** to our actual archived fighter picks. On different fighter sides, KO/SUB/DEC conditional probabilities, skill access, and current model calibration differ. Unconditionally raising finish probability produced **more wrong high-confidence method calls**.

**Therefore we reject both candidate adjustments.** Do not force extra KO/DEC selections simply because some events had many knockouts or many decisions. Do not train odds on these retrospective variants.

## What remains genuinely promising

1. **Winner+timing coherent six-state projection:** Separate research found retrospective six-way Brier and exact method improvements for historical/unified when matching both independently saved winner and pre-event timing forecasts. That is *mathematically distinct* from the failed global intercept/quality correction, and remains unpromoted pending genuine pre-event shadow locking and at least the existing 300-bout prospective promotion gate.
2. **Strength-of-opposition infrastructure:** all 153 historical training examples had exact, past-only identity matches. Even though a simple UFC Elo did not improve the current fighter+method benchmark, it remains an interpretable, leakage-safe feature for future challenger testing.
3. **Opponent-specific durability and counter-grappling:** Current datasets need better pre-fight measures of high-quality opponent knockdown resistance, defensive submissions, meaningful mat returns, get-ups per control exchange, and 3/5-round decision survival. These metrics must come from previous completed fights, not hypothetical scouting claims.
4. **Method vs timing model coherence:** Six exact fighter+method classes should reconcile with saved winner P and fight distance; still evaluate probabilistic forecasts, not just count popular method categories.
5. **Primary source verification:** UFC334's 26 fighter totals/72 fighter rounds are provisional mirrored UFCStats-derived. Do not silently admit them to official champion training before approved provenance/first-party reconciliation.

## Provenance / code

- Full data and exact metrics: `reports/ufc334_2026-11-14/SELECTED_FIGHTER_EXACT_METHOD_3CARD_RETROSPECTIVE.json`
- Original selected-fighter research (no grade writes): `src/wshlx_ufc/predicted_side_method_shadow.py`
- Read-only benchmark runner: `tools/run_selected_fighter_method_shadow.py`
- Model/locked-card tests: `tests/test_ufc_predicted_side_method_shadow.py`
- Verified CI run: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/43987572406
- Original 153-case actual-winner quality benchmark: `reports/ufc334_2026-11-14/QUALITY_AWARE_METHOD_153_7FOLD_RESEARCH_RESULTS.json`

**Governance: same Reference champion, Historical/Unified shadows, Stage A odds-blind freeze, Stage B FanDuel-only gates, and pre-existing exact bets and frozen odds. No model or bankroll assumptions changed.**
