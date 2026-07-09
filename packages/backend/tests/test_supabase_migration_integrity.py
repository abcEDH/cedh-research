import unittest
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"

CEDH_GUARD = "t.game = 'Magic: The Gathering' AND t.format = 'EDH'"


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

    def test_multigame_deck_identities_scopes_commanders_by_game(self) -> None:
        sql = (MIGRATIONS_DIR / "20260706000000_multigame_deck_identities.sql").read_text()

        self.assertIn("ADD COLUMN IF NOT EXISTS game TEXT NOT NULL DEFAULT 'Magic: The Gathering'", sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS identity_kind TEXT NOT NULL DEFAULT 'commander'", sql)
        self.assertIn("DROP CONSTRAINT IF EXISTS commanders_name_key", sql)
        self.assertIn("ADD CONSTRAINT commanders_game_name_key UNIQUE (game, name)", sql)
        self.assertIn("CHECK (identity_kind IN ('commander', 'legend', 'leader', 'archetype', 'unknown'))", sql)

    def test_multigame_tournaments_index_covers_game_format_recency(self) -> None:
        sql = (MIGRATIONS_DIR / "20260706000001_tournaments_game_format_index.sql").read_text()

        self.assertIn("idx_tournaments_game_format_date", sql)
        self.assertIn("ON tournaments(game, format, start_date DESC)", sql)

    def test_elo_view_scoping_guards_and_preserves_column_order(self) -> None:
        sql = (MIGRATIONS_DIR / "20260706000002_scope_cedh_elo_views.sql").read_text()

        self.assertIn(f"WHERE {CEDH_GUARD}", sql)
        # Column order must be byte-for-byte the 20260524000000 definition.
        self.assertIn(
            "SELECT\n  g.id AS game_id,\n  g.tournament_id,\n  t.start_date,",
            sql,
        )
        self.assertIn("gp.seat_position\nFROM games g", sql)
        self.assertIn("ALTER VIEW regional_elo_game_results SET (security_invoker = true);", sql)
        self.assertIn("ALTER VIEW global_elo_game_results SET (security_invoker = true);", sql)

    def test_analytics_view_scoping_guards_every_recreated_surface(self) -> None:
        sql = (MIGRATIONS_DIR / "20260706000003_scope_cedh_analytics_views.sql").read_text()

        commanders_guard = "c.game = 'Magic: The Gathering'"
        self.assertIn(CEDH_GUARD, sql)
        self.assertIn(commanders_guard, sql)
        for view_name in (
            "commander_stats",
            "commander_head_to_head",
            "player_tournament_journey",
            "pod_composition",
            "player_seat_distribution",
            "commander_meta_monthly",
            "commander_momentum",
            "commander_first_appearances",
            "player_commander_entries",
        ):
            self.assertIn(f"CREATE OR REPLACE VIEW {view_name} AS", sql, view_name)
            self.assertIn(f"ALTER VIEW {view_name} SET (security_invoker = true);", sql, view_name)
        for matview_name in (
            "commander_weekly_trends",
            "commander_monthly_trends",
            "card_frequencies_by_commander",
            "card_frequencies_global",
            "card_performance_by_commander",
            "card_performance_global",
        ):
            self.assertIn(f"DROP MATERIALIZED VIEW IF EXISTS {matview_name}", sql, matview_name)
            self.assertIn(f"CREATE MATERIALIZED VIEW {matview_name} AS", sql, matview_name)
        # Retired surfaces must not come back.
        self.assertNotIn("CREATE OR REPLACE VIEW round_win_rates", sql)
        self.assertNotIn("CREATE OR REPLACE VIEW seat_position_stats", sql)

    def test_deck_identity_read_models_define_multigame_surfaces(self) -> None:
        sql = (MIGRATIONS_DIR / "20260713000000_deck_identity_read_models.sql").read_text()

        self.assertIn("CREATE OR REPLACE VIEW deck_identity_stats AS", sql)
        self.assertIn("SELECT t.game, t.format, c.id AS identity_id, c.name, c.identity_kind,", sql)
        self.assertIn("CREATE MATERIALIZED VIEW meta_share_weekly AS", sql)
        self.assertIn(
            "CREATE UNIQUE INDEX idx_meta_share_weekly_pk\nON meta_share_weekly(game, format, week, identity_id);",
            sql,
        )
        self.assertIn("CREATE OR REPLACE FUNCTION refresh_meta_share_weekly()", sql)
        self.assertIn("SECURITY DEFINER", sql)
        self.assertIn("ALTER VIEW deck_identity_stats SET (security_invoker = true);", sql)
        self.assertIn("GRANT SELECT ON deck_identity_stats TO anon, authenticated;", sql)

    def test_canonical_leaderboard_counts_preserves_existing_column_order(self) -> None:
        sql = (MIGRATIONS_DIR / "20260409140000_fix_global_leaderboard_canonical_counts.sql").read_text()

        self.assertIn("g.player_id,\n    p.name AS player_name", sql)
        self.assertIn("s.region_key AS primary_region_key,\n    s.country_key AS primary_country_key,\n    NULL::text AS country_key", sql)
        self.assertNotIn("NULL::text AS country_key,\n    g.player_id", sql)
        self.assertIn("MAX(game_date)::date AS last_game_date", sql)


if __name__ == "__main__":
    unittest.main()
