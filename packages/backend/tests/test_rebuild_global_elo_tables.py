import sys
import types
from datetime import date
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.modules["psycopg2"] = None

fake_ingest = types.ModuleType("ingest")
fake_ingest.SupabaseClient = MagicMock
fake_ingest.load_local_env = MagicMock
_real_ingest = sys.modules.get("ingest")
sys.modules["ingest"] = fake_ingest

import rebuild_global_elo_tables as rebuild  # noqa: E402

if _real_ingest is not None:
    sys.modules["ingest"] = _real_ingest
else:
    del sys.modules["ingest"]


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

    def test_apply_game_scores_every_player_in_an_eligible_full_pod(self) -> None:
        rows = [
            {
                "game_id": "game-1",
                "tournament_id": "tournament-1",
                "player_id": f"player-{index}",
                "entry_id": f"entry-{index}",
                "player_name": f"Player {index}",
                "topdeck_id": f"topdeck-{index}",
                "start_date": "2026-07-01T00:00:00Z",
                "result": "win" if index == 1 else "loss",
                "seat_position": index - 1,
            }
            for index in range(1, 5)
        ]

        ratings: dict[str, dict] = {}
        events = rebuild.apply_game(
            rows,
            ratings,
            {},
            {},
            date(2026, 7, 2),
            update_activity=False,
        )

        self.assertEqual(set(ratings), {"player-1", "player-2", "player-3", "player-4"})
        self.assertEqual(
            {event["player_id"] for event in events},
            {"player-1", "player-2", "player-3", "player-4"},
        )
        self.assertEqual({event["opponent_count"] for event in events}, {3})

    def test_build_arg_parser_exposes_tier_independently(self) -> None:
        args = rebuild.build_arg_parser().parse_args(["--tier", "local"])

        self.assertEqual(args.tier, "local")

    def test_validate_apply_tier_rejects_alternate_tiers(self) -> None:
        with self.assertRaises(SystemExit):
            rebuild.validate_apply_tier(True, "local")

        rebuild.validate_apply_tier(False, "local")

    def test_validate_incremental_tier_allows_only_ranking(self) -> None:
        rebuild.validate_incremental_tier("2026-07-01", "ranking")

        with self.assertRaises(SystemExit):
            rebuild.validate_incremental_tier("2026-07-01", "all")


if __name__ == "__main__":
    main()
