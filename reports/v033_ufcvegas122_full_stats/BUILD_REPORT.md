# UFC Vegas 122 full-stat integration — v0.33 backbone refresh

- Canonical mirror source: `5e38ebeb9bb854c9ab4359f8f6f5b444328c555c`
- Full card verified: **12/12 bouts, 50 fighter-round stat rows**
- Decisive fights added to clean feedback: **11**
- Majority draw: **Ernesta Kareckaite vs. Melissa Gatto** — preserved raw, excluded from binary/method targets.
- Clean feedback ledger: **112 decisive fights**
- Causal training rows: **8,754**
- Latest included decisive performance date: **2026-10-10 00:00:00+00:00**
- Verified Kai Kamaka / Kai Kamaka III histories are reconciled before feature construction.

## Prospective Vegas 122 evidence

- Winner: **6-5-1**, decisive accuracy 54.5%
- Displayed method class: **8-3**
- Timing leans: **8-4**
- Stage B: **1-4**, -1.981u

## Governance decisions

- **No winner champion change.** One poor card is not enough to replace the reference model.
- **v0.33 remains the full-stat backbone**, now refreshed through Oct. 10.
- **v0.34 remains shadow-only.** Its selected experience-only shadow was refreshed on the new causal history, but Vegas 122 is not counted as validation because v0.34 was designed after the event.
- **Method calibration remains a leading shadow**, subject to the existing promotion sample rule.
- **Timing remains on probation at 0.25u max** with the 12-point edge and sparse-sample gates unchanged.
- **Sparse underdog protections remain unchanged.** Frye/Tanzilovi stay in the prospective disagreement-study track, not a new staking rule.

## Draw handling

The Kareckaite-Gatto draw is excluded from the binary winner and method targets. Its 6 fighter-round rows are preserved in the raw package. A neutral-history representation is intentionally not activated until it can be benchmarked separately, avoiding the previous failure mode of silently treating draws as losses.
