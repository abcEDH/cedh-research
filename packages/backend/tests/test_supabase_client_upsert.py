"""Unit tests for SupabaseClient.upsert batching.

A single upsert is one SQL statement, so an oversized payload trips the
Postgres statement_timeout (error 57014) — the failure that broke the global
Elo recompute. These tests pin the chunking behavior that prevents it.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from supabase_client import UPSERT_BATCH_SIZE, SupabaseClient  # noqa: E402


def _make_client() -> tuple[SupabaseClient, Mock]:
    """Build a SupabaseClient with a mocked supabase-py client.

    Bypasses __init__ so no real credentials / network are needed. Each
    .upsert(batch).execute() echoes its batch back as result.data.
    """
    client = SupabaseClient.__new__(SupabaseClient)
    table = Mock()

    def _upsert(batch, **kwargs):
        execute = Mock()
        execute.execute.return_value = Mock(data=list(batch))
        return execute

    table.upsert.side_effect = _upsert
    inner = Mock()
    inner.table.return_value = table
    client._client = inner
    return client, table


class TestUpsertBatching(unittest.TestCase):
    def test_large_list_is_split_into_batches(self) -> None:
        client, table = _make_client()
        rows = [{"player_id": i} for i in range(UPSERT_BATCH_SIZE * 2 + 7)]

        returned = client.upsert("global_elo_ratings", rows, on_conflict="player_id")

        # Three requests: two full batches + the remainder.
        self.assertEqual(table.upsert.call_count, 3)
        sent_sizes = [len(call.args[0]) for call in table.upsert.call_args_list]
        self.assertEqual(sent_sizes, [UPSERT_BATCH_SIZE, UPSERT_BATCH_SIZE, 7])
        # on_conflict is forwarded on every batch.
        for call in table.upsert.call_args_list:
            self.assertEqual(call.kwargs.get("on_conflict"), "player_id")
        # All rows are returned, concatenated and in order.
        self.assertEqual(returned, rows)

    def test_small_list_sends_single_request(self) -> None:
        client, table = _make_client()
        rows = [{"player_id": 1}, {"player_id": 2}]

        client.upsert("t", rows)

        self.assertEqual(table.upsert.call_count, 1)
        self.assertEqual(table.upsert.call_args.args[0], rows)

    def test_single_dict_row_sends_one_request(self) -> None:
        client, table = _make_client()
        row = {"player_id": 1}

        client.upsert("t", row)

        self.assertEqual(table.upsert.call_count, 1)
        self.assertEqual(table.upsert.call_args.args[0], [row])

    def test_empty_list_makes_no_requests(self) -> None:
        client, table = _make_client()

        returned = client.upsert("t", [])

        self.assertEqual(table.upsert.call_count, 0)
        self.assertEqual(returned, [])


if __name__ == "__main__":
    unittest.main()
