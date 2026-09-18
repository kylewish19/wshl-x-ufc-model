# Recovery completion receipt — 2026-09-18

This receipt closes the three recovery tasks carried forward from the September 15 UFC handoff.

## 1. Latest learned challenger rebuilt as a new verified revision

The exact lost v0.26 binaries were not recovered and are not being relabeled.

Instead, the documented v0.26 residual-method architecture was rebuilt as **v0.27-reconstruction** and executed in GitHub Actions from a pinned data source. The resulting artifacts are committed under `artifacts/v027_reconstruction/`.

Status: **trained shadow / reconstruction only — not promoted**.

Artifact SHA-256 values:

| Artifact | SHA-256 |
|---|---|
| Winner reconstruction | `fb08125a96791dc332b024c896db64f39b90cb998ce777dd859a60afb638b7c0` |
| Method baseline reconstruction | `91cc68aa269b766958c3a67e4466ebf1e4fe0d3561fa052fab57fce5d10e365e` |
| Method residual v0.27 | `9f8d43e6c10eca6e23acf036ac064b2196986624a869d446ed41bfc41c643f12` |
| Timing reconstruction | `90bd9a3802b75956fb856d70cd402f99b1588be2a75bcd9883192bf16c2268be` |

The reconstruction is intentionally a new revision because a summary and old hashes cannot reproduce the lost v0.26 binaries byte-for-byte.

### Retrospective reconstruction benchmark

Across the 52 clean fights that can be evaluated with earlier clean cards as feedback:

| Metric | Reconstructed baseline | v0.27 residual challenger |
|---|---:|---:|
| Accuracy | 38.46% | 38.46% |
| Multiclass Brier | 0.664379 | 0.702834 |
| Log loss | 1.057470 | 1.104844 |
| SUB calls | 1 | 3 |
| SUB recall | 11.11% | 11.11% |

The v0.27 residual challenger **does not outperform its reconstructed baseline** on probability quality. It therefore remains a shadow and receives zero promotion credit.

This does not contradict the recorded lost-v0.26 result; the feature formulas and reconstructed baselines here are not byte-identical to the missing old package.

## 2. Fighter-performance feature history brought current

The old recoverable UFC feature feed contained **8,630 decisive fights through August 1, 2026**.

The new causal rebuild contains **8,707 decisive UFC fights through September 12, 2026**, an exact **+77-fight** post-August-1 extension.

The 77 new prefight snapshots are committed as:

- `data/features/reconstructed/prefight_winner_features_2026-08-02_to_cutoff.csv`
- `data/features/reconstructed/prefight_method_features_2026-08-02_to_cutoff.csv`

Their SHA-256 values are:

- winner features: `d63ea664f871e39281b8af7e893c2659c7f149d2fe40109607ca8cacd46a445d`
- method features: `c48f6440033f59e30ff52ab907117b1fe4618a2f9116c8ca970432abc41691f1`

Every target-event feature snapshot is built only from earlier event dates. All fights on the same event date are frozen before any result from that date updates fighter history.

Upstream UFCStats-derived data are pinned to:

`Greco1899/scrape_ufc_stats@cb4ecb64dd62324a7a51a378f6b5bbb0fc99bc65`

This makes the recovery reproducible instead of depending on a mutable live scrape.

## 3. Historical record consolidated in GitHub

The clean 64-fight machine-readable ledger is committed at:

`data/results/clean_ufc_64_2026-09-05.csv`

Automated tests enforce the preserved handoff totals:

- 64 fights
- winner: 36-28
- displayed method: 28-36
- winner + displayed method: 15-49
- predicted methods: 37 DEC / 25 KO / 2 SUB
- actual methods: 21 DEC / 31 KO / 12 SUB

The append-only master audit through Paris is:

`docs/MASTER_UFC_RECORD_AUDIT_2026-09-18.md`

It preserves the August 23 audit, Shanghai delta, Paris delta and Paris Stage A lock hash without rewriting old predictions.

## Current governance state

Historical official/champion roles remain preserved as:

- winner: **v0.3.1**
- conditional method: **v0.4.0**
- round/timing: **v0.3.1**
- v0.18 timing: retained historical shadow research
- v0.27-reconstruction: **current reconstructed shadow**, zero prospective validation fights

No reconstructed model is promoted automatically.

The next prospective UFC card should create a fresh odds-blind feature snapshot and prediction lock, run the configured model layers and simulations, then wait for prices. After the event, grading may create another challenger revision if the evidence supports a change.
