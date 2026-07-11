"""Regression tests for the TopDeck Elo importer's replace-snapshot pruning.

See docs/decisions/0016-rank-activity-window-and-topdeck-snapshot-pruning.md:
`upsert_elo_rows` upserts the freshly fetched TopDeck Elo snapshot and deletes
any `topdeck_player_elos` row not present in that snapshot, in the same
transaction, so delisted players (e.g. banned cheaters) don't linger with a
stale rating/rank indefinitely (issue #252 / PR #263).
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import import_topdeck_player_elos as importer  # noqa: E402


def _make_conn_and_cursor() -> tuple[MagicMock, MagicMock]:
    """Build a mock connection whose `with conn.cursor() as cursor:` yields
    the same mock cursor every time, matching how `upsert_elo_rows` uses it.
    """
    conn = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 0
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = False
    return conn, cursor


def _elo_row(topdeck_id: str, elo: float = 2000.0, games_played: int = 10, ranking: int = 1) -> dict:
    return {
        "topdeck_id": topdeck_id,
        "name": f"Player {topdeck_id}",
        "username": None,
        "profile_image_url": None,
        "elo": elo,
        "games_played": games_played,
        "ranking": ranking,
    }


class UpsertEloRowsPruningTests(unittest.TestCase):
    # Patched via the already-imported `import_topdeck_player_elos` module's
    # own `psycopg2` attribute rather than a fresh `psycopg2.extras.execute_values`
    # lookup: another test module in this suite (test_rebuild_player_commander_profiles.py)
    # sets `sys.modules["psycopg2"] = None` at import time as a stub, which
    # would make a bare `@patch("psycopg2.extras.execute_values")` re-import
    # fail once both modules have been collected in the same pytest session.
    @patch("import_topdeck_player_elos.psycopg2.extras.execute_values")
    def test_upserts_present_rows_and_prunes_absent_rows(self, mock_execute_values: MagicMock) -> None:
        conn, cursor = _make_conn_and_cursor()
        cursor.rowcount = 4  # 4 stale rows deleted by the DELETE statement

        rows = [_elo_row("td-1"), _elo_row("td-2")]

        pruned = importer.upsert_elo_rows(
            conn, rows, players_by_topdeck_id={}, source_url="https://example.com/elo.json"
        )

        self.assertEqual(pruned, 4)

        mock_execute_values.assert_called_once()
        upsert_args = mock_execute_values.call_args.args
        self.assertIs(upsert_args[0], cursor)
        db_rows = upsert_args[2]
        self.assertEqual([row[0] for row in db_rows], ["td-1", "td-2"])

        delete_calls = [c for c in cursor.execute.call_args_list if "DELETE" in c.args[0]]
        self.assertEqual(len(delete_calls), 1)
        _, delete_params = delete_calls[0].args
        self.assertEqual(delete_params, (["td-1", "td-2"],))

        conn.commit.assert_called_once()

    @patch("import_topdeck_player_elos.psycopg2.extras.execute_values")
    def test_upserted_rows_carry_matched_player_ids(self, mock_execute_values: MagicMock) -> None:
        conn, _cursor = _make_conn_and_cursor()
        rows = [_elo_row("td-1")]
        players_by_topdeck_id = {"td-1": {"id": "player-1"}}

        importer.upsert_elo_rows(
            conn, rows, players_by_topdeck_id=players_by_topdeck_id, source_url="https://example.com/elo.json"
        )

        db_rows = mock_execute_values.call_args.args[2]
        self.assertEqual(db_rows[0][0], "td-1")
        self.assertEqual(db_rows[0][1], "player-1")

    @patch("import_topdeck_player_elos.psycopg2.extras.execute_values")
    def test_empty_snapshot_aborts_without_upserting_or_deleting(self, mock_execute_values: MagicMock) -> None:
        conn, cursor = _make_conn_and_cursor()

        pruned = importer.upsert_elo_rows(
            conn, rows=[], players_by_topdeck_id={}, source_url="https://example.com/elo.json"
        )

        self.assertEqual(pruned, 0)
        mock_execute_values.assert_not_called()
        cursor.execute.assert_not_called()
        conn.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
