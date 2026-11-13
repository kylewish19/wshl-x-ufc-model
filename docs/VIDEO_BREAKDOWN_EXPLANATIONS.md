# WSHL_X UFC — Fight explanation and video pack (v1)

Goal: preserve the existing predictive model while adding traceable explanations
to every frozen UFC fight, suitable for WSHL_X video research.

## What this produces
- Original Reference, Historical and OOF Unified winner probabilities.
- Each model's OWN fighter's leading method: conditional on their win and the
  exact winner-plus-method joint probability are displayed separately.
- Original primary timing pick with current and Unified timing probabilities.
- Consensus vs winner disagreement, method/timing model coherence warnings.
- Opponent's statistical route (the reference model's probability and conditional method).
- Recorded age, reach, UFC bout counts, inactivity facts as DESCRIPTIVE context.
- A roughly one-minute model-based narration script and a long-form chapter outline.
- An audit record distinguishing research PASS/LEAN/SIDE from any official bet.
- Optional sourced, human-reviewed tactical notes (never automatically assumed).

## Critical evidence limitations
These are structured explanations of WHAT the frozen models predict and how
their outputs relate. The original Stage A artifacts DO NOT provide per-fight
feature contributions, SHAP explanations, or retraining counterfactuals.
A fighter being younger, longer, or more experienced does NOT prove that this
factor caused the trained model to favor the fighter.

UFC 334 has archived written-preview research but no verifiable continuous
full-fight tape review. This generator never invents tactical observations.
A detailed 3–5-minute technical breakdown still requires independently
reviewed film, striking/wrestling/grappling data and sources.

## How to regenerate for any event
With the same JSON schema as UFC 334:

  python tools/generate_ufc_video_breakdowns.py \
    --stage-a data/locks/EVENT/stage_a_final_selection.json \
    --raw data/locks/EVENT/stage_a_model_raw_three_view.json \
    --json-out reports/EVENT/VIDEO_BREAKDOWN_RESEARCH.json \
    --markdown-out reports/EVENT/VIDEO_BREAKDOWN_RESEARCH.md

Optional reviewed scouting notes:

  --notes reports/EVENT/reviewed_scouting_sources.json

Scouting-source JSON is an object keyed by string fight number, e.g.:

  {
    "6": [
      {
        "category": "grappling",
        "claim": "Specific, carefully reviewed and sourced observation",
        "source_url": "https://example.com/actual-source",
        "source_type": "full_fight_or_stats",
        "reviewed_by_human": true
      }
    ]
  }

Merely setting reviewed_by_human does NOT independently verify a claim or URL.
The reviewer must actually watch/read the evidence and check accuracy. Valid
categories: striking, grappling, conditioning, durability, recent_form,
opponent_path, other.

## Guards
- Verifies byte-for-byte SHA-256 of the archived raw file versus frozen lock.
- Refuses changed matchup identifiers, probabilities, duplicate fight numbers,
  odds-exposed inputs, unlocked Stage A, and mismatched model outcomes.
- Refuses to infer odds, betting edge, winning wagers, causality, or video evidence.
- Uses only Stage A. Never reads Stage B or actual fight results.
- Does not rewrite existing Stage A, Stage B, shadow model, code weights or PR.
- Generates fresh derived files separately; records both model agreement and
  disagreements and 15-point method/timing coherence flags.
- Tests in tests/test_video_breakdown.py run on every research-branch push.

## Governance
This is an additive editorial capability only. It does NOT promote the Unified
shadow, merge PR #1, retrain a model or change a pick. The research pack can be
superseded by a separately dated editorial update without editing the frozen
pre-price prediction artifacts.
