# 0007 - Split Scheduled Ingestion and Elo Maintenance Pipelines

## Status
Accepted

## Context
Originally, scheduled ingestion (pulling new tournament data from TopDeck, normalizing, persisting) and Elo recompute (rebuilding rating tables from accumulated game results) shared one CI workflow. This caused three reliability gaps (PR #120):
1. A failure in either half could mark the other half failed.
2. Recurrence cadences differ — ingestion wants frequent, Elo wants on-demand.
3. Failure-mode recovery differs — ingestion is idempotent re-runnable, Elo recompute requires explicit job lifecycle tracking.

## Decision
Operate two independent pipelines:

| Pipeline | Workflow | Trigger | Failure mode |
|----------|----------|---------|---------------|
| Scheduled ingestion | `.github/workflows/ci-backend-ingestion.yml` | Cron schedule (data freshness target) | Re-run is safe; idempotent |
| Backend maintenance / Elo recompute | `.github/workflows/ci-backend-maintenance.yml` | Manual dispatch only (see ADR 0008) | Marks queued job rows failed in Supabase |

Each pipeline owns its own MV refresh, validation, and lifecycle tracking. PR-time CI uses a third workflow (`ci-backend.yml`) that runs unit/integration tests only — no live ingestion or recompute on PR (PR #54, #80).

## Consequences

**Easier**
- Either pipeline can fail without poisoning the other.
- PR CI is fast and deterministic — no Supabase-pagination flakiness.
- Ingestion can run frequently without invoking the expensive recompute path.

**Harder**
- Three workflows to keep in sync on shared concerns (Supabase secrets, Python dep install, validation scripts).
- "Where do I run X?" requires reading the workflow names — no single dashboard.

### Cross-Repo Impact
`cedh-research` only.

## Sources
- PR #54 — "ci: split backend smoke checks from maintenance runs"
- PR #80 — "ci: remove redundant ingestion from PR workflow"
- PR #117 — "Backend cron pipeline hardening and MV refresh"
- PR #120 — "Architecture: split scheduled ingestion into its own Cron pipeline"
- `.github/workflows/ci-backend-ingestion.yml`
- `.github/workflows/ci-backend-maintenance.yml`
