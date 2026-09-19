from __future__ import annotations

import unittest

from evaluate_pairing_profile_diagnostics import can_form_profile, local_neighbor_profile_recall
from sim_types import Pod


class PairingProfileDiagnosticsTest(unittest.TestCase):
    def test_can_form_profile_from_point_pool(self) -> None:
        self.assertTrue(can_form_profile([5, 5, 0, 0], (5, 0, 0)))
        self.assertFalse(can_form_profile([5, 0, 0], (5, 5, 0)))

    def test_local_neighbor_profile_recall_uses_table_position_window(self) -> None:
        class State:
            standings = {
                "a": type("Standing", (), {"points": 5})(),
                "b": type("Standing", (), {"points": 5})(),
                "c": type("Standing", (), {"points": 0})(),
                "d": type("Standing", (), {"points": 0})(),
            }

        expected = [(5, 5), (0, 0)]
        pods = [
            Pod(round_index=1, table_number=1, player_ids=["a", "c"]),
            Pod(round_index=1, table_number=2, player_ids=["b", "d"]),
        ]

        self.assertEqual(local_neighbor_profile_recall(expected, pods, State(), radius=0), 0.0)
        self.assertEqual(local_neighbor_profile_recall(expected, pods, State(), radius=1), 1.0)


if __name__ == "__main__":
    unittest.main()
