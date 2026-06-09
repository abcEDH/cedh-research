import os
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import regional_elo  # noqa: E402


class RegionalEloJobLifecycleTests(TestCase):
    def test_claim_job_updates_pending_row_and_sets_github_run_id(self) -> None:
        client = Mock()
        client.update.return_value = [{"id": "job-123"}]

        claimed = regional_elo.claim_job(client, "job-123", github_run_id=456)

        self.assertTrue(claimed)
        client.update.assert_called_once_with(
            regional_elo.MAINTENANCE_JOBS_TABLE,
            {
                "status": "running",
                "started_at": client.update.call_args.args[1]["started_at"],
                "heartbeat_at": client.update.call_args.args[1]["heartbeat_at"],
                "github_run_id": 456,
            },
            {"id": "eq.job-123", "status": "in.(pending,dispatched)"},
        )

    def test_claim_job_returns_false_when_no_row_was_updated(self) -> None:
        client = Mock()
        client.update.return_value = []

        claimed = regional_elo.claim_job(client, "job-123", github_run_id=0)

        self.assertFalse(claimed)

    def test_update_job_heartbeat_only_targets_running_jobs(self) -> None:
        client = Mock()

        regional_elo.update_job_heartbeat(client, "job-123")

        client.update.assert_called_once_with(
            regional_elo.MAINTENANCE_JOBS_TABLE,
            {"heartbeat_at": client.update.call_args.args[1]["heartbeat_at"]},
            {"id": "eq.job-123", "status": "eq.running"},
        )

    def test_complete_job_records_metrics_against_running_job(self) -> None:
        client = Mock()

        regional_elo.complete_job(
            client,
            "job-123",
            {
                "ratings_count": 10,
                "state_activity_count": 20,
                "duration_seconds": 30.5,
            },
        )

        client.update.assert_called_once_with(
            regional_elo.MAINTENANCE_JOBS_TABLE,
            {
                "status": "completed",
                "completed_at": client.update.call_args.args[1]["completed_at"],
                "heartbeat_at": client.update.call_args.args[1]["heartbeat_at"],
                "ratings_count": 10,
                "state_activity_count": 20,
                "duration_seconds": 30.5,
            },
            {"id": "eq.job-123", "status": "eq.running"},
        )


class RefreshMaterializedViewsTests(TestCase):
    def test_refresh_materialized_views_calls_all_functions(self) -> None:
        client = Mock()

        result = regional_elo.refresh_materialized_views(client)

        self.assertEqual(client.rpc.call_count, 3)
        client.rpc.assert_any_call("refresh_commander_trends")
        client.rpc.assert_any_call("refresh_card_frequencies")
        client.rpc.assert_any_call("refresh_card_performance")
        self.assertEqual(result, 3)

    def test_refresh_materialized_views_continues_on_failure(self) -> None:
        client = Mock()
        client.rpc.side_effect = [
            Exception("first function failed"),
            None,
            None,
        ]

        result = regional_elo.refresh_materialized_views(client)

        self.assertEqual(client.rpc.call_count, 3)
        self.assertEqual(result, 2)

    def test_refresh_materialized_views_returns_success_count(self) -> None:
        client = Mock()

        result = regional_elo.refresh_materialized_views(client)

        self.assertEqual(result, 3)


class RegionalEloCliValidationTests(TestCase):
    def test_job_id_requires_apply(self) -> None:
        with patch.object(sys, "argv", ["regional_elo.py", "--job-id", "job-123", "--dry-run"]):
            with patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"}, clear=False):
                with self.assertRaises(SystemExit) as ctx:
                    regional_elo.main()

        self.assertEqual(ctx.exception.code, 1)


class FetchDistinctCommanderIdsTests(TestCase):
    """Validates the query used by fetch_distinct_commander_ids.

    Previously used an invalid PostgREST filter on game_participants
    (entries.tournament_id / entries.player_id) that caused 400 errors.
    The fix queries tournament_entries with a FK dot-filter on tournament_id.start_date.
    """

    @patch("regional_elo.fetch_all")
    def test_queries_tournament_entries_not_game_participants(self, mock_fetch_all: Mock) -> None:
        mock_fetch_all.return_value = []
        client = Mock()

        regional_elo.fetch_distinct_commander_ids(client, lookback_months=6)

        table_arg = mock_fetch_all.call_args[0][1]
        self.assertEqual(table_arg, "tournament_entries")

    @patch("regional_elo.fetch_all")
    def test_filters_by_tournament_start_date_via_fk(self, mock_fetch_all: Mock) -> None:
        mock_fetch_all.return_value = []
        client = Mock()

        regional_elo.fetch_distinct_commander_ids(client, lookback_months=6)

        params = mock_fetch_all.call_args[0][2]
        self.assertIn("tournament_id.start_date", params)
        self.assertTrue(params["tournament_id.start_date"].startswith("gte."))

    @patch("regional_elo.fetch_all")
    def test_excludes_rows_with_no_commander_id(self, mock_fetch_all: Mock) -> None:
        mock_fetch_all.return_value = [
            {"commander_id": "abc123"},
            {"commander_id": None},
            {"commander_id": ""},
        ]
        client = Mock()

        result = regional_elo.fetch_distinct_commander_ids(client)

        self.assertEqual(result, {"abc123"})


