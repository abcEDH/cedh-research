# Backend Maintenance Validation

The GitHub Actions maintenance workflow and local checks use the same script:

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
