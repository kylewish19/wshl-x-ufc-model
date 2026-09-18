# v0.27 reconstruction build report

- Status: **V0.27_RECONSTRUCTION_TRAINED_SHADOW**
- Upstream: \`Greco1899/scrape_ufc_stats@cb4ecb64dd62324a7a51a378f6b5bbb0fc99bc65\`
- Training cutoff (exclusive): **2026-09-13T00:00:00+00:00**
- Decisive UFC fights reconstructed: **8,707**
- Latest completed event in feed: **2026-09-12**
- Clean WSHL_X feedback rows: **64**
- Post-Aug-1 prefight rows restored: **77**

## Clean-64 winner reconstruction benchmark

- Accuracy: 0.6094
- Brier: 0.242288
- Log loss: 0.681104

## Clean-card conditional method reconstruction

- Chronology evaluation fights: 52
- Baseline accuracy / candidate accuracy: 0.3846 / 0.3846
- Baseline Brier / candidate Brier: 0.664379 / 0.702834
- Baseline log loss / candidate log loss: 1.057470 / 1.104844
- Baseline SUB recall / candidate SUB recall: 0.1111111111111111 / 0.1111111111111111

## Interpretation

This is a verified **reconstruction shadow**, not a promotion and not the lost v0.26 binary.
All historical matchup features are frozen from fights dated strictly earlier than the target event.
Same-day fights are frozen together before any same-day result updates the histories.
