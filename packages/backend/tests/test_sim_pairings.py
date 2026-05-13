from datetime import datetime
import random
import unittest

from sim_pairings import pair_swiss_round, pair_topdeck_bracket, select_top_cut, topdeck_bye_rank
from sim_types import FeatureContext, SimPlayer, TournamentSpec
from sim_engine import initialize_state


def make_state(player_count: int = 8):
    players = [
        SimPlayer(player_id=f"p{index}", name=f"Player {index}", elo=1500.0, tiebreak_seed=index)
        for index in range(1, player_count + 1)
    ]
    spec = TournamentSpec(
        tournament_id="test",
        name="Test",
        start_date=datetime(2026, 1, 1),
        swiss_rounds=4,
        top_cut=4,
        player_count=player_count,
    )
    return initialize_state(spec, players, feature_context=FeatureContext())


class SimPairingsTest(unittest.TestCase):
    def test_eligible_players_limit_pairings_and_top_cut(self):
        state = make_state()
        state.eligible_player_ids = {"p1", "p2", "p3", "p4"}
        for player_id, standing in state.standings.items():
            standing.points = 10 if player_id in {"p5", "p6"} else 0

        pods = pair_swiss_round(state, 0, random.Random(1))

        self.assertEqual([player_id for pod in pods for player_id in pod.player_ids], ["p1", "p2", "p3", "p4"])
        self.assertEqual(select_top_cut(state), ["p1", "p2", "p3", "p4"])

    def test_fast_live_mode_still_avoids_repeats_for_small_pairing_sets(self):
        state = make_state()
        state.fast_live_mode = True
        state.spec.repeat_avoidance_max_pods = 32
        state.feature_context.tournament_pair_meetings[("p1", "p2")] = 1

        pods = pair_swiss_round(state, 1, random.Random(1))

        self.assertFalse(any({"p1", "p2"}.issubset(set(pod.player_ids)) for pod in pods))

    def test_repeat_avoidance_can_be_disabled_by_threshold(self):
        state = make_state()
        state.spec.repeat_avoidance_max_pods = 0
        state.feature_context.tournament_pair_meetings[("p1", "p2")] = 1

        pods = pair_swiss_round(state, 1, random.Random(1))

        self.assertTrue(any({"p1", "p2"}.issubset(set(pod.player_ids)) for pod in pods))

    def test_topdeck_bye_rank(self):
        self.assertEqual(topdeck_bye_rank(40), 8)
        self.assertEqual(topdeck_bye_rank(10), 2)
        self.assertIsNone(topdeck_bye_rank(16))

    def test_top10_bracket_pairing(self):
        players = [f"p{index}" for index in range(1, 11)]

        auto_advancers, pods = pair_topdeck_bracket(players, 4)

        self.assertEqual(auto_advancers, ["p1", "p2"])
        self.assertEqual([pod.player_ids for pod in pods], [["p3", "p6", "p7", "p10"], ["p4", "p5", "p8", "p9"]])

    def test_top64_bracket_pairing(self):
        players = [f"p{index}" for index in range(1, 65)]

        auto_advancers, pods = pair_topdeck_bracket(players, 4)

        self.assertEqual(auto_advancers, [])
        self.assertEqual(len(pods), 16)
        self.assertEqual(pods[0].player_ids, ["p1", "p32", "p33", "p64"])
        self.assertEqual(pods[-1].player_ids, ["p16", "p17", "p48", "p49"])


if __name__ == "__main__":
    unittest.main()
