import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import derive_standing_results


class DerivedStandingResultsTests(unittest.TestCase):
    def test_derives_win_loss_draw_and_points_from_completed_tables(self) -> None:
        rounds = [
            {
                "round": 1,
                "tables": [
                    {
                        "players": [{"id": "winner"}, {"id": "loser"}],
                        "winner_id": "winner",
                    },
                    {
                        "players": [{"id": "drawer"}, {"id": "other"}],
                        "winner_id": "Draw",
                    },
                ],
            }
        ]

        self.assertEqual(
            derive_standing_results(rounds),
            {
                "winner": {"wins": 1, "losses": 0, "draws": 0, "points": 5},
                "loser": {"wins": 0, "losses": 1, "draws": 0, "points": 0},
                "drawer": {"wins": 0, "losses": 0, "draws": 1, "points": 1},
                "other": {"wins": 0, "losses": 0, "draws": 1, "points": 1},
            },
        )

    def test_ignores_tables_without_a_result(self) -> None:
        rounds = [
            {
                "tables": [
                    {"players": [{"id": "a"}, {"id": "b"}], "status": "Active"},
                ]
            }
        ]

        self.assertEqual(derive_standing_results(rounds), {})


if __name__ == "__main__":
    unittest.main()
