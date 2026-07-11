import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commander_dedup import repoint_commander_matchups  # noqa: E402


class RepointCommanderMatchupsTests(unittest.TestCase):
    """Regression coverage for the commander_matchups FK-violation bug.

    commander_matchups.commander_id and .opponent_commander_id both have
    non-cascading foreign keys to commanders(id). A merge that repoints
    tournament_entries and then deletes the duplicate commander row, without
    also repointing commander_matchups, fails the DELETE with a foreign-key
    violation whenever the duplicate has any matchup rows - leaving a
    half-merged duplicate (tournament_entries already repointed, commander
    row still present).
    """

    @patch("commander_dedup.requests.patch")
    def test_repoints_both_commander_id_and_opponent_commander_id_columns(self, mock_patch: Mock) -> None:
        mock_patch.return_value = Mock(raise_for_status=Mock())
        client = Mock()
        client.url = "https://example.supabase.co"
        client.headers = {"apikey": "test-key"}

        repoint_commander_matchups(client, "source-id", "target-id")

        self.assertEqual(mock_patch.call_count, 2)

        calls = [(call.kwargs["params"], call.kwargs["json"]) for call in mock_patch.call_args_list]
        self.assertIn(
            ({"commander_id": "eq.source-id"}, {"commander_id": "target-id"}),
            calls,
        )
        self.assertIn(
            ({"opponent_commander_id": "eq.source-id"}, {"opponent_commander_id": "target-id"}),
            calls,
        )

        for call in mock_patch.call_args_list:
            self.assertEqual(call.args[0], "https://example.supabase.co/rest/v1/commander_matchups")
            self.assertEqual(call.kwargs["timeout"], 60)

    @patch("commander_dedup.requests.patch")
    def test_raises_on_http_error(self, mock_patch: Mock) -> None:
        response = Mock()
        response.raise_for_status.side_effect = RuntimeError("boom")
        mock_patch.return_value = response
        client = Mock()
        client.url = "https://example.supabase.co"
        client.headers = {}

        with self.assertRaises(RuntimeError):
            repoint_commander_matchups(client, "source-id", "target-id")


if __name__ == "__main__":
    unittest.main()
