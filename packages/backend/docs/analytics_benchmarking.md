# Analytics Benchmarking

Use the backend maintenance checker to benchmark live analytics surfaces and compare results against a saved baseline.

## Run a benchmark

```bash
python packages/backend/src/ci_backend_checks.py benchmark \
  --output /tmp/analytics-benchmark.json
```

## Compare against a baseline

```bash
python packages/backend/src/ci_backend_checks.py benchmark \
  --compare-to /tmp/analytics-benchmark-baseline.json \
  --max-regression-pct 25
```

## Focus on one surface

```bash
python packages/backend/src/ci_backend_checks.py benchmark \
  --only commander_stats \
  --only regional_elo_leaderboard_state
```

## What it checks

- Captures best, median, and worst request times for each query.
- Verifies each query still returns the expected columns.
- Verifies each query still returns at least the expected minimum number of rows.
- Optionally compares the current run to a saved JSON baseline and fails on row-count, shape, or performance regressions.

## Notes

- The benchmark reads live Supabase views and RPCs, so `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` must be set.
- The harness resolves a fixture commander, card, and regional sample automatically, so the benchmark stays representative without hardcoded IDs.
