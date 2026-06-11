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


class GameEventsAlwaysWrittenTests(TestCase):
    """Game events are always written to global_elo_game_events (no flag required)."""

    _ENV = {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"}

    def _run_main(self) -> Mock:
        """Run main() with --apply and return the SupabaseClient mock."""
        argv = ["regional_elo.py", "--apply"]
        # update_ratings_with_games now returns db_event_rows
        fake_db_rows = [{"region_type": "global", "region_key": "ALL", "game_id": "g1", "player_id": "p1"}]
        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, self._ENV, clear=False):
                with patch("regional_elo.SupabaseClient") as mock_cls:
                    mock_client = Mock()
                    mock_cls.return_value = mock_client
                    mock_client.upsert.return_value = None
                    mock_client.update.return_value = []
                    with patch("regional_elo.fetch_elo_watermark", return_value=None):
                        with patch("regional_elo.fetch_participants_for_leaderboard", return_value=[]):
                            with patch("regional_elo.fetch_distinct_entry_ids", return_value=set()):
                                with patch("regional_elo.process_results", return_value=[]):
                                    with patch("regional_elo.update_ratings_with_games", return_value=fake_db_rows):
                                        with patch("regional_elo.fetch_player_index", return_value={}):
                                            with patch("regional_elo.fetch_topdeck_elo_by_topdeck_id", return_value={}):
                                                with patch("regional_elo.fetch_primary_state_stats", return_value={}):
                                                    with patch("regional_elo.fetch_canonical_event_counts", return_value={}):
                                                      with patch("regional_elo.build_active_leaderboard_rows", return_value=[]):
                                                        with patch("regional_elo.upsert_active_leaderboard_rows"):
                                                            with patch("regional_elo.delete_stale_active_leaderboard_rows"):
                                                                with patch("regional_elo.build_player_profiles", return_value=[]):
                                                                    with patch("regional_elo.build_primary_commanders", return_value={}):
                                                                        with patch("regional_elo.detect_active_players", return_value=[]):
                                                                            with patch("regional_elo.refresh_materialized_views", return_value=0):
                                                                                regional_elo.main()
                    return mock_client

    def test_game_events_always_upserted(self) -> None:
        mock_client = self._run_main()

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
        # player_id falls back to entry_id when player_id is absent
        pairs = {frozenset([e["player_id"], e["opp_player_id"]]) for e in events}
        self.assertIn(frozenset(["e1", "e2"]), pairs)
        self.assertIn(frozenset(["e3", "e4"]), pairs)
        # No cross-game pairs
        self.assertNotIn(frozenset(["e1", "e3"]), pairs)
        self.assertNotIn(frozenset(["e1", "e4"]), pairs)

    def test_events_carry_game_metadata(self) -> None:
        rows = [
            {"game_id": "g1", "tournament_id": "t1", "start_date": "2026-01-01",
             "entry_id": "e1", "result": "win",  "seat_position": 1, "rating": 1500},
            {"game_id": "g1", "tournament_id": "t1", "start_date": "2026-01-01",
             "entry_id": "e2", "result": "loss", "seat_position": 2, "rating": 1500},
        ]
        events = regional_elo.process_results(rows)
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e["game_id"], "g1")
        self.assertEqual(e["tournament_id"], "t1")
        self.assertEqual(e["game_date"], "2026-01-01")
        self.assertEqual(e["opponent_count"], 1)

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
            ("global", "ALL", "p1"): regional_elo.create_empty_ratings_row("p1", "global", "ALL"),
            ("global", "ALL", "p2"): regional_elo.create_empty_ratings_row("p2", "global", "ALL"),
        }
        events = [
            {
                "player_id": "p1", "opp_player_id": "p2", "entry_id": "e1",
                "outcome": "win", "game_id": "g1", "tournament_id": "t1",
                "game_date": "2026-01-01", "is_draw": False, "opponent_count": 1,
            }
        ]
        db_rows = regional_elo.update_ratings_with_games(ratings, events)
        self.assertEqual(ratings[("global", "ALL", "p1")]["wins"], 1)
        self.assertEqual(ratings[("global", "ALL", "p2")]["losses"], 1)

    def test_returns_game_event_rows_with_rating_fields(self) -> None:
        ratings = {
            ("global", "ALL", "p1"): regional_elo.create_empty_ratings_row("p1", "global", "ALL"),
            ("global", "ALL", "p2"): regional_elo.create_empty_ratings_row("p2", "global", "ALL"),
        }
        events = [
            {
                "player_id": "p1", "opp_player_id": "p2", "entry_id": "e1",
                "outcome": "win", "game_id": "g1", "tournament_id": "t1",
                "game_date": "2026-01-01", "is_draw": False, "opponent_count": 1,
            }
        ]
        db_rows = regional_elo.update_ratings_with_games(ratings, events)
        self.assertEqual(len(db_rows), 2)
        by_player = {r["player_id"]: r for r in db_rows}
        self.assertIn("p1", by_player)
        self.assertIn("p2", by_player)
        winner = by_player["p1"]
        loser = by_player["p2"]
        self.assertEqual(winner["game_result"], "win")
        self.assertEqual(loser["game_result"], "loss")
        self.assertGreater(winner["rating_after"], winner["rating_before"])
        self.assertLess(loser["rating_after"], loser["rating_before"])
        self.assertAlmostEqual(winner["rating_delta"], winner["rating_after"] - winner["rating_before"], places=5)
        self.assertEqual(winner["game_id"], "g1")
        self.assertEqual(winner["region_type"], "global")


