# November 17 — fully matched Reference vs historical baselines

**Status: FULL 153/153 MATCH, GitHub Actions PASS, NO MODEL PROMOTION**

Verified CI: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44195202280

## Provenance and identity audit

- The unchanged clean 153-grade Reference ledger (`data/results/clean_ufc_153_2026-11-07.csv`) was joined to the newly exported **same-fight, same-event-date** prior-only historical feature matrix and source outcomes.
- **153/153** fighter pairs matched and **153/153** decisive winner/method source labels agreed. No missing fights. No fuzzy identity guessing.
- Exactly one explicitly audited alias: **Stanley Dorsainvil** (grade ledger) is **Stan Dorsainvil** (pinned secondary source), in the Aug. 22 Gauge Young fight. Date, opponent, winner, and decision method agree in both sources. The script now fails if any of the 153 no longer align.
- **89 of 153** selections have separate original Stage A artifacts; these cover seven later dated cards but some early original artifacts do not provide complete pre-event timestamp proof.
- **41 of 153** selections span the three event dates marked as having pre-fight timestamp evidence. The first 64 are reconstructed grade rows, **not** independently verifiable historical locks.
- Artifact: GitHub Actions `wshlx-historical-feature-baselines-research`, containing paired audit `reports/model_health/2026-11-17_MATCHED_REFERENCE_BASELINES.json`, dated pre-event features, separate outcomes and benchmark results.

## Direct same-fight winner comparison

| Provenance cohort | Reference winners | Smoothed prior UFC win-rate winners | Past-only UFC Elo winners |
|---|---:|---:|---:|
| All clean 153 post-event grades (12 events) | **92/153 (60.13%)** | 83/153 (54.25%) | 82/153 (53.59%) |
| 89 later rows with separate Stage A files (7 events) | **56/89 (62.92%)** | 45/89 (50.56%) | 45/89 (50.56%) |
| 41 with pre-fight timestamp evidence (3 events) | 20/41 (48.78%) | 17/41 (41.46%) | **22/41 (53.66%)** |

This pairing repairs the earlier error of comparing models on **different** samples. Still, all the historic rows have been previously researched; the 41 timestamped picks cover just three events and are not a fresh prospective model trial. The paired whole-event bootstrap 95% percentile interval for **Reference minus prior UFC win-rate winner accuracy** on all 153 is **−1.99pp to +14.74pp** (seed 19, 1,000 draws). It crosses zero, so an advantage is not established by this test.

## Exact fighter + finish method

- Reference displayed exact method: **48/153 (31.37%)** in the complete archived grade; **33/89 (37.08%)** on later original Stage A selections; **11/41 (26.83%)** for timestamp-evidenced rows.
- Reference's *same picked fighter* but fixed 2021–25 most-common **DEC** method: **30/153**, **20/89**, **10/41** exact. Simple win-rate fighter + fixed DEC: **28/153**, **16/89**, **8/41** exact.
- Important alternative already established in the November 17 performance audit: a **fixed KO** paired with the Reference's same fighter yields **50/153** exact versus the displayed method's **48/153** retrospectively. Selecting KO from the *first 64* and using it on the *next 89* yielded **30/89** versus Reference's **33/89**. Therefore we cannot infer method-model superiority from beating DEC alone.
- The Reference's submission class issue persists: historical 153 actual submissions **24**; model submission calls **10**; correct submission class and exact fighter+submission both **2**. No global SUB weight boost is justified.

## Interpretation / limits

1. Simple pre-event historical win-rate and Elo probability baselines **were genuinely paired to the same 153 identities** here, but Reference **probabilities** were not available as a consistently source-timestamped comparable series across all 153. Therefore the report compares **selection accuracy and exact outcomes**, not head-to-head Brier/log loss for Reference.
2. Never cherry-pick the strong 89-row reference subset while hiding the weaker 41-row timestamped comparison. The sample and provenance differences are essential.
3. 2026 was extensively used in past model-development experiments. These results do **not** count toward an independently prospective model-challenger promotion.
4. None of this establishes FanDuel value, risk-adjusted profits, or a winning betting strategy. Stage B odds and approved selected wagers remain completely separate.
5. Source is a pinned secondary UFCStats-compatible export. No fabricated regional form, direct get-ups, time-varying reach, or future career ratings are in this first benchmark.

## Next workstream (no production changes)

Obtain a **common 41+ true original frozen probabilistic Reference/Historical/Unified prediction set** with preserved source timestamps and replay consistent winner and 6-class scoring; expand via future genuinely prospective locked fights before any model challenge. Log distinct fighter/method/timing errors, sample sizes, calibration, and event-level variability. Do not retrain just because the next card goes poorly. Existing **>=300 truly prospective observations** guard remains where applicable.

**Reference/Historical/Unified unchanged. Stage A/B locks unchanged. FanDuel gates unchanged. No promotion.**
