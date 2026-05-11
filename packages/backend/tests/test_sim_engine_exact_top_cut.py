from datetime import datetime
import unittest

from sim_engine import exact_top_cut_probabilities
from sim_models import predict_decisive_win_probabilities
from sim_pairings import pair_topdeck_bracket
from sim_types import SimPlayer, StandingRow, TournamentSpec, TournamentState


def build_state(player_count: int, top_cut: int) -> tuple[list[str], TournamentState]:
    player_ids = [f"p{index}" for index in range(1, player_count + 1)]
    players = {
        player_id: SimPlayer(player_id=player_id, name=player_id, elo=1500.0, tiebreak_seed=index)
        for index, player_id in enumerate(player_ids, start=1)
    }
    state = TournamentState(
        spec=TournamentSpec(
            tournament_id="test",
            name="Test",
            start_date=datetime(2024, 1, 1),
            swiss_rounds=7,
            top_cut=top_cut,
            player_count=player_count,
        ),
        players=players,
        standings={player_id: StandingRow(player_id=player_id) for player_id in player_ids},
    )
    return player_ids, state


class ExactTopCutTests(unittest.TestCase):
    def test_top4_equal_elos(self):
        player_ids, state = build_state(4, 4)
        winners, advancement = exact_top_cut_probabilities(player_ids, state)
        _auto_advancers, pods = pair_topdeck_bracket(player_ids, state.spec.swiss_rounds)
        expected = predict_decisive_win_probabilities(pods, state)[(state.spec.swiss_rounds, 1)]

        self.assertAlmostEqual(sum(winners.values()), 1.0)
        self.assertEqual(set(advancement[4]), set(player_ids))
        for player_id, probability in zip(player_ids, expected, strict=True):
            self.assertAlmostEqual(winners[player_id], probability)
            self.assertAlmostEqual(advancement[4][player_id], 1.0)

    def test_top10_auto_advancers_and_play_in_probabilities(self):
        player_ids, state = build_state(10, 10)
        winners, advancement = exact_top_cut_probabilities(player_ids, state)
        _auto_advancers, pods = pair_topdeck_bracket(player_ids, state.spec.swiss_rounds)
        play_in_probabilities = predict_decisive_win_probabilities(pods, state)

        self.assertAlmostEqual(sum(winners.values()), 1.0)
        self.assertAlmostEqual(advancement[4]["p1"], 1.0)
        self.assertAlmostEqual(advancement[4]["p2"], 1.0)
        for pod in pods:
            probabilities = play_in_probabilities[(pod.round_index, pod.table_number)]
            for player_id, probability in zip(pod.player_ids, probabilities, strict=True):
                self.assertAlmostEqual(advancement[4][player_id], probability)

    def test_top16_equal_elos(self):
        player_ids, state = build_state(16, 16)
        winners, advancement = exact_top_cut_probabilities(player_ids, state)
        _auto_advancers, pods = pair_topdeck_bracket(player_ids, state.spec.swiss_rounds)
        quarterfinal_probabilities = predict_decisive_win_probabilities(pods, state)

        self.assertAlmostEqual(sum(winners.values()), 1.0)
        for pod in pods:
            probabilities = quarterfinal_probabilities[(pod.round_index, pod.table_number)]
            for player_id, probability in zip(pod.player_ids, probabilities, strict=True):
                self.assertAlmostEqual(advancement[4][player_id], probability)


if __name__ == "__main__":
    unittest.main()