class FetchEloWatermarkTests(TestCase):
    def test_returns_game_date_when_rows_exist(self) -> None:
        client = Mock()
        client.select.return_value = [{"game_date": "2026-05-11T16:00:00+00:00"}]

        result = regional_elo.fetch_elo_watermark(client)

        self.assertEqual(result, "2026-05-11T16:00:00+00:00")
        client.select.assert_called_once_with(
            "global_elo_game_events",
            {
                "select": "game_date",
                "region_type": "eq.global",
                "order": "game_date.desc",
                "limit": "1",
            },
        )

    def test_returns_none_when_table_empty(self) -> None:
        client = Mock()
        client.select.return_value = []

        result = regional_elo.fetch_elo_watermark(client)

        self.assertIsNone(result)


class LoadRatingsFromSnapshotTests(TestCase):
    @patch("regional_elo._rpc_fetch_all")
    def test_builds_ratings_dict_from_rpc_rows(self, mock_rpc: Mock) -> None:
        mock_rpc.return_value = [
            {"player_id": "abc-123", "rating": 1650.5, "games_played": 20,
             "wins": 10, "draws": 2, "losses": 8, "last_game_date": "2026-01-01"},
        ]
        client = Mock()

        result = regional_elo.load_ratings_from_snapshot(client, "2026-01-02T00:00:00Z")

        key = (regional_elo.GLOBAL_REGION_TYPE, regional_elo.GLOBAL_REGION_KEY, "abc-123")
        self.assertIn(key, result)
        row = result[key]
        self.assertAlmostEqual(row["rating"], 1650.5)
        self.assertEqual(row["wins"], 10)
        self.assertEqual(row["games_played"], 20)

    @patch("regional_elo._rpc_fetch_all")
    def test_skips_rows_without_player_id(self, mock_rpc: Mock) -> None:
        mock_rpc.return_value = [
            {"player_id": None, "rating": 1500},
            {"player_id": "p1", "rating": 1500},
        ]
        client = Mock()

        result = regional_elo.load_ratings_from_snapshot(client, "2026-01-01T00:00:00Z")

        self.assertEqual(len(result), 1)


class FetchParticipantsSinceTests(TestCase):
    @patch("regional_elo.fetch_all")
    def test_rest_path_uses_gte_filter(self, mock_fetch_all: Mock) -> None:
        mock_fetch_all.return_value = []
        client = Mock()

        regional_elo.fetch_participants_since(client, "2026-05-11T16:00:00+00:00", direct=None)

        params = mock_fetch_all.call_args[0][2]
        self.assertIn("start_date", params)
        self.assertTrue(params["start_date"].startswith("gte."))
        self.assertIn("neq.bye", params.get("result", ""))

    def test_direct_path_uses_gte_filter(self) -> None:
        direct = Mock()
        direct.select.return_value = []

        regional_elo.fetch_participants_since(Mock(), "2026-05-11", direct=direct)

        params = direct.select.call_args[0][1]
        self.assertTrue(params["start_date"].startswith("gte."))


