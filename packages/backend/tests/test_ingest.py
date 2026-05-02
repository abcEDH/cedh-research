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
    extract_standing_rates,
    INGESTION_JOB_ALREADY_CLAIMED_EXIT_CODE,
    normalize_commander_name,
    sanitize_commander_payload,
    SupabaseClient,
    claim_ingestion_job,
    complete_ingestion_job,
    fail_ingestion_job,
    main,
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
            timeout=30,
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
