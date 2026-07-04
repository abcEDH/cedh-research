import unittest
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260704000000_topdeck_webhook_events.sql"
)


class TopdeckWebhookMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(MIGRATION_PATH.exists(), f"Migration not found at {MIGRATION_PATH}")
        self.source = MIGRATION_PATH.read_text()

    def test_delivery_id_is_unique(self) -> None:
        self.assertIn("CREATE UNIQUE INDEX IF NOT EXISTS webhook_events_delivery_id_key", self.source)

    def test_rls_enabled_without_public_read(self) -> None:
        self.assertIn("ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY", self.source)
        # Payloads can contain player PII — no anon/public access, unlike
        # ingestion_jobs.
        self.assertNotIn("GRANT SELECT ON webhook_events", self.source)
        self.assertNotIn('"Public read access"\n  ON webhook_events', self.source)

    def test_trigger_source_check_includes_webhook(self) -> None:
        self.assertIn("'cron','manual','edge_function','webhook'", self.source)
        self.assertIn("ADD COLUMN IF NOT EXISTS target_tid", self.source)

    def test_targeted_enqueue_shares_daily_advisory_lock(self) -> None:
        enqueue_body = self.source.split("enqueue_targeted_ingestion", 1)[1]
        self.assertIn("pg_advisory_xact_lock(8675310)", enqueue_body)

    def test_processing_trigger_is_exception_safe(self) -> None:
        trigger_body = self.source.split("process_webhook_event", 1)[1]
        self.assertIn("EXCEPTION WHEN OTHERS THEN", trigger_body)
        self.assertIn("'error'", trigger_body)

    def test_only_real_tournament_finished_events_enqueue(self) -> None:
        self.assertIn("NEW.event_type <> 'tournament.finished'", self.source)
        self.assertIn("NEW.is_test", self.source)

    def test_dispatch_reuses_existing_edge_function(self) -> None:
        self.assertIn("/functions/v1/trigger-ingestion-refresh", self.source)
        self.assertIn("net.http_post", self.source)
        self.assertIn("vault.decrypted_secrets", self.source)


if __name__ == "__main__":
    unittest.main()
