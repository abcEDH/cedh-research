import unittest
import os
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch


try:
    import requests as requests_module
except ModuleNotFoundError:
    requests_module = types.ModuleType("requests")
    requests_module.get = Mock()
    requests_module.post = Mock()
    requests_module.patch = Mock()
    requests_module.exceptions = types.SimpleNamespace(
        ConnectionError=ConnectionError,
        Timeout=TimeoutError,
        ReadTimeout=TimeoutError,
        JSONDecodeError=ValueError,
        HTTPError=RuntimeError,
        RequestException=Exception,
    )
    sys.modules["requests"] = requests_module

dateutil_module = types.ModuleType("dateutil")
dateutil_parser_module = types.ModuleType("dateutil.parser")
dateutil_parser_module.parse = lambda value: value
dateutil_module.parser = dateutil_parser_module
sys.modules.setdefault("dateutil", dateutil_module)
sys.modules.setdefault("dateutil.parser", dateutil_parser_module)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import (  # noqa: E402
    clean_commander_card_name,
    DataIngester,
    DirectPostgresClient,
    extract_standing_rates,
    INGESTION_JOB_ALREADY_CLAIMED_EXIT_CODE,
    _run_ingestion,
    chunk_items,
    default_backfill_run_key,
    load_tids,
    normalize_commander_name,
    sanitize_commander_payload,
    SupabaseClient,
    claim_ingestion_job,
    complete_ingestion_job,
    fail_ingestion_job,
    main,
    TopDeckClient,
)


class ExtractStandingRatesTests(unittest.TestCase):
    def test_uses_primary_and_opponent_fallbacks_independently(self) -> None:
        standing = {
            "successRate": 0.72,
            "opponentWinRate": 0.41,
        }

        win_rate, opponent_win_rate = extract_standing_rates(standing)

        self.assertEqual(win_rate, 0.72)
        self.assertEqual(opponent_win_rate, 0.41)

    def test_accepts_percent_values_for_both_fields(self) -> None:
        standing = {
            "winRate": 71,
            "opponentSuccessRate": 48,
        }

        win_rate, opponent_win_rate = extract_standing_rates(standing)

        self.assertEqual(win_rate, 0.71)
        self.assertEqual(opponent_win_rate, 0.48)


class IngestCliDefaultsTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "TOPDECK_API_KEY": "topdeck-key",
            "SUPABASE_SERVICE_KEY": "supabase-key",
            "SUPABASE_URL": "https://test.supabase.co",
        },
        clear=False,
    )
    @patch("ingest._run_ingestion")
    @patch("ingest.DataIngester")
    @patch("ingest.SupabaseClient")
    @patch("ingest.TopDeckClient")
    @patch("ingest.load_local_env")
    def test_recent_ingest_defaults_to_45_days_leagues_and_no_player_floor(
        self,
        mock_load_local_env: Mock,
        mock_topdeck_client: Mock,
        mock_supabase_client: Mock,
        mock_data_ingester: Mock,
        mock_run_ingestion: Mock,
    ) -> None:
        with patch.object(sys, "argv", ["ingest.py"]):
            main()

        args = mock_run_ingestion.call_args.args[0]
        self.assertEqual(args.days, 45)
        self.assertTrue(args.leagues)
        self.assertEqual(args.min_players, 0)

    @patch.dict(
        os.environ,
        {
            "TOPDECK_API_KEY": "topdeck-key",
            "SUPABASE_SERVICE_KEY": "supabase-key",
            "SUPABASE_URL": "https://test.supabase.co",
        },
        clear=False,
    )
    @patch("ingest._run_ingestion")
    @patch("ingest.DataIngester")
    @patch("ingest.SupabaseClient")
    @patch("ingest.TopDeckClient")
    @patch("ingest.load_local_env")
    def test_recent_ingest_can_opt_out_of_leagues(
        self,
        mock_load_local_env: Mock,
        mock_topdeck_client: Mock,
        mock_supabase_client: Mock,
        mock_data_ingester: Mock,
        mock_run_ingestion: Mock,
    ) -> None:
        with patch.object(sys, "argv", ["ingest.py", "--no-leagues"]):
            main()

        args = mock_run_ingestion.call_args.args[0]
        self.assertFalse(args.leagues)

    @patch.dict(
        os.environ,
        {
            "TOPDECK_API_KEY": "topdeck-key",
            "SUPABASE_SERVICE_KEY": "supabase-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_DB_URL": "postgres://test",
        },
        clear=False,
    )
    @patch("ingest._run_ingestion")
    @patch("ingest.DirectPostgresClient")
    @patch("ingest.SupabaseClient")
    @patch("ingest.TopDeckClient")
    @patch("ingest.load_local_env")
    def test_direct_mode_uses_direct_postgres_for_ingester(
        self,
        mock_load_local_env: Mock,
        mock_topdeck_client: Mock,
        mock_supabase_client: Mock,
        mock_direct_client: Mock,
        mock_run_ingestion: Mock,
    ) -> None:
        with patch.object(sys, "argv", ["ingest.py", "--direct"]):
            main()

        mock_direct_client.assert_called_once_with("postgres://test")
        ingester = mock_run_ingestion.call_args.args[3]
        self.assertIs(ingester.supabase, mock_direct_client.return_value)
        mock_direct_client.return_value.close.assert_called_once()

    def test_recent_ingest_uses_exclusive_next_day_end_boundary(self) -> None:
        args = types.SimpleNamespace(
            tournament_id=None,
            tids_file=None,
            days=60,
            leagues=True,
            min_players=0,
            skip_existing_tournaments=False,
            limit=0,
        )
        topdeck = Mock()
        topdeck.search_tournaments.return_value = []
        ingester = Mock()

        with patch("ingest.datetime") as mock_datetime:
            mock_datetime.now.return_value = __import__("datetime").datetime(2026, 5, 11, 18, 0)
            _run_ingestion(args, topdeck, Mock(), ingester, "")

        topdeck.search_tournaments.assert_called_once_with(
            start_date="2026-03-12",
            end_date="2026-05-12",
            leagues=True,
        )

    def test_recent_ingest_preserves_search_event_data_when_detail_payload_is_empty(self) -> None:
        args = types.SimpleNamespace(
            tournament_id=None,
            tids_file=None,
            names_file=None,
            days=1,
            leagues=True,
            min_players=0,
            skip_existing_tournaments=False,
            limit=0,
        )
        event_data = {
            "city": "Mission Viejo",
            "state": "California",
            "country": "United States",
            "location": "23854 Via Fabricante unit b 1, Mission Viejo, CA 92691, USA",
            "lat": 33.616879,
            "lng": -117.681948,
        }
        topdeck = Mock()
        topdeck.search_tournaments.return_value = [
            {
                "id": "event-1",
                "name": "Event 1",
                "standings": [{"id": "player-1"}],
                "eventData": event_data,
                "isLeague": True,
            }
        ]
        topdeck.get_tournament.return_value = {
            "id": "event-1",
            "name": "Event 1",
            "standings": [{"id": "player-1"}],
            "rounds": [],
            "eventData": {},
        }
        ingester = Mock()
        ingester.process_tournament.return_value = None

        _run_ingestion(args, topdeck, Mock(), ingester, "")

        processed_tournament = ingester.process_tournament.call_args.args[0]
        self.assertEqual(processed_tournament["eventData"], event_data)
        self.assertTrue(processed_tournament["isLeague"])

    @patch("ingest.requests.post")
    def test_topdeck_search_defaults_is_league_false_when_league_search_enabled(
        self, mock_post: Mock
    ) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"TID": "event-1", "tournamentName": "Event 1"},
            {"TID": "league-1", "tournamentName": "League 1", "isLeague": True},
        ]
        mock_post.return_value = mock_response

        tournaments = TopDeckClient("topdeck-key").search_tournaments(leagues=True)

        self.assertFalse(tournaments[0]["isLeague"])
        self.assertTrue(tournaments[1]["isLeague"])

    def test_process_tournament_writes_is_league_when_topdeck_supplies_flag(self) -> None:
        topdeck = Mock()
        topdeck.get_tournament_tier.return_value = None
        supabase = Mock()
        supabase.upsert.return_value = [{"id": "tournament-1"}]
        ingester = DataIngester(topdeck, supabase)

        ingester.process_tournament(
            {
                "id": "league-1",
                "name": "League 1",
                "startDate": 1777618800,
                "standings": [],
                "rounds": [],
                "swissNum": 0,
                "topCut": 0,
                "isLeague": True,
            }
        )

        tournament_data = supabase.upsert.call_args.args[1]
        self.assertTrue(tournament_data["is_league"])

    def test_process_tournament_does_not_clear_missing_location_or_tier(self) -> None:
        topdeck = Mock()
        topdeck.get_tournament_tier.return_value = None
        supabase = Mock()
        supabase.upsert.return_value = [{"id": "tournament-1"}]
        ingester = DataIngester(topdeck, supabase)

        ingester.process_tournament(
            {
                "id": "event-1",
                "name": "Event 1",
                "startDate": 1777618800,
                "standings": [],
                "rounds": [],
                "eventData": {},
            }
        )

        tournament_data = supabase.upsert.call_args.args[1]
        self.assertNotIn("city", tournament_data)
        self.assertNotIn("state", tournament_data)
        self.assertNotIn("country", tournament_data)
        self.assertNotIn("venue", tournament_data)
        self.assertNotIn("tier", tournament_data)


