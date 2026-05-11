import unittest
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
PUBLIC_EVENT_LOG_MIGRATION = MIGRATIONS_DIR / "20260507000000_public_event_log_alias.sql"


class PublicEventLogMigrationTests(unittest.TestCase):
    def test_public_alias_reads_directly_from_global_event_table(self) -> None:
        sql = PUBLIC_EVENT_LOG_MIGRATION.read_text()

        self.assertIn("CREATE OR REPLACE VIEW public.global_elo_game_event_log AS", sql)
        self.assertIn("FROM public.global_elo_game_events e", sql)
        self.assertNotIn("FROM regional_elo_game_event_log", sql)
        self.assertIn("ALTER VIEW public.global_elo_game_event_log SET (security_invoker = true)", sql)
        self.assertIn("GRANT SELECT ON public.global_elo_game_event_log TO anon, authenticated", sql)


if __name__ == "__main__":
    unittest.main()
