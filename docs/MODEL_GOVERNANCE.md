# Model governance

## Champion / challenger

The preserved historical champions are references only until their exact executable artifacts are restored and verified:

- Winner: v0.3.1
- Conditional method: v0.4.0
- Round/timing: v0.3.1

New code in this repository begins as a **challenger**. A challenger is not called official merely because it performs well on a recently graded card.

## Weekly lifecycle

1. Collect and timestamp prefight data.
2. Build features using information available strictly before the bout.
3. Run champion and eligible shadow/challenger models.
4. Produce and hash a frozen prediction lock.
5. Only then inspect sportsbook prices for value analysis.
6. After the event, append official results.
7. Grade every frozen prediction and probability, including passes.
8. Diagnose errors by model layer.
9. Implement only justified changes.
10. Retrain a challenger on training data ending before its validation period.
11. Compare calibration, discrimination, class recall, log loss, Brier score, and stability.
12. Commit code/data-schema changes with an explicit lesson.
13. Preserve the old model and lock.

## Leakage rules

Never use the target fight result or any post-fight information as a feature.

Historical feature rows must be reconstructed as-of the fight date. Present-day career averages may not be copied backward into old fights.

Training folds for evaluation must respect chronology. Random train/test splits are not the primary model-selection evidence.

## Odds

Odds are not prediction features in the core fight models. Predictions are frozen first. Prices may be used afterward to calculate expected value and to decide whether a supported outcome is bettable.

## Permanent UFC Stage B Top 5 + Top 5 straight-bet cards (effective 2026-11-07)

Stage B now has two independently graded FanDuel-only categories: **Top 5 Longshots** (American **+200 and longer**) and **Top 5 Best Bets** (American **−150 to +190**, inclusive). A fight may appear **at most once across both categories**, even under different methods, totals, fighters or props; maximum five eligible picks per category, never forced to five. **+191 to +199 and shorter than −150 are outside these two categories.**

Select only verified, timestamped, pre-fight FanDuel lines from the existing odds-blind frozen Stage A. Research, price, calibration, Stage A support, and market-family checks must all pass; preserve existing probability/method/timing gates. Rank gate-cleared candidates by **conservative expected value**, then edge and reliability, and enforce exclusive fight allocation across categories. **Price alone cannot flip Stage A or promote a PASS, and a new tier cannot bypass blocked method bets.**

After the card, grade W-L, units risked, net P/L and ROI for **each category separately**, with pushes/voids/pending distinguished. Recommendations are **not** evidence of actual wager placement. Three-leg parlays are optional research only, never a required Top-5 output. The new categories do **not** rewrite old official betting records.

See the executable specification and schema in [TWO_TIER_TOP5_FANDUEL_POLICY.md](TWO_TIER_TOP5_FANDUEL_POLICY.md), `src/wshlx_ufc/two_tier_card.py`, and `tests/test_two_tier_card.py`.

## One primary timing prediction per fight — new WSHL_X workflow (effective Nov 7, 2026)

Each UFC matchup must have **exactly ONE clearly named primary timing forecast** for post-card grading (rather than presenting GTD, O/U, and rounds-to-start as if all are simultaneously official picks). This is a **prediction-track slot**, NOT a requirement to gamble on that slot.

- From the **pre-fight odds-blind timing probabilities**, consider GTD Yes/No, relevant fight O/U thresholds, and Round 3 Starts Yes/No; choose the most reliable prediction based on a documented deterministic rule, using the **minimum** of the current and unified timing-model probability as an uncalibrated agreement/stress check. Both full probability vectors stay in the archive. Do not optimize based on FanDuel prices.
- Avoid automatically assigning **Round 2 Starts Yes** to every fight just because it is mechanically likely and heavily priced; keep R2 probabilities in the full data but omit the routine R2-Yes market from the *primary-pick competition* unless a different documented model design earns promotion. Other timing markets may be selected instead. Round 4/5 starts for main events remain available for full reporting but are not silently inserted into the previously fixed timing-selection menu.
- **Future cards:** predeclare and freeze a single timing market per fight in **Stage A before looking at any sportsbook odds**. The bookmaker may not offer that threshold; in that case mark PRICE UNAVAILABLE or PASS, **never retroactively substitute another timing prop** without a versioned, explicitly identified research alternative.
- **November 7 transition exception:** the Stage A file was already frozen *without one designated timing market* before the user requested this policy. A separately timestamped **pre-event Stage B research tracking file** was generated from the original frozen current/unified timing probabilities and the markets visible in the FanDuel screenshots. **It is not retrospectively claimed to be the original pre-price Stage A pick**, despite the probabilities being unmodified.
- **Stage B:** attach the screenshot's timestamped FanDuel price, then check conservative expected value, 12-percentage-point timing edge, sufficient UFC evidence, timing-vs-method family coherence and all other existing timing rules. If any gate fails, mark **MODEL FORECAST ONLY / NO APPROVED BET**. An attractive odds quote does not override this.
- **Post-fight grading:** grade exactly one selected timing event per fight independently of moneyline, method, all other forecast markets, and officially wagered timing bets. Report 14-slate accuracy, separate type breakdown, and prospective calibration / ROI only when an actual pre-event price-qualified official timing bet was recorded.
- Keep the historical raw timing probabilities for later diagnostic grading but **do not inflate the primary timing pick win count by evaluating several correlated markets and choosing the best outcome after the fact**.

For Nov 7 the audit selector is `tools/select_ufcvegas124_single_timing_picks.py` and the separately frozen tracking file is `data/locks/ufcvegas124_2026-11-07/stage_b_one_timing_forecast_per_fight.json`.

## Tape

Tape is a separately logged evidence layer. Each source must be classified honestly as one of:

- continuous full fight
- highlights
- clip
- report/statistics
- unavailable

Do not encode a full-fight-review feature when only highlights or a recap were available.

## Promotion

Promotion requires prospective evidence and explicit authorization. Historical handoff policy required at least 300 newly locked prospective fights before model promotion; that rule remains in force unless deliberately revised in a future governance commit.

## Reproducibility

Actual fight-card simulation runs must save:

- model/version identifiers
- feature snapshot ID
- code commit SHA
- random seed
- trial count
- frozen probabilities
- generated market probabilities
- timestamp

A simulation or retraining run is not considered completed unless its output is saved.
