# v0.31 UFC 331 full-stat integration

- Full UFC 331 bouts with stats: **12/12**
- Fighter-round stat rows: **52**
- Causal training rows through UFC 331: **8,719**
- Clean graded feedback rows: **76**
- Timing bins: **30 seconds**

## Causal handling

UFC 331 round stats do not alter UFC 331's own prefight features. They enter each fighter's history only after the fight, so they affect future cards.
The prior Pantoja-Van injury stoppage remains excluded from Pantoja's performance-history aggregation while the official result remains preserved.

## Winner benchmark

- Accuracy: **0.6053**
- Brier: **0.242220**
- Log loss: **0.682050**

## Method calibration chronology

- Baseline accuracy: **0.3594**
- Calibrated accuracy: **0.4062**
- Baseline Brier: **0.660739**
- Calibrated Brier: **0.641662**

## Status

**Full UFC 331 stats integrated.** The data state is current through Sept. 19; model artifacts remain shadow until the next unseen UFC card.
