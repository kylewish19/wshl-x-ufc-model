# WSHL_X UFC Model

A versioned UFC prediction and grading project for WSHL_X.

## Core model layers

1. **Winner** — probability each fighter wins.
2. **Conditional method** — KO/TKO, submission, or decision given the winning fighter.
3. **Timing / survival** — fight-duration distribution, over/under rounds, goes-the-distance, and round-start probabilities.
4. **Joint outcomes** — coherent fighter + method probabilities derived from the winner and conditional-method layers.
5. **Double chance** — fighter-specific KO/SUB, KO/DEC, and SUB/DEC probabilities derived from joint outcomes.
6. **Simulation** — seeded Monte Carlo draws from the frozen model probabilities.

## Non-negotiable workflow

- Use only information available before the fight when building historical training rows.
- Do not let sportsbook odds determine the prediction.
- Freeze and archive predictions before looking at prices.
- Grade every frozen probability, including passes.
- Append results; never rewrite an old lock.
- Retrain challengers after grading when lessons justify a change.
- Do not promote a challenger merely because it fits the latest card.
- Keep winner, method, and timing models separate so errors can be diagnosed.
- Label tape evidence honestly: full fight, highlights, clip, report/statistics, or unavailable.
- Run seeded 10,000-trial simulations per fight/layer when producing an actual card.
- Never claim a simulation, trained model, or code change unless it was actually executed and saved.

## Historical continuity

The September 15, 2026 project handoff is the source of truth for the recoverable pre-repository history. It records:

- preserved official roles: winner v0.3.1, method v0.4.0, round/timing v0.3.1;
- 64 clean UFC fights through UFC Paris with winner 36-28, displayed method 28-36, and winner+method 15-49;
- a demonstrated decision-heavy method bias: 37 DEC / 25 KO / 2 SUB predicted versus 21 DEC / 31 KO / 12 SUB actual;
- strong Paris timing-market directional grading, but correlated observations that must not be treated as independent bets;
- an experimental v0.26 update that was executed in a prior workspace but not safely archived, so it is **not** treated as a recoverable trained package here.

This repository starts by preserving that history and rebuilding forward without inventing missing artifacts.

## Status

**Repository scaffold / research rebuild. No new UFC model has been promoted from this repo yet.**

See `docs/MODEL_GOVERNANCE.md` and `docs/HISTORICAL_HANDOFF.md`.