class DirectPostgresClientTests(unittest.TestCase):
    @patch("ingest.psycopg2.extras.execute_values")
    @patch("ingest.psycopg2.connect")
    def test_upsert_sends_row_value_tuples(self, mock_connect: Mock, mock_execute_values: Mock) -> None:
        cursor = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=None)
        cursor.fetchall.return_value = [("player-1", "Alice")]
        cursor.description = [("id",), ("name",)]
        connection = Mock()
        connection.closed = False
        connection.cursor.return_value = cursor
        mock_connect.return_value = connection

        result = DirectPostgresClient("postgres://test").upsert(
            "players",
            [{"topdeck_id": "td-1", "name": "Alice"}],
            on_conflict="topdeck_id",
        )

        self.assertEqual(result, [{"id": "player-1", "name": "Alice"}])
        execute_args = mock_execute_values.call_args.args
        self.assertEqual(execute_args[2], [("td-1", "Alice")])
        connection.commit.assert_called_once()

    @patch("ingest.psycopg2.connect")
    def test_select_supports_rest_style_in_filter_projection_order_and_paging(
        self, mock_connect: Mock
    ) -> None:
        cursor = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=None)
        cursor.fetchall.return_value = [("td-1",)]
        cursor.description = [("topdeck_tid",)]
        connection = Mock()
        connection.closed = False
        connection.cursor.return_value = cursor
        mock_connect.return_value = connection

        result = DirectPostgresClient("postgres://test").select(
            "tournaments",
            {
                "select": "topdeck_tid",
                "topdeck_tid": "in.(td-1,td-2)",
                "order": "start_date.desc,topdeck_tid.asc",
                "limit": "10",
                "offset": "20",
            },
        )

        self.assertEqual(result, [{"topdeck_tid": "td-1"}])
        cursor.execute.assert_called_once_with(
            "SELECT topdeck_tid FROM tournaments WHERE topdeck_tid = ANY(%s) "
            "ORDER BY start_date DESC, topdeck_tid ASC LIMIT %s OFFSET %s",
            [["td-1", "td-2"], 10, 20],
        )


class TidManifestTests(unittest.TestCase):
    def test_load_tids_ignores_comments_blanks_and_duplicates(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tids.txt"
            path.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "",
                        "event-a",
                        "event-b extra metadata",
                        "event-a",
                    ]
                )
            )

            self.assertEqual(load_tids(path), ["event-a", "event-b"])

    def test_chunk_items_splits_fixed_size_batches(self) -> None:
        self.assertEqual(chunk_items(["a", "b", "c", "d", "e"], 2), [["a", "b"], ["c", "d"], ["e"]])

    def test_default_backfill_run_key_uses_manifest_name_and_batch_size(self) -> None:
        self.assertEqual(default_backfill_run_key(Path("logs/example.txt"), 50), "example:batch-50")


