# Prefect backend deployment

The production backend refresh is orchestrated by the `daily-backend-refresh`
Prefect flow. Supabase remains the durable job ledger; Prefect owns scheduling,
task visibility, and execution.

## Build the image

Build from the repository root because the Dockerfile copies the backend lockfile
and source tree:

```bash
docker build -f packages/backend/Dockerfile \
  -t ghcr.io/abcedh/cedh-backend:main .
docker push ghcr.io/abcedh/cedh-backend:main
```

The flow reads these runtime values from Prefect Secret blocks, falling back to
environment variables for local/container execution:

- `cedh-supabase-url` from `SUPABASE_URL`
- `cedh-supabase-service-key` from `SUPABASE_SERVICE_KEY`
- `cedh-topdeck-api-key` from `TOPDECK_API_KEY`
- optional `cedh-supabase-db-url` from `SUPABASE_DB_URL`

Create the blocks in Prefect Cloud. The deployment uses these exact block names;
populate them from the team secret manager without committing their values to
`prefect.yaml` or source control.

The current first deployment uses the `cedh-managed` Prefect Managed pool so it
can be tested without provisioning a separate cloud account. Managed execution
clones `main` and installs the backend packages at runtime. It is intentionally
an evaluation path; the custom image below is the production target.

## Register the deployment

Create or select a work pool that executes Docker containers, then register the
deployment from the repository root so the entrypoint path matches the
deployment configuration:

```bash
uv run --project packages/backend prefect deploy \
  --prefect-file packages/backend/prefect.yaml
```

The deployment is scheduled for 06:00 UTC daily. Run it manually first:

```bash
uv run prefect deployment run 'daily-backend-refresh/daily-backend-refresh'
```

Verify that the Prefect run creates an `ingestion_jobs` row with
`trigger_source = 'prefect'`, then an `elo_maintenance_jobs` row after ingestion
completes. The migrations `20260903010000_prefect_backend_dispatch.sql` and
`20260903020000_prefect_enqueue_idempotency.sql` prepare the schema and enqueue
RPCs but intentionally leave the legacy GitHub Actions dispatch schedules active.
Only after that verification, disable the legacy schedules manually:

```sql
SELECT cron.unschedule(jobname)
FROM cron.job
WHERE jobname IN (
  'ingestion-refresh-daily-dispatch',
  'elo-refresh-daily-dispatch'
);
```

## Rollback

Pause the Prefect deployment and manually dispatch the existing GitHub workflow
with a queued job ID. The Supabase stale-job cleanup remains available during
and after the migration.
