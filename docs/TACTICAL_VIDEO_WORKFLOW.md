# WSHL_X UFC: Tactical video breakdowns (CANONICAL WORKFLOW)

## Why this exists

The former `VIDEO_BREAKDOWN_RESEARCH.md` pack recited the Reference, Historical, and
Unified model probabilities. That is an internal audit/report, **not** the
narration format for public videos.

The audience-facing scripts are now `TACTICAL_VIDEO_SCRIPTS.md`.
They answer **what the tactical advantages are, what each fighter needs to
do, where the opponent is dangerous, and what tactical exchange is decisive**.
They deliberately do not state our winner, method, or timing picks because
the host reveals those afterward.

## Required two-layer workflow for every future UFC card

**Layer A — Locked prediction system, unchanged**

1. Gather pre-fight fighter stats, form, UFC/verified regional evidence and
   tape source provenance. Train/rerun the existing models as governed.
2. Freeze Stage A as usual: reference, historical, unified, winner,
   fighter+method, duration/round markets, confidence, and gates.
3. Stage B can review FanDuel prices separately, strictly after the freeze.
4. The frozen Stage A data and original odds stay immutable.

**Layer B — Independent tactical explanation system**

1. Research every actual fight, using relevant UFC fighter profiles, event
   previews, UFCStats, opponent records, reputable fight technical analysis,
   and **watched/verified footage when available**.
2. Record specific, attributable tactical facts with URLs. Classify footage
   honestly. Do not claim to have watched full tape if unavailable.
3. Write a **75–140 word spoken script per matchup** with:
   - a striking, grappling, pace, or distance-control distinction;
   - how that distinction creates real winning opportunities;
   - what each fighter must do to put their tools into play;
   - why the opponent can disrupt that plan; and
   - a final question/tension before the pick reveal.
4. Do not narrate the model names, numeric predictions, FanDuel odds, or
   the explicit winner/method/timing picks. The host announces these next.
5. Scripts need to be **original analytical prose**; do not copy UFC articles
   or claim numerical feature attribution without true model explainability.
6. Gate publication on complete, sourced, editor-reviewed fight research.
   The generator refuses a missing fight or an invented source. A URL in the
   research packet does not itself prove that every sentence was verified.
7. Run `pytest` and save derived scripts under `reports/<event>/`.
8. After the event, grade the frozen prediction models. Tactical narration
   is separate editorial material and must not be retroactively used to
   change or backfill old predictions.

## How to generate

The reusable tool is:

```bash
python tools/generate_tactical_video_scripts.py \
  --stage-a data/locks/ufc334_2026-11-14/stage_a_final_selection.json \
  --raw data/locks/ufc334_2026-11-14/stage_a_model_raw_three_view.json \
  --research research/ufc334_2026-11-14_tactical_video_research.json \
  --markdown-out reports/ufc334_2026-11-14/TACTICAL_VIDEO_SCRIPTS.md \
  --json-out reports/ufc334_2026-11-14/TACTICAL_VIDEO_SCRIPTS.json
```

The GitHub workflow `publish-ufc-tactical-scripts.yml` does this when new
researched event files are committed. It does not automatically invent
unsourced scouting observations for future cards.

## UFC 334 notes

- All 13 public scripts have distinct, sourced technical scenarios.
- Sources are public UFC fighter/editorial pages, cited third-party
  previews or official UFCStats, where available.
- **Editorial status: written-source desk research; continuous full-fight
  tape not verified**. Final fact/tape check and late fight-week confirmation
  is required before recording.
- Original Stage A frozen file and model branch are unchanged.
- Winner, method, timing and any FanDuel value picks must come from the
  separate frozen models/price gate, not from persuasive-sounding narration.

---

## 2026-11-12 policy — three-model consensus is the ON-CAMERA pick reveal, not a model change

The creator wants a viewer-friendly, fight-specific argument followed by his **winner,
method, and timing** choices, not a narration of model names. The newly added
`src/wshlx_ufc/consensus_video.py` produces a **separate** presentation card
from all three originally archived model views, WITHOUT promoting the shadows,
altering champion or shadow coefficients, changing any original frozen prediction,
mutating Stage B, or altering the official post-event grading reference.

