from __future__ import annotations

import unittest
from datetime import datetime

from evaluate_topdeck_pairings import score_profile_feasibility
from sim_engine import initialize_state
from sim_types import FeatureContext, Pod, SimPlayer, TournamentSpec


def make_state():
    players = [
        SimPlayer(player_id=f"p{index}", name=f"Player {index}", elo=1500.0, tiebreak_seed=index)
        for index in range(1, 9)
    ]
    spec = TournamentSpec(
        tournament_id="test",
        name="Test",
        start_date=datetime(2026, 1, 1),
        swiss_rounds=2,
        top_cut=4,
        player_count=8,
    )
    return initialize_state(spec, players, feature_context=FeatureContext())


class PairingScoreProfilesTest(unittest.TestCase):
    def test_score_profile_feasibility_scores_point_and_record_profiles(self) -> None:
        state = make_state()
        for player_id in ("p1", "p2", "p3", "p4"):
            state.standings[player_id].points = 5
            state.standings[player_id].wins = 1
        for player_id in ("p5", "p6", "p7", "p8"):
            state.standings[player_id].losses = 1

        feasible_pods = [
            Pod(round_index=1, table_number=1, player_ids=["p1", "p2", "p3", "p4"]),
            Pod(round_index=1, table_number=2, player_ids=["p5", "p6", "p7", "p8"]),
        ]
        mixed_pods = [
            Pod(round_index=1, table_number=1, player_ids=["p1", "p2", "p5", "p6"]),
            Pod(round_index=1, table_number=2, player_ids=["p3", "p4", "p7", "p8"]),
        ]

        self.assertEqual(score_profile_feasibility(state, feasible_pods)["points_profile_recall"], 1.0)
        self.assertEqual(score_profile_feasibility(state, feasible_pods)["record_profile_recall"], 1.0)
        self.assertEqual(score_profile_feasibility(state, mixed_pods)["points_profile_recall"], 0.0)
        self.assertEqual(score_profile_feasibility(state, mixed_pods)["record_profile_recall"], 0.0)


if __name__ == "__main__":
    unittest.main()
