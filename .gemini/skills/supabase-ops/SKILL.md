---
name: supabase-ops
description: Operations for Supabase database management, migrations, and materialized view refreshes. Use when you need to run SQL migrations, refresh card performance views, or debug data ingestion issues in Supabase.
---

# Supabase Operations

## Workflows

### Running Migrations
1. Prefer replaying the migration chain locally before pushing:
   - `supabase start`
   - `supabase db reset --local --no-seed --yes`
2. Use `supabase db push` to push new migrations from `packages/backend/supabase/migrations/` only after the replay passes.
3. Ensure `DB_PASSWORD` is available or `DATABASE_URL` is set in the environment.
4. Check for drift before and after changes:
   - `supabase migration list`
   - `supabase db reset --local --no-seed --yes`
   - `python -m unittest packages.backend.tests.test_ingestion_sql_migrations packages.backend.tests.test_regional_elo_leaderboard_migration`

### Migration Safety Rules
- Treat `CREATE OR REPLACE VIEW` as a contract, not a refactor point.
- Do not change a view column's order, name, or type in place unless you also drop and recreate the view.
- Avoid `SELECT *` in replayed views or unions unless the output shape is pinned elsewhere.
- Cast aggregate columns explicitly to preserve the existing column type across replays.
- If a migration depends on an optional extension or schema object, guard it explicitly with `to_regclass()`, `pg_extension`, or a `DO $$ ... EXCEPTION WHEN undefined_table` block.
- If preview fails on a later migration, inspect the exact statement number and the committed SQL in that file before touching anything else.

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

### Debugging Preview Drift
When Supabase Preview fails, use the following order:
1. Capture the exact `statement N`, file name, and SQL snippet.
2. Compare the local file to the committed version with `git show HEAD:packages/backend/supabase/migrations/<file>.sql`.
3. Inspect the live object shape with:
   - `select pg_get_viewdef('public.<view>'::regclass, true);`
   - `select ordinal_position, column_name, data_type from information_schema.columns where table_schema = 'public' and table_name = '<view>' order by ordinal_position;`
   - `select * from supabase_migrations.schema_migrations order by version;`
4. If the error involves a repeated `CREATE OR REPLACE VIEW`, verify all earlier migrations define the same output contract.
5. If the error involves cron or another optional extension, confirm the migration does not assume the extension exists in preview.

## Environment Variables
- `SUPABASE_URL`: Project URL (Required)
- `SUPABASE_SERVICE_KEY`: Service role key for admin tasks (Required)
- `DATABASE_URL`: Connection string for CLI/Direct PG access (Optional)
- `DB_PASSWORD`: Password for remote database (Optional)
