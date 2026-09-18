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

- preserved historical official roles: winner v0.3.1, method v0.4.0, round/timing v0.3.1;
- 64 clean UFC fights through UFC Paris with winner 36-28, displayed method 28-36, and winner+method 15-49;
- a demonstrated decision-heavy method localization problem: 37 DEC / 25 KO / 2 SUB predicted versus 21 DEC / 31 KO / 12 SUB actual;
- strong Paris timing-market directional grading, but correlated observations that must not be treated as independent bets;
- an experimental v0.26 update that was executed in a prior workspace but not safely archived.

## Recovery status — September 18, 2026

The three recovery tasks from the handoff are now materially complete:

- the clean 64-fight ledger and append-only master audit through Paris are in GitHub;
- the stale UFC performance history has been causally rebuilt from **8,630 fights through Aug. 1** to **8,707 decisive fights through Sep. 12**, restoring 77 post-August-1 prefight rows;
- the documented lost-v0.26 residual-method idea has been rebuilt, trained and hashed as **v0.27-reconstruction**.

The exact old v0.26 binary is still not recoverable and is not being impersonated.

The new v0.27 residual challenger remains **shadow only**. On its reconstructed chronology benchmark it tied baseline accuracy but produced worse Brier score and log loss, so it has not earned promotion.

No new model from this repository has been promoted over the preserved historical champions.

See:
- `docs/RECOVERY_COMPLETE_2026-09-18.md`
- `docs/MASTER_UFC_RECORD_AUDIT_2026-09-18.md`
- `docs/MODEL_GOVERNANCE.md`
- `artifacts/v027_reconstruction/manifest.json`
