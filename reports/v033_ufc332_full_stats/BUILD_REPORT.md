# v0.33 UFC 332 full-stat integration

- UFC 332 full stats: **14/14 bouts, 50 fighter-round rows**
- Clean feedback ledger: **101 fights**
- Causal training rows: **8,743**
- Latest included performance date: **2026-10-03 00:00:00+00:00**
- Same-name Anthony Romero histories are separated before feature construction.

## Frozen UFC 332 prospective evidence

- Winner reference: **13-1 (92.9%)**, Brier **0.1539**, log loss **0.4830**
- Winner v0.32 shadow: **13-1 (92.9%)**, Brier **0.1542**, log loss **0.4842**
- Method baseline: **42.9%**, Brier **0.5496**
- Method calibrated: **71.4%**, Brier **0.4086**
- Method residual: **42.9%**, Brier **0.5964**
- Timing leans: **8-6 (57.1%)**

## Promotion decision

**Winner v0.32 is not promoted.** The reference still had slightly better probability quality on the frozen UFC 332 test.
**Method calibration remains the leading shadow, not champion.** It won another unseen card, but the 300-fight prospective promotion rule remains in force.
**Timing remains shadow/probationary.** Keep the 12-point edge gate, sparse-sample block and 0.25u official timing stake cap.
**v0.33 is the new full-stat data backbone for future cards.**
