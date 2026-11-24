# WSHL_X UFC Qatar — November 24, 2026 verified POST-CARD lessons from actual totals

**After-event audit, not pre-fight predictive information.** All 12 bouts finished and are verified against UFC result coverage plus twelve separately linked Cage Almanac UFCStats-derived fight detail pages. Original champion, 3 Stage A views, Coherent shadow, new V3/V4/V5/V7 sidecars unchanged and SHA-checked. The actual event was Nov 21; the fight stat snapshot was reviewed Nov 24.

**Immutable grade and full per-fight status:** `data/grades/ufcqatar_2026_11_21_all_frozen_models_and_public_card_grade.json`, produced and committed after reproducible passing CI https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/45488023126 .
**Preserved independent UFCStats-derived fight TOTALS:** `data/results/ufcqatar_2026-11-21/ufcstats_derived_postevent_fight_totals_2026-11-24.json`. It includes 24 fighter records / 12 fights, knockdowns, significant and total strikes, takedown attempts and successes, submission attempts, reversals, cage control and exact external source links. **Per-round stats are present on the linked sources but are not yet re-ingested into this totals-only file.**

## 1. The central diagnosis has CHANGED: winner was excellent, FINISH was weak

- Original Reference **11/12 winning fighters correct** (91.7%), **only 4/12 fighter + method exact** (33.3%). Original 11-fight source slate excluding late Mitchell/Yousaf: **10/11 winners, 3/11 exact**.
- Historical **10/12 winner, 5/12 exact**. Unified **11/12 winner, 3/12 exact**. New V3 primary **8/12 winner, 3/12 exact**; V4 **9/12 winner, 4/12 exact**. **None of these new winner heads beat the original Reference or Unified on this card.**
- Frozen **Coherent Reference winner-and-timing-aligned** **11/12 winners, 7/12 exact (58.3%)**; similarly Coherent Unified **11/12 winners, 7/12 exact**. Coherent Historical **10/12 winners, 5/12 exact**. Coherent is a postprocessor of original models, NOT a fourth independent winner model, and only one event has been observed. Original 11 only Coherent Reference/Unified **6/11 exact (54.5%)**.
- V5 fighter-specific regional method with V3 held winner **8/12 winners, 5/12 exact**. V7 direct bilat six 230 **8/12 winners, 5/12 exact**. They improved exact ranking relative to their poorer winner choices, not enough to replace original winner. 
- Real event methods: **8/12 decisions, 3/12 KO/TKO, 1/12 SUB**. Reference had predicted KO for **10/12**, DEC for only **2/12**, so 7 of 11 correctly forecast winners were assigned the wrong method. Historical and Unified also leaned too heavily into KO, despite decent winner selection.
- Coherent Ref/Unified method correct conditional on correctly selected winner **7/11 = 63.6%**, versus original Reference **4/11 = 36.4%**, original Unified **3/11 = 27.3%**. Better **on this card**, not yet proved durable.
- New direct six v7 produced apparently giant exact P (e.g. Nurgozhay KO ~79.8% with unverified Lorenz cross-promotion identity); although this specific pick HIT, the QA warning must NOT be retrospectively dropped or model confidence labeled calibrated.

**Implication:** Our immediate predictive bottleneck was to choose which correctly identified fighter finishes by KO/SUB vs reaches the scorecards, not to flip winning fighters in pursuit of one more speculative regression model.

## 2. All actual 12-bout postfight stat comparisons suggest concrete hypotheses

**Dom Mar Fan vs Nikolas Motta — Mar Fan DEC, NOT KO:** Mar Fan 59/110 sig strikes vs Motta 14/85. **4/9 takedowns, 6:01 control**; Motta scored a knockdown but did not gain the decision. A finish model based on offensive strikes and reach missed a control+volume points pathway. UFCStats-derived evidence https://cagealmanac.com/fights/9011 .

**Tahir Abdullayev vs Jake Matthews — Abdullayev DEC:** Despite being the relative UFC newcomer, Abdullayev landed **5 of 7 takedowns and 9:02 control**, 32/72 significant strikes vs 18/71. Veteran-experience priors must never override verified opponent-specific grappling ability. https://cagealmanac.com/fights/9010 .

**Amir Albazi vs Alessandro Costa — Albazi SUB R3 4:34:** Only submission on the card. Albazi **7 of 10 takedowns, 6:19 control** and one submission attempt producing a late finish. Our DEC method assumption missed threat-to-conversion, despite both fighters having offensive grappling success. Don't boost every fighter's SUB quota globally. https://cagealmanac.com/fights/9009 .

**Shamil Gaziev vs Tallison Teixeira — Teixeira DEC, NOT KO:** Teixeira **47/114 sig strikes to Gaziev 15/42**, **0 knockdowns**. Teixeira landed 20 body and 21 leg significant strikes, just 6 to the head, showing durable outpointing instead of the predicted single strike finish. https://cagealmanac.com/fights/9008 .

**Aleksandre Topuria vs Santiago Luna — Luna DEC:** Luna 142/363 significant strikes vs Topuria 65/149; split decision but 0 knockdowns. Volume and late-round persistence are important for method/decision forecasting; WSHL_X public GTD YES correct. https://cagealmanac.com/fights/9007 .

**Jared Cannonier vs Ikram Aliskerov — Aliskerov DEC, NOT KO:** Aliskerov 39/79 sig strikes vs 20/73, **4 of 6 takedowns, 6:55 control and 3 submission attempts**, but no actual finish. Winning positional grappling and attempted submissions do not mean a converted SUB/KO. The V3/V4/V5/V7 DEC hit, originals KO lost the method. https://cagealmanac.com/fights/9006 .

