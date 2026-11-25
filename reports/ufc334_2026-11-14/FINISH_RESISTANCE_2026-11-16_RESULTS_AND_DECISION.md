# November 16 — Finishing Resistance and Grappling-Defense Research

**WSHL_X UFC model research branch** `feature/historical-conditional-rates`

## Decision

**Reject the current resistance-aware method adjustment.** It did not improve exact predicted fighter + victory method or proper six-way probability scoring. Keep the new historical feature code as a versioned research resource, NOT a champion model update or odds gate input.

This conclusion comes from an actual selected-fighter method backtest, not from a known-winner conditional prediction score.

## 1. Historical fight/stat coverage and usable features

An internally checksum-verified, pinned *third-party UFCStats-compatible archive* through **November 7, 2026** supplied:

| Metric | Count |
|---|---:|
| UFC bouts processed | **8,871** |
| UFC bouts with both fighters' recorded statistics | **8,850** |
| Individual fighter-stat rows missing | **42** |
| Historical fighters encountered | **2,773** |
| Prior knockdown-absorbed bouts not lost by KO | **1,268** |
| Prior opponent submission-attempt threat exposures | **4,266** |
| Legacy round-format discrepancies flagged | **27** |

For a *retrospective pre-event November 14 query* covering UFC334's 13 original matchups, **25/26 fighters** had prior UFC statistics and **20/26** had prior exposure to opponents classified by their *then-existing* UFC finishing record.

We added pre-fight, date-lagged indicators of:

- Previous KO and submission losses per prior UFC bout (sparse-sample shrunk).
- Opponent-credited knockdowns absorbed per 15 minutes and the share of prior knocked-down bouts not ending in KO defeat.
- Previous submission attempts faced and the share of such bouts without a submission loss.
- Previous opponent control time, including >=60 seconds of conceded control and whether those bouts ended in a submission loss.
- Actual takedowns faced / allowed, shrunk takedown-defense rate, and prior UFC stat sample coverage.
- Prior bouts against fighters who already had an established UFC finishing record **at the time of that earlier fight**, with survival statistics.
- Previous KO, submission-attempt, and takedown offense rates, measured only in earlier completed fights.

**Definitions matter:** UFCStats REV is not an independent get-up count, and conceded control does not prove a fighter returned to the feet. There is **no direct observed get-up count** in this dataset. We did NOT fabricate one, substitute it with reversals, or claim a full-fight tape review.

All contemporaneous fights on the same calendar date use features frozen **before that date**. Neither future fight results nor the actual UFC334 performance stats are permitted into pre-event predictors. The incoming fighter card can be queried without fake result rows.

Primary data source remains a **pinned secondary UFCStats scrape**, not a first-party live UFCStats export. The separate November 14 UFC334 post-event mirror remains provisional and excluded from this archive.

## 2. True selected-fighter retrospective method benchmark

The three locked odds-blind Stage A cards from October 24 (UFC333, 14 bouts), November 7 (Vegas124, 14 bouts), and November 14 (UFC334, 13 bouts) provided **40 decisive fight outcomes plus one majority draw**.

Each model's originally selected fighter and fighter-win probability were frozen and unchanged. Both fighters' pre-event stats were reconstructed before selecting the candidate conditional finish method. Method calibration trained strictly on the first **125, 139, and 153** *previous* causal method examples respectively. Outcomes of each test event were labels only, never inputs.

| Model | Version | Exact fighter + method | Six-way Brier ↓ | Six-way log loss ↓ |
|---|---|---:|---:|---:|
| Reference | Original coherent baseline | **9/40** | **0.82084** | **1.63822** |
| Reference | Intercept only | 6/40 | 0.88488 | 1.78611 |
| Reference | Durability/resistance challenger | 6/40 | 0.88521 | 1.78556 |
| Historical | Original coherent baseline | **13/40** | **0.75924** | **1.58457** |
| Historical | Intercept only | 12/40 | 0.79877 | 1.66633 |
| Historical | Durability/resistance challenger | 12/40 | 0.79958 | 1.66688 |
| Unified | Original coherent baseline | **14/40** | **0.76488** | **1.56636** |
| Unified | Intercept only | 13/40 | 0.81344 | 1.67148 |
| Unified | Durability/resistance challenger | 13/40 | 0.81407 | 1.67149 |

