# WSHL_X UFC Qatar — original Stage A frozen + three-view Coherent Challenger

**EVENT:** UFC Fight Night: Prochazka vs Stirling, 2026-11-21. **Captured:** 2026-11-18. **Status:** ORIGINAL STAGE A FROZEN PRE-EVENT (11 official-site/user-supplied fights plus ONE media-reported provisional 12th bout). **STAGE B:** NOT RUN, NO BETS AUTHORIZED.

**Verification:** [GitHub Actions success](https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44402086325). Source frozen at `2026-11-18T21:31:31.338799+00:00`, separate coherence shadow generated `2026-11-18T21:31:33.464944+00:00`; both before original official start `2026-11-21T15:00:00+00:00`. Separate Git commits were pushed. The original raw SHA256 is `e5083bd605640e82731d8ee487fb1ac7c4d81d280faaf4f359edbeda1e8c2500`, final SHA256 is `eb5b161b2ff2ac541de7319d2047fffc1dc40c5afed5192643649cd5c5fcb277`; coherent shadow independently verifies both.

## All fighter-side forecast picks and original method/timing

| # | Bout | Reference P(winner) / method | Historical P(winner) / method | Unified P(winner) / method | One primary original timing forecast | Posture |
|---|---|---|---|---|---|---|
| 1 | Diyar Nurgozhay vs Alik Lorenz | Diyar Nurgozhay 67.9% / KO/TKO | Diyar Nurgozhay 53.8% / KO | Diyar Nurgozhay 58.2% / KO | Fight goes distance NO 66.2% (Unified 71.5%) | PASS |
| 2 | Nikolas Motta vs Dom Mar Fan | Dom Mar Fan 70.8% / KO/TKO | Dom Mar Fan 78.1% / KO | Dom Mar Fan 76.1% / KO | Over 1.5 rounds 63.4% (Unified 62.8%) | LEAN |
| 3 | Jake Matthews vs Tahir Abdullayev | Jake Matthews 51.4% / KO/TKO | Tahir Abdullayev 60.4% / KO | Tahir Abdullayev 56.9% / KO | Over 1.5 rounds 69.7% (Unified 68.2%) | PASS |
| 4 | Amir Albazi vs Alessandro Costa | Amir Albazi 54.6% / DEC | Alessandro Costa 50.1% / DEC | Amir Albazi 51.3% / DEC | Over 1.5 rounds 76.9% (Unified 74.6%) | PASS |
| 5 | Shamil Gaziev vs Tallison Teixeira | Tallison Teixeira 67.1% / KO/TKO | Tallison Teixeira 77.9% / KO | Tallison Teixeira 75.0% / KO | Fight goes distance NO 73.5% (Unified 75.9%) | LEAN |
| 6 | Aleksandre Topuria vs Santiago Luna | Santiago Luna 54.4% / KO/TKO | Santiago Luna 67.9% / KO | Santiago Luna 64.0% / KO | Over 1.5 rounds 81.1% (Unified 80.3%) | PASS |
| 7 | Jared Cannonier vs Ikram Aliskerov | Ikram Aliskerov 74.2% / KO/TKO | Ikram Aliskerov 81.0% / KO | Ikram Aliskerov 79.1% / KO | Fight goes distance NO 60.7% (Unified 62.3%) | SIDE |
| 8 | Kyoji Horiguchi vs Asu Almabayev | Kyoji Horiguchi 58.3% / DEC | Asu Almabayev 57.9% / DEC | Asu Almabayev 53.1% / DEC | Over 1.5 rounds 78.5% (Unified 77.1%) | PASS |
| 9 | Dan Hooker vs Brian Ortega | Dan Hooker 55.2% / KO/TKO | Dan Hooker 59.7% / DEC | Dan Hooker 58.3% / KO | Over 1.5 rounds 70.0% (Unified 69.8%) | PASS |
| 10 | Aljamain Sterling vs Kevin Vallejos | Kevin Vallejos 67.0% / KO/TKO | Kevin Vallejos 65.6% / DEC | Kevin Vallejos 66.0% / KO | Over 1.5 rounds 72.8% (Unified 71.9%) | LEAN |
| 11 | Jiri Prochazka vs Navajo Stirling | Navajo Stirling 56.3% / KO/TKO | Navajo Stirling 66.8% / KO | Navajo Stirling 63.8% / KO | Fight goes distance NO 71.6% (Unified 77.3%) | LEAN |
| 12 | John Mitchell vs Shoaib Yousaf [PROVISIONAL] | John Mitchell 96.4% / KO/TKO | John Mitchell 50.0% / KO | John Mitchell 72.9% / KO | Fight goes distance NO 87.0% (Unified 85.4%) | PASS |

