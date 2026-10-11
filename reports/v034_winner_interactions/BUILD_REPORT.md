# v0.34 winner feature ablation

Created after the UFC Vegas 122 miss audit. Every candidate remains **shadow-only**.

Base: **67-34 (66.3%)**, Brier 0.2217, log loss 0.6379

## Variants

- **experience_only**: 68-33 (67.3%), Brier 0.2217 (-0.0001), log loss 0.6380 (+0.0001); retrospective gate=FAIL
- **access_only**: 68-33 (67.3%), Brier 0.2221 (+0.0003), log loss 0.6389 (+0.0009); retrospective gate=FAIL
- **pace_only**: 68-33 (67.3%), Brier 0.2228 (+0.0010), log loss 0.6420 (+0.0040); retrospective gate=FAIL
- **access_plus_pace**: 68-33 (67.3%), Brier 0.2230 (+0.0013), log loss 0.6427 (+0.0048); retrospective gate=FAIL
- **full**: 70-31 (69.3%), Brier 0.2242 (+0.0024), log loss 0.6552 (+0.0173); retrospective gate=FAIL
- **damage_only**: 66-35 (65.3%), Brier 0.2244 (+0.0026), log loss 0.6520 (+0.0141); retrospective gate=FAIL

Best retrospective Brier variant: **experience_only**.

## Governance

This is multiple-hypothesis development work performed after UFC Vegas 122. Even a retrospective PASS is not enough for promotion. The official winner reference stays unchanged; the selected candidate is stored only as a future-card shadow.
