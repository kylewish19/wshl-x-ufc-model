# Recovered model history and current status

Recovered on 2026-09-18 from the project handoff, master audit, model development reports, and frozen-card reports.

## Clean prospective grading record

The repository now contains `data/results/clean_ufc_64_2026-09-05.csv`, reconstructed from the exact current-process audit through Shanghai plus the preserved Paris grade.

Validation totals:

| Metric | Record |
|---|---:|
| Winner | 36-28 (56.3%) |
| Displayed method | 28-36 (43.8%) |
| Winner + displayed method | 15-49 (23.4%) |
| Displayed methods | 37 DEC / 25 KO / 2 SUB |
| Actual methods | 21 DEC / 31 KO / 12 SUB |

The exact totals match the September 15 continuity handoff. The ledger is a grading/history table, not a replacement for the missing historical numerical feature snapshots.

## Model registry

| Component | Status | Recovered evidence |
|---|---|---|
| Winner v0.3.1 | historical official/champion | regularized logistic; 27 prefight features; 7,597 chronological OOF rows; 61.68% historical accuracy, Brier 0.2309, log loss 0.6538 |
| Winner v0.8 | rejected shadow | tree/blend family; selected blend +0.09 pp historical accuracy; failed promotion gates |
| Winner v0.9 | rejected shadow | opponent-adjusted time-causal layer; failed required accuracy/bootstrap gates |
| Winner v0.10 | rejected shadow | sparse/debutant experience interactions; broader debutant slice did not improve probability quality |
| Method v0.4.0 | historical official/champion | conditional method baseline; exact executable binary not yet restored into this repo |
| Method v0.20 | retained shadow | hierarchical finish-vs-decision then SUB-vs-KO; 6,148 compatible rows after Shanghai append; improved finish/SUB recall but not total probability quality enough to promote |
| Method v0.21 | diagnostic/rejected | limited-UFC regional router; stage one promising in development but unstable exposed-period decision recall; stage two submission router rejected |
| Method v0.22 | rejected | timing fusion into v0.20 failed frozen gates; timing remains separate |
| Method v0.23 | data-only seed | 50 clean fights, 100 fighter-side snapshots, 300 candidate rows, 829 career evidence rows, 163 source rows; only 49/300 measured pathway rows |
| Method v0.24 | fitted shadow | coarse feedback learner; feature-limited and class balancing overreacted to small DWCS sample |
| Method v0.25 | fitted shadow | 65 feedback fights = 50 UFC + 15 DWCS; class balancing removed; stronger regularization; Paris did not have a frozen v0.25 prospective lock |
| Method v0.26 | executed then lost | Paris labels appended 65→79 feedback rows; conditional residual method challenger trained on 64 UFC fights; final files were not archived before workspace cleanup |
| Timing v0.18 | retained shadow | direct coherent survival/competing-risk layer; 8,397 eligible historical fights and 7,756 expanding-year OOF predictions; beat empirical baseline Brier/log-loss across all ten timing targets |
| Double chance v0.19 | shadow | derived probability layer; not an independent model and not promoted |

## Recovered v0.20 method result

The decision-heavy issue was tested rather than manually corrected.

Across 2,918 chronological 2018-2023 development predictions:

- finish recall: 61.13% → 63.65%
- SUB recall within finishes: 38.29% → 41.33%
- decision overcall ratio: 1.489 → 1.460
- accuracy: 53.12% → 52.98%
- log loss: 0.9495 → 0.9500

So v0.20 improved the specific class-recall problem but did not clearly improve total predictive quality. It correctly remained a shadow.

## Recovered v0.18 timing result

Historical OOF population: 7,756 predictions.

Selected examples:

- GTD Brier 0.2408 vs empirical baseline 0.2522
- O0.5 Brier 0.1057 vs 0.1078
- O1.5 Brier 0.2151 vs 0.2240
- O2.5 Brier 0.2403 vs 0.2516

Five-round samples were much smaller and must retain an uncertainty penalty.

## v0.26 recovery boundary

The old v0.26 run is not relabeled as recovered.

Known executed architecture:
- append 14 Paris labels to the 65-row feedback file;
- refit v0.25-style method C=0.10 and winner calibration C=0.25 without class balancing;
- train a conditional residual method challenger on 64 UFC fights;
- two residual heads: finish-vs-DEC and SUB-vs-KO conditional on finish;
- ridge=10;
- ten frozen statistical interaction inputs;
- train-fold imputation/scaling, missingness flags, ±5 standardized clipping;
- debutant population defaults treated as missing individual evidence;
- 20 targeted tests passed in the lost workspace.

Because the original source/binaries are absent, the repository reconstruction is named **v0.27-reconstruction**, not v0.26. No claim of byte-identical reproduction is allowed.

## Current readiness boundary

The clean grading history is restored. Model logic and governance are restored. Exact old binary artifacts and the post-August-1 numerical fighter-performance feed are not.

Do not issue a new-card prediction from a reconstructed challenger until its required prefight feature feed is refreshed and the model is actually fitted/saved.
