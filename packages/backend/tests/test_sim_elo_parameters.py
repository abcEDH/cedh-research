import unittest
from datetime import datetime

from run_topdeck_ongoing_tournament_sim import update_elos_for_result
from sim_engine import build_tournament_context, exact_top_cut_probabilities, initialize_state
from sim_models import (
    CANDIDATE_WINNER_FEATURES,
    build_candidate_winner_feature_row,
    build_round_snapshot,
    predict_decisive_win_probabilities,
    predict_decisive_win_probs,
)
from sim_types import Pod, PodResult, SimPlayer, TournamentSpec


class PublishedSeatModelTests(unittest.TestCase):
    def setUp(self):
        self.ids = ["a", "b", "c", "d"]
        self.state = initialize_state(
            TournamentSpec("test", "Test", datetime(2026, 9, 19), 3, 4, 4),
            [SimPlayer(pid, pid, 1500) for pid in self.ids],
        )

    def pod(self, round_index=0):
        return Pod(round_index, 1, self.ids, seats_by_player=dict(zip(self.ids, [1, 2, 3, 4], strict=True)))

    def expected(self, offsets):
        weights = [2 ** (offset / 200) for offset in offsets]
        return [w / sum(weights) for w in weights]

    def test_swiss_and_topcut_use_published_stage_values(self):
        for r, offsets in [
            (0, [0, -48.820457256958306, -97.04491395828074, -144.80626927577129]),
            (3, [0, -117.5921368942531, -172.63550764675733, -227.7663864826161]),
        ]:
            pod = self.pod(r)
            scalar = predict_decisive_win_probs(pod, self.state)
            batch = predict_decisive_win_probabilities([pod], self.state)[(r, 1)]
            for pid, got, expected in zip(self.ids, batch, self.expected(offsets), strict=True):
                self.assertAlmostEqual(got, expected)
                self.assertAlmostEqual(scalar[pid], expected)

    def test_actual_seat_map_not_player_list_order(self):
        pod = self.pod(3)
        pod.seats_by_player = dict(zip(self.ids, [4, 3, 2, 1], strict=True))
        probabilities = predict_decisive_win_probs(pod, self.state)
        self.assertGreater(probabilities["d"], probabilities["a"])

    def test_partial_and_three_player_seats_have_no_offset(self):
        for seats, ids in [({"a": 1}, self.ids), ({"a": 1, "b": 2, "c": 3}, self.ids[:3])]:
            pod = Pod(0, 1, ids, seats_by_player=seats)
            for v in predict_decisive_win_probs(pod, self.state).values():
                self.assertAlmostEqual(v, 1 / len(ids))

    def test_exact_final_uses_topcut_offsets(self):
        winners, _ = exact_top_cut_probabilities(self.ids, self.state)
        expected = self.expected([0, -117.5921368942531, -172.63550764675733, -227.7663864826161])
        for pid, p in zip(self.ids, expected, strict=True):
            self.assertAlmostEqual(winners[pid], p)
        self.assertAlmostEqual(sum(winners.values()), 1)

    def test_candidate_feature_uses_topcut_offset(self):
        pod = self.pod(3)
        context = build_tournament_context(self.state.spec)
        snapshot = build_round_snapshot(self.state, context, 4)
        features = build_candidate_winner_feature_row(
            pod, self.state, context, snapshot, "b", predict_decisive_win_probs(pod, self.state)
        )
        self.assertAlmostEqual(features[CANDIDATE_WINNER_FEATURES.index("candidate_seat_bonus")], -117.5921368942531)

    def test_replay_uses_published_swiss_learning_rate(self):
        pod = self.pod()
        expected = self.expected([0, -48.820457256958306, -97.04491395828074, -144.80626927577129])
        result = PodResult(0, 1, self.ids, False, "a", tuple(expected), 0)
        update_elos_for_result(self.state, pod, result)
        self.assertAlmostEqual(self.state.players["a"].elo, round(1500 + 64.20106085407248 * (1 - expected[0]), 6))


if __name__ == "__main__":
    unittest.main()