The fighter-win selections therefore remained unchanged: **Reference 25/40, Historical 26/40, Unified 26/40** across these same dated samples. All changes were to research-only conditional method outputs.

A sample limitation: Historical and Unified's originally archived six-class joint probabilities do not always equal their separately saved winner marginals. For a fair comparison on a fixed original fighter-win probability, the baseline here uses original **conditional** KO/SUB/DEC proportions recombined with the saved winner marginal, just like the previous selected-fighter benchmark; it is not rewriting raw historic forecasts.

The case mix and model development are **retrospective**, not genuinely pre-registered prospective 40-fight evidence. One event has only 12 decided fights. Do not use these results to claim live ROI or adjust FanDuel prices.

## 3. Why reject this candidate?

The older actual-winner conditional method experiments had appeared to improve classification. But evaluating our *actual fighter selections* again reveals that a broad finish-rate adjustment increases six-way probability error. The newly added resistance factors did **not** overcome that weakness.

In addition, the candidate uses a small number of finish/no-finish and KO-vs-SUB features across only 153 labeled methods, with conservative ridge regularization. Many important combat attributes are missing or only proxied:

- Specific opponent caliber and fight style beyond coarse UFC finishing history.
- Individual get-up success and re-wrestling (not directly in UFCStats).
- Precise time under opponent control before a stoppage versus after a stoppage.
- Knockdown severity and whether the fighter was hurt but not officially knocked down.
- Submission attempt positions and defended submissions (attempt count alone is insufficient).
- Non-UFC/regional fighting data for fighters with sparse UFC experience.

Adding more features without credible denominators, dated provenance, and unseen validation could worsen accuracy further.

## 4. Code/data produced

- **`src/wshlx_ufc/prefight_finish_resistance.py`** — immutable-source previous-bout resistance and attack histories; true future card query; direct-getup refusal; same-day leakage guard.
- **`tests/test_ufc_prefight_finish_resistance.py`** — hand-checkable synthetic fights and a complete UFC334 original-card future query with the pinned archive.
- **`tools/audit_ufc334_prefight_resistance.py`** — reproducible full coverage audit on 26 UFC334 fighters.
- **`src/wshlx_ufc/resistance_method_shadow.py`** — retrospective original selected fighter + method, fixed winner P, date-lagged method calibration and six-way proper scores.
- **`tools/benchmark_resistance_method_selected_fighter.py`** — research-only benchmark runner.
- **`tests/test_ufc_resistance_method_shadow.py`** — winner selection invariant, method scores, pre-date features, missing stats, and no wager-approval regression.
- **`reports/ufc334_2026-11-14/FINISH_RESISTANCE_SELECTED_FIGHTER_3CARD_RESEARCH.json`** — full per-event/per-model scorecard.
- Successful original data audit: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/43988964181
- Successful retrospective resistance benchmark: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/43989338994

## 5. Next legitimate model-development priorities

1. Keep data-cleaning and prior-competition strength features, but DO NOT move the resistant-method coefficients to the champion or pricing pipeline.
2. Evaluate the separate **winner + direct-timing coherent six-way probability sidecar** on a genuinely unplayed card with a timestamped odds-blind lock; that challenger showed some encouraging retrospective arithmetic improvements, but no prospective promotion evidence.
3. Improve **method-timing consistency**, submission recall and 3- vs 5-round finish hazards with more training examples. Distinguish model calibration from top-label accuracy.
4. Seek real round-level position and get-up observation from verified tape/event providers only if legally and practically available; don't infer it from control time.
5. Preserve original Reference/Historical/Unified frozen outputs, the 10,000 simulations, FanDuel-only Stage B risk gates, independent grades and existing >=300 prospective observation promotion requirement.

**Final governance state:** no original Stage A/B file changed, no official betting pick changed, no production model or method weights promoted, no independent get-up data fabricated.
