# v0.34 winner interactions — clean112 diagnostic

This reruns every v0.34 ablation after integrating UFC Vegas 122 full stats.

**Governance warning:** v0.34 was designed after UFC Vegas 122 and partly from its misses. Therefore Vegas 122 is contaminated development data for these features. This report is diagnostic only and cannot promote or reselect a model.

Base: **73-39 (65.2%)**, Brier 0.227049, log loss 0.650181

## Variants

- **experience_only**: 73-39 (65.2%), Brier 0.226397 (-0.000652), log loss 0.648714 (-0.001468); retrospective gate=PASS
- **access_only**: 74-38 (66.1%), Brier 0.227024 (-0.000025), log loss 0.650236 (+0.000054); retrospective gate=FAIL
- **damage_only**: 73-39 (65.2%), Brier 0.228216 (+0.001167), log loss 0.660609 (+0.010428); retrospective gate=FAIL
- **pace_only**: 74-38 (66.1%), Brier 0.229113 (+0.002065), log loss 0.656360 (+0.006179); retrospective gate=FAIL
- **access_plus_pace**: 74-38 (66.1%), Brier 0.229230 (+0.002181), log loss 0.656738 (+0.006557); retrospective gate=FAIL
- **full**: 76-36 (67.9%), Brier 0.229373 (+0.002324), log loss 0.666636 (+0.016455); retrospective gate=FAIL

Best retrospective Brier on clean112: **experience_only**.

No production or shadow-selection change is authorized from this rerun. The previously selected experience-only shadow remains the tracked v0.34 candidate until genuinely future frozen-card evidence accumulates.
