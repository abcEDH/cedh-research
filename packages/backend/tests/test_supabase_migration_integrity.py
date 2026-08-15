import unittest
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
ELO_TIERS_MIGRATION = MIGRATIONS_DIR / "20260726000000_elo_ranking_eligibility_tiers.sql"
GAME_LEVEL_ELIGIBILITY_MIGRATION = MIGRATIONS_DIR / "20260727042641_ranking_game_level_eligibility.sql"


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


if __name__ == "__main__":
    unittest.main()
