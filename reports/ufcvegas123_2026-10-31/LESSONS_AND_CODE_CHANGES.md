# UFC Vegas 123 — Oct. 31 missed-card retrospective learning audit

Event: **UFC Fight Night: Moicano vs Nolan** (12 bouts, Meta APEX, Las Vegas, 2026-10-31)  
Event status: **NOT PICKED / NO FROZEN STAGE A / NO STAGE B**  
Audit date: **November 6, 2026**  
Repository branch: `feature/historical-conditional-rates`, **not main**.

## Decision: learn the data, never invent picks

The user was away and **did not send a card or odds before October 31**. It is legitimate to add complete official post-fight results and raw per-round statistics for future chronological training, but *not* to backdate odds-blind model picks, classify results as 12 bets, or assign units/EV.

- Official graded/tracked fights remain **139**; this event contributes **12 additional historical performance observations** and therefore a total of **151 observed fights** across these two buckets, **not 151 prediction grades**.
- No retrospective "win rate" or simulated pre-event wagering P/L is entered.
- Offline model calculations below are conditioned on the **observed winner**, an outcome variable. They are **diagnostics of the method layer only** and cannot be treated as genuine fighter-plus-method prediction accuracy.

## Source and round-stat completeness

- UFC event source: https://www.ufc.com/event/ufc-fight-night-october-31-2026
- UFC main-card recap: https://www.ufc.com/news/ufc-fight-night-moicano-vs-nolan-results
- UFC preliminary-card recap: https://www.ufc.com/news/ufc-fight-night-moicano-vs-nolan-prelim-results
- UFC scorecards: https://www.ufc.com/news/ufc-fight-night-moicano-vs-nolan-official-scorecards
- Primary structured stats: **Greco1899/scrape_ufc_stats commit `3d4886d222e72be2c5336b49b98b721f5103d949`**, November 1, 2026 refresh; original files checksum-pinned.

| Data gate | Confirmed |
|---|---:|
| Official event/result/detail bouts | 12/12 |
| Bouts with per-round observations | 12/12 |
| Fighter-round statistical rows | **64/64** |
| Fighter-bout aggregates | **24/24** |
| Identity/round duplicate-result mismatches | 0 |

- All **12 outcomes** verified against official event results and UFCStats: **5 KO/TKO**, **1 SUB**, **6 DEC**.
- **Two of five KO/TKOs were doctor stoppages**: Jean-Paul Lebosnoyani–Farman Hasanov (R3 2:11, facial cut); Rodrigo Sezinando–Theodor Berggren (R2 5:00, facial cut). These remain KO in our three-class model, with separately preserved `doctor_stoppage=True` to support future hazard/market diagnostics; do not relabel them as standard knockouts in narrative analysis.
- **Source discrepancy:** The UFC *event-result listing*, UFCStats bout record, and contemporary result reports say **Joe Kropschot def. Nick Klein by submission, Round 2 at 1:25**. Some UFC recap/scorecard *headings* and an athlete-profile line incorrectly print **Round 3, 1:25**; their round-by-round story itself describes the finish in Round 2. We preserve **R2 1:25** from the event/structured record and flag the conflict, rather than hiding it.
- Note an Oct. 30 weigh-in exception: **Francis Marshall weighed 148 lb**, above the non-title featherweight limit; record if future pre-fight weigh-in feature work is undertaken, but do not insert into older pre-event feature snapshots without date-correct provenance.

Primary data: `data/raw/ufcvegas123_2026-10-31/availability.json`.  
Event-only fighter stats: `data/results/ufcvegas123_2026-10-31_fighter_stats.csv`.  
Unpicked result ledger: `data/results/ufcvegas123_2026-10-31_retrospective_only.csv`.

## Five fights worth learning from

All statistics in this section are **post-fight measurements**. They cannot be retroactively inserted into these fights' pre-fight model features.

### Moicano vs Nolan — escape/grappling defense before damage

Moicano landed **3/5 takedowns**, accrued **7:17 control**, and attempted a submission. Nolan ultimately won by **R3 TKO** after **69/92 significant strikes** versus Moicano's **9/12**, **38/44 ground significant strikes**, and one knockdown. UFC's recap reports Nolan successfully defended prolonged back-control attacks, escaped/transitioned, then damaged Moicano standing and on top.

**Hypothesis for future frozen cards:** positional grappling control without submission conversion must be contrasted with opponent get-up/sweep/counter-wrestling and damaging-strike upside. Takedown counts alone cannot represent sustained threat.

### Nick Klein vs Joe Kropschot — reverse/counter submission access

Klein landed **2/2 takedowns** and accumulated **3:01 control**, versus Kropschot **1/1 takedown** and **1:47 control**; however Kropschot logged **3 submission attempts** and won an **inverted triangle armbar R2 1:25**.

**Hypothesis:** model SUB-vs-KO access from defensive grappling responses, submissions attacked against a controlling opponent, and athlete-specific BJJ background—not merely offensive takedown completion. A fighter with fewer takedowns can still finish by submission. Note DWCS/regional prior substrate may be vital in a UFC debutant's sparse sample.

