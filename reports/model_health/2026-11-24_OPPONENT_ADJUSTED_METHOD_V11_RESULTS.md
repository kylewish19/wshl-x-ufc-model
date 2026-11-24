# November 24 — opponent-adjusted finishing method v11
Verified run: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45494717295 (success; 7 targeted tests passed; all original Qatar lock checksums unchanged).

## Research
45 additional candidate-relative features: five channels (KO win, SUB win, KD, submission attempt, TD/control access), offensive and defensive historical opponent-relative residuals and exposure counts (20 per fighter), five combined attack/defense exposure proxies. Opponent exposure rates and UFC-only Elo are frozen before each historical day, and bounded Elo weights are applied at the historical meeting. These are descriptive residuals/proxies, not causal effects, calibrated opportunity probabilities, or observed get-ups. UFC-only strength does not equal worldwide strength.

Important source correction: legacy aggregate parser can coerce missing source statistics to zero. New strict access totals reconstruct only KD, submission attempts, TD landed and control from raw dated round rows; exclude ambiguous duplicate keys and incomplete per-field totals. Corrected run: 8,871 historical bouts, 2,772 name-keyed fighter histories, 17,344 complete fighter-bout records (8,672 bouts complete on both sides), 950 missing fighter-field totals, 2 duplicate raw round keys excluded. The original aggregate parser and comparator models remain unchanged; strict inputs apply to the new V11 block only. Initial run 45494466069 used less strict inputs and is superseded for V11. Regional source SHA verified and 3,016/3,036 identity-matched modern bout rows reused; 2026 source vintage can contain backfills. Earlier dates only, previous-year C tuning, fixed v3 logistic57 winner throughout. Repeatedly inspected 2024–26 cohorts, not prospective.

## Corrected matched benchmark
| Model | Exact 2024/511 | Exact 2025/513 | Exact 2026/488 | Six logloss 2024/25/26 | Exact SUB 2024/25/26 |
|---|---:|---:|---:|---|---|
| regional_v5_fixed54 |177|173|158|1.597690/1.588951/1.611080|19/15/12|
| regional54_tuned |172|182|157|1.579442/1.583747/1.606669|13/9/12|
| regional_bilateral70 |177|187|153|1.570327/1.571015/1.604674|17/13/12|
| round86 |172|177|158|1.589366/1.584341/1.609649|13/12/11|
| regional_round118 |170|183|156|1.570266/1.565560/1.591135|14/12/12|
| adjusted_UFC83 |172|171|151|1.583084/1.582333/1.609691|16/10/10|
| adjusted_full163 |167|184|151|1.569965/1.567558/1.588112|14/13/13|
| hierarchical_adjusted163 |167|183|157|1.562355/1.570524/1.589190|14/11/10|
Fixed winner hits 310/314/303. Regional bilateral 517/1512 exact vs v5 508/1512. Full adjusted163 502/1512, hierarchical 507/1512, round86 507/1512. No stable exact or submission advantage despite lower logloss. Do not promote. Full per-bout six-state forecasts, paired event bootstrap, coverage audit in CI artifact.

## Files and decision
src/wshlx_ufc/opponent_adjusted_method_v11.py; tools/benchmark_opponent_adjusted_method_v11.py; tests/test_ufc_opponent_adjusted_method_v11.py; .github/workflows/ufc-opponent-adjusted-method-v11.yml.
All original frozen forecasts and production Stage A/B unchanged. New source correction is research-only; the inherited zero-coercion issue in other heads warrants independent audit before a broader fix. Nov14/21 history extension is not yet consumed by V11, nor is a prospective V11 runner built. No new betting selections. Prioritize calibration and selection on fresh events, retain Coherent Reference/Unified, v5 and v10 as comparators, audit actual round/position coverage and test a prespecified method-only blend against strongest baselines rather than multiplying feature count. 60–70% exact accuracy and reliable perfect groups not established.