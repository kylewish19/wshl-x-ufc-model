# UFC 333 — official-stat integration, method-model investigation, and code decision

Event: **UFC 333: Volkanovski vs Evloev**, October 24, 2026  
Audit date: November 6, 2026  
Branch: `feature/historical-conditional-rates` (**not main; no production promotion**)

## Source provenance and completeness

- UFCStats fight, fighter, and per-round statistics are preserved from **Greco1899/scrape_ufc_stats commit `5d6622ffc349a1d0c6dd25158d737a96b889a3e0`**, the October 25 data refresh.
- Official UFC event page/scorecards and the original frozen stage-A grade are cross-checked for 14 bouts.
- **14/14 results, 14/14 fight-detail records, 14/14 fights with stats, 62/62 fighter-round rows, 28 fighter-bout aggregated rows; no result/round-key mismatches.**
- Raw source hashes, event extracts and UFCStats fight-detail links: `data/raw/ufc333_2026-10-24/availability.json`.
- Per-fighter stat sums for all 14 fights: `data/results/ufc333_2026-10-24_fighter_fight_stats.csv`.

## Immutable frozen-card grading

- Official reference winner: **8/14 (57.1%)**.
- Historical conditional winner shadow: **9/14 (64.3%)**.
- OOF-unified winner shadow: **8/14 (57.1%)**.
- Reference confidence postures: **SIDE 3/4**, **LEAN 2/4**, **PASS projections 3/6**. Passes are not bets.
- Frozen reference-side **top conditional method**: **6/14 (42.9%)**; exact reference side + selected-side method: **3/14 (21.4%)**.
- Separately, the UFC333 grading file scores the model's **unconditional finish-class output** at **7/14**. This is a different target than selected-side conditional method and must not be substituted in the 139-row `displayed_method` history.
- Only promoted method on the card, **Yakhyaev by submission**, missed: Yakhyaev won via R1 TKO. No official UFC333 Stage B FanDuel card is on record, so no units or ROI may be assigned retroactively.
- UFC333 results were added for *future* training only **after** this frozen grade was saved; no pick was flipped.

## Longer-run method weakness is real, but not a one-direction global fix

The 125 previously graded clean fights have archived *displayed* method picks from multiple evolving model versions. Across them:

| Class | Actual | Frozen displayed calls | Correctly identified actuals |
|---|---:|---:|---:|
| KO/TKO | 68 | 64 | 42 |
| Submission | **22** | **7** | **2** |
| Decision | 35 | 54 | 20 |

- Submission recall: **2/22 = 9.1%**. The model often recognizes fight-ending potential yet mislabels the actual submission route.
- UFC333 selected-side classes: **8 KO, 2 SUB, 4 DEC calls**, versus **6 KO, 1 SUB, 7 DEC** outcomes; **6/14** classes correct, **0/1** true submission recognized.
- Across 139 graded fights, the mixed-version **displayed-method** record is **70/139 (50.4%)** with **2/23 (8.7%)** submission recall. This is a *tracking ledger*, not the prospective performance of a single frozen method-model version.
- Earlier cards showed excess decision calls; UFC333 showed an excess of KO calls in the current calibrated class probabilities. Therefore **do not apply a blanket KO-to-DEC adjustment**. Diagnose *fight-level localization* and conditional fighter-specific method, not merely the card's aggregate distribution.

## Official UFCStats diagnostic cases (post-fight interpretation only)

These rows justify research questions, **not** hindsight feature updates to UFC333:

- **Vagaev–Malkoun**: Malkoun landed **106** significant strikes to Vagaev's **71**, but Vagaev completed **6/12 takedowns**, Malkoun **0/4**. The reference's Malkoun SIDE was wrong. Test *effective grappling access vs high-volume striking* in a future winner challenger; small UFC samples remain important.
- **Volkanovski–Evloev**: Volkanovski landed **56/110** significant strikes, Evloev **40/65**. Evloev achieved **3/7 takedowns** but only **0:46 control**; Volkanovski **1/2 takedowns, 1:44 control**, and TKO R2. This distinguishes landing takedowns from maintaining control and defending dangerous counters.
- **Yan–Merab**: The pinned snapshot shows Merab **5/58 takedowns** and **1:54 control**, versus Yan **0/1 and 0:23**. Yan won a five-round decision. Mere takedown attempt volume is not equivalent to winning effective sequences; investigate completion/retention and opponent defensive response.
- **Abus Magomedov–Rowston**: Rowston completed **1/1 takedowns**; Magomedov attempted **one submission** and won by **R1 guillotine technical submission**. A counter-submission can occur despite the winning fighter having zero takedowns. Test counter-submission exposure rather than offensive takedowns alone.
- **Yakhyaev–Krylov**: Yakhyaev recorded both **a submission attempt** and **a knockdown**, but the decisive result was **R1 TKO by knee**, not the official predicted submission. Submission access does not guarantee submission as the finishing method.
- **Dawson–Aliev**: Dawson **5/7 takedowns**, **6:18 control** and won DEC; the official reference Dawson side was correct against both shadow winners.

**Methodology:** These stats are observed *after* fights. Pre-fight training must build each fighter's historical aggregate using only bouts before the target date. No full-fight tape playback was performed for this audit.

