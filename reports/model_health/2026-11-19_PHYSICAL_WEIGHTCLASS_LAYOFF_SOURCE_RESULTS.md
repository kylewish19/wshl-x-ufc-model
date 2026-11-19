# Nov 19 — Source-hashed UFC DOB, reach/height, same-division and layoff research

**Result: TRUE new data fields assembled and year-fold tested. STILL NO model promotion.**

GitHub Actions fully successful: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44433269497
Archive: `wshlx-pre-event-profile-weightclass-layoff-research`, with full `sourced_context_results.json` and `historical_context_2024_2026_forecasts.csv`.

Repository implementation:
- `src/wshlx_ufc/prefight_profile_context.py`
- `tools/audit_prefight_profile_context_2026.py`
- `tests/test_ufc_prefight_profile_context.py`
- `.github/workflows/ufc-sourced-profile-context-research.yml`.

## What source-verified new features were constructed

The PREVIOUS 101-column pre-event matrix lacked physical and specific UFC fight-context features. The **pinned 2026-11-08** third-party UFCStats-compatible secondary archive actually contains `ufc_fighter_tott.csv` (DOB, height, reach) and `ufc_fight_results.csv` (historical per-bout division), plus dated event details.

Source SHA256:
- Fighter `ufc_fighter_tott.csv`: `3296e67941f984cd5484488226e5a5d94de3249c63fe289fbc66d98546311ea1`.
- Historical `ufc_fight_results.csv`: `b99d94a82984f07ec34d9f04423fd7edd67ea28d6d320a8da` — **CAUTION:** This visible string may be malformed; the executable report's **own** SHA256 is the authoritative source identity; inspect `sourced_context_results.json` rather than hand-copied text.
- Event and feature source hashes checked against `data/raw/ufcvegas124_2026-11-07/availability.json`; any mismatch stops the code.

Current fight-day weight class is known BEFORE the bout; previous same-class UFC bout count, days since previous UFC fight, and previous-year UFC appearances are computed by source fighter identities with strict whole-calendar-day snapshot (no current opponent/result or same-day result leakage). Date-of-birth permits age-on-fight-date computation; fighter height and reach were observed in **2026 profile snapshots**, not shown to have been sourced with versioned historic dates, so their retroactive use is tagged **historically unverified for revision/availability**. Current profile `WEIGHT` is deliberately **not** treated as past fight division.

All **3,036** modern bout identities joined to specific bout-source records; 0 unmatched. 2026: both fighters had age measured 443/492, both reach 377/492; full historical UFC layoff 382/492, same-weightclass prior counts 492/492 (zero prior same-class bouts for new fighters is a valid count, not missing performance). 1997 UFC Japan Sakuraba–Silveira source pair appears twice on one day; research's date+pair key cannot distinguish both bouts and therefore **quarantines** the ambiguous historical key. Independent historical reporting supports a genuine same-night rematch: https://www.mmafighting.com/2017/7/6/15831082/the-story-behind-kazushi-sakuraba-first-and-only-night-in-the-ufc . This is NOT evidence of a source fabrication. None of the modern 3,036 bout keys were lost.

No regional/cross-promotion scores, injuries, time-varying reach, actual get-up counts or video-derived metrics have been invented.

## Factorized exact fighter+method: 2024, 2025, already-inspected 2026

| Historical folds | Old 38 fields | + prior same division and layoff | + DOB age | + 2026-snapshot height/reach |
|---|---:|---:|---:|---:|
| 2024, 511 decisive | **169** | 172 | 175 | **182** |
| 2025, 513 decisive | **170** | 166 | 175 | **185** |
| 2026, 488 decisive | **145** | 145 | 138 | **136** |

2026 direct-six model baseline **143** exact; adding source context **145**, age **145**, and then height/reach **147** exact. But 2026 direct-six six-state log loss becomes significantly **worse** after adding physical data (1.6296 baseline → 1.6718 with full profiles). Cannot call this a uniformly better model.

Winner accuracy in 2026 *did* increase when adding all physical/context fields to factorized model: **293/488 to 301/488** winners, while exact winner+method declined **145 to 136**. Thus a winner improvement is insufficient and these new variables are not yet safe.

2024 and 2025 factorized full-profile six-class log loss improves (2024 1.6077→1.5767; 2025 1.6065→1.5605), but the 2026 result worsens (1.6360→1.6483). No model version demonstrates replicable improvement across all three historical periods.

## Why there is no promotion

1. The user's primary target is exact fighter+method, 60–70% full-card aspiration. Best of the evaluated factorized research models remains 27.9–36.1% exact; nowhere near goal, and highest historical year isn't an unseen sample.
2. Physical-profile values used for older fights are back-calculated from a 2026 secondary archive; DOB is largely invariant, but height/reach are not independently source-timestamped per historic fight. Many 2026 debutants lack full reach metadata; missingness may be nonrandom.
3. Results are **three previously studied retrospective periods**, not fresh prospectively registered estimates and not a bet-side comparison to locked Historical/Unified on all 1,512 fights.
4. Adding complexity often boosts winner Brier or historical log loss while **degrading actual exact winner+method picks**, contradicting project success criteria.
5. One hard-coded top-2-to-5 selection consensus policy tested separately performed poorly in 2025–26. No bets are authorized by these historical experiments, and no 100% perfect group is promised.

## Next specific work (not yet completed)

- Inspect 2026 error strata for physical-profile missingness, rookies/debutants, weight-class switch and fighter age; compare a date-verifiable `prior_same_weightclass/layoff` branch separately from retrospective physical attributes.
- Obtain verifiable **pre-fight-era** profile height/reach or explicitly restrict them to research without claiming old timestamp provenance.
- Strengthen new winner+method joint optimization on paired event folds and test a previously frozen Historical/Unified benchmark; compare exact selections and proper six-class scores.
- For the 2–5 picks, consider a pre-registered selectively trained correctness gate on pre-event model probabilities and evidence coverage, using **past** event labels only; test prospectively, abstain when support is low.
- Keep November 21 Reference/Historical/Unified Stage A and the pre-event Coherent Challenger **unchanged**; don't manufacture past pre-event predictions for new models. Minimum 300 truly prospective observations remains a promotion guard, not a waiting period before research.

**Outcome:** New feature data and code were successfully generated and audited, but the challenge of exact winner+method is NOT fixed yet. Nothing here implies FanDuel edge or 60–70% exact card performance.
