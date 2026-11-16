# WSHL_X — Cross-event method/winner/timing coherence challenger

**Research date:** November 16, 2026

**Status:** POST-EVENT RETROSPECTIVE SHADOW, **NOT PROMOTED**. The Reference champion and all original frozen Stage A and FanDuel Stage B records are byte-for-byte untouched. This study is a derived six-state probability analysis; it is not a rewrite of any historical prediction.

## Why this needed investigating

Historical and Unified are each composed of separately fitted/calibrated **winner**, **fighter + method** and **round/duration** components. On original archived predictions for UFC 333, Vegas 124 and UFC 334, the sum of the three 'Fighter A wins by KO/SUB/DEC' probabilities can differ from that same model's stated Fighter A win probability by as much as **17.57 percentage points** Historical and **10.23pp** Unified.

Independently, the six-method probability of **any** finish can differ from the corresponding direct timing-hazard `GTD_NO` probability by as much as **26.03pp** Historical and **32.33pp** Unified. This is structurally unsuitable for consistent betting prices, especially when trying to make moneyline + method + timing props tell the same probabilistic story.

The solution being tested is **iterative proportional fitting (IPF)** of the six existing probabilities, constrained to the selected standalone fighter win probability and, in variant B, also to the existing direct fight-finish probability. This is a *mathematical reconciliation*, not a trained prediction weight, and does not invent new information.

## Three dated pre-event snapshots; 40 decisive bouts (one draw excluded)

| Model | Projection | Six-way Brier ↓ | Six-way log loss ↓ | Retrospective exact fighter + method |
|---|---|---:|---:|---:|
| Historical | Original frozen | 0.75678 | 1.57129 | 13/40 |
| Historical | Winner-marginal only | 0.75924 | 1.58457 | 13/40 |
| Historical | Winner **and** timing | **0.74242** | **1.56474** | **20/40** |
| Unified | Original frozen | 0.76418 | 1.56110 | 14/40 |
| Unified | Winner-marginal only | 0.76488 | 1.56636 | 14/40 |
| Unified | Winner **and** timing | **0.73977** | **1.52524** | **16/40** |

Those 40 bouts are 14 at UFC 333 (Oct 24), 14 at UFC Vegas 124 (Nov 7), 12 decisive + one majority draw at UFC 334 (Nov 14). **The three events are NOT 40 independent full-card validations; projection design occurred after observing results from these events.** The historical result belongs in a research diagnostic, NOT a claim of verified prospective improvement.

The winner-marginal-only projection does not change a selected fighter's relative KO/SUB/DEC method ranking, so it did not improve the exact win + method calls. The combined winner+timing projection altered that ranking toward more decision outcomes, because the timing and method models disagree about how often fights finish early.

### Breakdown by event

| Model | Event | Original six-way Brier | Combined constrained Brier | Interpretation |
|---|---|---:|---:|---|
| Historical | Oct 24 | 0.82457 | 0.79304 | Improved |
| Historical | Nov 7 | 0.69401 | 0.68255 | Improved |
| Historical | Nov 14 | 0.75093 | **0.75321** | **Worsened** |
| Unified | Oct 24 | 0.83397 | 0.81101 | Improved |
| Unified | Nov 7 | 0.69808 | 0.67859 | Improved |
| Unified | Nov 14 | 0.75986 | 0.72802 | Improved |

**Important failure check:** Historical's combined projection worsened both Brier and log loss on UFC 334; a coherent probability model is not automatically a superior predictive model. Its 3-date sample is too small to promote a new production method estimator.

## Exact mechanics and model integrity

- **Original:** all six raw outcome probabilities unchanged.
- **Winner-only variant:** normalize A-side three outcomes to existing standalone P(A), and B-side to 1−P(A).
- **Winner + timing variant:** additionally normalize all KO+SUB outcomes (across both fighters) to the model's **pre-event direct** `GTD_NO` probability, all decision outcomes to `GTD_YES`. Alternate row/column scaling until errors are under 1e−11.
- Keeps KO:SUB odds ratios within each fighter unchanged; remains a six-way simplex with all probabilities strictly positive.
- No bookmaker prices, actual fight stats, current outcomes, or video scripts enter the projection **features or inputs**. Actual results are used **only to score it after the event**. The experiment and candidate selection themselves were chosen after examining those historical cards.
- A draw is **not** one of the six outcomes; the UFC334 Medić–Holland draw is excluded from six-way Brier/log-loss and exact fighter+method metrics.
- Original winner selections remain unchanged. Both these shadows remain **unapproved** and have no independent betting authorization or EV calibration.
- All 41 fights in each model's shadow now reconcile to the saved winner and finish probabilities within approximately `1e-12`.

## Decision and next evidence gate

**Promote neither variant now.** A new shadow for the *next unplayed UFC card* may be generated from odds-blind Stage A in parallel with all existing Reference/Historical/Unified outputs, without replacing them. Lock it pre-fight and grade **both exact fighter+method and proper Brier/log-loss**, including decision and submission recall, across a substantial prospective sample (retain the existing 300-fight prospective gate where applicable). Proper score improvement and preservation of win accuracy—not last week's apparent fixes—must govern promotion.

Source/raw/grade provenance and all 82 model-fight projection pairs:
- `reports/ufc334_2026-11-14/THREE_EVENT_COHERENT_METHOD_SHADOW_EXPERIMENT.json`
- `src/wshlx_ufc/joint_coherence_shadow.py`
- `tests/test_ufc_three_event_joint_coherence_shadow.py`

**Stage A unchanged. Stage B unchanged. No price promotion.**
