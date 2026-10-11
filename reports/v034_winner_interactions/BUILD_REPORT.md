# v0.34 winner interaction challenger

This challenger was created after the UFC Vegas 122 miss audit. It is **shadow-only** regardless of retrospective results.

- Base OOF: **67-34 (66.3%)**, Brier 0.2218, log loss 0.6380
- Candidate OOF: **66-35 (65.3%)**, Brier 0.2240, log loss 0.6515
- Candidate minus base Brier: **+0.0023** (lower is better)
- Candidate minus base log loss: **+0.0135** (lower is better)

## Added matchup interactions

- takedown access versus opponent takedown defense
- submission access versus opponent submission exposure
- control access versus opponent control conceded
- knockdown pressure versus opponent knockdown vulnerability
- striking output versus opponent absorption
- reach × damage-pressure interaction
- log UFC-experience gap

## Governance

These features were designed after UFC Vegas 122, so even a strong historical OOF result is not prospective proof. The current official winner reference stays unchanged until the challenger proves itself on future frozen cards.