**Majority rule.** Exact 3/3 = "unanimous"; 2/3 = "majority"; 1/1/1 =
"no consensus." Winner uses the fighter side. Fighter+method uses a combined
(fighter, KO/TKO/SUB/DEC) pair for each model's OWN selected winner; never count
"KO" on opposite fighters as method agreement. Timing uses the SAME predeclared
comparable set of GTD yes/no, over/under 1.5 and 2.5, and Round 3 starts yes/no,
without FanDuel odds. Historical timing uses its archived direct probabilities,
while Current and Unified timing use their saved 10k simulation distributions.

**Important scientific limitation.** The Unified view blends other components;
these three are not three statistically independent votes. A 2/3 or 3/3 consensus
is not a calibrated likelihood, an official approved wager, or a license to
ignore uncertainty. The previous original reference Stage A winner,
SIDE/LEAN/PASS classification, main timing prediction, and frozen grade stay
immutable. An on-camera consensus may differ from the original Reference pick
or timing forecast; report and grade both separately. In particular, the
posture of an existing PASS remains PASS even with three-way agreement.

### Aligning scripts honestly, while preventing feedback into the models

1. Freeze and hash all three raw model views BEFORE any script is composed.
2. Derive the separately labeled creator-consensus display. **Do not select
   a pick based on the strength of a verbal explanation.**
3. Independently research the skills and history that make the chosen path
   *plausible*: range/footwork, striking levels, defensive entries, grappling
   access, takedown control, get-ups, pace, durability and round survival.
4. A reviewer compares the drafted script against the consensus winner,
   full fighter+method pair, timing market, and model disagreement, one fight
   at a time. This is a **human editorial integrity check**; software cannot
   genuinely validate that a tactical narrative fits the fight. Flag
   `auto_tactical_alignment_verified = false` until reviewed.
5. If there isn't convincing evidence for the majority KO/SUB/decision
   route, explain the uncertainty transparently. Do NOT invent a striking
   advantage, a claimed weakness, or fictitious footage to justify it.
6. Opponent-quality research is welcome and should be integrated only when
   supported. Record the named recent opponents, official result and finish
   method, opponent quality *at the time* (ranking, verified record, UFC/
   regional level, notable wins), and style similarity to the next opponent.
   Note when winning against a good opponent says little about a different
   stylistic threat; account for the opponent's age, injuries, short notice
   and fight phase. Never claim "fighter A beat a good fighter therefore
   fighter B cannot win." If sourcing is unavailable, omit the claim.
7. On camera, deliver only **tactical breakdown + counter-scenario**.
   The video report automatically fills the consensus winner, fighter+method, and timing from the original 2-of-3 or 3-of-3 predictions. The host reads those after the tactical explanation; no handwritten or improvised pick selection is needed. Technical
   predictions that fail model-family coherence are *forecasts*, NOT approved
   bets, even with unanimous model agreement.
8. Keep a clean provenance trail and score the old frozen original, new
   consensus shadow card, and approved betting card as different ledgers.
   Do not conflate a compelling video with measured predictive accuracy.

### UFC 334 example of separate timing records

For Johnson vs Almeida the **original** Stage A primary timing forecast was
`GTD_NO`; the newer three-model editorial timing-vote winner is
`OVER_1.5` (Historical + Unified). The two can even both occur, but they
are different markets and must not be misrepresented as the same historical pick.

Generate the new overlay with `tools/generate_consensus_video_card.py`.
The resulting `reports/ufc334_2026-11-14/CONSENSUS_VIDEO_REVEAL.md` is for
pick-reveal preparation; `TACTICAL_VIDEO_SCRIPTS.md` is for spoken matchup
analysis. The script must never rewrite the model outcomes.


## Public-facing script formatting (November 12, 2026)

The **published spoken Markdown** `reports/<event>/TACTICAL_VIDEO_SCRIPTS.md`
contains **only** the fight heading, tactical breakdown, pick-reveal transition
and automatically populated winner, method and timing picks. Do not show
`2/3 agreement`, `3/3 agreement`, sources, research notes, coherence/price
warnings or internal grading metadata in the script.

**Internal integrity is not discarded.** `research/<event>_tactical_video_research.json`
retains source URLs, research notes and provenance; `TACTICAL_VIDEO_SCRIPTS.json`
retains those plus 2-of-3/3-of-3 vote records and method/timing warnings.
The presentation format is not permission to ignore those warnings or to
claim sourced research was verified by full fight-tape review. Neither
the original Stage A lock nor Stage B betting gates are changed.
