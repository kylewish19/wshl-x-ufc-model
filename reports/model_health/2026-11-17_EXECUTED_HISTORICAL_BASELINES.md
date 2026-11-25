# November 17 — executed historical as-of matrix & transparent baselines

**Status:** GitHub Actions PASSED. Research-only baseline; NO Reference/Historical/Unified model promotion, no Stage A/B changes, no betting/ROI claim.

**Verified CI:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44193866672

## Source integrity and partitions

- Input: pinned secondary UFCStats-compatible files up to Nov 7, extracted at as-of-exclusive **2026-11-14**.
- Full history: **8,871** distinct bouts, each with pre-event features and a separately keyed post-event label.
- 2021–2025 training-label era: **2,544** bouts across **212** events; **2,527** decisive + **17** draws.
- 2026 already-inspected research era: **492** bouts across **39** events; **488** decisive + **4** draws.
- Modern-window draws: **21**, never converted into DEC wins.
- At least one UFC debutant: **458** (2021–25), **110** (2026). At least one fighter under 5 prior UFC fights: **1,563** (2021–25), **310** (2026). Prior-rate absence stays null, with debut flags; it is not false zero performance.
- Input fight-stat CSV SHA256: `f5b316d5e745bd89da921b2c9711ec9209c2fa39dcbcd80bcb063b62d9175bcb`
- Exported pre-event features SHA256: `42d8bf6d88ece5e9591e5ed532dadf146ff82fcd3b78d10d4b3ee41eb7d15a3a`
- Exported post-event labels SHA256: `4f817dfe435b6dbf3e682cbb4991d1812be8ad6fffb335ccec904cf847b9d9a8`
- The full CSV matrices and benchmark JSON are in the CI run's `wshlx-historical-feature-baselines-research` artifact.

## Frozen first-pass 2026 retrospective scoring (488 decisive bouts, 39 event clusters)

| Baseline | Winner accuracy | Winner Brier ↓ | Winner log loss ↓ | 6-class fighter+method exact | 6-class Brier ↓ | 6-class log loss ↓ |
|---|---:|---:|---:|---:|---:|---:|
| 50/50 winner + 2021–25 method prior | N/A† | 0.250000 | 0.693147 | 23.57% | 0.820547 | 1.743085 |
| Past-only UFC Elo + method prior | 56.76% | 0.246109 | 0.685341 | 23.36% | 0.818220 | 1.735279 |
| Smoothed prior UFC win rate + method prior | **60.25%** | **0.242448** | **0.677927** | **25.61%** | **0.815269** | **1.727865** |

† Coin-flip probability 0.5 does not select a unique fighter. The implementation's arbitrary A-side tie-break yields 55.33% on this particular source ordering; it should **not** be interpreted as useful coin-flip predictive performance. Use the probability metrics instead.

Event-cluster bootstrap, 1,000 resamples seed 19, **Elo minus coinflip binary Brier** 95% percentile interval: **−0.00750 to −0.000097**. This is an uncertainty description for the retrospective archive, not a prospective model improvement or market claim.

### Method prevalence shift and why it matters

| Outcome class | 2021–25 decisive training | 2026 decisive retrospective |
|---|---:|---:|
| Decision | 1,263 / 2,527 (**49.98%**) | 205 / 488 (**42.01%**) |
| KO/TKO | 817 / 2,527 (**32.33%**) | 199 / 488 (**40.78%**) |
| Submission | 447 / 2,527 (**17.69%**) | 84 / 488 (**17.21%**) |

The fixed training-era most-common method is DEC; it scores **42.01%** as a 2026 method-class-only constant. The method prior above was smoothed with one pseudo-observation in each class. **Do not add global KO/SUB boosts based on this retrospective difference.** Real selected-fighter method accuracy and calibration must be evaluated.

## Hard limitations and next locked task

- **These are simple non-trained comparators, not a new UFC champion or a simulated future card.**
- **2026 has been studied and adjusted on already.** Treat 2026 as retrospective research, never unexamined out-of-time validation.
- Reference/Historical/Unified predictions **were not evaluated against the exact same 488-bout set** here. Comparing the simple baselines' 60.25% to the historical 153-fight Reference's 60.13% is invalid (different bout sets/vintages); avoid making that comparison.
- Fighter physical metadata age/reach/height and direct get-ups are not validated as time-safe fields; this first baseline intentionally excludes them. Regional transfer strength remains unobserved.
- The next task is a **fighter-identity/date-matched Reference vs simple baseline audit** on the original pre-event frozen predictions with reliable provenance, then a truly prospective preregistered challenger. Continue honoring **>=300 new prospective observations** promotion guard where applicable.
- No historical pick locks, FanDuel real quotes, odds-blind Stage A predictions, Stage B approvals, wager records, current models or simulation weights were changed.