class CommanderNormalizationTests(unittest.TestCase):
    def test_clean_commander_card_name_maps_stranger_things_to_in_universe(self) -> None:
        self.assertEqual(clean_commander_card_name("Lucas, the Sharpshooter"), "Bjorna, Nightfall Alchemist")

    def test_clean_commander_card_name_unescapes_quotes(self) -> None:
        self.assertEqual(clean_commander_card_name("K\\'rrik, Son of Yawgmoth"), "K'rrik, Son of Yawgmoth")

    def test_clean_commander_card_name_strips_double_faced_backside(self) -> None:
        self.assertEqual(
            clean_commander_card_name("Etali, Primal Conqueror // Etali, Primal Sickness"),
            "Etali, Primal Conqueror",
        )

    def test_normalize_commander_name_strips_back_faces_from_partner_pair(self) -> None:
        self.assertEqual(
            normalize_commander_name(
                [
                    "Etali, Primal Conqueror // Etali, Primal Sickness",
                    "Vivi Ornitier",
                ]
            ),
            "Etali, Primal Conqueror / Vivi Ornitier",
        )

    def test_sanitize_commander_payload_canonicalizes_name_and_components(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Kraum, Ludevic\\'s Opus / Tymna the Weaver",
                ["Kraum, Ludevic\\'s Opus", "Tymna the Weaver"],
            ),
            (
                "Tymna the Weaver / Kraum, Ludevic's Opus",
                ["Tymna the Weaver", "Kraum, Ludevic's Opus"],
            ),
        )

    def test_sanitize_commander_payload_maps_stranger_things_pair(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Lucas, the Sharpshooter / Will the Wise",
                ["Lucas, the Sharpshooter", "Will the Wise"],
            ),
            (
                "Bjorna, Nightfall Alchemist / Wernog, Rider's Chaplain",
                ["Bjorna, Nightfall Alchemist", "Wernog, Rider's Chaplain"],
            ),
        )

    def test_sanitize_commander_payload_rejects_illegal_pair(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Etali, Primal Conqueror / Kinnan, Bonder Prodigy",
                ["Etali, Primal Conqueror", "Kinnan, Bonder Prodigy"],
            ),
            ("Unknown Commander", ["Unknown Commander"]),
        )

    def test_normalize_commander_name_uses_canonical_legal_pair_order(self) -> None:
        self.assertEqual(
            normalize_commander_name(["Haldan, Avid Arcanist", "Pako, Arcane Retriever"]),
            "Pako, Arcane Retriever / Haldan, Avid Arcanist",
        )


class SupabaseClientUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = SupabaseClient("https://test.supabase.co", "test-service-key")

    @patch("ingest.requests.patch")
    def test_update_sends_patch_request(self, mock_patch: Mock) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "row-1", "status": "running"}]
        mock_patch.return_value = mock_response

        result = self.client.update(
            "elo_maintenance_jobs",
            {"status": "running"},
            {"id": "eq.job-123", "status": "eq.pending"},
        )

        mock_patch.assert_called_once_with(
            "https://test.supabase.co/rest/v1/elo_maintenance_jobs",
            json={"status": "running"},
            headers=self.client.headers,
            params={"id": "eq.job-123", "status": "eq.pending"},
            timeout=90,
        )
        self.assertEqual(result, [{"id": "row-1", "status": "running"}])

    @patch("ingest.requests.patch")
    def test_update_retries_on_connection_error(self, mock_patch: Mock) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "row-1"}]
        mock_patch.side_effect = [
            requests_module.exceptions.ConnectionError("Connection refused"),
            mock_response,
        ]

        with patch("ingest.time.sleep"):
            result = self.client.update(
                "elo_maintenance_jobs",
                {"status": "running"},
            )

        self.assertEqual(mock_patch.call_count, 2)
        self.assertEqual(result, [{"id": "row-1"}])

    @patch("ingest.requests.patch")
    def test_update_retries_on_transient_http_error(self, mock_patch: Mock) -> None:
        first_response = Mock()
        first_response.status_code = 503
        first_response.text = "service unavailable"
        http_error = requests_module.exceptions.HTTPError("503")
        http_error.response = first_response
        first_response.raise_for_status.side_effect = http_error

        second_response = Mock()
        second_response.status_code = 200
        second_response.json.return_value = [{"id": "row-1"}]

        mock_patch.side_effect = [first_response, second_response]

        with patch("ingest.time.sleep"):
            result = self.client.update(
                "elo_maintenance_jobs",
                {"status": "running"},
            )

        self.assertEqual(mock_patch.call_count, 2)
        self.assertEqual(result, [{"id": "row-1"}])

    @patch("ingest.requests.patch")
    def test_update_returns_empty_list_on_no_match(self, mock_patch: Mock) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_patch.return_value = mock_response

        result = self.client.update(
            "elo_maintenance_jobs",
            {"status": "running"},
            {"id": "eq.nonexistent"},
        )

        self.assertEqual(result, [])


class SupabaseClientRpcTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = SupabaseClient("https://test.supabase.co", "test-service-key")

    @patch("ingest.requests.post")
    def test_rpc_sends_post_to_correct_endpoint(self, mock_post: Mock) -> None:
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        result = self.client.rpc("refresh_commander_trends")

        mock_post.assert_called_once_with(
            "https://test.supabase.co/rest/v1/rpc/refresh_commander_trends",
            json={},
            headers=self.client.headers,
            timeout=120,
        )
        self.assertIsNone(result)

    @patch("ingest.requests.post")
    def test_rpc_uses_higher_timeout(self, mock_post: Mock) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        self.client.rpc("refresh_card_frequencies", timeout=120)

        call_kwargs = mock_post.call_args.kwargs
        self.assertEqual(call_kwargs["timeout"], 120)


