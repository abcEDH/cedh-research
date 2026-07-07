import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backfill_flat_firestore_games import fetch_tournaments  # noqa: E402
from game_registry import GAME_REGISTRY  # noqa: E402


class FetchTournamentsScopingTests(unittest.TestCase):
    """The flat Firestore backfill only ever recovers legacy cEDH data (PR #247
    review): its tournament scan must be scoped to cEDH so a coincidental
    Firestore hit can never attach the MTG-only "Unknown Commander" fallback
    to a Riftbound/Gundam/YGO tournament_entries row."""

    def test_fetch_tournaments_scopes_to_cedh_game_and_format(self) -> None:
        client = Mock()
        client.select.return_value = []

        fetch_tournaments(client, only_leagues=False)

        cedh = GAME_REGISTRY["cedh"]
        params = client.select.call_args.args[1]
        self.assertEqual(params["game"], f"eq.{cedh.db_game}")
        self.assertEqual(params["format"], f"eq.{cedh.db_format}")

    def test_only_leagues_filter_is_preserved_alongside_game_scope(self) -> None:
        client = Mock()
        client.select.return_value = []

        fetch_tournaments(client, only_leagues=True)

        params = client.select.call_args.args[1]
        self.assertEqual(params["name"], "ilike.*league*")
        self.assertIn("game", params)
        self.assertIn("format", params)


if __name__ == "__main__":
    unittest.main()
