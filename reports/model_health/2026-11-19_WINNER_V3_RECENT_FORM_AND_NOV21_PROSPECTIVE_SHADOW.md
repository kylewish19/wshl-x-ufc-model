# WSHL_X — Winner v3 recent-form research + immutable Nov21 UFC Qatar future shadow

**Research evaluation:** 2026-11-19. **Status:** independent dated winner challenger, **NOT promoted** to Reference, Historical, Unified or bets.

**Chronological training/evaluation GitHub CI:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44616520174
**Immutable future November 21 research-only lock CI:** https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44618011906
**Novel frozen sidecar:** `data/shadow_locks/ufcqatar_2026-11-21/winner_v3_prospective_shadow.json`
**Lock time:** `2026-11-19T21:22:24.603880+00:00`, well before official `2026-11-21T15:00:00+00:00` first-bout start.
**Original source lock hash:** `eb5b161b2ff2ac541de7319d2047fffc1dc40c5afed5192643649cd5c5fcb277` unchanged.
**Original Coherent shadow hash:** `56953d0b7507f42697e7deab49dbe91a25ae0a3c3ff1947399ea4bae7192cdd4` unchanged.
**Historical pinned secondary UFCStats-compatible statistics SHA256:** `f5b316d5e745bd89da921b2c9711ec9209c2fa39dcbcd80bcb063b62d9175bcb` through 2026-11-07 only. **Nov14 UFC334 results were NOT used**.

## Technical contribution to WINNER prediction

The existing 38-dimensional as-of source matrix lacked enough actual significant-strike production/absorption and recent-fight trend context. We constructed 19 independently sourced, date-lagged features for each candidate fighter, in `src/wshlx_ufc/winner_recent_form_v3.py`:

- Prior stat fight count, observed significant strikes landed/absorbed per 15, strike accuracy/defense, takedown accuracy and defense;
- Last three/five UFC results, signed winning/losing streak, recent three bouts sig-strikes generated/absorbed, knockdowns, takedowns, sub attempts;
- UFC bouts in last 365 days, recent stats coverage, and explicit absence of observed past stats.

**Data safety:** All 8,871 historical fight snapshots use source archives with SHA-verified future cutoffs; all same-day fights are frozen before updating any same-day combatants. All 3,036 2021–Nov7 source fight rows were uniquely rejoined, 0 missing. Do NOT claim direct get-up stats, injuries or regional fighter skill were observed. The physical age/reach/height retrospective enrichment was NOT introduced into this v3 experiment, since reach/height wasn't historically versioned and had failed 2026 tests.

The winner heads trained 2021 through before 2024, 2025, 2026 target years:
- Fixed UFC prior winrate and past-only Elo;
- Symmetric regularized logistic (38 vs **57** features);
- Small regularized tree boosted winner (38 vs **57** features).

The same **multinomial KO/SUB/DEC conditional method model for both potential winning fighters** is fitted strictly BEFORE each test year and held FIXED across ALL these winner heads. Thus any difference in exact fighter+method is due to the winner side/probability changes, not a simultaneous method-model retune. Full six-class probabilities, 500-seed event clustered uncertainty, and fighter/method labels are saved under the research Actions artifact `wshlx-winner-v3-recent-form-2024-26`.

## Strict chronological results, same method predictor

| Year and decisive fights | Older logistic 38 winner accuracy | New logistic 57 winner accuracy | Older logistic exact | New logistic exact | Older log loss (six-class) | New log loss |
|---|---|---|---|---|---|---|
| 2024 (511) | 309/511 **60.5%** | 310/511 **60.7%** | **169/511 (33.1%)** | 168/511 (32.9%) | 1.60769 | **1.60475** |
| 2025 (513) | 305/513 **59.5%** | 314/513 **61.2%** | **170/513 (33.1%)** | 169/513 (32.9%) | 1.60652 | **1.60116** |
| 2026 retrospect (488) | 293/488 **60.0%** | 303/488 **62.1%** | 145/488 (29.7%) | **157/488 (32.2%)** | 1.63604 | **1.62830** |

New logistic-57 winner Brier improved in **all three** years: 2024 **.23063 → .22971**, 2025 **.23373 → .23084**, 2026 **.23328 → .22981**. Event-level clustered winner-accuracy/exact-hit confidence bands crossed zero in each period. The 2026 retrospective gain is **not proven reproducible**.

The boosted-57 learner achieved exact **175/511, 176/513, 149/488**, versus older logistic 38 **169/511, 170/513, 145/488**. But boosted-57 had slightly WORSE six-class log loss in all three folds than older logistic 38, and won only **292/488** fights in 2026 vs old **293/488**. No compelling winner model dominates all criteria. Do not reward one 2026 improvement while ignoring degraded earlier exact rates and uncertainty.

