# November 21 UFC Qatar — independent NEW direct six-outcome v7 PRE-EVENT research lock

**Research only, never Stage A or FanDuel Stage B.**

- **Verified executed GitHub Actions**: https://github.com/kylewish19/wshl-x-ufc-model/actions/runs/44633002610 (full tests, prior event source SHAs, exact foreign database source SHA, proper 6-way sum, signed git commit all PASSED).
- **Immutable pre-event file**: `data/shadow_locks/ufcqatar_2026-11-21/worldwide_direct_six_v7_prospective_shadow.json`.
- **GitHub timestamp**: `2026-11-19T22:55:36.469296+00:00` (5:55 p.m. EST Nov19), strictly before first bout Nov21 `15:00 UTC`.
- **Primary and ONLY chosen direct six-outcome research model:** `direct_paired230` (logistic on 230 bilateral pre-fight features), using `winner_marginal_method` decision rule (choose side from sum of its KO/SUB/DEC probabilities then choose most likely method on that side); 2025 previous-year conditional tuning gave `C=0.025`. This was prechosen before Nov21 result. NOT a late global-six pick switch.
- **Historical training through pinned 2026-11-07 only**; `3,015` decisive fights beginning 2021. Imported external verified historic professional MMA only on pre-fight dates; pinned Fight Canon release SHA256 `8185a2163b5f97071dbc4ec68667cceb43f5e321fadc38c26b5069303af4d949`. All 12 matchups built via independent pre-day UFC stats and vetted cross-promotion player histories where available. No Nov14 UFC334 results used. No odds features.
- **Original Reference/Historical/Unified Stage A, coherent shadow, winner v3, v4 and method v5 fully SHA verified UNCHANGED**. All 6 source file hashes copied into v7 lock for immutable provenance. No production model promoted or official bets approved. The new v7 model is an experimental entirely separate architecture, not a vote among original model picks.
- **Code:** `tools/lock_ufcqatar_direct_six_v7_research.py`; pipeline `.github/workflows/ufc-qatar-direct-six-v7-research-lock.yml`; offline historical study `tools/benchmark_worldwide_direct_six_v7.py`. Distinct from v6 and v8, which have NO pre-registered primary 11/21 picks.

## FULL pre-registered primary research card

| Bout | V7 direct-six research exact fighter+method | P winner | P exact fighter+method | Source warning |
|---|---|---:|---:|---|
| Diyar Nurgozhay vs Alik Lorenz | Diyar Nurgozhay **KO/TKO** | 89.83% | 79.83% | **UNVERIFIED REGIONAL ID, PASS** |
| Nikolas Motta vs Dom Mar Fan | Dom Mar Fan **KO/TKO** | 64.35% | 31.89% | Sparse UFC history |
| Jake Matthews vs Tahir Abdullayev | Jake Matthews **DEC** | 57.60% | 40.26% | Sparse UFC history |
| Amir Albazi vs Alessandro Costa | Amir Albazi **DEC** | 53.90% | 28.36% | Normal research |
| Shamil Gaziev vs Tallison Teixeira | Shamil Gaziev **KO/TKO** | 54.84% | 30.66% | Sparse UFC history |
| Aleksandre Topuria vs Santiago Luna | Santiago Luna **DEC** | 51.93% | 22.15% | Sparse UFC history |
| Jared Cannonier vs Ikram Aliskerov | Ikram Aliskerov **DEC** | 73.46% | 33.77% | Normal research |
| Kyoji Horiguchi vs Asu Almabayev | Asu Almabayev **SUB** | 50.14% | 23.34% | Normal research, essentially no winner margin |
| Dan Hooker vs Brian Ortega | Brian Ortega **DEC** | 50.74% | 33.96% | Normal research, essentially no winner margin |
| Aljamain Sterling vs Kevin Vallejos | Kevin Vallejos **KO/TKO** | 53.49% | 33.33% | Sparse UFC history |
| Jiří Procházka vs Navajo Stirling | Navajo Stirling **KO/TKO** | 76.63% | 59.30% | Normal research, UNVALIDATED calibration |
| John Mitchell vs Shoaib Yousaf (provisional) | John Mitchell **KO/TKO** | 50.00% | 24.14% | **BOTH external identities unverified, AUTO-PASS** |

**Important model miscalibration warning**: v7 returns **79.8% exact** for Nurgozhay KO despite the fighter's opponent Alik Lorenz lacking verified cross-promotion ID, and **59.3% exact** for Navajo Stirling KO despite earlier matched three-year full-card models only scoring roughly 33–39% exact. These are numerical output probabilities, **NOT verified calibrated exact hit rates** or authorized betting edges. Rank or recommendations MUST NOT use unverified ID exact p as reliable. At minimum the first and last bouts remain PASS. Do NOT market as 80%-accurate exact bets or 2–5 locks.

## How to use the event

Keep the original original signed Stage A locked. Prospective grade the same unique decisive fight IDs versus pre-fight original Reference/Historical/Unified, Coherent original shadow, v3, v4, v5 and this v7 *as separately preregistered model arms*. No consensus cherry-picking, flip or late weighting. Note v6 method and v8 global-elo studies **have no separately frozen prospective sidecar**, so cannot claim prospective Nov21 scores. Exclude actual canceled/void/draw from decisive six-way and do not change the slate after seeing results.

**No specific FanDuel odds or playable approved bets generated in this research experiment.** Stage B can separately price the original officially registered hypotheses, with odds source/date/EV gates and pass logic. Additional 11/21 research model predictions do not qualify to override original Stage A.
