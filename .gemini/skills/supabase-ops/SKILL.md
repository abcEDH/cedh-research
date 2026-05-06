---
name: supabase-ops
description: Operations for Supabase database management, migrations, and materialized view refreshes. Use when you need to run SQL migrations, refresh card performance views, or debug data ingestion issues in Supabase.
---

# Supabase Operations

## Workflows

### Running Migrations
1. Use `supabase db push` to push new migrations from `packages/backend/supabase/migrations/`.
2. Ensure `DB_PASSWORD` is available or `DATABASE_URL` is set in the environment.

### Refreshing Materialized Views
Run the following RPC calls via the `db_ops.py` script:
- `refresh_card_frequencies()`: Updates card inclusion rates.
- `refresh_card_performance()`: Updates win rate delta stats for cards.
- `refresh_commander_trends()`: Updates weekly/monthly trend data.

Example usage:
```bash
python3 supabase-ops/scripts/db_ops.py rpc refresh_card_frequencies
```

### Troubleshooting Ingestion
Check `ingestion_jobs` and `backfill_progress_telemetry` tables for status.

## Environment Variables
- `SUPABASE_URL`: Project URL (Required)
- `SUPABASE_SERVICE_KEY`: Service role key for admin tasks (Required)
- `DATABASE_URL`: Connection string for CLI/Direct PG access (Optional)
- `DB_PASSWORD`: Password for remote database (Optional)