**Previously frozen two cards, UFC333 Oct24 + Vegas124 Nov7, 28 bouts:** New logistic-57: **17/28 winners, 11/28 exact**, six-class logloss **1.5937**. Original Historical **20/28 winners, 10/28 exact** and Unified **19/28 winners, 11/28 exact** on those same cards. No claim of surpassing original Historical's winner selections. The original models' method marginal coherence defects require care comparing native joint proper scores.

## First genuine research-only future Nov21 card lock

Train exactly **3,015** date-before-2026-11-14 decisive fights (source through Nov7) and use *only* existing previous-date matchup features on user's 12 Nov21 fighters. Each original frozen fight has its own query-only feature record, no fake outcomes entered any training or score. The new logistic-57 is predeclared as **the primary independent research winner head** for future grading, while all five other winner heads are auxiliary diagnostic comparisons. Method head remains separately trained multinomial.

| Fight | V3 primary research winner + method | Winner P | Exact fighter+method P | Status |
|---|---|---:|---:|---|
| Nurgozhay–Lorenz | **Nurgozhay DEC** | 57.1% | 29.0% | PASS (Lorenz lacks verified prior UFC source identity) |
| Motta–Mar Fan | **Mar Fan KO/TKO** | 71.6% | 37.5% | LOW SAMPLE |
| Matthews–Abdullayev | **Matthews DEC** | 54.4% | 33.2% | LOW SAMPLE |
| Albazi–Costa | **Albazi DEC** | 51.1% | 23.2% | RESEARCH |
| Gaziev–Teixeira | **Gaziev KO/TKO** | 56.8% | 32.0% | RESEARCH (disagrees with all three original winner views) |
| Topuria–Luna | **Aleksandre Topuria DEC** | 55.7% | 32.6% | LOW SAMPLE (disagrees with all three original winner views) |
| Cannonier–Aliskerov | **Aliskerov DEC** | 75.7% | 35.2% | RESEARCH |
| Horiguchi–Almabayev | **Almabayev SUB** | 53.8% | 26.5% | RESEARCH |
| Hooker–Ortega | **Hooker KO/TKO** | 53.7% | 25.6% | RESEARCH |
| Sterling–Vallejos | **Vallejos KO/TKO** | 50.5% | 30.4% | RESEARCH |
| Procházka–Stirling | **Stirling KO/TKO** | 70.1% | **41.0%** | RESEARCH |
| Mitchell–Yousaf (provisional) | **Mitchell KO/TKO** | **50.0% tie**, not a credible winner preference | 21.7% | AUTO-PASS, 0/0 UFC bouts and unverified source identities |

No Nov21 fight's selected exact fighter+method P exceeds 50%. **Do not claim any near-lock** and do not convert 71% winner P into a 71% exact bet. Some V3 methods disagree with original Reference (e.g. Aliskerov DEC vs KO). These are frozen DIFFERENT predictions to grade, not late model flips.

### Evaluation after bout outcomes appear

- Keep all original Reference/Historical/Unified and independently locked Coherent predictions immutable.
- Grade V3 primary fighter winner, own selected KO/SUB/DEC, exact fighter+method, winner Brier/log loss, six-state Brier/log loss, KO/SUB/DEC confusion and quality warnings. Ignore cancellations and draws for a decisive six-class record, but document them as VOID/nondecisive, not wins.
- Compare identical fight identities and original locked source probabilities; avoid aggregating different samples. All 12 research predictions are a single **event**, not 12 independent model-promotion experiments. Count unique genuinely future decisive bouts just once toward the previously defined prospective evidence gate when eligible.
- After this event, do NOT select among the other five V3 research heads using its observed results and then falsely call that model primary. `logit_recent_57` is registered as primary now.
- No claim of 60–70% full-card exact accuracy or perfect 2–5 bet groups. Betting approval remains the separate FanDuel-only Stage B, without changes.

**Sources/code paths:** `src/wshlx_ufc/winner_recent_form_v3.py`, `tools/benchmark_winner_recent_form_v3.py`, `tests/test_ufc_winner_recent_form_v3.py`, `tools/lock_ufcqatar_winner_v3_research.py`, `tests/test_ufc_qatar_winner_v3_future_query.py`, `.github/workflows/ufc-winner-v3-recent-form-research.yml`, `.github/workflows/lock-ufcqatar-winner-v3-research.yml`.

**No champion promotion and no rewrite of Nov21 odds-blind original picks.**
