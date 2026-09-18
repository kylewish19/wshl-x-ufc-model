# Data sources and provenance

The model must preserve source provenance and an as-of timestamp for every feature snapshot.

## Tier 1 — official UFC sources

### UFC Record Book / Stat Leaders
- https://statleaders.ufc.com/
- Career, fight, round, combined-fight, combined-round, and event views.
- Current fields include striking, grappling, timing, control/top/bottom position, takedowns, submission attempts, and finish records.

Use this as an official validation source and for current/aggregate UFC statistics where the required historical as-of value can be reconstructed.

### UFC event and athlete pages
- https://www.ufc.com/events
- https://www.ufc.com/athletes

Useful for official event/result context, scheduled bout information, fighter biographical data, and cross-checking roster/status information.

## UFCStats

- http://ufcstats.com/

Historically valuable for bout/round-level UFC statistics. The project handoff records that direct UFCStats access was challenged in the prior workspace and was **not** bypassed.

Policy:
- Use it when legally and technically accessible.
- Cache source timestamps and raw snapshots.
- Do not bypass access controls.
- Do not claim a fighter's recent UFCStats rows were refreshed unless they were actually retrieved and saved.

## Tier 2 — secondary verification

Secondary MMA record/news sources may be used to verify:
- regional/debutant fight history
- bout cancellations/replacements
- short-notice context
- result discrepancies
- non-UFC footage/event context

Any secondary field must retain its source and timestamp. Conflicts with official sources are logged, not silently overwritten.

## Tape / video evidence

Tape is not treated like an ordinary numeric scrape. Each reviewed item is stored as an evidence record with:
- fighter/fight
- source
- access timestamp
- classification: full fight / highlights / clip / report-statistics / unavailable
- observations
- confidence/reliability

## Historical reconstruction rule

A present-day career aggregate is **not** automatically valid for an old fight.

For a fight on date T, a training row may use only information known before T. Historical rolling statistics should be rebuilt from prior bouts rather than copied backward from today's totals.

## Source freshness

For each future card:
1. refresh official/current fighter information;
2. save raw snapshots where redistribution is permitted;
3. compute prefight features;
4. freeze the feature manifest and prediction lock;
5. append result labels only after the event.

If a required source is stale or unavailable, mark the feature missing and let the model's imputation/missingness logic handle it rather than inventing a value.
