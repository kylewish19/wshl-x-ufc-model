# Historical handoff — 2026-09-15

This document preserves only the recoverable high-level state transferred into this repository.

## Clean current-model UFC sample

Through UFC Paris on September 5, 2026:

| Metric | Record |
|---|---:|
| Winner | 36-28 (56.3%) |
| Displayed method | 28-36 (43.8%) |
| Winner + displayed method | 15-49 (23.4%) |

Displayed method calls across the 64-fight clean sample:

- Predicted: 37 DEC / 25 KO / 2 SUB
- Actual: 21 DEC / 31 KO / 12 SUB

This supports a real submission-recall / decision-heavy concern. The response is **not** to force more submissions. The research target is to improve conditional access and finishing-pathway features.

## Paris timing snapshot

Directional grades recorded in the handoff:

- round totals: 33-11
- goes distance: 8-6
- round starts: 20-10

These are correlated market observations across 14 fights, not 64 independent wagers and not a profitability claim.

## v0.26 status

A prior workspace reportedly executed a v0.26 experimental residual method challenger, tests, and replay. Final archive saving and master-audit writeback were not completed and the workspace was later removed.

Therefore this repository does **not** claim to possess or reproduce the old trained v0.26 package. Any rebuild must get a new version/hash unless exact artifacts are later restored and verified.

## Preserved research lessons

- access before weapon
- distinguish takedown attempts from successful access/control
- account for opponent get-ups and counter-grappling
- model offensive-wrestling exposure that can create neck/back/scramble danger
- distinguish attempted volume from durable control
- track KO, SUB, and DEC recall separately
- do not use result labels as retroactive prefight features
- do not rewrite old locks after grading
