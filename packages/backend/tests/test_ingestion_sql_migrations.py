import unittest
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
INGESTION_JOBS_MIGRATION = MIGRATIONS_DIR / "20260420000000_ingestion_jobs.sql"
INGESTION_CRON_MIGRATION = MIGRATIONS_DIR / "20260420010000_ingestion_cron_schedule.sql"
PG_NET_MIGRATION = MIGRATIONS_DIR / "20260507010000_enable_pg_net.sql"
ELO_CRON_MIGRATION = MIGRATIONS_DIR / "20260411010000_elo_cron_schedule.sql"


class IngestionSqlMigrationTests(unittest.TestCase):
    def test_enqueue_ingestion_refresh_uses_advisory_lock_instead_of_skip_locked(self) -> None:
        sql = INGESTION_JOBS_MIGRATION.read_text()

        self.assertIn("pg_advisory_xact_lock(8675310)", sql)
        self.assertNotIn("FOR UPDATE SKIP LOCKED", sql)

    def test_fallback_elo_cron_skips_when_ingestion_job_is_active(self) -> None:
        sql = INGESTION_CRON_MIGRATION.read_text()

        self.assertIn("CREATE OR REPLACE FUNCTION trigger_elo_refresh_via_edge()", sql)
        self.assertIn("FROM ingestion_jobs", sql)
        self.assertIn("status IN ('pending', 'dispatched', 'running')", sql)
        self.assertIn("Skipping fallback Elo refresh because ingestion job", sql)
        self.assertIn("RETURN NULL;", sql)

    def test_pg_net_migration_enables_extension(self) -> None:
        sql = PG_NET_MIGRATION.read_text()

        self.assertIn("CREATE EXTENSION IF NOT EXISTS pg_net;", sql)

    def test_cron_migrations_guard_missing_cron_extension(self) -> None:
        elo_sql = ELO_CRON_MIGRATION.read_text()
        ingestion_sql = INGESTION_CRON_MIGRATION.read_text()

        for sql in (elo_sql, ingestion_sql):
            self.assertIn("to_regclass('cron.job') IS NOT NULL", sql)
            self.assertIn("EXECUTE format('SELECT cron.unschedule(%L)'", sql)
            self.assertIn("EXECUTE format(", sql)
            self.assertIn("SELECT cron.schedule(%L, %L, %L)", sql)


if __name__ == "__main__":
    unittest.main()
