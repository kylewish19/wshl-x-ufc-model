# UFC Qatar (November 21, 2026) — independently frozen models graded November 24

**12 of 12 decisive event bouts verified. Source: SPORTS ILLUSTRATED MMA and Cage Almanac UFCStats-derived outcomes, 2026-11-21/22. All original predictions preserved by source SHA checks.**

| Model/view | Winners | Exact fighter + method | Conditional method given correct winner |
|---|---:|---:|---:|
| reference | 11/12 | **4/12** | 4/11 |
| historical | 10/12 | **5/12** | 5/10 |
| unified | 11/12 | **3/12** | 3/11 |
| coherent_reference_aligned | 11/12 | **7/12** | 7/11 |
| coherent_historical_aligned | 10/12 | **5/12** | 5/10 |
| coherent_unified_aligned | 11/12 | **7/12** | 7/11 |
| winner_v3_primary | 8/12 | **3/12** | 3/8 |
| winner_v4_primary | 9/12 | **4/12** | 4/9 |
| method_v5_primary | 8/12 | **5/12** | 5/8 |
| direct_six_v7_primary | 8/12 | **5/12** | 5/8 |

Original frozen Stage A primary timing: **10/12** correct; no FanDuel price/ROI inferred.
Separate public user-selected fighter/method/GTD/double-chance video card: **6/12**; not the official original card.

## Fight-by-fight, primary views

| Matchup | Actual | Reference | Historical | Unified | Coherent reference | Coherent unified | V3 | V4 | V5 | V7 | Public |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Nurgozhay vs Lorenz | Nurgozhay KO | Nurgozhay KO ✅ | Nurgozhay KO ✅ | Nurgozhay KO ✅ | Nurgozhay KO ✅ | Nurgozhay KO ✅ | Nurgozhay DEC ~ | Nurgozhay DEC ~ | Nurgozhay DEC ~ | Nurgozhay KO ✅ | Diyar Nurgozhay KO ✅ |
| Motta vs Fan | Fan DEC | Fan KO ~ | Fan KO ~ | Fan KO ~ | Fan KO ~ | Fan KO ~ | Fan KO ~ | Fan KO ~ | Fan DEC ✅ | Fan KO ~ | Dom Mar Fan KO/DEC ✅ |
| Matthews vs Abdullayev | Abdullayev DEC | Matthews KO ❌ | Abdullayev KO ~ | Abdullayev KO ~ | Matthews DEC ❌ | Abdullayev DEC ✅ | Matthews DEC ❌ | Matthews DEC ❌ | Matthews DEC ❌ | Matthews DEC ❌ | Jake Matthews DEC ❌ |
| Albazi vs Costa | Albazi SUB | Albazi DEC ~ | Costa DEC ❌ | Albazi DEC ~ | Albazi DEC ~ | Albazi DEC ~ | Albazi DEC ~ | Albazi DEC ~ | Albazi DEC ~ | Albazi DEC ~ | Amir Albazi DEC ❌ |
| Gaziev vs Teixeira | Teixeira DEC | Teixeira KO ~ | Teixeira KO ~ | Teixeira KO ~ | Teixeira KO ~ | Teixeira KO ~ | Gaziev KO ❌ | Gaziev KO ❌ | Gaziev KO ❌ | Gaziev KO ❌ | Tallison Teixeira KO ❌ |
| Topuria vs Luna | Luna DEC | Luna KO ~ | Luna KO ~ | Luna KO ~ | Luna DEC ✅ | Luna DEC ✅ | Topuria DEC ❌ | Luna DEC ✅ | Topuria DEC ❌ | Luna DEC ✅ | FIGHT_GOES_DISTANCE_YES ✅ |
| Cannonier vs Aliskerov | Aliskerov DEC | Aliskerov KO ~ | Aliskerov KO ~ | Aliskerov KO ~ | Aliskerov KO ~ | Aliskerov KO ~ | Aliskerov DEC ✅ | Aliskerov DEC ✅ | Aliskerov DEC ✅ | Aliskerov DEC ✅ | Ikram Aliskerov KO ❌ |
| Horiguchi vs Almabayev | Horiguchi DEC | Horiguchi DEC ✅ | Almabayev DEC ❌ | Almabayev DEC ❌ | Horiguchi DEC ✅ | Almabayev DEC ❌ | Almabayev SUB ❌ | Almabayev SUB ❌ | Almabayev SUB ❌ | Almabayev SUB ❌ | Asu Almabayev SUB/DEC ❌ |
| Hooker vs Ortega | Hooker DEC | Hooker KO ~ | Hooker DEC ✅ | Hooker KO ~ | Hooker DEC ✅ | Hooker DEC ✅ | Hooker KO ~ | Hooker KO ~ | Hooker DEC ✅ | Ortega DEC ❌ | Dan Hooker KO/DEC ✅ |
| Sterling vs Vallejos | Vallejos DEC | Vallejos KO ~ | Vallejos DEC ✅ | Vallejos KO ~ | Vallejos DEC ✅ | Vallejos DEC ✅ | Vallejos KO ~ | Vallejos KO ~ | Vallejos KO ~ | Vallejos KO ~ | Kevin Vallejos KO ❌ |
| Prochazka vs Stirling | Stirling KO | Stirling KO ✅ | Stirling KO ✅ | Stirling KO ✅ | Stirling KO ✅ | Stirling KO ✅ | Stirling KO ✅ | Stirling KO ✅ | Stirling KO ✅ | Stirling KO ✅ | Navajo Stirling KO ✅ |
| Mitchell vs Yousaf | Mitchell KO | Mitchell KO ✅ | Mitchell KO ✅ | Mitchell KO ✅ | Mitchell KO ✅ | Mitchell KO ✅ | Mitchell KO ✅ | Mitchell KO ✅ | Mitchell KO ✅ | Mitchell KO ✅ | John Mitchell KO ✅ |

## Source facts and defensible findings

- Event produced **8 decisions, 3 KO/TKO finishes, 1 submission**. Reference originally got 11/12 winners but just 4/12 exact, an observable METHOD bottleneck.
- Coherent Reference and Coherent Unified **winner_and_timing_aligned** research variants each reached **7/12 exact (58.3%)**, keeping their same original winner picks. These are probability postprocessors, not an independent learner; do not claim 58.3% future accuracy from a single event or retrospectively select the winning postprocessor.
- Winner v3/v4 did not improve winner accuracy on this forward event. Method v5 and direct six v7 got 5/12 exact but both chose only 8/12 correct winners, so the old winner head remained strongest this event.
- Original first 11 bouts plus previously reported late provisional Mitchell/Yousaf scored separately in structured JSON. The last fight is counted as genuine decisive, but not retroactively part of original 11 originally confirmed fights.
- The public card graded separately: user double-chance and GTD bets are treated as combined markets, not the same exact-method category. No FanDuel prices, stakes or independently verified closing lines supplied, so zero hypothetical/real profitability conclusions.
- ONE event is insufficient for model promotion. Preserve all original source SHA and register new predictions before another future fight. Compare opponent-specific finish mechanisms and original GTD timing props after reviewing actual UFCStats per-fight stats, not invented tape observations.

## External verification

- https://www.si.com/fannation/mma/news/ufc-qatar-free-live-stream-results-highlights-prochazka-vs-stirling
- https://cagealmanac.com/events/ufc-fight-night-prochazka-vs-stirling-cbf69f
- https://www.ufc.com/news/ufc-qatar-results-prochazka-vs-stirling

Legend: ✅ exact; ~ winner correct but method wrong; ❌ winning fighter incorrect.
