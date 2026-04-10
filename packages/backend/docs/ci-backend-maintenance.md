# Backend Maintenance Validation

The GitHub Actions maintenance workflow is manual-only now. By default it runs a non-destructive smoke check:

```bash
gh workflow run ci-backend-maintenance.yml -f smoke_days=30
```

To run a full recompute from the dispatch UI, select `refresh_mode=full`.

`--smoke-days` is validation-only and now requires `--dry-run` if you call the script directly:

```bash
cd packages/backend
uv run python src/regional_elo.py --smoke-days 30 --dry-run
```

For a full refresh, run the script without `--smoke-days` from the real scheduler or an explicit maintenance task.

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
