# Backend Maintenance Validation

The GitHub Actions maintenance workflow is manual-only now. By default it runs a non-destructive smoke check:

```bash
gh workflow run ci-backend-maintenance.yml -f smoke_days=30
```

To run a full recompute from the dispatch UI, select `refresh_mode=full`.

Supabase Cron now owns the scheduled full refresh path. The scheduler only enqueues work and dispatches the workflow with a queue `job_id`; the Python worker still performs the actual Elo recompute inside GitHub Actions.

`--smoke-days` is validation-only and now requires `--dry-run` if you call the script directly:

```bash
cd packages/backend
uv run python src/regional_elo.py --smoke-days 30 --dry-run
```

For a full refresh, run the script with `--apply` and without `--smoke-days` from the real scheduler or an explicit maintenance task:

```bash
cd packages/backend
uv run python src/regional_elo.py --apply
```

If you need to replay a queued job manually, pass the queue id explicitly:

```bash
cd packages/backend
uv run python src/regional_elo.py --apply --job-id 00000000-0000-0000-0000-000000000000
```

The maintenance workflow accepts the same optional `job_id` input:

```bash
gh workflow run ci-backend-maintenance.yml -f refresh_mode=full -f job_id=<job-uuid>
```

See `packages/backend/docs/elo-cron-architecture.md` for the enqueue, dispatch, stale-job cleanup, and secret requirements.

The local and CI checks use the same validation script:

```bash
cd packages/backend
SUPABASE_URL=... SUPABASE_SERVICE_KEY=... uv run python src/ci_backend_checks.py all
```

Run an individual check with one of:

```bash
uv run python src/ci_backend_checks.py views
uv run python src/ci_backend_checks.py data-integrity
uv run python src/ci_backend_checks.py regional-elo
```

The script retries transient `5xx` responses and prints a per-check summary before exiting non-zero on failure.
