from __future__ import annotations

import unittest

from evaluate_topdeck_pairings import build_historical_rounds, score_pairings
from sim_types import Pod


class EvaluateTopdeckPairingsTest(unittest.TestCase):
    def test_score_pairings_uses_copod_pairs_and_exact_pods(self) -> None:
        actual = [
            Pod(round_index=0, table_number=1, player_ids=["a", "b", "c", "d"]),
            Pod(round_index=0, table_number=2, player_ids=["e", "f", "g", "h"]),
        ]
        predicted = [
            Pod(round_index=0, table_number=1, player_ids=["a", "b", "c", "d"]),
            Pod(round_index=0, table_number=2, player_ids=["e", "f", "h", "x"]),
        ]

        metrics = score_pairings(predicted, actual)

        self.assertAlmostEqual(metrics["pair_recall"], 9 / 12)
        self.assertAlmostEqual(metrics["pair_precision"], 9 / 12)
        self.assertAlmostEqual(metrics["exact_pod_recall"], 1 / 2)
        self.assertAlmostEqual(metrics["table_exact_recall"], 1 / 2)

    def test_build_historical_rounds_separates_byes_from_pods(self) -> None:
        rows = [
            {
                "game_id": "g1",
                "entry_id": "e1",
                "player_id": "p1",
                "round_number": 1,
                "table_number": 1,
                "result": "bye",
            },
            {
                "game_id": "g2",
                "entry_id": "e2",
                "player_id": "p2",
                "round_number": 1,
                "table_number": 2,
                "result": "win",
            },
            {
                "game_id": "g2",
                "entry_id": "e3",
                "player_id": "p3",
                "round_number": 1,
                "table_number": 2,
                "result": "loss",
            },
        ]

        rounds = build_historical_rounds(rows, {("g2", "e2"): 2, ("g2", "e3"): 1})

        self.assertEqual(rounds[1].byes, ["p1"])
        self.assertEqual(len(rounds[1].pods), 1)
        self.assertEqual(rounds[1].pods[0].player_ids, ["p2", "p3"])
        self.assertEqual(rounds[1].pods[0].seats_by_player, {"p2": 2, "p3": 1})
        self.assertEqual(rounds[1].results[0].winner_id, "p2")


if __name__ == "__main__":
    unittest.main()
