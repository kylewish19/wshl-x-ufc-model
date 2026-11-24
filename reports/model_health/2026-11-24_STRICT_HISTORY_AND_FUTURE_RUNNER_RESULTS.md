# Nov 24 — Strict historical input audit and updated-data research runner

Verified GitHub Actions: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45497258904 — success, 7 targeted tests passed, original frozen Qatar forecasts verified by SHA. No official model or bet changes.

## Actual audit
Pinned UFCStats-derived archive, 8,871 bouts:
- Legacy both-fighter complete statistical records: 8,850.
- Strict both-fighter complete statistical records: 8,672.
- 178 previously complete bouts quarantined for incomplete/invalid data.
- 2 duplicate raw round keys excluded.
- Missing or invalid reconstructed fighter-field totals: control seconds 398; KD, SUB attempts, TD landed/attempted, sig strikes landed/attempted each 184. These are field counts, not distinct bouts.
- Both-complete records with changed numeric values: 0.
- Modern pre-fight feature/form rows changed by strict adapter: 0.
- All result labels unchanged.

The strict adapter reconstructs required statistics from raw round rows and validates recorded totals against elapsed round duration. It retains each fight's result but drops both fighters from the legacy rate update if one side is incomplete; this conservative complete-case rule sacrifices partially available information. No claim that the missing-stat defect affected modern predictions: on this exact archive, the 2021–Nov7 2026 feature/form inputs were unchanged. Reason for the lack of overlap was not separately broken down by event era/fighter. Other source pipelines and models not tested here may still have data issues.

## Fixed-architecture matched comparison
Same v3 symmetric logistic57 winner and multinomial38 method, fixed C=.20. Four arms: both legacy, strict method only, strict winner only, both strict. All four generated IDENTICAL aggregate results, with matched feature/form rows and unchanged labels.

| Year | Decisive bouts | Winners | Exact | Six logloss |
|---|---:|---:|---:|---:|
|2024|511|310|168|1.604755|
|2025|513|314|169|1.601160|
|2026 through Nov7|488|303|157|1.628300|

No predictive improvement, no promotion. Reexamined historical tests, not new prospective evidence.

## Updated-data future runner
`tools/run_future_updated_history_research.py` uses the tested Nov14/21 extension directly. Default results-only history, optional Qatar secondary statistics, no UFC334 provisional detailed stats. Fit two separate legacy-input vs strict-input v3 research arms using the same 3,039 decisive 2021–Nov21 outcomes (24 additions; 8,896 total historical bouts including one added draw). Query resistance, quality and recent form from the same extended histories. Integration fixture proved both names' prior bout counts increased by one after including the late Qatar bout. Both model outputs have coherent six-state probabilities and no bet approvals.

This is a generic research runner, not migrated Reference, Coherent, Stage A/B, V5, V10, V11 or V12. Integration uses an explicitly hypothetical in-memory matchup and no actual future event lock. CLI requires a caller-checked lineup/source reference and strictly future date, checks start time, refuses overwrite, and stores lineup hash. The caller verification flag is not automatic external lineup verification; name matching alone does not establish unique fighter identity. The source vintage remains explicitly through Nov21 and must be refreshed as further events occur. The runner currently excludes same-calendar-day execution, even before first bout; no claim of a complete production-ready pipeline.

Code: `src/wshlx_ufc/strict_history_inputs_v1.py`, `tools/benchmark_strict_history_v1.py`, `tools/run_future_updated_history_research.py`, `tests/test_ufc_strict_history_inputs_v1.py`, `.github/workflows/ufc-strict-history-input-v1.yml`.

## Next
Do not chase accuracy with more backtests on the same 1,512 fights. For the next genuine future event, verify actual lineup, source freshness and fighter identities, then independently lock the existing original and Coherent arms; compare a limited set of updated research arms without overwriting official predictions. The 300-unique prospective minimum remains, Coherent has 12 unique observations. No new bets or profitability claim.