class BuildPrimaryCommandersTests(TestCase):
    """Tests for build_primary_commanders()."""

    def _make_row(self, player_id: str, commander_name: str | None) -> dict:
        return {
            "player_id": player_id,
            "commander_id": "some-uuid",
            "commanders": {"name": commander_name} if commander_name else None,
        }

    @patch("regional_elo.fetch_all")
    def test_returns_most_played_known_commander(self, mock_fetch_all: Mock) -> None:
        """Player with 3 known entries (2 A, 1 B) → primary is A."""
        mock_fetch_all.return_value = [
            self._make_row("p1", "Thrasios, Triton Hero"),
            self._make_row("p1", "Thrasios, Triton Hero"),
            self._make_row("p1", "Najeela, the Blade-Blossom"),
        ]
        result = regional_elo.build_primary_commanders(Mock())
        self.assertIn("p1", result)
        self.assertEqual(result["p1"][0], "Thrasios, Triton Hero")

    @patch("regional_elo.fetch_all")
    def test_known_pct_computed_correctly(self, mock_fetch_all: Mock) -> None:
        """4 entries, 3 known → known_pct = 0.75."""
        mock_fetch_all.return_value = [
            self._make_row("p1", "Najeela, the Blade-Blossom"),
            self._make_row("p1", "Najeela, the Blade-Blossom"),
            self._make_row("p1", "Najeela, the Blade-Blossom"),
            self._make_row("p1", regional_elo.UNKNOWN_COMMANDER_NAME),
        ]
        result = regional_elo.build_primary_commanders(Mock())
        self.assertIn("p1", result)
        self.assertAlmostEqual(result["p1"][1], 0.75)

    @patch("regional_elo.fetch_all")
    def test_excludes_players_below_0_5_threshold(self, mock_fetch_all: Mock) -> None:
        """Player with only 1 known out of 3 total (0.33) should be omitted."""
        mock_fetch_all.return_value = [
            self._make_row("p1", "Najeela, the Blade-Blossom"),
            self._make_row("p1", regional_elo.UNKNOWN_COMMANDER_NAME),
            self._make_row("p1", regional_elo.UNKNOWN_COMMANDER_NAME),
        ]
        result = regional_elo.build_primary_commanders(Mock())
        self.assertNotIn("p1", result)

    @patch("regional_elo.fetch_all")
    def test_excludes_unknown_commander_from_primary(self, mock_fetch_all: Mock) -> None:
        """Unknown Commander entries are never chosen as the primary commander."""
        mock_fetch_all.return_value = [
            self._make_row("p1", regional_elo.UNKNOWN_COMMANDER_NAME),
            self._make_row("p1", regional_elo.UNKNOWN_COMMANDER_NAME),
            self._make_row("p1", "Tymna the Weaver"),
        ]
        # known_pct = 1/3 ≈ 0.33 → below threshold, omitted
        result = regional_elo.build_primary_commanders(Mock())
        self.assertNotIn("p1", result)

    @patch("regional_elo.fetch_all")
    def test_excludes_entries_with_null_commander(self, mock_fetch_all: Mock) -> None:
        """Entries with no commander data do not count as known."""
        mock_fetch_all.return_value = [
            self._make_row("p1", None),
            self._make_row("p1", None),
            self._make_row("p1", "Kenrith, the Returned King"),
        ]
        # known_pct = 1/3 → below 0.5, omitted
        result = regional_elo.build_primary_commanders(Mock())
        self.assertNotIn("p1", result)

    @patch("regional_elo.fetch_all")
    def test_multiple_players_independent(self, mock_fetch_all: Mock) -> None:
        """Each player's primary commander is computed independently."""
        mock_fetch_all.return_value = [
            self._make_row("p1", "Thrasios, Triton Hero"),
            self._make_row("p1", "Thrasios, Triton Hero"),
            self._make_row("p2", "Najeela, the Blade-Blossom"),
            self._make_row("p2", "Najeela, the Blade-Blossom"),
        ]
        result = regional_elo.build_primary_commanders(Mock())
        self.assertEqual(result["p1"][0], "Thrasios, Triton Hero")
        self.assertEqual(result["p2"][0], "Najeela, the Blade-Blossom")

    @patch("regional_elo.fetch_all")
    def test_passes_correct_table_and_select(self, mock_fetch_all: Mock) -> None:
        """fetch_all is called with tournament_entries and the right select param."""
        mock_fetch_all.return_value = []
        regional_elo.build_primary_commanders(Mock())
        table_arg = mock_fetch_all.call_args[0][1]
        params_arg = mock_fetch_all.call_args[0][2]
        self.assertEqual(table_arg, "tournament_entries")
        self.assertIn("commanders(name)", params_arg.get("select", ""))

    @patch("regional_elo.fetch_all")
    def test_empty_input_returns_empty_dict(self, mock_fetch_all: Mock) -> None:
        mock_fetch_all.return_value = []
        result = regional_elo.build_primary_commanders(Mock())
        self.assertEqual(result, {})


