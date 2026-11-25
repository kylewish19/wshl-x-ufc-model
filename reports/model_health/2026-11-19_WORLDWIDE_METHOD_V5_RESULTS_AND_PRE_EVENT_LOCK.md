# WSHL_X UFC: independently trained world-MMA Method v5 and pre-event November 21 research lock

**Completed:** November 19, 2026. **Research only — NOT a production prediction update and NOT a validated 70%-exact model or 100%-correct bet selector.**

**Verified workflow:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44625645961 . Full code/test/compare/lock and source checks passed. Workflow artifact `wshlx-worldwide-mma-method-v5-chronological-audit` includes all date-ordered class forecasts and the independently committed prospective shadow.

### Data and identity

The exact external data version is Fight Canon public SQLite `db-2026-11-19-1934`, SHA256 `8185a2163b5f97071dbc4ec68667cceb43f5e321fadc38c26b5069303af4d949`. The source was joined through UFCStats-style event dates and **both** opponents to unique athlete IDs, not fuzzy name matches. 3,016/3,036 modern UFC matchup identities corroborated; 20 left unverified and not guessed. Many UFC debutants now have observed prior non-UFC professional records and recorded KO/SUB/DEC finishes; all are filtered to fight dates *before* the evaluated UFC event. Since this is a Nov 2026 secondary consolidated snapshot, historically delayed corrections/backfill remain a limitation.

New Method v5 conditional six-state research is *NOT* Unified or Coherent reweighting. It independently trains KO/SUB/DEC **for a candidate winning fighter**, then predicts methods for *both* possible winning fighters before the fight, with consistent six-cell joint probabilities. New 54 predictors = old as-of 38 UFC finish/resistance/opponent quality features + 16 genuine, vetted regional-pro fight-record/method features; alternative hierarchical method model also evaluated. Training 2021 up to immediately before the year tested; 2024/25/26 have all been used during project development, not pristine future performance.

### Matched paired results, fixed winner model

| Year | Winner head fixed | Prior UFC-only Method 38 exact | New regional Method 54 exact | SUB method class correct old→new |
|---|---|---:|---:|---:|
| 2024 (511) | Winner v3 logistic 57 | 168 | **177** | 12→20 of 83 |
| 2025 (513) | Winner v3 logistic 57 | 169 | **173** | 12→16 of 91 |
| 2026 retrospective (488) | Winner v3 logistic 57 | 157 | **158** | 12→15 of 84 |
| 2024 (511) | Winner v4 boosted 73 | 169 | **180** | 10→19 of 83 |
| 2025 (513) | Winner v4 boosted 73 | 187 | **196** | 12→16 of 91 |
| 2026 retrospective (488) | Winner v4 boosted 73 | **163** | 159 | 9→12 of 84 |

Full six-outcome log loss improves in all matched new-method settings tested, but exact hit improvement is small on 2026 and can turn negative with v4 boosted winner. KO/SUB/DEC method problems persist: 2026 v3+regional model identified only **15 of 84** true SUB classes. No quota-driven SUB adjustment. The absolute best cited historical full-card exact hit rate among these is **196/513 (38.2%)**, nowhere near user's 60–70% target. A small historically selected group cannot honestly be promised perfect every card.

### Genuinely NEW future card method-only lock for Nov 21

File: `data/shadow_locks/ufcqatar_2026-11-21/worldwide_method_v5_prospective_shadow.json`, **locked UTC Nov 19 2026 at 22:09:16.786617**, strictly before first bout Nov 21 at 15:00 UTC.

- **Primary preregistered research conditional-method head:** `worldwide_MMA_multinomial54`; baseline `prior_UFC_only_multinomial38` plus `worldwide_MMA_hierarchical54` are side-by-side diagnostic.
- **Winner head is FIXED to the already independently locked V3 logistic 57**. Automated CI confirms winner P(A) reproduced exactly from previously separately locked V4 diagnostic storage, and new experiment changes only the KO/SUB/DEC method conditional. No fight winner is flipped in this particular method-only study.
- All existing November 21 **Reference/Historical/Unified Stage A**, separate **Coherent Challenger**, **Winner v3 original shadow**, **Winner v4 original shadow** are immutable and referenced by SHA256. Neither official picks, betting odds, nor old grades modified. Late media-reported Mitchell vs Yousaf marked provisional PASS due to no reliable UFC/wide MMA identities.
- Only 2 of 12 fights change **method** from V3's frozen 38-feature conditional head: **Dom Mar Fan KO/TKO → DEC** and **Dan Hooker KO/TKO → DEC** (winner held fixed). V3+v5 selected: `Mar Fan DEC`, `Hooker DEC`; same fighter selections as original Winner v3. Remaining same method predictions. New highest exact-outcome probability **Navajo Stirling KO/TKO 44.4%** (NOT a lock). Cannonier vs Aliskerov: **Ikram Aliskerov DEC 40.3%**. Provisional Mitchell vs Yousaf source unverified PASS; numeric 50% winner tie is not an identifiable winner edge.
- New method v5 predictions are only research, **zero bets authorized**, cannot be selectively changed or "retrofitted" based on results. After card, grade same decisive bouts head-to-head against original Stage A and the first genuine coherence, v3, v4 shadows, with fighter+method exact, method-specific confusion/recall, Brier/log loss. Non-events/cancellations VOID, not wins.
- Current minimum **300 genuine prospective unique decisive fights** guard for model promotion unchanged; this card is 1 event only. Distinguish method-only v5 evaluation from v4 whole-model winner changes.

### Next model development

Extend genuinely verified *opponent-relative* positional grappling data without inventing direct get-up measures; examine linked Fight Canon round-by-round data completeness, real UFCStats prior position, control, takedown and submission-attempt chain measures. Validate ages/reach only when historical source vintages exist. Use event-level forward training comparisons and preserve future prospective locks before claiming win-rate or perfect exact group. Compute betting edge from FanDuel only, independent of untested high confidence.

**Measured development status:** Better real-world source coverage, some dated historical improvement on winner accuracy and method scoring, but **NO reproducible proof of 70% full-card fighter+method or 100% on 2–5 picks every card**. Promotions: 0. Betting approvals from these research candidates: 0.