## Coherent challenger — corresponding three research variants (NOT a new independent winner model)

The research sidecar preserves each original model's winner, displays its original frozen method and constrained winner+GTD method, and reconciles the six joint cells to the original winner and direct-finish probabilities. It does **not** generate an independent fourth winner or change original Stage A markets.

| # | Original Reference → coherent | Original Historical → coherent | Original Unified → coherent |
|---|---|---|---|
| 1 | KO → KO | KO → KO | KO → KO |
| 2 | KO → KO | KO → KO | KO → KO |
| 3 | KO → DEC | KO → KO | KO → DEC |
| 4 | DEC → DEC | DEC → DEC | DEC → DEC |
| 5 | KO → KO | KO → KO | KO → KO |
| 6 | KO → DEC | KO → DEC | KO → DEC |
| 7 | KO → KO | KO → KO | KO → KO |
| 8 | DEC → DEC | DEC → DEC | DEC → DEC |
| 9 | KO → DEC | DEC → DEC | KO → DEC |
| 10 | KO → DEC | DEC → KO | KO → DEC |
| 11 | KO → KO | KO → KO | KO → KO |
| 12 | KO → KO | KO → KO | KO → KO |

## Primary eligibility and quality findings

- Reference winner disagreements: fight numbers `3, 4, 8`; these do not flip original Reference winner picks.
- Research PASS fights: `1, 3, 4, 6, 8, 9, 12`. Stage A SIDE/LEAN does not authorize a bet; Stage B FanDuel gate still required.
- Method vs original direct-timing finish discrepancy >15 percentage points: `2, 3, 4, 6, 9, 10` — existing method-price gate remains blocked where applicable; the unpromoted coherent sidecar cannot override.
- Number **12**, John Mitchell vs Shoaib Yousaf, was reported on Nov17 by MMA Fighting but still missing from the official UFC event page at this verification. Both fighters have zero previously completed UFC bouts, and raw Reference **96.4%** is flagged as a severe low-data extrapolation. Preserve raw for grading but official posture **PASS**, no high-confidence claim.
- Source notes draw from the UFC's Nov16 preview and independently reported late booking, not continuous observed fight tape. Full bout-specific explanations/risks are in the frozen final `fights[].research_reason` and source-limited `tape_provenance`. Nobody asserted an unseen fight video was watched.
- Older models and architecture preserved: Reference coefficients through Sep12, associated feature state through Nov7; historical winner through Nov7, historical method/timing through Oct17; unified global weights fixed through Oct17. Nov14 UFC334 outcomes are **not** incorporated into these pre-event model forecasts.

## Full analytical source and next actions

Official venue and 11 bout page: https://www.ufc.com/event/ufc-fight-night-november-21-2026
Official Nov16 UFC tactical narrative: https://www.ufc.com/news/fight-by-fight-preview-ufc-fight-night-prochazka-vs-stirling-qatar
Late addition report (not yet official-site listed): https://www.mmafighting.com/ufc/522129/ufc-signs-two-fighters-for-late-notice-undercard-matchup-for-ufc-qatar

Source outputs: `data/locks/ufcqatar_2026-11-21/stage_a_model_raw_three_view.json`, `stage_a_final_selection.json`, `stage_a_final_audit.json`; separate immutable `data/shadow_locks/ufcqatar_2026-11-21/coherent_joint_pre_event_shadow.json`.

**Next:** verify final UFC weigh-in and 12th bout official status Friday Nov20; record last-minute cancellation/scale status as a separate amendment without rewriting original picks; collect real time-stamped FanDuel lines for Stage B Top 5 Best Bets / Top 5 Longshots, approval and price gates. After the event, grade all twelve original slots (void/cancel if needed), raw methods, timing, and the separately frozen coherent candidates; count genuinely gradeable prospective bouts toward 300 exactly once. No prices were consumed and no wager was actually placed.
