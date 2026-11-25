# Nov 17 — frozen three-view probability audit

**Research only. No production model or Stage A/B changes.** CI: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44196129448. Artifact: wshlx-historical-feature-baselines-research. Audit script: `tools/audit_frozen_three_view_probabilities.py`.

## Identity and provenance
Three original Stage A final locks on Oct 24, Nov 7 and Nov 14 contain SHA-256-linked raw three-view predictions whose timestamps precede the events. All 41 original bouts matched their final identity and verified results; one draw excluded from binary winner/method scoring, retained for timing and coherence. Edmonton is Reference-only and not included. Comparison is retrospective, already researched, not a new unseen validation sample.

## 40 decisive, 3 events
| Metric | Reference | Historical | Unified |
|---|---:|---:|---:|
| Winner hits | 25 | 26 | 26 |
| Winner Brier | .233163 | .223540 | .222212 |
| Winner log loss | .660781 | .639393 | .637177 |
| Exact own-selected fighter+method | 9 | 13 | 14 |
| Method class hits | 18 | 18 | 20 |
| Global six-cell top-pick hits | 8 | 12 | 12 |
| Six-class Brier | .820843 | .756779 | .764177 |
| Six-class log loss | 1.638220 | 1.571287 | 1.561095 |
| SUB class hits / actual 4 | 0 | 3 | 3 |
| SUB calls | 4 | 11 | 9 |

The 40 decisive fights comprise 21 DEC, 15 KO/TKO, 4 SUB. Reference called 29 KO, 7 DEC and 4 SUB. Historical called 15/14/11; Unified 20/11/9 respectively. These are model-native, own-selected-fighter methods, not actual-winner oracle results. Neither shadow is promoted.

**41-bout probability integrity:** Reference has 0 winner/joint marginal gaps >1pp; Historical 34, Unified 33 (33 and 32 respectively if excluding the draw). Maximum gaps 17.57pp and 10.23pp; no original native joint distributions repaired by this audit. Winner proper scores and six-cell proper scores are intentionally kept distinct. Direct GTD (41 bouts including draw): actual 22, expected Reference 19.29, Historical 18.17, Unified 19.01; Brier .238074/.236604/.235771. These timing differences are small.

## Same 28 decisive bouts, independent simple baselines available (Oct24 and Nov7)
| Model | Winner hits | Winner Brier | Winner log loss | Exact selected fighter+method | Six-cell log loss |
|---|---:|---:|---:|---:|---:|
| Reference |17|.239178|.670487|8|1.634801|
| Historical |20|.213633|.618106|10|1.583688|
| Unified |19|.217474|.626374|11|1.569335|
| Past-only UFC Elo + fixed method prior |16|.239443|.671762|10|1.626292|
| Smoothed prior UFC win rate + fixed prior |12|.245762|.684486|8|1.639016|
| 50/50 winner + fixed prior |N/A|.250000|.693147|N/A|1.647677|

Coinflip ties must not count as meaningful deterministic picks. Fixed method distribution is based on 2021–25 counts. No simple baseline for Nov14 was invented, since it is outside the pinned outcome feature matrix.

## Statistical interpretation
Event-cluster bootstrap (1,000, seed19) for shadow minus Reference winner Brier: Historical [-.032961,+.027528]; Unified [-.027011,+.014138], both cross zero. Unified six-cell log-loss difference [-.104328,-.028509] is descriptive only (three already-studied events, not a genuine prospective interval). Reference's exact-method weakness is evident but shadow distributions are not internally coherent. Do NOT use these results to promote a model or change any existing prop-price gate.

## Next development
Pre-register a coherent shadow probability architecture: separate winner calibration, conditional KO/SUB/DEC on each fighter, multiply conditional method by the same winner head to enforce marginal identity, compare native vs coherent model distributions and simple baselines without retroactive changes, and log prospective future outcomes. Include direct timing consistency checks. Preserve the >=300 genuinely prospective observation guard where applicable and never use this retrospective audit as new prospective evidence. No odds, wager records, original simulations or forecasts altered.

Full reproducible JSON: `reports/model_health/2026-11-17_FROZEN_THREE_VIEW_PROBABILITY_AUDIT.json` inside verified Actions artifact.