### Smith–Brown and Durden–Osbourne — control-heavy decisions

Jacobe Smith won via decision after **3/3 takedowns**, **8:53 control**, and **40** significant strikes to Brown's **16**; Durden won via decision after **6/8 takedowns**, **6:51 control**, and **35** significant strikes to Osbourne's **15**.

**Hypothesis:** some highly effective grappling is a decision-grinding pathway, not a submission knockout path. Distinguish control conversion from finishing pressure in conditional method probabilities and hazards.

### Luana Santos–Yana Santos — effective position vs striking volume

Luana won by decision with **5/16 takedowns** and **7:35 control**, despite landing **15 significant strikes** versus Yana's **17**.

**Hypothesis:** test an opponent-specific grappling/control-vs-striking interaction for winner, accounting for actual completion/retention; raw sig-strike count alone would misread this fight.

### Szabova–Lisboa — sustained top damage and R3 stoppage

Lucia Szabova won via R3 TKO after **5/8 takedowns**, **9:03 control**, **70** significant strikes to Lisboa's **14**, and **43** ground significant strikes.

**Hypothesis:** strong control coupled with substantial ground-damage production can produce a **late TKO**, not automatically decision. Compare combinations of prior ground-damage rate, control retention, and opponent defensive response. Test on unseen cards.

## Offline reconstruction of pre-Oct31 method signals

A deterministic reconstructed **conditional-method-on-actual-winner** check used causal fighter snapshots from Oct. 31 and fitted all models on **pre-Oct31 observations only** (8,781 earlier historical fight rows for the baseline and 139 prior OOF-grade feedback rows for calibrators). This was computed **after the event**; *the actual winning fighter is intentionally supplied*, and there was **no independent pre-event frozen model card**.

| Retrospective conditional method on known winner | Class accuracy | Multiclass Brier ↓ | Log loss ↓ |
|---|---:|---:|---:|
| Baseline method | **7/12 (58.3%)** | **0.5160** | **0.8659** |
| Intercept-calibrated | 8/12 (66.7%) | 0.5917 | 0.9724 |
| SUB-access challenger | 8/12 (66.7%) | 0.5893 | 0.9345 |

All three **predicted zero SUB top classes**, so all missed Kropschot's submission; the calibrated and access views called **nine KOs** against five actual KO/TKO outcomes. Better top-class accuracy does not imply better probability quality: the **baseline has the best Brier and log loss** on these 12.

This is consistent with prior concerns about **submission under-recognition**, while UFC333 and now Oct31 demonstrate that blanket finish/KO inflation creates decision-calibration problems. Never promote on 12 unpicked observations. Full diagnostics: `reports/ufcvegas123_2026-10-31/retrospective/integration_report.json`.

## Actual code/data changes executed and committed

1. `tools/gather_ufcvegas123_full_stats.py`: pinned postevent scraper, 12-bout official outcomes cross-check, 64 round rows, special doctor stop and names `Zach` vs `Zachary` and `Joe` vs `Joseph` reconciliation, content checksum receipts.
2. `tools/integrate_ufcvegas123_retrospective.py`: rebuild every past fighter's causal features with Oct31 admitted to future state **only**; archive 24 fighter-bout aggregated stat rows, 12 unpicked observed outcomes; output valid offline known-winner method diagnostics without counting them as picks.
3. Future-only **shadow artifacts** updated through Oct31: winner, method baseline, method calibrator, method residual, 30-second timing; stored with checksums and report under `artifacts/ufcvegas123_post_event_shadow`.
4. Preserve `clean_ufc_139_2026-10-24.csv` **untouched**; no official Stage A/Stage B for Oct31; official record and P/L unchanged.
5. `tests/test_ufcvegas123_retrospective_integrity.py`: permanent checks for source counts, Kropschot R2 outcome, doctor-stop flags, the unpicked ledger barrier, normalized known-winner method probabilities, and non-promotion governance.
6. GitHub Actions workflows run import, causality rebuild, grading separation, and the full regression suite, on `feature/historical-conditional-rates`.

## Evidence-based recommendation

**Deploy data infrastructure; do not promote new predictive coefficients from this card.** For next candidates, specify in advance and test with chronological out-of-sample folds and future pre-event freezes:

1. Counter-submission access and opponent offensive grappling exposure (Kropschot–Klein; Abus–Rowston).
2. Grappling control *quality*: completion rate, retained control, get-ups and sweeps, opponent sub defense and vulnerability (Moicano–Nolan; Durden–Osbourne).
3. Ground-damage + control interactions in late finishing vs decision survival (Szabova–Lisboa).
4. Distinguish doctor stoppages/cuts in finish-hazard diagnostics without blindly recoding official KO/TKO method labels.

The 300 newly frozen prospective fight promotion gate remains in place; this missed/unpicked card does **not** contribute 12 to it. Full-fight continuous tape was not watched in this environment: source basis is UFC round-level statistics, official recaps, and UFC event results.

**Final status:** 12/12 full-stats data integrated, causal historical backbone **8,793 fights**, five postevent future-only shadows refitted, current champion unchanged, official predictions graded remain **139**.
