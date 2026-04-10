# Elo Cron Architecture

Scheduled Global Elo maintenance now flows through a queue instead of invoking the Python worker directly from a scheduler.

## Flow

1. `pg_cron` runs `public.trigger_elo_refresh_via_edge()` once per day.
2. `trigger_elo_refresh_via_edge()` calls `enqueue_elo_refresh('cron')`.
3. If no active job already exists, the function creates one `elo_maintenance_jobs` row in `pending`.
4. The same SQL function invokes the Supabase Edge Function `trigger-elo-refresh` through `pg_net`.
5. The Edge Function validates the queued job and dispatches `.github/workflows/ci-backend-maintenance.yml` with `refresh_mode=full` and `job_id=<uuid>`.
6. `regional_elo.py --apply --job-id <uuid>` claims the job, emits heartbeats after each major write phase, and records final counts or failures.
7. A second cron job marks abandoned `pending`, `dispatched`, or `running` jobs as `stale` after 30 minutes without a heartbeat.

## Components

- Queue table: `public.elo_maintenance_jobs`
- Enqueue function: `public.enqueue_elo_refresh(trigger_source text)`
- Dispatch wrapper: `public.trigger_elo_refresh_via_edge()`
- Stale cleanup: `public.cleanup_stale_elo_jobs(stale_minutes integer)`
- Edge Function: `packages/backend/supabase/functions/trigger-elo-refresh/index.ts`
- Worker: `packages/backend/src/regional_elo.py`
- Workflow: `.github/workflows/ci-backend-maintenance.yml`

## Schedule

- Full refresh dispatch: `0 6 * * *` (06:00 UTC daily)
- Stale cleanup: `*/15 * * * *` (every 15 minutes)

Adjust the cron expressions in `20260411010000_elo_cron_schedule.sql` if the operating window changes.

## Secrets

Database Vault secrets used by `trigger_elo_refresh_via_edge()`:

- `project_url`: Supabase project URL, for example `https://<project-ref>.supabase.co`
- `anon_key`: Supabase anon key used to invoke the Edge Function

Edge Function environment variables:

- `GITHUB_PAT`: fine-grained token with GitHub Actions write access to `abcEDH/cedh-research`
- Optional overrides: `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_WORKFLOW_ID`, `GITHUB_REF`

Supabase runtime environment expected by the function:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`

## Manual Operations

- Manual smoke checks remain unchanged:
  - `gh workflow run ci-backend-maintenance.yml -f smoke_days=30`
- Manual full refreshes remain available:
  - `gh workflow run ci-backend-maintenance.yml -f refresh_mode=full`
- To replay a queued job intentionally:
  - `gh workflow run ci-backend-maintenance.yml -f refresh_mode=full -f job_id=<job-uuid>`

## Operational Notes

- The queue blocks concurrent refreshes at the enqueue stage by refusing to create a new `pending` job while any job is `pending`, `dispatched`, or `running`.
- The worker only claims jobs already in `pending` or `dispatched`, which prevents accidental replays from overwriting an already-running job row.
- `stale` jobs are terminal and intentionally unblock the next scheduled enqueue.
