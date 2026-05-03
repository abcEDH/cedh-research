# 0013 - TopDeck Attribution and API Compliance

## Status
Accepted

## Context
TopDeck.gg is the upstream source for tournament results, standings, and decklist data ingested into the product. TopDeck's API has rate limits, expects visible attribution from consumers, and has subtle data shapes (e.g. league-style standings) that need defensive normalization. Without explicit alignment to the upstream contract, the product risks (a) losing API access for terms violations, and (b) corrupting downstream analytics with malformed standings data.

## Decision
- **Visible attribution** on user-facing surfaces that show TopDeck-derived data. Tournament URLs are built via a shared `buildTopdeckTournamentUrl` helper; decklist URLs via `buildTopdeckDecklistUrl`.
- **Rate-limit handling** in the backend ingestion client — backoff on 429, bounded retry, log on terminal failure.
- **League / draw-style standings** are normalized defensively: wins/losses/draws are captured as separate fields; parse failures are logged, not swallowed.
- **API key** (`TOPDECK_API_KEY`) is a backend-only secret — never exposed to the frontend.

## Consequences

**Easier**
- Compliance posture is documented and centralized in the ingestion client.
- Attribution surfaces consistently — no per-page divergence.
- Adding a new TopDeck-derived view doesn't require re-deriving URL conventions.

**Harder**
- Upstream schema changes still require a coordinated migration on our side.
- Rate-limit-aware retry logic increases ingestion runtime variability.

### Cross-Repo Impact
`cedh-research` only.

## Sources
- PR #53 — "feat: checkpoint TopDeck compliance and attribution"
- Commits extracting `buildTopdeckTournamentUrl` and `buildTopdeckDecklistUrl` into shared utility
- `packages/backend/src/ingest.py` (ingestion client)
- README — `TOPDECK_API_KEY` is listed as a backend-only env var
