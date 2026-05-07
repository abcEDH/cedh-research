# pg_cron Orchestration Runbook

This is the short operational index for the scheduled ingestion and Elo flow.
For the deeper architecture and workflow details, see:

- [Elo cron architecture](./elo-cron-architecture.md)
- [Backend maintenance validation](./ci-backend-maintenance.md)
- [Data dictionary](./data_dictionary.md)

## What Matters

- `pg_cron` owns the schedule.
- The SQL wrappers enqueue job rows and call the Edge Functions through `pg_net`.
- The Edge Functions dispatch the GitHub workflows.
- The workflows run the Python workers and update the job tables.

## Current Trigger Points

- Ingestion dispatch: `0 6 * * *` UTC
- Elo dispatch: `30 6 * * *` UTC
- Stale cleanup: every 15 minutes

## Quick Checks

1. Run the wrapper:

```sql
select public.trigger_ingestion_refresh_via_edge();
select public.trigger_elo_refresh_via_edge();
```

2. Confirm the job row moved beyond `pending`:

```sql
select id, status, created_at, dispatched_at, completed_at, error_text
from ingestion_jobs
order by created_at desc
limit 5;
```

3. Check the HTTP dispatch record:

```sql
select id, status_code, content, created
from net._http_response
order by created desc
limit 5;
```

4. Confirm GitHub queued the expected workflow run.

## Recent Fixes

- The public player-log alias now reads directly from `global_elo_game_events`.
- `pg_net` is installed so `net.http_post(...)` works.
- The Edge Functions use cron-specific secrets so the runtime config is isolated from browser-facing Supabase keys.

## Common Failures

- `schema "net" does not exist` means `pg_net` is missing.
- `Requested function was not found` means the Edge Function is not deployed.
- `Unauthorized` usually means the cron secret does not match the Edge Function secret.
- `Missing required environment variable: GITHUB_PAT` means the workflow dispatch token is absent.
