import unittest
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
ELO_TIERS_MIGRATION = MIGRATIONS_DIR / "20260726000000_elo_ranking_eligibility_tiers.sql"
GAME_LEVEL_ELIGIBILITY_MIGRATION = MIGRATIONS_DIR / "20260727042641_ranking_game_level_eligibility.sql"
ELO_DISPLAY_STATS_MIGRATION = MIGRATIONS_DIR / "20260916160213_get_elo_display_stats.sql"
WINRATE_MATRIX_MIGRATION = MIGRATIONS_DIR / "20261115000000_winrate_matrix_and_pod_metrics_rpc.sql"
META_EV_MIGRATION = MIGRATIONS_DIR / "20261115010000_commander_meta_ev_rpc.sql"


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
        """#147/#148: get_winrate_matrix's and get_pod_metrics' public signatures, the shared
        Wilson CI / significance / top-N-by-metashare helpers, and the grants that expose all
        of them to PostgREST. See test_wilson_ci_helper.py for the pure-Python mirror of the CI
        formula and test_pod_top_two_derivation.py for the "top 2" placement logic.
        """
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        self.assertIn("CREATE OR REPLACE FUNCTION public.wilson_ci_95(", sql)
        self.assertIn("CREATE OR REPLACE FUNCTION public.top_commanders_by_metashare(", sql)
        self.assertIn("CREATE OR REPLACE FUNCTION public.is_rate_statistically_significant(", sql)
        self.assertIn(
            "CREATE OR REPLACE FUNCTION public.get_winrate_matrix(\n  top_n integer DEFAULT 30,\n"
            "  days_back integer DEFAULT 180\n)",
            sql,
        )
        self.assertIn(
            "CREATE OR REPLACE FUNCTION public.get_pod_metrics(\n  top_n integer DEFAULT 30,\n"
            "  days_back integer DEFAULT 180\n)",
            sql,
        )
        self.assertIn(
            "RETURNS TABLE (\n  deck_a_commander_id uuid,\n  deck_b_commander_id uuid,\n"
            "  games_played bigint,\n  wins bigint,\n  losses bigint,\n  draws bigint,\n"
            "  point_winrate numeric,\n  ci_low numeric,\n  ci_high numeric\n)",
            sql,
        )
        self.assertIn(
            "RETURNS TABLE (\n  commander_id uuid,\n  pods_present bigint,\n  wins bigint,\n"
            "  top_two bigint,\n  threat_score numeric,\n  threat_ci_low numeric,\n"
            "  threat_ci_high numeric,\n  survivability numeric,\n  survivability_ci_low numeric,\n"
            "  survivability_ci_high numeric,\n  is_statistically_significant boolean\n)",
            sql,
        )
        for fn in (
            "wilson_ci_95(bigint, bigint)",
            "top_commanders_by_metashare(integer, integer)",
            "is_rate_statistically_significant(bigint, numeric, numeric)",
            "get_winrate_matrix(integer, integer)",
            "get_pod_metrics(integer, integer)",
        ):
            for role in ("anon", "authenticated", "service_role"):
                self.assertIn(f"GRANT EXECUTE ON FUNCTION public.{fn} TO {role};", sql)

    def test_winrate_matrix_forces_exact_mirror_cell_winrate(self) -> None:
        """Acceptance criterion on #147: a commander vs itself must return exactly 50%, not an
        even/odd approximation of the split."""
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        self.assertIn("WHEN c.x_a_commander_id = c.x_b_commander_id THEN 0.5::numeric", sql)
        self.assertIn("x_top_games AS x_games,\n      ROUND(x_top_games / 2.0)::bigint AS x_wins,", sql)

    def test_winrate_matrix_omits_empty_cells_and_excludes_byes(self) -> None:
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        self.assertIn("WHERE c.x_games > 0", sql)
        self.assertIn("a.result <> 'bye'", sql)
        self.assertIn("b.result <> 'bye'", sql)
        self.assertIn("gp.result <> 'bye'", sql)

    def test_pod_metrics_shares_wilson_and_metashare_helpers_not_duplicated_math(self) -> None:
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        pod_metrics_start = sql.index("FUNCTION public.get_pod_metrics(")
        pod_metrics_body = sql[pod_metrics_start : pod_metrics_start + 4000]
        self.assertIn("public.top_commanders_by_metashare(top_n, days_back)", pod_metrics_body)
        self.assertIn(
            "CROSS JOIN LATERAL public.wilson_ci_95(pm.x_wins, pm.x_pods_present) threat_ci",
            pod_metrics_body,
        )
        self.assertIn(
            "CROSS JOIN LATERAL public.wilson_ci_95(pm.x_top_two, pm.x_pods_present) surv_ci",
            pod_metrics_body,
        )
        self.assertIn("public.is_rate_statistically_significant(", pod_metrics_body)

    def test_meta_ev_migration_defines_expected_rpc_surface(self) -> None:
        """#149: get_commander_meta_ev's signature and the grants exposing it to PostgREST. See
        test_commander_meta_ev.py for the pure-Python mirror of the weighting/fallback math.
        """
        sql = META_EV_MIGRATION.read_text()

        self.assertIn(
            "CREATE OR REPLACE FUNCTION public.get_commander_meta_ev(\n  top_n integer DEFAULT 30,\n"
            "  days_back integer DEFAULT 180,\n  min_triple_obs integer DEFAULT 10\n)",
            sql,
        )
        self.assertIn(
            "RETURNS TABLE (\n  commander_id uuid,\n  meta_ev numeric,\n  meta_ev_ci_low numeric,\n"
            "  meta_ev_ci_high numeric,\n  composition_coverage numeric,\n",
            sql,
        )
        self.assertIn("  pods_present bigint,\n", sql)
        self.assertIn("  is_statistically_significant boolean\n)", sql)
        for role in ("anon", "authenticated", "service_role"):
            self.assertIn(
                f"GRANT EXECUTE ON FUNCTION public.get_commander_meta_ev(integer, integer, integer) TO {role};",
                sql,
            )

    def test_meta_ev_depends_on_winrate_matrix_for_pairwise_fallback(self) -> None:
        sql = META_EV_MIGRATION.read_text()

        self.assertIn("FROM public.get_winrate_matrix(top_n, days_back)", sql)
        self.assertIn("min_triple_obs", sql)

    def test_meta_ev_computes_its_own_pods_present_and_significance(self) -> None:
        """Codex review finding on PR #384 (second pass): get_pod_metrics' pods_present counts
        every non-bye participation regardless of pod size, while get_commander_meta_ev only
        ever aggregates over exactly-4-player pods (its x_focal CTE) -- the two can legitimately
        disagree, so the Meta EV badge must use this RPC's own pods_present/significance, never
        borrowed from get_pod_metrics. See test_commander_meta_ev.py for the frontend-facing
        regression test of this exact scenario.
        """
        sql = META_EV_MIGRATION.read_text()

        self.assertIn("x_total_pods AS pods_present", sql)
        self.assertIn(
            "public.is_rate_statistically_significant(x_total_pods, x_meta_ev, 0.25) AS is_statistically_significant",
            sql,
        )

    def test_winrate_family_rpcs_exclude_future_dated_tournaments(self) -> None:
        """Codex review finding on PR #384: these RPCs' own windowed queries bypass the
        future-date upper bound that 20260815000000_exclude_future_dated_tournaments.sql
        established for commander_stats/commander_weekly_trends/commander_monthly_trends (a
        2030-dated TopDeck practice event previously contaminated those unbounded windows).
        Every independent windowed query across both migrations needs its own copy of the
        bound -- it is not inherited by restricting to a top-N commander_id alone, since a
        future-dated game can still be counted for an already-legitimate top-N commander.
        """
        winrate_sql = WINRATE_MATRIX_MIGRATION.read_text()
        meta_ev_sql = META_EV_MIGRATION.read_text()

        # top_commanders_by_metashare, get_winrate_matrix's x_window_games + x_overall, and
        # get_pod_metrics' x_pod_metrics: 4 independent windowed queries in this migration.
        self.assertEqual(
            winrate_sql.count("t.start_date::date <= CURRENT_DATE"),
            4,
            "expected the future-date upper bound in all 4 windowed queries",
        )
        # get_commander_meta_ev's own x_window_games CTE.
        self.assertIn("t.start_date::date <= CURRENT_DATE", meta_ev_sql)

    def test_top_commanders_by_metashare_excludes_unknown_commander_placeholder(self) -> None:
        """Codex review finding on PR #384: 'Unknown Commander' is the literal placeholder name
        persisted for unresolved decklists (sanitize_commander_payload in
        packages/backend/src/ingest.py) and is excluded from ranking views elsewhere in this
        repo (commander_weekly_trends/commander_monthly_trends, and the frontend's own
        getCommanderRankings in apps/web/src/lib/commanders/fetchers.ts). Without this
        exclusion it could occupy a top-N metashare slot and produce a meaningless matchup
        row/column, displacing a real commander. Excluded once, centrally, in the shared
        top_commanders_by_metashare helper so get_winrate_matrix, get_pod_metrics and
        get_commander_meta_ev all inherit it via their shared x_top CTE.
        """
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        fn_start = sql.index("FUNCTION public.top_commanders_by_metashare(")
        fn_body = sql[fn_start : fn_start + 1800]
        self.assertIn("JOIN commanders c ON c.id = te.commander_id", fn_body)
        self.assertIn("AND c.name <> 'Unknown Commander'", fn_body)

    def test_meta_ev_casts_total_pods_sum_to_bigint(self) -> None:
        """Codex review finding on PR #384 (third pass, P1): Postgres's SUM(bigint) returns
        numeric, not bigint. Without an explicit ::bigint cast, the resulting x_total_pods is
        numeric, which is neither implicitly coercible to
        is_rate_statistically_significant's declared `p_trials bigint` parameter (function-call
        argument resolution requires an implicit cast, and numeric->bigint is only an
        assignment-context cast) nor an exact match for the `pods_present bigint` RETURNS TABLE
        column -- so every call to get_commander_meta_ev would fail at the Postgres level.
        """
        sql = META_EV_MIGRATION.read_text()

        self.assertIn("SUM(tev.x_triple_pods)::bigint AS x_total_pods", sql)

    def test_winrate_family_rpcs_exclude_unfinished_games(self) -> None:
        """Codex review finding on PR #384 (third pass, P2): ingest.py persists an in-progress
        or not-yet-reported TopDeck pod with games.status taken directly from the API
        ("Active"/"Pending"), and is_draw_winner_id(None) treats a still-missing winner_id the
        same as a genuine TopDeck "Draw" -- so an unfinished pod currently looks identical to a
        real draw unless something excludes it. Applies the same completion-status convention
        the internal Elo eligibility views use (20260726000000_elo_ranking_eligibility_tiers.sql)
        to every independent windowed query across both migrations: the shared
        top_commanders_by_metashare cutoff, get_winrate_matrix's x_window_games + x_overall,
        get_pod_metrics' x_pod_metrics, and get_commander_meta_ev's x_window_games -- 4 in this
        migration, 1 in the other, same count as the future-date bound (same reasoning: scoping
        to a top-N commander_id alone does not exclude a specific unfinished game).
        """
        winrate_sql = WINRATE_MATRIX_MIGRATION.read_text()
        meta_ev_sql = META_EV_MIGRATION.read_text()
        status_filter = "LOWER(COALESCE(g.status, 'completed')) IN ('completed', 'complete', 'done')"

        self.assertEqual(
            winrate_sql.count(status_filter),
            5,
            "expected the unfinished-game filter in all 4 windowed queries, plus 1 mention in "
            "the module header's documentation comment",
        )
        self.assertIn(status_filter, meta_ev_sql)
        # get_pod_metrics' x_placements CTE must carry the game id forward so x_pod_metrics can
        # join games and apply the filter -- otherwise there'd be nothing to join on.
        self.assertIn("gp.game_id AS x_game_id", winrate_sql)
        self.assertIn("JOIN games g ON g.id = pl.x_game_id", winrate_sql)


if __name__ == "__main__":
    unittest.main()