class IngestionJobLifecycleTests(unittest.TestCase):
    def test_claim_ingestion_job_sends_update(self) -> None:
        client = Mock()
        client.update.return_value = [{"id": "job-1"}]
        result = claim_ingestion_job(client, "job-1", github_run_id=99)
        self.assertTrue(result)
        client.update.assert_called_once()
        call_args = client.update.call_args
        self.assertEqual(call_args.args[0], "ingestion_jobs")
        self.assertEqual(call_args.args[1]["status"], "running")
        self.assertEqual(call_args.args[1]["github_run_id"], 99)

    def test_claim_ingestion_job_returns_false_on_empty(self) -> None:
        client = Mock()
        client.update.return_value = []
        result = claim_ingestion_job(client, "job-1", github_run_id=0)
        self.assertFalse(result)

    def test_claim_ingestion_job_raises_on_operational_error(self) -> None:
        client = Mock()
        client.update.side_effect = ConnectionError("Supabase unreachable")
        with self.assertRaises(ConnectionError):
            claim_ingestion_job(client, "job-1", github_run_id=0)

    @patch.dict(
        os.environ,
        {
            "TOPDECK_API_KEY": "topdeck-key",
            "SUPABASE_SERVICE_KEY": "supabase-key",
            "SUPABASE_URL": "https://test.supabase.co",
        },
        clear=False,
    )
    @patch("ingest._run_ingestion")
    @patch("ingest.update_ingestion_heartbeat")
    @patch("ingest.claim_ingestion_job")
    @patch("ingest.DataIngester")
    @patch("ingest.SupabaseClient")
    @patch("ingest.TopDeckClient")
    @patch("ingest.load_local_env")
    def test_main_exits_with_distinct_code_when_job_already_claimed(
        self,
        mock_load_local_env: Mock,
        mock_topdeck_client: Mock,
        mock_supabase_client: Mock,
        mock_data_ingester: Mock,
        mock_claim_ingestion_job: Mock,
        mock_update_ingestion_heartbeat: Mock,
        mock_run_ingestion: Mock,
    ) -> None:
        mock_claim_ingestion_job.return_value = False

        with patch.object(sys, "argv", ["ingest.py", "--job-id", "job-1"]):
            with self.assertRaises(SystemExit) as exc:
                main()

        self.assertEqual(exc.exception.code, INGESTION_JOB_ALREADY_CLAIMED_EXIT_CODE)
        mock_update_ingestion_heartbeat.assert_not_called()
        mock_run_ingestion.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "TOPDECK_API_KEY": "topdeck-key",
            "SUPABASE_SERVICE_KEY": "supabase-key",
            "SUPABASE_URL": "https://test.supabase.co",
        },
        clear=False,
    )
    @patch("ingest._run_ingestion")
    @patch("ingest.update_ingestion_heartbeat")
    @patch("ingest.claim_ingestion_job")
    @patch("ingest.DataIngester")
    @patch("ingest.SupabaseClient")
    @patch("ingest.TopDeckClient")
    @patch("ingest.load_local_env")
    def test_main_exits_when_claim_ingestion_job_errors(
        self,
        mock_load_local_env: Mock,
        mock_topdeck_client: Mock,
        mock_supabase_client: Mock,
        mock_data_ingester: Mock,
        mock_claim_ingestion_job: Mock,
        mock_update_ingestion_heartbeat: Mock,
        mock_run_ingestion: Mock,
    ) -> None:
        mock_claim_ingestion_job.side_effect = ConnectionError("Supabase unreachable")

        with patch.object(sys, "argv", ["ingest.py", "--job-id", "job-1"]):
            with self.assertRaises(SystemExit) as exc:
                main()

        self.assertEqual(exc.exception.code, 1)
        mock_claim_ingestion_job.assert_called_once()
        mock_update_ingestion_heartbeat.assert_not_called()
        mock_run_ingestion.assert_not_called()

    def test_fail_ingestion_job_truncates_error(self) -> None:
        client = Mock()
        fail_ingestion_job(client, "job-1", "x" * 3000)
        call_args = client.update.call_args
        self.assertLessEqual(len(call_args.args[1]["error_text"]), 2000)

    def test_complete_ingestion_job_sets_completed_status(self) -> None:
        client = Mock()
        complete_ingestion_job(client, "job-1", {"duration_seconds": 42.5})
        call_args = client.update.call_args
        self.assertEqual(call_args.args[1]["status"], "completed")
        self.assertEqual(call_args.args[1]["duration_seconds"], 42.5)


if __name__ == "__main__":
    unittest.main()
