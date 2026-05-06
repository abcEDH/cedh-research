# 0003 - Supabase (Postgres) as System of Record

## Status
Accepted

## Context
The product needs a relational store for structured tournament/standings data, materialized aggregates for fast leaderboard reads, and a query layer accessible from both a Next.js frontend (anon key) and a Python ingestion backend (service-role key). It also needs row-level security so the public client cannot read tables it shouldn't.

## Decision
Use Supabase as the single primary datastore.
- All structured data lives in Supabase Postgres.
- Schema evolution is exclusively via SQL migrations under `packages/backend/supabase/migrations/` (51 migrations as of this writing).
- Row-Level Security (RLS) is **on** for public-facing tables; access boundaries are enforced in Postgres, not the application layer.
- Materialized views are used for leaderboard aggregates that are read more often than they change.
- Two-key access model: `NEXT_PUBLIC_SUPABASE_ANON_KEY` for the browser (public, RLS-bounded reads); `SUPABASE_SERVICE_KEY` for the backend (privileged writes, server-only).

## Consequences

**Easier**
- One source of truth for application data, analytics aggregates, and operational state.
- RLS lets the frontend query the database directly without an intermediate API tier.
- Migrations + materialized views + cron-driven recompute is a pattern the team knows.

**Harder**
- Materialized view refresh must be sequenced explicitly (see PR #117) — it is not automatic on writes.
- RLS regressions are easy to ship without a dedicated audit (PR #55 had to retrofit lockdown).
- The service-role key is a high-blast-radius secret; leaking it bypasses RLS entirely.

### Cross-Repo Impact
`cedh-research` only. Supabase project ID `msjjihqbxtgjdtapywrj` (production).

## Sources
- `packages/backend/supabase/migrations/` (51 migrations)
- README.md "Environment" section
- PR #55 — "chore: lock down public tables and limit ingest"
- PR #117 — "Backend cron pipeline hardening and MV refresh"
- PR #93222d0 — "chore(security): add RLS + view hardening followup migration"