class GameEventsUpsertFlagTests(TestCase):
    """--include-game-events guards the 1M+ row upsert that was timing out the cron runner.

    Without the flag, global_elo_game_events must NOT be written. With the flag, it must be.
    """

    _ENV = {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"}

    def _run_main(self, extra_argv: list) -> Mock:
        """Run main() with --apply and return the SupabaseClient mock."""
        argv = ["regional_elo.py", "--apply"] + extra_argv
        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, self._ENV, clear=False):
                with patch("regional_elo.SupabaseClient") as mock_cls:
                    mock_client = Mock()
                    mock_cls.return_value = mock_client
                    mock_client.upsert.return_value = None
                    mock_client.update.return_value = []
                    with patch("regional_elo.fetch_participants_for_leaderboard", return_value=[]):
                        with patch("regional_elo.fetch_distinct_entry_ids", return_value=set()):
                            with patch("regional_elo.process_results", return_value=[{"entry_id": "e1", "opp_entry_id": "e2", "outcome": "win"}]):
                                with patch("regional_elo.update_ratings_with_games"):
                                    with patch("regional_elo.fetch_player_index", return_value={}):
                                        with patch("regional_elo.fetch_topdeck_elo_by_topdeck_id", return_value={}):
                                            with patch("regional_elo.fetch_primary_state_stats", return_value={}):
                                                with patch("regional_elo.build_active_leaderboard_rows", return_value=[]):
                                                    with patch("regional_elo.upsert_active_leaderboard_rows"):
                                                        with patch("regional_elo.delete_stale_active_leaderboard_rows"):
                                                            with patch("regional_elo.build_player_profiles", return_value=[]):
                                                                with patch("regional_elo.detect_active_players", return_value=[]):
                                                                    with patch("regional_elo.refresh_materialized_views", return_value=0):
                                                                        regional_elo.main()
                    return mock_client

    def test_game_events_upsert_skipped_by_default(self) -> None:
        mock_client = self._run_main([])

        upsert_tables = [call.args[0] for call in mock_client.upsert.call_args_list]
        self.assertNotIn("global_elo_game_events", upsert_tables)

    def test_game_events_upsert_runs_with_flag(self) -> None:
        mock_client = self._run_main(["--include-game-events"])

        upsert_tables = [call.args[0] for call in mock_client.upsert.call_args_list]
        self.assertIn("global_elo_game_events", upsert_tables)


class ProcessResultsTests(TestCase):
    def test_groups_by_game_id(self) -> None:
        rows = [
            {"game_id": "g1", "entry_id": "e1", "result": "win",  "seat_position": 1, "rating": 1500},
            {"game_id": "g1", "entry_id": "e2", "result": "loss", "seat_position": 2, "rating": 1500},
            {"game_id": "g2", "entry_id": "e3", "result": "win",  "seat_position": 1, "rating": 1500},
            {"game_id": "g2", "entry_id": "e4", "result": "loss", "seat_position": 2, "rating": 1500},
        ]
        events = regional_elo.process_results(rows)
        self.assertEqual(len(events), 2)
        pairs = {frozenset([e["entry_id"], e["opp_entry_id"]]) for e in events}
        self.assertIn(frozenset(["e1", "e2"]), pairs)
        self.assertIn(frozenset(["e3", "e4"]), pairs)
        # No cross-game pairs
        self.assertNotIn(frozenset(["e1", "e3"]), pairs)
        self.assertNotIn(frozenset(["e1", "e4"]), pairs)

    def test_does_not_explode_at_scale(self) -> None:
        # 1000 rows across 250 4-player games → ~750 events (3 per game), not millions
        rows = [
            {
                "game_id": f"g{i // 4}",
                "entry_id": f"e{i}",
                "result": "win" if i % 4 == 0 else "loss",
                "seat_position": i % 4 + 1,
                "rating": 1500,
            }
            for i in range(1000)
        ]
        events = regional_elo.process_results(rows)
        self.assertLess(len(events), 2000)

    def test_fallback_no_game_id(self) -> None:
        rows = [
            {"entry_id": "e1", "result": "win",  "seat_position": 1, "rating": 1500},
            {"entry_id": "e2", "result": "loss", "seat_position": 2, "rating": 1500},
        ]
        events = regional_elo.process_results(rows)
        self.assertEqual(len(events), 1)


class UpdateRatingsTests(TestCase):
    def test_reverse_lookup_updates_correctly(self) -> None:
        ratings = {
            ("global", "global", "e1"): regional_elo.create_empty_ratings_row("e1", "global", "global"),
            ("global", "global", "e2"): regional_elo.create_empty_ratings_row("e2", "global", "global"),
        }
        events = [{"entry_id": "e1", "opp_entry_id": "e2", "outcome": "win"}]
        regional_elo.update_ratings_with_games(ratings, events)
        self.assertEqual(ratings[("global", "global", "e1")]["wins"], 1)
        self.assertEqual(ratings[("global", "global", "e2")]["losses"], 1)


if __name__ == "__main__":
    main()
