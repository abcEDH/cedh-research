import sys
import types
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.modules["psycopg2"] = None

fake_ingest = types.ModuleType("ingest")
fake_ingest.SupabaseClient = MagicMock
fake_ingest.load_local_env = MagicMock
sys.modules["ingest"] = fake_ingest

import rebuild_global_elo_tables as rebuild  # noqa: E402


class RebuildGlobalEloTablesTests(TestCase):
    def test_eligible_game_ids_preserves_games_with_mixed_participant_eligibility(self) -> None:
        rows = [
            {"game_id": "game-1", "ranking_eligible": True},
            {"game_id": "game-1", "ranking_eligible": False},
            {"game_id": "game-2", "ranking_eligible": False},
        ]

        self.assertEqual(rebuild.eligible_game_ids(rows, "ranking"), {"game-1"})

    def test_eligible_game_ids_rejects_unknown_tiers(self) -> None:
        with self.assertRaises(ValueError):
            rebuild.eligible_game_ids([], "unknown")


if __name__ == "__main__":
    main()
