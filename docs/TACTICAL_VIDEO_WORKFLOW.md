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
