# Nov20 — verified prospective selection and profitability audit: initial implementation

**Current run:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44758880936 — GitHub CI **SUCCESS**, 19 passed tests, 12 frozen bouts checked, all six previous-source checksums preserved.

### What's been built, rather than promised

1. `src/wshlx_ufc/forward_validation_v1.py`: exact winner+method six-state result scoring, winner vs class split, log loss and Brier; protects 50/50 numerical tie; no outcome inferred from unknown/pending results.
2. `prospective_calibration_history`: requires same registered model and previous pre-event locked + independently verified bout results; rejects future event leakage or duplicate opponent identity; 95% Wilson lower reliability bound per probability bin.
3. `research_selection`: 0–5 only (never forces 2–5); fighter-ID and late provisional quarantine; min 300 previously prospective observations + 50 same probability-bin observations + Wilson lower bound >=55% for RESEARCH eligibility. No special guarantee of 100% accuracy or validated profitability from those thresholds.
4. `fanduel_price_audit`: ONLY **verified and evidence-referenced FanDuel** timestamped quotes matching fighter/method market, both original and screenshot/document source checks, uses prospective conservative probability lower bound for fair price, edge and unit EV. **Never authorizes actual bet from a research-only model**. Reuses existing Stage B for actual tracked approved wagers.
5. `grade_selected_card`: counts actual W/L/VOID/PENDING, exact-rate and *all picks right* for previously locked eligible 2–5 groups. Never counts pending/VOID as victories.
6. `tools/audit_ufcqatar_forward_selection_readiness.py`: independently verifies exact original Stage A SHA and v7 original source hash, frozen fighter order, date before event, and reports every matchup with quality and abstain reasoning.
7. Tests `tests/test_ufc_forward_validation_v1.py`, `tests/test_ufc_qatar_forward_readiness_v1.py`, plus existing selection gates. CI `.github/workflows/ufc-forward-selection-v1-audit.yml` saves timestamped readiness JSON in workflow artifacts.

**Nov21 12-bout audit outcome:** 12 research rows reviewed, **zero legitimate new selected exact bets**, zero new official Stage B approvals; genuinely prospective prior v7 graded records = **0** today; at least one fighter identity remains unverified, including Lorenz and late Mitchell/Yousaf. Historical 2024–2026 backtests must NOT be relabeled as new prospective evidence. No original picks, methods or timing predictions changed. This is proper abstention, NOT proof the favorite/pick is wrong or model has zero predictive information.

**Why zero:** The newer direct-six v7 model has not demonstrated calibrated exact success on 300 NEW independently locked/verified bouts. Its nominal 79.8% Nurgozhay KO exact P (with unverified Lorenz identity) is numerically high but not credible as a verified betting edge. Stage B cannot be opened using a fabricated FanDuel quote or an unverified calibration threshold. The new system does not claim a 70% winner+method rate.

### Next source-evidence actions

- November 21 event: after genuine results, grade previously independently frozen original Reference/Historical/Unified, Coherent, v3 Winner, v4 Winner, v5 Method, direct-six v7 on identical unique decisive bouts; grade public video picks as a DIFFERENT ledger if user wants, not as model backtests.
- Add a single cross-model prospective scoreboard (winner rate, conditional method given winner, six-class proper scores, exact hits, subgroup source quality) as more official grades become available; record a small selected exact strategy with explicit abstentions.
- Require VERIFIED FanDuel prices, market identity, timestamp and archived source before evaluating or tracking return; use actual settlement data and separate hypothetical 1-unit simulations from real approved wagers.
- Workstreams and release gates in `docs/WSHLX_UFC_PERFORMANCE_RECOVERY_PLAN_2026_11_20.md`.
- No automatic background monitoring, no model promotion, no unsourced 2–5 exact locks or 70% performance claims.

**Code branch:** `feature/historical-conditional-rates` on `kylewish19/wshl-x-ufc-model`. Champion and Nov21 source files remain frozen.
