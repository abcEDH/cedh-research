from __future__ import annotations

import unittest
from datetime import datetime

import numpy as np

from sim_engine import initialize_state
from sim_models import (
    CANDIDATE_WINNER_FEATURES,
    LoadedCandidateWinnerModel,
    LoadedDrawModel,
    build_round_snapshot,
    predict_decisive_win_probabilities,
    predict_pod_outcome_probabilities,
)
from sim_types import FeatureContext, Pod, SimPlayer, TournamentSpec


class FixedOutcomeModel:
    classes_ = np.array([0, 1, 2, 3, 4])

    def predict_proba(self, x_matrix):
        return np.tile(np.array([[0.20, 0.10, 0.30, 0.25, 0.15]]), (x_matrix.shape[0], 1))


class FixedDrawModel:
    def predict_proba(self, x_matrix):
        return np.tile(np.array([[0.80, 0.20]]), (x_matrix.shape[0], 1))


class SeatWinnerModel:
    classes_ = np.array([0, 1])

    def predict_proba(self, x_matrix):
        seat_index = CANDIDATE_WINNER_FEATURES.index("candidate_seat")
        positive = x_matrix[:, seat_index] / 10.0
        return np.column_stack((1.0 - positive, positive))


class PodOutcomeModelTest(unittest.TestCase):
    def test_pod_outcome_artifact_returns_draw_and_conditional_win_probabilities(self) -> None:
        players = [
            SimPlayer(player_id=f"p{index}", name=f"Player {index}", elo=1500.0, tiebreak_seed=index)
            for index in range(1, 5)
        ]
        spec = TournamentSpec(
            tournament_id="test-event",
            name="Test Event",
            start_date=datetime(2026, 1, 1),
            swiss_rounds=1,
            top_cut=4,
            player_count=4,
        )
        state = initialize_state(spec, players, feature_context=FeatureContext())
        from sim_engine import build_tournament_context

        context = build_tournament_context(spec)
        pod = Pod(round_index=0, table_number=1, player_ids=[player.player_id for player in players])
        snapshot = build_round_snapshot(state, context, 1)
        artifact = LoadedDrawModel(
            features=["is_swiss"],
            model=FixedOutcomeModel(),
            calibration="uncalibrated",
            feature_indexes=np.array([0]),
            target="pod_outcome",
            winner_source="artifact",
        )

        draw_probabilities, win_probabilities = predict_pod_outcome_probabilities(
            [pod],
            state,
            context,
            artifact,
            snapshot,
        )

        key = (0, 1)
        self.assertAlmostEqual(draw_probabilities[key], 0.20)
        self.assertEqual(len(win_probabilities[key]), 4)
        self.assertAlmostEqual(sum(win_probabilities[key]), 1.0)
        self.assertAlmostEqual(win_probabilities[key][0], 0.10 / 0.80)
        self.assertAlmostEqual(win_probabilities[key][1], 0.30 / 0.80)

    def test_candidate_winner_artifact_replaces_elo_winner_shares(self) -> None:
        players = [
            SimPlayer(player_id=f"p{index}", name=f"Player {index}", elo=1600.0 - (index * 25), tiebreak_seed=index)
            for index in range(1, 5)
        ]
        spec = TournamentSpec(
            tournament_id="test-event",
            name="Test Event",
            start_date=datetime(2026, 1, 1),
            swiss_rounds=1,
            top_cut=4,
            player_count=4,
        )
        state = initialize_state(spec, players, feature_context=FeatureContext())
        from sim_engine import build_tournament_context

        context = build_tournament_context(spec)
        pod = Pod(
            round_index=0,
            table_number=1,
            player_ids=[player.player_id for player in players],
            seats_by_player={player.player_id: index for index, player in enumerate(players, start=1)},
        )
        snapshot = build_round_snapshot(state, context, 1)
        draw_artifact = LoadedDrawModel(
            features=["is_swiss"],
            model=FixedDrawModel(),
            calibration="uncalibrated",
            feature_indexes=np.array([0]),
        )
        winner_artifact = LoadedCandidateWinnerModel(
            features=list(CANDIDATE_WINNER_FEATURES),
            model=SeatWinnerModel(),
            blend_weight=1.0,
        )

        draw_probabilities, win_probabilities = predict_pod_outcome_probabilities(
            [pod],
            state,
            context,
            draw_artifact,
            snapshot,
            winner_artifact,
        )

        key = (0, 1)
        self.assertAlmostEqual(draw_probabilities[key], 0.20)
        self.assertAlmostEqual(sum(win_probabilities[key]), 1.0)
        self.assertAlmostEqual(win_probabilities[key][0], 0.10)
        self.assertAlmostEqual(win_probabilities[key][1], 0.20)
        self.assertAlmostEqual(win_probabilities[key][2], 0.30)
        self.assertAlmostEqual(win_probabilities[key][3], 0.40)

    def test_pod_outcome_draw_only_artifact_uses_elo_winner_shares(self) -> None:
        players = [
            SimPlayer(player_id="p1", name="Player 1", elo=1800.0, tiebreak_seed=1),
            SimPlayer(player_id="p2", name="Player 2", elo=1600.0, tiebreak_seed=2),
            SimPlayer(player_id="p3", name="Player 3", elo=1500.0, tiebreak_seed=3),
            SimPlayer(player_id="p4", name="Player 4", elo=1400.0, tiebreak_seed=4),
        ]
        spec = TournamentSpec(
            tournament_id="test-event",
            name="Test Event",
            start_date=datetime(2026, 1, 1),
            swiss_rounds=1,
            top_cut=4,
            player_count=4,
        )
        state = initialize_state(spec, players, feature_context=FeatureContext())
        from sim_engine import build_tournament_context

        context = build_tournament_context(spec)
        pod = Pod(round_index=0, table_number=1, player_ids=[player.player_id for player in players])
        snapshot = build_round_snapshot(state, context, 1)
        artifact = LoadedDrawModel(
            features=["is_swiss"],
            model=FixedOutcomeModel(),
            calibration="uncalibrated",
            feature_indexes=np.array([0]),
            target="pod_outcome",
            draw_class=0,
            winner_source="external",
        )

        draw_probabilities, win_probabilities = predict_pod_outcome_probabilities(
            [pod],
            state,
            context,
            artifact,
            snapshot,
        )

        key = (0, 1)
        expected_elo_winners = predict_decisive_win_probabilities([pod], state)[key]
        self.assertAlmostEqual(draw_probabilities[key], 0.20)
        self.assertNotAlmostEqual(win_probabilities[key][0], 0.10 / 0.80)
        for actual_probability, expected_probability in zip(win_probabilities[key], expected_elo_winners, strict=True):
            self.assertAlmostEqual(actual_probability, expected_probability)

    def test_pod_outcome_artifact_forces_top_cut_draw_probability_to_zero(self) -> None:
        players = [
            SimPlayer(player_id=f"p{index}", name=f"Player {index}", elo=1500.0, tiebreak_seed=index)
            for index in range(1, 5)
        ]
        spec = TournamentSpec(
            tournament_id="test-event",
            name="Test Event",
            start_date=datetime(2026, 1, 1),
            swiss_rounds=1,
            top_cut=4,
            player_count=4,
        )
        state = initialize_state(spec, players, feature_context=FeatureContext())
        from sim_engine import build_tournament_context

        context = build_tournament_context(spec)
        pod = Pod(round_index=1, table_number=1, player_ids=[player.player_id for player in players])
        snapshot = build_round_snapshot(state, context, 1)
        artifact = LoadedDrawModel(
            features=["is_swiss"],
            model=FixedOutcomeModel(),
            calibration="uncalibrated",
            feature_indexes=np.array([0]),
            target="pod_outcome",
            winner_source="artifact",
        )

        draw_probabilities, win_probabilities = predict_pod_outcome_probabilities(
            [pod],
            state,
            context,
            artifact,
            snapshot,
        )

        key = (1, 1)
        self.assertEqual(draw_probabilities[key], 0.0)
        self.assertAlmostEqual(sum(win_probabilities[key]), 1.0)
        self.assertAlmostEqual(win_probabilities[key][0], 0.10 / 0.80)
        self.assertAlmostEqual(win_probabilities[key][1], 0.30 / 0.80)


if __name__ == "__main__":
    unittest.main()
