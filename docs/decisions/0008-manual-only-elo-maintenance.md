# 0008 - Elo Maintenance Is Manual-Only

## Status
Accepted

## Context
The Elo recompute path is expensive (it touches global Elo game results, rebuilds ratings, and refreshes downstream materialized views) and has fallback complexity — when `global_elo_game_results` is missing it falls back to the legacy `regional_elo_game_results` path. Running this on a recurring schedule produced:
- Long retry loops on 404s when expected views were missing (PR #82).
- Noisy CI signal that obscured real regressions.
- Background recompute storms when migrations were in flight.

## Decision
The Elo maintenance workflow (`ci-backend-maintenance.yml`) runs **only on manual dispatch**. It is not triggered by:
- A cron schedule
- Push to `main`
- PR events
- Any other automated trigger

Operational use looks like: open the workflow in GitHub Actions → "Run workflow" → choose branch and parameters → confirm.

## Consequences

**Easier**
- CI noise drops to zero in steady state.
- Recompute is gated by an explicit human decision; rollbacks are simple ("don't run it").
- Migration days stop fighting the recompute pipeline.

**Harder**
- Forgetting to run it after a meaningful data change leaves stale Elo aggregates indefinitely.
- There is no SLO on freshness — it is "whenever a human runs it".
- Non-author engineers need to know this workflow exists and when to dispatch it.

### Cross-Repo Impact
`cedh-research` only.

## Sources
- PR #82 — "Harden regional Elo job against missing global tables"
- PR #89 — "ci: manual-only Elo maintenance"
- `.github/workflows/ci-backend-maintenance.yml`
