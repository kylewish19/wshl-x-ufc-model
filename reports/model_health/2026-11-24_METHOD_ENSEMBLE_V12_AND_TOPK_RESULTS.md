# November 24 — Method ensemble v12 and exact selection evaluation

Verified GitHub Actions run https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45495483749, three targeted tests passed; original frozen Qatar SHA checks passed. The corrected v11 artifact from run 45494717295 was consumed and its forecast SHA verified. No new picks or production promotion.

## Design and limitations
Six preexisting method arms: regional v5 fixed54, bilateral70, round86, regional-round118, adjusted163, hierarchical-adjusted163. All already out-of-year predictions; same v3 logistic57 winner probabilities. 2024 (511 bouts) trains ensemble for 2025 (513); 2024+2025 (1024) train for 2026 through Nov7 (488). No 2024 meta-test, no result from the target year enters its meta-weights. These years were repeatedly inspected during model development, hence not fresh prospective evidence. No Reference or Coherent probabilities were included in this historical comparison because no matched out-of-year predictions were available in the artifact. Method-only blend preserves winner marginal. Actual winner used only on earlier labeled meta-training observations to estimate conditional method distributions, never to select test winner.
- Equal blend; simplex weights optimized for conditional logloss with fixed shrinkage toward uniform; optional group weights strongly shrunk to global (80 previous records minimum); optional conditional temperature fit on earlier meta-training data. Group definition fixed by <3 prior UFC bouts, insufficient stats or observed higher submission/takedown activity, and remaining established fights. These are coarse proxies, not verified fighting styles, and no weight-class-specific model was tested. Calibration is fitted on the same earlier meta-training data as weights, not a separately fitted calibration fold; later test is held apart.
- 2026 learned global weights in listed model order: .042589/.268051/.046231/.184843/.200839/.257448; temperature .919209. 2025 weights .084074/.230829/.049033/.148758/.175195/.312111; temperature .899898.
- Top-k diagnostic: rank within each 11–14 decisive-bout historical card by probability of method for selected winning fighter; 39 cards 2025, 38 cards 2026, k=2,3,4,5. Forced top-k diagnostic only, not the prospective abstention gate or a price-approved bet.

## Matched results
| Model | Exact 2025/513 | Exact 2026/488 | Logloss 2025/2026 | Exact SUB 2025/2026 |
|---|---:|---:|---|---|
| regional v5 |173|158|1.588951/1.611080|15/12|
| bilateral70 |187|153|1.571015/1.604674|13/12|
| round86 |177|158|1.584341/1.609649|12/11|
| regional-round118 |183|156|1.565560/1.591135|12/12|
| adjusted163 |184|151|1.567558/1.588112|13/13|
| hierarchical163 |183|157|1.570524/1.589190|11/10|
| equal blend |186|155|1.566567/1.591204|12/9|
| learned global |184|154|1.565845/1.590423|12/10|
| learned group |184|154|1.565697/1.590373|12/10|
| global temperature |184|154|1.565527/1.592487|12/10|

Winner hits fixed 314/513 and 303/488. Equal blend 341/1001 vs bilateral70 and hierarchical163 340/1001. Learned weights improve proper score relative to v5 but don't improve exact totals over equal blend; neither learned group nor temperature improves exact vs global. No stable superiority over strongest component; adjusted163 better proper score in 2026. Submission exact hits worse than v5. No promotion.

## Top-k combined (77 eligible historical cards)
| k | Equal blend hits | Equal perfect cards | Regional v5 hits | v5 perfect cards |
|---|---:|---:|---:|---:|
|2|65/154|11/77|70/154|16/77|
|3|93/231|6/77|100/231|5/77|
|4|125/308|2/77|125/308|0/77|
|5|153/385|0/77|155/385|0/77|

Learned global top2 61/154, 11 perfect cards; top3 95/231, 7 perfect cards; top4 126/308, 2 perfect cards; top5 149/385, 0 perfect cards. Bilateral70 had one perfect top5 group across these 77 cards, not repeatable evidence. No model consistently identifies flawless 2–5 picks. No odds or verified ROI. Do not infer reliable win probability from forced rankings.

## Decision
Do not promote v12 or add more model arms merely to improve already-inspected tests. Preserve code, test artifact and handoff. Production Stage A/B unchanged. Next practical priority: connect vetted Nov14/21 history extension to future research runners, resolve identities, preregister limited model comparisons on genuinely upcoming events, and audit legacy missing-stat encoding. Coherent Reference/Unified first forward event remains 12 unique bouts, not a 300-bout evaluation. Keep real FanDuel settlement and price evidence separate; 60–70% exact and flawless groups not achieved. No promises of future work or guaranteed betting results.
