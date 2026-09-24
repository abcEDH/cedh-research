import unittest
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
ELO_TIERS_MIGRATION = MIGRATIONS_DIR / "20260726000000_elo_ranking_eligibility_tiers.sql"
GAME_LEVEL_ELIGIBILITY_MIGRATION = MIGRATIONS_DIR / "20260727042641_ranking_game_level_eligibility.sql"
ELO_DISPLAY_STATS_MIGRATION = MIGRATIONS_DIR / "20260916160213_get_elo_display_stats.sql"
WINRATE_MATRIX_MIGRATION = MIGRATIONS_DIR / "20260924000000_get_winrate_matrix_rpc.sql"


class SupabaseMigrationIntegrityTests(unittest.TestCase):
    def test_elo_tier_migration_exposes_canonical_eligibility_views(self) -> None:
        sql = ELO_TIERS_MIGRATION.read_text()

        for view_name in (
            "games_ranking_eligible",
            "games_local_eligible",
            "games_all_eligible",
            "games_elo_tiers",
        ):
            self.assertIn(f"CREATE OR REPLACE VIEW public.{view_name}", sql)
        self.assertIn("NULLIF(BTRIM(te.decklist_text), '')", sql)
        self.assertIn("ranking_eligible", sql)
        self.assertIn("local_eligible", sql)
        self.assertNotIn("WHERE entry_id IN (SELECT", sql)

    def test_migration_versions_are_unique(self) -> None:
        versions = []
        for path in MIGRATIONS_DIR.glob("*.sql"):
            versions.append(path.name.split("_", 1)[0])

        duplicates = sorted({version for version in versions if versions.count(version) > 1})

        self.assertEqual(duplicates, [], f"duplicate migration versions found: {duplicates}")

    def test_ranking_eligibility_is_game_level_without_decklist_filter(self) -> None:
        sql = GAME_LEVEL_ELIGIBILITY_MIGRATION.read_text()

        self.assertIn("t.player_count >= 30", sql)
        self.assertIn("AS ranking_eligible", sql)
        self.assertNotIn("decklist_text", sql)
        self.assertNotIn("decklist_url", sql)

    def test_elo_display_stats_matches_game_level_eligibility_and_bounds_ids(self) -> None:
        sql = ELO_DISPLAY_STATS_MIGRATION.read_text()

        self.assertIn("p.topdeck_id = ANY (p_topdeck_ids[1:50])", sql)
        self.assertNotIn("decklist_text", sql)
        self.assertNotIn("decklist_url", sql)

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

        expected_columns = (
            "s.region_key AS primary_region_key,\n"
            "    s.country_key AS primary_country_key,\n"
            "    NULL::text AS country_key"
        )
        self.assertIn(expected_columns, sql)
        self.assertNotIn("s.country_key AS primary_country_key,\n    s.region_key AS primary_region_key,", sql)

    def test_sweep_pending_migration_uses_token_based_compare_and_clear(self) -> None:
        """#314 follow-up hardening: the ack must be a compare-and-clear
        keyed on a token, not an unconditional read-and-clear, so a failed
        rebuild or a stale ack can't drop or clobber a pending request. See
        ``test_consume_partner_commander_sweep_pending.py`` for the Python
        side of this contract.
        """
        sql = (MIGRATIONS_DIR / "20260815020000_partner_commander_sweep_pending.sql").read_text()

        self.assertIn("token         uuid", sql)
        self.assertIn("RETURNS uuid", sql)
        self.assertIn("gen_random_uuid()", sql)
        self.assertIn("consume_partner_commander_sweep_pending(\n  p_token uuid\n)", sql)
        self.assertIn("AND token = p_token", sql)
        self.assertIn("AND pending = true", sql)

    def test_sweep_pending_migration_restricts_rpcs_to_service_role(self) -> None:
        """These are internal maintenance RPCs (mark/consume the sweep-pending
        flag) that must not be callable by anon/authenticated PostgREST
        clients -- Postgres grants EXECUTE to PUBLIC by default, so an
        explicit revoke is required. Matches the house pattern used by e.g.
        20260511235955_global_elo_incremental_snapshot_rpcs.sql and
        20260618183116_active_global_elo_player_ids_rpc.sql.
        """
        sql = (MIGRATIONS_DIR / "20260815020000_partner_commander_sweep_pending.sql").read_text()

        self.assertIn(
            "REVOKE ALL ON FUNCTION mark_partner_commander_sweep_pending(integer) FROM PUBLIC, anon, authenticated;",
            sql,
        )
        self.assertIn(
            "REVOKE ALL ON FUNCTION consume_partner_commander_sweep_pending(uuid) FROM PUBLIC, anon, authenticated;",
            sql,
        )
        self.assertIn("GRANT EXECUTE ON FUNCTION mark_partner_commander_sweep_pending(integer) TO service_role;", sql)
        self.assertIn("GRANT EXECUTE ON FUNCTION consume_partner_commander_sweep_pending(uuid) TO service_role;", sql)

    def test_canonical_leaderboard_counts_preserves_existing_column_order(self) -> None:
        sql = (MIGRATIONS_DIR / "20260409140000_fix_global_leaderboard_canonical_counts.sql").read_text()

        self.assertIn("g.player_id,\n    p.name AS player_name", sql)
        expected_columns = (
            "s.region_key AS primary_region_key,\n"
            "    s.country_key AS primary_country_key,\n"
            "    NULL::text AS country_key"
        )
        self.assertIn(expected_columns, sql)
        self.assertNotIn("NULL::text AS country_key,\n    g.player_id", sql)
        self.assertIn("MAX(game_date)::date AS last_game_date", sql)

    def test_winrate_matrix_migration_defines_expected_rpc_surface(self) -> None:
        """#147: get_winrate_matrix's public signature, its shared Wilson CI and
        top-N-by-metashare helpers, and the grants that expose all three to
        PostgREST. See test_wilson_ci_helper.py for the pure-Python mirror of
        the CI formula and test_winrate_matrix_integration.py for the opt-in
        live-database fixture check.
        """
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        self.assertIn("CREATE OR REPLACE FUNCTION public.wilson_ci_95(", sql)
        self.assertIn("CREATE OR REPLACE FUNCTION public.top_commanders_by_metashare(", sql)
        self.assertIn(
            "CREATE OR REPLACE FUNCTION public.get_winrate_matrix(\n  top_n integer DEFAULT 30,\n"
            "  days_back integer DEFAULT 180\n)",
            sql,
        )
        self.assertIn(
            "RETURNS TABLE (\n  deck_a_commander_id uuid,\n  deck_b_commander_id uuid,\n"
            "  games_played bigint,\n  wins bigint,\n  losses bigint,\n  draws bigint,\n"
            "  point_winrate numeric,\n  ci_low numeric,\n  ci_high numeric\n)",
            sql,
        )
        for fn in (
            "wilson_ci_95(bigint, bigint)",
            "top_commanders_by_metashare(integer, integer)",
            "get_winrate_matrix(integer, integer)",
        ):
            for role in ("anon", "authenticated", "service_role"):
                self.assertIn(f"GRANT EXECUTE ON FUNCTION public.{fn} TO {role};", sql)

    def test_winrate_matrix_forces_exact_mirror_cell_winrate(self) -> None:
        """Acceptance criterion on #147: a commander vs itself must return
        exactly 50%, not an even/odd approximation of the split."""
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        self.assertIn("WHEN c.x_a_commander_id = c.x_b_commander_id THEN 0.5::numeric", sql)
        self.assertIn("x_top_games AS x_games,\n      ROUND(x_top_games / 2.0)::bigint AS x_wins,", sql)

    def test_winrate_matrix_omits_empty_cells_and_excludes_byes(self) -> None:
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        self.assertIn("WHERE c.x_games > 0", sql)
        self.assertIn("a.result <> 'bye'", sql)
        self.assertIn("b.result <> 'bye'", sql)
        self.assertIn("gp.result <> 'bye'", sql)


if __name__ == "__main__":
    unittest.main()
