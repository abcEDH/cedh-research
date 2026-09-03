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

The image needs these runtime environment variables in its Prefect work pool:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `TOPDECK_API_KEY`
- optional `SUPABASE_DB_URL` for direct Postgres operations

Do not commit those values to `prefect.yaml`.

The current first deployment uses the `cedh-managed` Prefect Managed pool so it
can be tested without provisioning a separate cloud account. Managed execution
clones `main` and installs the backend packages at runtime. It is intentionally
an evaluation path; the custom image below is the production target.

## Register the deployment

Create or select a work pool that executes Docker containers, then register the
deployment from `packages/backend`:

```bash
cd packages/backend
uv run prefect deploy
```

The deployment is scheduled for 06:00 UTC daily. Run it manually first:

```bash
uv run prefect deployment run 'daily-backend-refresh/daily-backend-refresh'
```

Verify that the Prefect run creates an `ingestion_jobs` row with
`trigger_source = 'prefect'`, then an `elo_maintenance_jobs` row after ingestion
completes. Only after that verification should the migration
`20260903010000_prefect_backend_dispatch.sql` be applied, because it disables the
legacy GitHub Actions dispatch schedules.

## Rollback

Pause the Prefect deployment and manually dispatch the existing GitHub workflow
with a queued job ID. The Supabase stale-job cleanup remains available during
and after the migration.
