from datetime import datetime
import random
import unittest

from sim_pairings import (
    opponent_match_win_percentage,
    pair_swiss_round,
    pair_topdeck_bracket,
    select_top_cut,
    topdeck_bye_rank,
)
from sim_types import FeatureContext, SimPlayer, TournamentSpec
from sim_engine import apply_points_drop_if_due, initialize_state


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

        self.assertEqual({player_id for pod in pods for player_id in pod.player_ids}, {"p1", "p2", "p3", "p4"})
        self.assertEqual(select_top_cut(state), ["p1", "p2", "p3", "p4"])

    def test_points_drop_filters_future_pairings_and_top_cut(self):
        state = make_state(6)
        state.spec.drop_after_round = 2
        state.spec.drop_min_points = 6
        state.eligible_player_ids = {"p1", "p2", "p3", "p4", "p5"}
        for player_id, points in {
            "p1": 6,
            "p2": 5,
            "p3": 10,
            "p4": 0,
            "p5": 6,
            "p6": 8,
        }.items():
            state.standings[player_id].points = points

        changed = apply_points_drop_if_due(state, completed_round_number=2)
        pods = pair_swiss_round(state, 2, random.Random(1))

        self.assertTrue(changed)
        self.assertEqual(state.eligible_player_ids, {"p1", "p3", "p5"})
        self.assertEqual({player_id for pod in pods for player_id in pod.player_ids}, {"p1", "p3", "p5"})
        self.assertEqual(select_top_cut(state), ["p3", "p1", "p5"])

    def test_swiss_pairing_randomizes_players_within_same_points(self):
        state = make_state()
        pods = pair_swiss_round(state, 0, random.Random(1))

        self.assertEqual([pod.player_ids for pod in pods], [["p4", "p7", "p2", "p6"], ["p8", "p1", "p5", "p3"]])

    def test_swiss_pairing_chunks_adjacent_records(self):
        state = make_state()
        for player_id in ("p1", "p2", "p3", "p4"):
            state.standings[player_id].points = 5
            state.standings[player_id].wins = 1

        pods = pair_swiss_round(state, 1, random.Random(1))

        self.assertEqual({player_id for pod in pods[:1] for player_id in pod.player_ids}, {"p1", "p2", "p3", "p4"})

    def test_topdeck_pod_sizes_use_three_player_pods_for_one_extra_player(self):
        state = make_state(41)

        pods = pair_swiss_round(state, 0, random.Random(1))

        self.assertEqual([len(pod.player_ids) for pod in pods], [4, 4, 4, 4, 4, 4, 4, 4, 3, 3, 3])

    def test_repeat_avoidance_runs_at_or_below_threshold(self):
        state = make_state()
        state.spec.repeat_avoidance_max_pods = 32
        state.feature_context.tournament_pair_meetings[("p1", "p2")] = 1

        pods = pair_swiss_round(state, 1, random.Random(7))

        self.assertFalse(any({"p1", "p2"}.issubset(set(pod.player_ids)) for pod in pods))

    def test_repeat_avoidance_skips_above_threshold(self):
        state = make_state()
        state.spec.repeat_avoidance_max_pods = 1
        state.feature_context.tournament_pair_meetings[("p1", "p2")] = 1

        pods = pair_swiss_round(state, 1, random.Random(7))

        self.assertTrue(any({"p1", "p2"}.issubset(set(pod.player_ids)) for pod in pods))

    def test_opponent_match_win_percentage_uses_match_points(self):
        state = make_state()
        state.standings["p1"].opponents = {"p2", "p3"}
        state.standings["p2"].points = 6
        state.standings["p2"].wins = 1
        state.standings["p2"].draws = 1
        state.standings["p2"].losses = 1
        state.standings["p2"].pods_played = 3
        state.standings["p3"].points = 0
        state.standings["p3"].losses = 3
        state.standings["p3"].pods_played = 3

        self.assertAlmostEqual(opponent_match_win_percentage(state, "p1"), 0.30)

    def test_select_top_cut_randomizes_exact_ties_after_tiebreak_seed(self):
        state = make_state(2)
        state.spec.top_cut = 1
        state.players["p1"].tiebreak_seed = 1
        state.players["p2"].tiebreak_seed = 1

        self.assertEqual(select_top_cut(state, rng=random.Random(1)), ["p1"])

        state.standings_random_tiebreakers.clear()
        self.assertEqual(select_top_cut(state, rng=random.Random(2)), ["p2"])

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
