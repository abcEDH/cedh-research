# 0006 - Page-Level Caching with Next.js `unstable_cache`

## Status
Accepted

## Context
The home page, commanders page, and regional-Elo leaderboard are read-heavy and the underlying aggregates change much less frequently than they are read (recompute cadence is hours; read cadence is per-pageview). Doing live Supabase joins on every request was producing avoidable load and slow TTFB.

## Decision
Wrap each read-heavy server-side data fetcher in `unstable_cache` (Next.js App Router caching primitive) with:
- Explicit cache keys that include version suffixes so we can force-bust by bumping the key.
- Tags grouped by surface so a single recompute can invalidate all reads for that surface.
- Time-based revalidation (`revalidate` seconds) sized to the recompute cadence.

Surfaces using this pattern:
- Home page (PR #122)
- Commanders page (PR #116)
- Regional-Elo leaderboard (PR #118)
- Per-region "latest commanders" enrichment (added later)

When the underlying read model changes shape, the cache key is incremented in the same PR (e.g. `c9b4001 fix(web): bump leaderboard cache keys to force-refresh migrated elo data`).

## Consequences

**Easier**
- Cold-cache renders happen once per revalidation window per region; warm responses are sub-100ms.
- Cache invalidation is explicit and version-controlled (cache-key bumps show up in the diff).

**Harder**
- `unstable_cache` is unstable by name — Next.js may revise its semantics in future majors.
- Forgetting to bump the cache key after a read-model change ships stale data to users.
- Cache keys are scattered across many fetchers; no central registry.

### Cross-Repo Impact
`apps/web/` only.

## Sources
- PR #116 — "Cache commanders page data fetches"
- PR #118 — "Cache regional-elo leaderboard data fetches"
- PR #122 — "fix: cache homepage and remove stale widgets"
- Commit `c9b4001` — "fix(web): bump leaderboard cache keys to force-refresh migrated elo data"
