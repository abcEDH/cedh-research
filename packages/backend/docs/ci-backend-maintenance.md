# Backend Maintenance Validation

The GitHub Actions maintenance workflow is manual-only now. Use the dispatch UI or the CLI to run a recent Elo recompute:

```bash
gh workflow run ci-backend-maintenance.yml -f smoke_days=30
```

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
