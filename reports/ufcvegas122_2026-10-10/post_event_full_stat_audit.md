# UFC Vegas 122 post-event full-stat audit

Event: UFC Fight Night: Allen vs Duncan  
Date: 2026-10-10

## Grading state

- Frozen Stage A winner record on decisive fights: **6-5 (54.5%)**
- Ernesta Kareckaite vs Melissa Gatto ended in a majority draw and is excluded from the binary clean winner ledger.
- Displayed method class on decisive fights: **8-3 (72.7%)**
- Exact winner + displayed method: **6-5 (54.5%)**
- Timing leans: **8-4 (66.7%)**
- Official Stage B wagers: **1-4, -1.981u on 3.75u risked**
- Official timing wagers through this event: **0-5, -3.00u**

The 11 decisive fights are stored separately in `data/results/clean_ufcvegas122_11_2026-10-10.csv`. They will be merged into the cumulative clean ledger during the next full-stat integration. The draw is preserved in the event report but not forced into a binary winner label.

## Miss audit

### Felipe Franco vs Brendson Ribeiro

Frozen side: Franco 75.7%  
Frozen official method: Franco KO/TKO  
Actual: Ribeiro submission, R1 1:49 (guillotine)

This is both a winner-side and exact-method failure. The fight ended too quickly for useful accumulated striking statistics, and currently available post-event stat mirrors do not yet expose a reliable full UFCStats totals row for the bout. Treat this as a high-variance submission-path miss, not enough by itself to rewrite the method model. When the canonical UFCStats package arrives, inspect Franco's historical submission exposure and Ribeiro's submission-access profile.

### Niko Price vs Leon Shahbazyan

Frozen side: Shahbazyan 54.7%, low-confidence/sparse pass-zone  
Actual: Price TKO, R1 1:58

Post-event totals: Price landed **41 of 59 significant strikes to Shahbazyan's 0 of 1**, landed 58 total strikes, and controlled for **1:45**. This was not a close loss; the experienced veteran completely overwhelmed the sparse UFC sample.

Interpretation: the confidence governance worked because this was already classified as a sparse/high-variance pass rather than an official wager. No winner-model rewrite from this fight alone. Continue explicit sparse confidence caps and prospective tracking.

### Andre Fili vs Kai Kamaka III

Frozen side: Kamaka 59.1%  
Actual: Fili TKO, R2

Post-event totals: Fili landed **50 of 108 significant strikes** to Kamaka's **33 of 74**, scored the only knockdown, and won Round 1 on all scorecards before the finish. Fili also entered with a **74-inch reach versus 69 inches for Kamaka**.

Interpretation: the current winner model already includes age, reach, knockdown rates, striking output and defense, but only as mostly linear main effects/differentials. This result supports testing interaction terms such as reach x damage pressure and output x opponent absorption. It does **not** prove those terms should be promoted.

### Matheus Camilo vs Jai Herbert

Frozen side: Camilo 77.2%  
Actual: Herbert unanimous decision, 29-28 x3

Post-event totals: Camilo landed **43 of 86 significant strikes (50%)**; Herbert landed **54 of 157 (34%)**. Camilo completed **2 of 4 takedowns**, but Herbert still produced the larger total striking output and won Rounds 2 and 3. Herbert held an **8-inch reach advantage (77 vs 69)**.

Interpretation: this is the clearest evidence that accuracy alone is not enough. The current state tracks landed strikes/min and accuracy, but not a separate significant-strike attempt-rate feature in the production winner vector. A future challenger should test pace/attempt volume and its interaction with reach and opponent defense. Do not insert the feature into the champion until chronology tests improve.

### Brendan Allen vs Christian Leroy Duncan

Frozen side: Duncan 54.7%, pass-zone  
Actual: Allen submission, R5 2:46

Post-event totals: Duncan out-landed Allen **106-51 in significant strikes**, but Allen went **4 of 11 on takedowns**, accumulated **8:39 control time**, attempted **2 submissions**, and eventually finished the rear-naked choke.

Interpretation: this is the strongest argument for a nonlinear `access-before-weapon` winner challenger. The production winner model already contains takedown rate, takedown defense, submission attempts and control, but as mostly independent linear features. A striker can lead the standing statistics and still lose if the opponent can repeatedly gain grappling access. Test takedown-access, control-access and submission-access interactions prospectively.

## Correct underdogs that were passed

### Allen Frye Jr. +295

The frozen model picked Frye at 65.0% but we passed because both fighters had only one prior UFC bout. Frye won by first-round TKO.

### Otari Tanzilovi +176

The frozen model picked Tanzilovi at 56.1% but we passed because of sparse UFC evidence/current-camp uncertainty. Tanzilovi won by second-round TKO. Post-event stats show Tanzilovi out-landed Wellmaker **38-17 in significant strikes**, landed **2 of 4 takedowns**, and produced the finishing knockdown.

Lesson: do **not** remove the sparse-data rule after two examples. Start tracking a separate `sparse model-vs-market disagreement` bucket so we can determine prospectively whether large disagreement underdogs deserve a different staking policy later.

## Timing audit

The informational timing model went 8-4, but the only promoted timing wager (Walker-Meerschaert starts Round 3 YES) lost when Walker finished at 3:35 of Round 2. Walker dominated with **38-9 significant strikes, 3/3 takedowns and 6:45 control** before the stoppage.

The timing model remains on probation:

- 12 percentage-point minimum model-vs-break-even edge
- no official timing promotion if either fighter has fewer than two prior UFC bouts
- 0.25u maximum official timing stake until the prospective sample reaches 20 and cumulative timing P/L is non-negative

No additional timing-policy change is justified from one more loss.

## Development action

A new **v0.34 winner interaction challenger** has been added for retrospective chronology benchmarking. It tests:

- takedown access vs opponent takedown defense
- submission access vs opponent submission exposure
- control access vs opponent control conceded
- knockdown pressure vs opponent knockdown vulnerability
- striking output vs opponent absorption
- reach x damage-pressure interaction
- log UFC-experience gap

This challenger is **shadow-only**. These interactions were designed after UFC Vegas 122, so historical improvement cannot be treated as prospective proof. The official winner reference remains unchanged until future frozen cards validate the challenger.

## Data-integration status

The event result and diagnostic statistics have been recorded. A full v0.34 event integration/retrain should wait for a canonical UFCStats-style raw package containing all 12 bouts and round-level rows. Once available:

1. gather and checksum the raw event/results/round-stat/static files;
2. merge the 11 decisive fights into the cumulative clean ledger while retaining Kareckaite-Gatto as a draw outside the binary winner target;
3. rebuild causal fighter state through 2026-10-10;
4. refit winner, calibrated method and 30-second timing shadows;
5. compare the v0.34 interaction challenger against the official reference on calibration and future prospective cards before any promotion.

## Diagnostic sources

- UFC official results and scorecards for UFC Fight Night: Allen vs Duncan.
- UFCalendar post-event stat pages for Fili-Kamaka, Camilo-Herbert, Allen-Duncan, Price-Shahbazyan, Walker-Meerschaert and Wellmaker-Tanzilovi.
- Current public result mirrors for Prado-Bonfim and Franco-Ribeiro where full round-stat totals were not yet reliably exposed.