class CanonicalEventCountsTests(TestCase):
    """Tests for fetch_canonical_event_counts and canonical path in build_active_leaderboard_rows."""

    @patch("regional_elo.fetch_all")
    def test_fetch_canonical_event_counts_queries_leaderboard_view(self, mock_fetch_all: Mock) -> None:
        mock_fetch_all.return_value = [
            {"player_id": "p1", "games_played": 10, "wins": 5, "losses": 3, "draws": 2},
        ]
        result = regional_elo.fetch_canonical_event_counts(Mock())
        table_arg = mock_fetch_all.call_args[0][1]
        params_arg = mock_fetch_all.call_args[0][2]
        self.assertEqual(table_arg, "regional_elo_leaderboard")
        self.assertIn("games_played", params_arg.get("select", ""))
        self.assertIn(regional_elo.GLOBAL_REGION_TYPE, str(params_arg.get("region_type", "")))
        self.assertEqual(result["p1"]["wins"], 5)
        self.assertEqual(result["p1"]["losses"], 3)
        self.assertEqual(result["p1"]["draws"], 2)

    @patch("regional_elo.fetch_all")
    def test_fetch_canonical_event_counts_skips_rows_without_player_id(self, mock_fetch_all: Mock) -> None:
        mock_fetch_all.return_value = [
            {"player_id": None, "games_played": 5, "wins": 2, "losses": 2, "draws": 1},
            {"player_id": "p1", "games_played": 3, "wins": 1, "losses": 1, "draws": 1},
        ]
        result = regional_elo.fetch_canonical_event_counts(Mock())
        self.assertEqual(list(result.keys()), ["p1"])

    def test_build_active_leaderboard_rows_uses_canonical_counts_over_rating_row(self) -> None:
        rating_row = {
            "region_type": "global",
            "region_key": "ALL",
            "player_id": "p1",
            "rating": 1600,
            "games_played": 500,  # stale/overcounted
            "wins": 300,
            "losses": 100,
            "draws": 100,
        }
        canonical_counts = {
            "p1": {"games_played": 50, "wins": 25, "losses": 15, "draws": 10},
        }
        player_index = {"p1": {"id": "p1", "name": "Test Player", "topdeck_id": None}}

        rows = regional_elo.build_active_leaderboard_rows(
            [rating_row],
            player_index,
            {},
            {},
            "2026-01-01T00:00:00",
            canonical_counts,
        )

        global_row = next((r for r in rows if r["region_type"] == "global"), None)
        self.assertIsNotNone(global_row)
        self.assertEqual(global_row["games_played"], 50)
        self.assertEqual(global_row["wins"], 25)
        self.assertEqual(global_row["losses"], 15)
        self.assertEqual(global_row["draws"], 10)

    def test_build_active_leaderboard_rows_falls_back_to_rating_row_when_no_canonical(self) -> None:
        rating_row = {
            "region_type": "global",
            "region_key": "ALL",
            "player_id": "p1",
            "rating": 1600,
            "games_played": 42,
            "wins": 20,
            "losses": 12,
            "draws": 10,
        }
        player_index = {"p1": {"id": "p1", "name": "Test Player", "topdeck_id": None}}

        rows = regional_elo.build_active_leaderboard_rows(
            [rating_row],
            player_index,
            {},
            {},
            "2026-01-01T00:00:00",
            canonical_counts_by_player=None,
        )

        global_row = next((r for r in rows if r["region_type"] == "global"), None)
        self.assertIsNotNone(global_row)
        self.assertEqual(global_row["games_played"], 42)
        self.assertEqual(global_row["wins"], 20)


if __name__ == "__main__":
    main()
