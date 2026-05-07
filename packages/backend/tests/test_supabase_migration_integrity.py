import unittest
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"


class SupabaseMigrationIntegrityTests(unittest.TestCase):
    def test_migration_versions_are_unique(self) -> None:
        versions = []
        for path in MIGRATIONS_DIR.glob("*.sql"):
            versions.append(path.name.split("_", 1)[0])

        duplicates = sorted(
            {version for version in versions if versions.count(version) > 1}
        )

        self.assertEqual(duplicates, [], f"duplicate migration versions found: {duplicates}")

    def test_security_hardening_part2_uses_valid_plpgsql_array_loop(self) -> None:
        sql = (MIGRATIONS_DIR / "20260408000000_security_hardening_part2.sql").read_text()

        self.assertIn("FOR table_name IN", sql)
        self.assertIn("SELECT unnest(ARRAY[", sql)
        self.assertNotIn("FOREACH table_name IN ARRAY[", sql)

    def test_public_surface_migration_keeps_public_access(self) -> None:
        sql = (MIGRATIONS_DIR / "20260508000000_keep_public_surfaces_and_rls.sql").read_text()

        self.assertIn("ALTER VIEW player_commander_entries SET (security_invoker = true);", sql)
        self.assertIn("GRANT SELECT ON TABLE", sql)
        self.assertIn("ALTER TABLE public.global_elo_state_activity ENABLE ROW LEVEL SECURITY;", sql)
        self.assertIn("ALTER TABLE public.global_elo_game_events ENABLE ROW LEVEL SECURITY;", sql)

    def test_regional_elo_leaderboard_preserves_existing_column_order(self) -> None:
        sql = (MIGRATIONS_DIR / "20260408010000_include_unknown_state_global_elo_games.sql").read_text()

        self.assertIn("s.region_key AS primary_region_key,\n    s.country_key AS primary_country_key,\n    NULL::text AS country_key", sql)
        self.assertNotIn("s.country_key AS primary_country_key,\n    s.region_key AS primary_region_key,", sql)

    def test_canonical_leaderboard_counts_preserves_existing_column_order(self) -> None:
        sql = (MIGRATIONS_DIR / "20260409140000_fix_global_leaderboard_canonical_counts.sql").read_text()

        self.assertIn("g.player_id,\n    p.name AS player_name", sql)
        self.assertIn("s.region_key AS primary_region_key,\n    s.country_key AS primary_country_key,\n    NULL::text AS country_key", sql)
        self.assertNotIn("NULL::text AS country_key,\n    g.player_id", sql)
        self.assertIn("MAX(game_date)::date AS last_game_date", sql)


if __name__ == "__main__":
    unittest.main()
