# v0.32 UFC Vegas 121 full-stat integration

- Full event stats: **12/12 bouts, 54 fighter-round rows**
- Clean feedback ledger: **87 fights**
- Causal training rows: **8,729**
- DQ/NC and known injury-stoppage anomalies are excluded from clean performance training while activity dates are retained separately.

## First unseen v0.31 test

- Winner v0.31: **9-2 clean (81.8%)**, Brier **0.1312**, log loss **0.4371**
- Winner reference: **9-2 clean (81.8%)**, Brier **0.1309**, log loss **0.4363**
- Method baseline: **36.4%**, Brier **0.6758**
- Method calibrated: **54.5%**, Brier **0.5831**
- Method residual: **45.5%**, Brier **0.7064**
- Timing leans: **7-4 clean (63.6%)**

## Promotion decision

**Winner v0.31 is not promoted** because the reference was marginally better on probability quality despite identical accuracy.
**Method calibration is the leading shadow** after a clear prospective win, but needs more unseen fights before champion promotion.
**v0.32 is the current full-stat data backbone** for the next card.
