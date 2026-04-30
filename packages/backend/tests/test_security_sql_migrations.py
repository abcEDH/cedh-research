import unittest
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
SECURITY_FOLLOWUP_MIGRATION = MIGRATIONS_DIR / "20260430000000_security_hardening_followup.sql"


class SecuritySqlMigrationTests(unittest.TestCase):
    def test_followup_hardening_covers_active_elo_tables(self) -> None:
        sql = SECURITY_FOLLOWUP_MIGRATION.read_text()

        self.assertIn("ALTER TABLE public.global_elo_game_events ENABLE ROW LEVEL SECURITY;", sql)
        self.assertIn("ALTER TABLE public.global_elo_state_activity ENABLE ROW LEVEL SECURITY;", sql)
        self.assertIn('CREATE POLICY "Public read access" ON public.global_elo_game_events', sql)
        self.assertIn('CREATE POLICY "Public read access" ON public.global_elo_state_activity', sql)

    def test_followup_hardening_fixes_views_and_function_search_path(self) -> None:
        sql = SECURITY_FOLLOWUP_MIGRATION.read_text()

        self.assertIn("ALTER VIEW public.regional_elo_data_validity SET (security_invoker = true);", sql)
        self.assertIn("ALTER VIEW public.player_commander_entries SET (security_invoker = true);", sql)
        self.assertIn("ALTER VIEW public.regional_elo_game_event_log SET (security_invoker = true);", sql)
        self.assertIn("ALTER FUNCTION public.compute_game_key(uuid, integer, text, integer, boolean)", sql)
        self.assertIn("ALTER FUNCTION public.set_canonical_game_key()", sql)


if __name__ == "__main__":
    unittest.main()
