# Data layout

Raw source data and derived model tables must stay separate.

Recommended folders:

- `data/raw/` — immutable source snapshots and source metadata
- `data/interim/` — cleaned event/fighter/fight tables
- `data/features/` — timestamped prefight feature snapshots
- `data/locks/` — immutable prefight prediction locks
- `data/results/` — official result labels appended after events
- `data/grades/` — grading outputs
- `artifacts/` — trained model binaries plus metadata/manifests

Do not commit secrets, sportsbook credentials, or scraped material that cannot legally be redistributed.

Every historical feature row should include enough metadata to verify the source cutoff precedes the event.
