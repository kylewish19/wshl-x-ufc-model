# UFC Vegas 122 — v0.34 winner challenger decision

After the UFC Vegas 122 miss audit, we tested several new winner-model feature groups using chronology/out-of-fold evaluation on the 101-fight clean sample through UFC 332.

## Baseline

- Accuracy: **67-34 (66.34%)**
- Brier: **0.22175**
- Log loss: **0.63793**

## Candidate ablations

| Variant | Accuracy | Brier | Log loss | Decision |
|---|---:|---:|---:|---|
| pace only | 68-33 (67.33%) | 0.22275 | 0.64196 | FAIL |
| grappling access only | 68-33 (67.33%) | 0.22207 | 0.63886 | FAIL |
| damage/reach interactions only | 66-35 (65.35%) | 0.22439 | 0.65200 | FAIL |
| experience-gap only | 68-33 (67.33%) | **0.22169** | 0.63799 | FAIL |
| access + pace | 68-33 (67.33%) | 0.22301 | 0.64274 | FAIL |
| full interaction bundle | **70-31 (69.31%)** | 0.22420 | 0.65519 | FAIL |

The promotion gate requires non-worse accuracy **and** better Brier **and** better log loss. None of the candidates cleared all three.

## Interpretation

The full interaction bundle gained three correct winner calls historically, but its probability quality worsened substantially. That is not acceptable for a betting model because being more right at the 50% classification threshold while becoming more overconfident/miscalibrated can create worse pricing decisions.

The damage/reach interaction block was especially poor and should **not** be added to the production winner model based on the Fili-Kamaka result.

Pace and grappling-access features each added one historical correct call, but both slightly worsened Brier and log loss. They remain development ideas rather than production features.

The log UFC-experience-gap feature was the closest candidate: 68-33 with a microscopically better Brier, but log loss was slightly worse. It therefore also fails the promotion gate. The generated v0.34 artifact is stored as **SHADOW ONLY — NOT PROMOTED**.

## Decision

**No winner-model code change is promoted after UFC Vegas 122.**

The official winner reference remains unchanged. v0.33 remains the current full-stat backbone through UFC 332. The post-UFC-Vegas-122 ideas will continue to be tracked prospectively, and we will revisit them only after future frozen cards provide independent evidence.

This is intentionally conservative: UFC Vegas 122 was a bad winner card, but the correct response is to test hypotheses and reject changes that do not improve calibration, not to force the model to explain yesterday's misses.
