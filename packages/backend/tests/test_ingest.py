import unittest
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

from ingest import extract_standing_rates, SupabaseClient  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