**Kyoji Horiguchi vs Asu Almabayev — Horiguchi DEC despite Almabayev control:** Almabayev logged **7 of 9 takedowns and 9:43 control** with only 8 significant strikes; Horiguchi logged **158 total strikes (17 significant)** and **2 submission attempts**, winning the official decision. This result illustrates that takedown/control volume does not deterministically select winner or submission. Don't infer judging simply from aggregate control without review of effective offense. https://cagealmanac.com/fights/9005 .

**Dan Hooker vs Brian Ortega — Hooker DEC, NOT KO:** Hooker landed **146 of 281** significant strikes to Ortega's **70 of 186**, no knockdowns. Ortega made only **2 of 11** takedowns. This produced a long high-volume striking decision, and the original KO method overpredicted finish conversion. https://cagealmanac.com/fights/9004 .

**Aljamain Sterling vs Kevin Vallejos — Vallejos DEC, NOT KO:** 37/94 vs 32/93 significant strikes, **no knockdowns**. Sterling attempted **12 takedowns**, completed only **1**; Vallejos did not finish even with disrupted grappling entries. Durable decision possibility should not vanish because winner is a historical power finisher. https://cagealmanac.com/fights/9003 .

**Jiri Prochazka vs Navajo Stirling — Stirling KO R2 4:58:** Stirling 48/94 significant strikes vs Jiri 23/45, one knockdown and decisive finish. Most models agreed Stirling KO and HIT. https://cagealmanac.com/fights/9002 .

**Diyar Nurgozhay vs Alik Lorenz — Nurgozhay KO R2 0:24:** 37/56 significant strikes vs Lorenz 18/39, one knockdown. Correct exact; Lorenz nevertheless had NO verified UFC history pre-event, and correctly picked does not retroactively prove strong newcomer calibration. https://cagealmanac.com/fights/9012 .

**John Mitchell vs Shoaib Yousaf — Mitchell KO R1 3:50:** 26/35 sig strikes vs 16/38, one knockdown; both were UFC debutants and original late fight was a pre-event PASS in official betting posture. The exact research prediction landed but must not be advertised as a vetted high-reliability bet. https://cagealmanac.com/fights/9013 .

## 3. Timing bets and public WSHL_X selected picks graded independently

- Original Stage A locked **primary timing markets 10/12** (83.3%). The misses were **Gaziev–Teixeira GTD NO** and **Cannonier–Aliskerov GTD NO**, both actually decisions. This is still unpriced Stage A, **NOT 83% verified FanDuel bet return**.
- Public video card from pre-event user chat: **6/12** mixed straight exact methods, KO-or-DEC/SUB-or-DEC, and Topuria–Luna **GTD YES**. Wins: Nurgozhay KO, Mar Fan KO/DEC, Luna–Topuria GTD YES, Hooker KO/DEC, Stirling KO, Mitchell KO. Losses: Matthews DEC, Albazi DEC, Teixeira KO, Aliskerov KO, Almabayev SUB/DEC, Vallejos KO. Public bets were **NOT** 12 independent identical-probability exact states and are not interchangeable with the original model grades.
- No accepted preevent verified FanDuel quote archive, stake ledger or valid bet confirmation was supplied for these 12 selections, so ROI/EV cannot be calculated. Full prospective grade lists all 12 real results and source hashes.

## 4. Code-policy changes justified NOW vs changes requiring replication

**NOW completed (correctness and data acquisition, no retraining):**
- Immutable independently sourced result dataset; verified UFCStats-derived fight totals with source per bout; SHA-checked cross-model winner/exact/six-state proper-score grading; separate user-public mixed-market W/L; original primary timing and unpriced grade; source-of-truth GitHub Actions pass.
- Diagnose KO-heavy method family and inspect new Coherent R/U method prediction impact. Add this observed card to **future eligible outcomes** ONLY, not to frozen models.
- Preserve original first-11 vs late-provisional-12 reporting to avoid changing historical denominators.

**Requires multiple other genuine prospective UFC cards BEFORE predictive code changes:**
- Compare 38-feature KO/SUB/DEC prior vs temporal-consistent Coherent Reference+Unified aligned on multiple forward cards. Inspect confidence calibration, 95% clustered intervals and expected price/ROI, not just 7 hits out of 12.
- Evaluate whether distinguishing **striking hurt/knockdown opportunity from finish conversion** (KO conditioned on opponent finish resistance), **takedown entry/control vs submission completion**, and **scorecard round-winning pace** improves PREMATCH outcome probabilities. Research explicit feature missingness, don't invent get-ups or continuous tape review.
- Error decomposition: experienced-vs-newcomer grappling mismatch (Matthews/Abdullayev), 1/12 late SUB (Albazi/Costa), finish overprediction in 7 of the 11 correctly picked original winning fighters. Do not add a quota forcing 8 DEC next event based on this one decision-heavy card.
- True prospective locks and a predeclared 300+ unique-fight evaluation gate remain; no post-hoc model promotion or model chosen after observing the fight. The "58.3% exact" Coherent score is one card with overlapping derived views, not a 58% long-term model.
- Existing original Stage A locks and original FanDuel Stage B code remain untouched.

## All sources
- Verified event result fixtures `data/results/ufcqatar_2026-11-21/verified_event_results_2026-11-24.json`.
- 24-fighter numeric results `data/results/ufcqatar_2026-11-21/ufcstats_derived_postevent_fight_totals_2026-11-24.json`.
- Frozen all-10-arm graded JSON `data/grades/ufcqatar_2026_11_21_all_frozen_models_and_public_card_grade.json`.
- Full grade Markdown `reports/model_health/2026-11-24_UFC_QATAR_ALL_LOCKED_MODELS_GRADE.md`.
- Original sources remain SHA locked under `data/locks/ufcqatar_2026-11-21` and `data/shadow_locks/ufcqatar_2026-11-21`.
