import unittest
import types
import sys
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from supabase_client import (
    _describe_request_failure,
    SupabaseClient,
)

def _make_sb_client(data: list | None = None) -> tuple[Mock, Mock]:
    mock_inner = Mock()
    chain = Mock()
    chain.execute.return_value.data = data or []
    for method in ("select", "eq", "neq", "gte", "lte", "gt", "lt",
                   "ilike", "in_", "order", "limit", "offset"):
        getattr(chain, method).return_value = chain
    chain.not_ = Mock()
    chain.not_.is_.return_value = chain
    mock_inner.table.return_value.select.return_value = chain
    mock_inner.table.return_value.update.return_value = chain
    mock_inner.table.return_value.upsert.return_value = chain
    mock_inner.rpc.return_value = chain

    with patch("supabase_client.create_client", return_value=mock_inner):
        client = SupabaseClient("https://test.supabase.co", "test-service-key")
    return mock_inner, client

class SupabaseClientUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_inner, self.client = _make_sb_client([{"id": "row-1", "status": "running"}])

    def test_update_delegates_to_supabase_table(self) -> None:
        result = self.client.update(
            "elo_maintenance_jobs",
            {"status": "running"},
            {"id": "eq.job-123"},
        )
        self.mock_inner.table.assert_called_once_with("elo_maintenance_jobs")
        self.mock_inner.table.return_value.update.assert_called_once_with({"status": "running"})
        self.assertEqual(result, [{"id": "row-1", "status": "running"}])

    def test_update_applies_eq_filter(self) -> None:
        chain = self.mock_inner.table.return_value.update.return_value
        self.client.update("t", {"col": "val"}, {"id": "eq.abc"})
        chain.eq.assert_called_once_with("id", "abc")

    def test_update_returns_empty_list_on_no_match(self) -> None:
        _, client = _make_sb_client([])
        result = client.update("elo_maintenance_jobs", {"status": "running"}, {"id": "eq.nonexistent"})
        self.assertEqual(result, [])

    def test_update_propagates_exception(self) -> None:
        self.mock_inner.table.return_value.update.return_value.execute.side_effect = RuntimeError("db error")
        self.client._client = self.mock_inner
        with self.assertRaises(RuntimeError):
            self.client.update("t", {"col": "val"})

class SupabaseClientRpcTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_inner, self.client = _make_sb_client(None)

    def test_rpc_calls_correct_function(self) -> None:
        self.mock_inner.rpc.return_value.execute.return_value.data = None
        result = self.client.rpc("refresh_commander_trends")
        self.mock_inner.rpc.assert_called_once_with("refresh_commander_trends", {})
        self.assertIsNone(result)

    def test_rpc_returns_data_when_present(self) -> None:
        self.mock_inner.rpc.return_value.execute.return_value.data = [{"ok": True}]
        result = self.client.rpc("get_stats", {"p": "v"})
        self.mock_inner.rpc.assert_called_once_with("get_stats", {"p": "v"})
        self.assertEqual(result, [{"ok": True}])

class SupabaseClientSelectDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        _, self.client = _make_sb_client()

    def test_describe_request_failure_includes_status_and_body(self) -> None:
        response = Mock()
        response.status_code = 503
        response.text = "upstream connect error: connection refused\n"
        http_error = requests_module.exceptions.HTTPError("503 Server Error")
        http_error.response = response

        diag = _describe_request_failure(http_error, table="tournaments")

        self.assertIn("table=tournaments", diag)
        self.assertIn("HTTPError", diag)
        self.assertIn("status=503", diag)
        self.assertIn("upstream connect error", diag)

    def test_describe_request_failure_handles_connection_error_without_response(self) -> None:
        conn_error = requests_module.exceptions.ConnectionError("Connection refused")
        diag = _describe_request_failure(conn_error, table="elo_maintenance_jobs")
        self.assertIn("table=elo_maintenance_jobs", diag)
        self.assertIn("ConnectionError", diag)
        self.assertIn("Connection refused", diag)
        self.assertNotIn("status=", diag)

    def test_describe_request_failure_truncates_long_bodies(self) -> None:
        response = Mock()
        response.status_code = 500
        response.text = "x" * 5000
        http_error = requests_module.exceptions.HTTPError("500 Server Error")
        http_error.response = response

        diag = _describe_request_failure(http_error, table="t", body_chars=200)

        self.assertLess(len(diag), 400)

    def test_select_delegates_to_supabase_table(self) -> None:
        mock_inner, client = _make_sb_client([{"id": "row-1"}])
        result = client.select("tournaments", {"id": "eq.row-1"})
        mock_inner.table.assert_called_once_with("tournaments")
        self.assertEqual(result, [{"id": "row-1"}])

if __name__ == "__main__":
    unittest.main()
