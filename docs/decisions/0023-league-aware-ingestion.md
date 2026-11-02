# 0023 — League-aware ingestion and consistent commander forecasts

## Status

Accepted.

## Context

PR #296 expands recent ingestion to small events and leagues. Its original
implementation predates the Supabase client extraction and loses league flags
during Firestore fallback. Commander forecast ordering and its consumed
probability field also disagree after applying the latest-commander blend.

## Decision

Search 45 days with leagues enabled and no player-count floor by default. Preserve
explicit league flags; unknown flags must not overwrite known classifications.
Keep REST reads and job coordination, with an optional direct Postgres writer
for ingestion writes. Roll back failed direct operations before reusing the
connection and collect returned rows from every bulk-write page.

Publish the normalized 75/25 recency/latest blend in both `prediction_share` and
`model_share`, retaining the unblended `weighted_share`.

## Consequences

The lookback covers typical monthly leagues but cannot guarantee late finals;
older known events require targeted or manifest refreshes. Tracking unfinished
leagues independently of start date is a follow-up, not a claim of this change.
No minimum-size filter is applied to ingestion. Internal Elo remains governed
by ADR 0021's eligibility and canonical full replay.

### Cross-Repo Impact

The ingestion workflow and CLI defaults agree. Existing frontend consumers of
`prediction_share` receive the same probabilities used to rank commanders.
No database migration or live data rewrite is needed for this PR.

## Sources

- https://github.com/abcEDH/cedh-research/pull/296
- [ADR 0021](0021-tuned-internal-elo.md)