## Causal data integration

- Updated versioned, append-only clean history from **125 to 139**. Original 125 rows are unchanged.
- Full historical model-backbone population: **8,781 fights through 2026-10-24**.
- After grading, fitted **future-only SHADOW** winner, conditional-method baseline, method calibrator, residual, and 30-second timing models. Saved hashes and manifest in `artifacts/ufc333_post_event_shadow/manifest.json`.
- Applied prior Anthony Romero same-name separation and Kai Kamaka III alias reconciliation.
- Every method baseline for the clean feedback sample is reconstructed using performance rows *strictly before* the evaluated event date.
- Permanent regression tests cover official-source cardinality, original ledger immutability, chronological training dates, per-row probability conservation, and non-promotion governance.

## Real challenger benchmarks (lower Brier/log loss is better)

**Previously designed submission-access correction**: four access features and offset logistic SUB-vs-KO head; designed before UFC333 after Edmonton, so UFC333 is a genuinely later event for *design*, but its rebuilt method baseline is still a retrospective reconstruction.

| Model | Walk-forward 115 accuracy | Walk-forward Brier | UFC333 14 accuracy | UFC333 Brier |
|---|---:|---:|---:|---:|
| Reconstructed baseline | 47/115 (40.9%) | 0.6413 | 6/14 (42.9%) | 0.6607 |
| Intercept-calibrated | **59/115 (51.3%)** | **0.5822** | 6/14 (42.9%) | 0.7286 |
| SUB-access correction | 56/115 (48.7%) | 0.5955 | 5/14 (35.7%) | 0.7567 |

Access improved some historical SUB recall but degraded Brier and log loss and was **not** more accurate on UFC333. **Reject promotion.** Report: `reports/ufc333_2026-10-24/full_stats/method_walk_forward_comparison.json`.

**New v0.35 finish-vs-decision access correction**: logistic offset to calibrated *finish probability*, preserving the calibrated conditional KO-vs-SUB split. Features: recent finish rates, winner knockdown pressure, opponent damage exposure, winner submission attempts, opponent submission exposure, scheduled five rounds. **Designed after UFC333: all retrospective development only.**

| Method | 115-fight accuracy | 115-fight Brier | UFC333 accuracy | UFC333 Brier |
|---|---:|---:|---:|---:|
| Intercept-calibrated | 59/115 (51.3%) | **0.5822** | 6/14 | **0.7286** |
| v0.35 finish-access | 59/115 (51.3%) | 0.5937 | 6/14 | 0.7660 |

No accuracy improvement and worsened Brier/log loss. **Reject promotion and do not use v0.35 in the live card.** Code and full test results are archived at `tools/benchmark_method_finish_access_v035.py` and `reports/post_ufc333_method_finish_access/diagnostic.json`.

## Code decision / next research tests

**Implemented and retained:**
1. Pin and hash the first post-event official-stats scrape, verify all 14 results and all 62 fighter-round rows, retain original raw and per-event rows.
2. Append clean139 without rewriting clean125 or the frozen UFC333 Stage A/grade.
3. Refresh causal 8,781-fight backbone and train versioned post-UFC333 shadow artifacts.
4. Run chronology-controlled method comparisons, explicitly separating *selected-side conditional method*, *unconditional method class*, and *actual-winner conditional diagnostic*.
5. Add automatic regression tests for source integrity, chronology and non-promotion.

**Not justified:**
- Promoting historical/unified winners from one 9–5 event.
- Promoting a new submission-access correction just because it calls more submissions.
- Promoting v0.35 finish-vs-decision correction.
- Blanket increase/decrease in DEC or KO prior probability based on UFC333 alone.
- Retrofitting pre-event stage-A probabilities or calculating a nonexistent Stage B P/L.

**Next defensible challenger hypotheses to pre-register and collect prospective evidence for:**
1. **Counter-submission danger on opponent shots:** winner historical submission initiation **interacting with opponent takedown pressure and poor control retention**. This is *distinct* from rewarding the winner's offensive takedown rate alone; access can come from defending an opponent's shot.
2. **Effective grappling conversion:** takedown attempts, completed takedowns, control retained per successful takedown, get-ups and counter-grappling against the opponent's offensive style. Keep all inputs as-of their respective prior fights; do not leak new UFC333 stats into past predictions.
3. **Method-label reliability gate:** measure fighter-specific conditional KO/SUB/DEC calibration on frozen future cards before accepting an exact method official wager; protect against the Yakhyaev-type SUB-versus-KO error without chasing one event.
4. **Event-condition sensitivity:** check whether 3-round versus 5-round, weight class, and sparse UFC sample alter class calibration consistently across multiple future cards rather than explaining UFC333's seven decisions with hindsight.

Promotion still requires **at least 300 newly locked prospective fights**, better Brier and log loss, no unacceptable collapse in KO or DEC recall, real submission recall improvement, and explicit governance approval. Every candidate remains a shadow until that evidence exists.

**Outcome:** UFC333 has been completely integrated and graded; **no new predictive model deserves promotion on current evidence**. The code and data engineering improvements are real, executed and CI-tested.
