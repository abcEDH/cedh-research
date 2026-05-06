# 0005 - Persisted Read Models Over Request-Time Computation

## Status
Accepted

## Context
The leaderboard, regional Elo, and player-profile pages were originally computing enriched fields (TopDeck Elo rank, latest active commander, latest tournament metadata, country slices) at request time by joining several base tables in the Next.js server. This produced:
- Slow page TTFB on cold cache.
- Visible truncation when query limits were hit (e.g. Tymna/Kraum missing — PR #154).
- Brittle fallback paths that broke when a base view was missing or empty (PR #82).

## Decision
Adopt a **read-model** pattern: backend ingestion / cron jobs compute and persist enriched fields directly into the read tables that the frontend queries.

Concretely:
- The active leaderboard table carries `topdeck_elo`, `topdeck_elo_rank`, country/region slice fields, and latest-tournament metadata as columns.
- `player_commander_profiles` carries the player's latest tournament + commander metadata as columns.
- The frontend queries these tables directly with no request-time enrichment joins.

Recompute happens in cron jobs (see ADR 0007), not on the read path.

## Consequences

**Easier**
- Frontend queries are flat selects with predictable latency.
- Fallback logic on the read path shrinks dramatically.
- Pages can be cached aggressively (see ADR 0006) because the data they read is stable between recompute cycles.

**Harder**
- Schema changes propagate through migrations + ingestion code + read query — wider blast radius per change.
- Stale data is now possible if the recompute cron fails silently.
- Testing requires keeping ingestion and read consumers in sync (e.g. PR #154 had to bump active-commander limits and cache keys together).

### Cross-Repo Impact
`cedh-research` only.

## Sources
- PR #133 — "feat(backend): persist latest tournament + commander metadata on player_commander_profiles"
- PR #134 — "feat(backend): persist topdeck_elo + country slices on leaderboard"
- PR #145 — "perf(web): consume regional Elo read models"
- PR #154 — "fix: resolve commander performance truncation and decklist parsing bugs"
