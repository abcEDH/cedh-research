from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np

import ingest
import run_topdeck_ongoing_tournament_sim as ongoing
import sim_engine
from sim_engine import initialize_state
from sim_models import LoadedDrawModel
from sim_types import FeatureContext, PlayerHistory, SimPlayer, TournamentSpec
from tournament_sim_runner import DEFAULT_ADVANCEMENT_SIZES, build_common_output, run_simulation_from_state


class ConstantDrawModel:
    def predict_proba(self, x_matrix):
        draw_probability = np.full(x_matrix.shape[0], 0.12)
        return np.column_stack((1.0 - draw_probability, draw_probability))


def make_draw_model() -> LoadedDrawModel:
    return LoadedDrawModel(
        features=["is_swiss"],
        model=ConstantDrawModel(),
        calibration="uncalibrated",
        feature_indexes=np.array([0]),
    )


def make_state(player_count: int = 16, top_cut: int = 4):
    players = [
        SimPlayer(
            player_id=f"p{index}",
            name=f"Player {index}",
            elo=1500.0 + (index * 12),
            topdeck_id=f"td{index}",
            tiebreak_seed=index,
        )
        for index in range(1, player_count + 1)
    ]
    spec = TournamentSpec(
        tournament_id="test-event",
        name="Test Event",
        start_date=datetime(2026, 1, 1),
        swiss_rounds=2,
        top_cut=top_cut,
        player_count=player_count,
        repeat_avoidance_max_pods=32,
    )
    state = initialize_state(spec, players, feature_context=FeatureContext())
    state.fast_live_mode = True
    state.track_round_stats = False
    return state


def assert_probability_rows_close(test_case, actual, expected, probability_key: str) -> None:
    test_case.assertEqual([row["player_id"] for row in actual], [row["player_id"] for row in expected])
    test_case.assertEqual([row["name"] for row in actual], [row["name"] for row in expected])
    for actual_row, expected_row in zip(actual, expected, strict=True):
        test_case.assertAlmostEqual(actual_row[probability_key], expected_row[probability_key], places=12)


class OngoingTournamentSimParityTest(unittest.TestCase):
    def test_stream_main_builds_feature_context(self):
        state = make_state(4)
        tournament = {
            "id": "test-event",
            "name": "Test Event",
            "startDate": "2026-01-01T00:00:00+00:00",
            "standings": [{"id": "td1", "name": "Player 1", "standing": 1}],
            "rounds": [],
        }
        topdeck_client = Mock()
        topdeck_client.get_tournament.return_value = tournament
        feature_context = FeatureContext()

        with (
            patch.object(ongoing, "load_local_env"),
            patch.dict(os.environ, {"TOPDECK_API_KEY": "test-key", "SUPABASE_URL": "https://example.test", "SUPABASE_SERVICE_KEY": "service"}),
            patch.object(sys, "argv", [
                "run_topdeck_ongoing_tournament_sim.py",
                "--event-id",
                "test-event",
                "--swiss-rounds",
                "6",
                "--top-cut",
                "40",
                "--simulations",
                "10",
                "--stream",
                "--no-prepared-state-cache",
            ]),
            patch.object(ongoing, "TopDeckClient", return_value=topdeck_client),
            patch.object(ingest, "SupabaseClient", return_value=Mock()),
            patch.object(ongoing, "fetch_existing_players", return_value={"td1": {"id": "p1", "name": "Player 1"}}),
            patch.object(ongoing, "build_feature_context", return_value=feature_context) as build_feature_context,
            patch.object(ongoing, "build_base_state", return_value=(state, 0, None, {"rounds": []})),
            patch.object(ongoing, "load_draw_model_artifact", return_value=make_draw_model()),
            patch.object(ongoing, "run_live_monte_carlo_stream") as run_stream,
        ):
            ongoing.main()

        build_feature_context.assert_called_once()
        self.assertIs(run_stream.call_args.args[0], state)

    def test_build_base_state_preserves_historical_feature_priors_when_applying_posted_results(self):
        tournament = {
            "id": "test-event",
            "name": "Test Event",
            "startDate": "2026-01-01T00:00:00+00:00",
            "standings": [
                {"id": f"td{index}", "name": f"Player {index}", "standing": index}
                for index in range(1, 5)
            ],
            "rounds": [
                {
                    "round": 1,
                    "tables": [
                        {
                            "table": 1,
                            "status": "Completed",
                            "winner_id": "Draw",
                            "players": [{"id": f"td{index}"} for index in range(1, 5)],
                        }
                    ],
                }
            ],
        }
        player_records = {
            f"td{index}": {"id": f"p{index}", "name": f"Player {index}"}
            for index in range(1, 5)
        }
        feature_context = FeatureContext(
            player_history={"p1": PlayerHistory(draw_rate=0.25, win_rate=0.1, decisive_rate=0.75, games_played=20)},
            global_pair_meetings={("p1", "p2"): 7},
            global_recent_draw_rate_90d=0.13,
        )

        with patch.object(ongoing, "fetch_pre_tournament_elos", return_value={}):
            state, _active_round_index, _active_round_pods, _metadata = ongoing.build_base_state(
                Mock(),
                tournament,
                swiss_rounds=3,
                top_cut=4,
                feature_context=feature_context,
                player_records=player_records,
                repeat_avoidance_max_pods=32,
            )

        self.assertEqual(state.standings["p1"].points, 1)
        self.assertEqual(state.feature_context.global_recent_draw_rate_90d, 0.13)
        self.assertEqual(state.feature_context.player_history["p1"].draw_rate, 0.25)
        self.assertEqual(state.feature_context.global_pair_meetings[("p1", "p2")], 7)
        self.assertEqual(state.feature_context.tournament_pair_meetings[("p1", "p2")], 1)

    def test_build_base_state_treats_topdeck_bye_rows_as_completed_byes(self):
        tournament = {
            "id": "test-event",
            "name": "Test Event",
            "startDate": "2026-01-01T00:00:00+00:00",
            "standings": [
                {"id": f"td{index}", "name": f"Player {index}", "standing": index}
                for index in range(1, 5)
            ],
            "rounds": [
                {
                    "round": 4,
                    "tables": [
                        {
                            "table": "Byes",
                            "status": "Bye",
                            "players": [{"id": "td1"}, {"id": "td2"}],
                        }
                    ],
                },
                {
                    "round": 5,
                    "tables": [
                        {
                            "table": 1,
                            "status": "Completed",
                            "winner_id": "Draw",
                            "players": [{"id": "td3"}, {"id": "td4"}],
                        }
                    ],
                },
            ],
        }
        player_records = {
            f"td{index}": {"id": f"p{index}", "name": f"Player {index}"}
            for index in range(1, 5)
        }

        with (
            patch.object(ongoing, "fetch_pre_tournament_elos", return_value={}),
            patch.object(ongoing, "fetch_topdeck_elos_for_topdeck_ids", return_value={}),
        ):
            state, active_round_index, active_round_pods, metadata = ongoing.build_base_state(
                Mock(),
                tournament,
                swiss_rounds=7,
                top_cut=16,
                feature_context=FeatureContext(),
                player_records=player_records,
                repeat_avoidance_max_pods=32,
            )

        self.assertEqual(active_round_index, 5)
        self.assertIsNone(active_round_pods)
        self.assertEqual(state.current_round_index, 5)
        self.assertEqual(state.standings["p1"].points, 5)
        self.assertEqual(state.standings["p1"].bye_count, 1)
        self.assertEqual(state.standings["p2"].points, 5)
        self.assertEqual(state.standings["p2"].bye_count, 1)
        self.assertEqual(state.standings["p3"].points, 1)
        self.assertEqual(state.standings["p4"].points, 1)
        self.assertEqual(metadata["locked_current_tables"], [])
        self.assertEqual(metadata["rounds"], [(4, {"Bye": 1}), (5, {"Completed": 1})])

    def test_split_rounds_uses_round_position_for_bye_table_fallback(self):
        tournament = {
            "rounds": [
                {
                    "round": 5,
                    "tables": [
                        {
                            "table": 1,
                            "status": "Completed",
                            "winner_id": "td1",
                            "players": [{"id": "td1"}, {"id": "td2"}],
                        },
                        {
                            "table": "Byes",
                            "status": "Bye",
                            "players": [{"id": "td3"}, {"id": "td4"}],
                        },
                    ],
                }
            ],
        }
        id_map = {f"td{index}": f"p{index}" for index in range(1, 5)}

        completed_tables, _active_round_index, _active_round_pods, _active_player_ids, _metadata = ongoing.split_rounds(
            tournament,
            swiss_rounds=7,
            id_map=id_map,
        )

        self.assertEqual(
            [(pod.table_number, pod.player_ids) for pod, _result in completed_tables],
            [
                (1, ["p1", "p2"]),
                (2, ["p3"]),
                (3, ["p4"]),
            ],
        )

    def test_stream_final_snapshot_matches_non_stream_runner(self):
        state = make_state(16, top_cut=16)
        draw_model = make_draw_model()
        player_name_by_id = {player_id: player.name for player_id, player in state.players.items()}
        summary = run_simulation_from_state(
            state,
            draw_model,
            simulations=12,
            seed=11,
            workers=1,
            requested_advancement_sizes=DEFAULT_ADVANCEMENT_SIZES,
        )
        expected = build_common_output(
            summary=summary,
            state=state,
            player_name_by_id=player_name_by_id,
            active_player_count=len(state.players),
            historical_point_requirements=None,
            current_state={"completed_swiss_rounds": 0},
            top_limit=20,
        )

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            ongoing.run_live_monte_carlo_stream(
                state,
                draw_model,
                simulations=12,
                seed=11,
                start_round_index=0,
                locked_round_pods=None,
                max_exact_cut_size=16,
                requested_advancement_sizes=DEFAULT_ADVANCEMENT_SIZES,
                stream_interval_seconds=999.0,
                stream_batch_size=5,
                player_name_by_id=player_name_by_id,
                active_player_count=len(state.players),
                historical_point_requirements=None,
                current_state={"completed_swiss_rounds": 0},
                workers=1,
                top_limit=20,
            )

        snapshots = [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]
        final_snapshot = snapshots[-1]

        self.assertEqual(final_snapshot["status"], "complete")
        self.assertEqual(final_snapshot["completed"], 12)
        assert_probability_rows_close(
            self,
            final_snapshot["top_win_probabilities"],
            expected["top_win_probabilities"],
            "win_probability",
        )
        assert_probability_rows_close(
            self,
            final_snapshot["top_top_cut_probabilities"],
            expected["top_top_cut_probabilities"],
            "top_cut_probability",
        )
        assert_probability_rows_close(
            self,
            final_snapshot["top_top16_probabilities"],
            expected["top_top16_probabilities"],
            "top16_probability",
        )
        assert_probability_rows_close(
            self,
            final_snapshot["top_top4_probabilities"],
            expected["top_top4_probabilities"],
            "top4_probability",
        )
        self.assertEqual(final_snapshot["point_requirements"], expected["point_requirements"])

    def test_top16_top10_and_top4_use_exact_probability_propagation(self):
        state = make_state(16)
        draw_model = make_draw_model()
        context = sim_engine.build_tournament_context(state.spec)

        for cut_size in (16, 10, 4):
            qualified = [f"p{index}" for index in range(1, cut_size + 1)]
            with (
                patch.object(sim_engine, "exact_top_cut_probabilities", return_value=({"p1": 1.0}, {cut_size: {"p1": 1.0}})) as exact,
                patch.object(sim_engine, "simulate_bracket_winner") as sampled,
            ):
                sim_engine.resolve_bracket_probabilities(
                    qualified,
                    state,
                    rng=Mock(),
                    draw_model=draw_model,
                    context=context,
                )

            exact.assert_called_once()
            sampled.assert_not_called()

    def test_larger_cut_reduces_to_exact_top16_propagation(self):
        state = make_state(40, top_cut=40)
        draw_model = make_draw_model()
        context = sim_engine.build_tournament_context(state.spec)
        qualified = [f"p{index}" for index in range(1, 41)]
        rng = Mock()
        rng.random.return_value = 0.0

        with (
            patch.object(sim_engine, "exact_top_cut_probabilities", return_value=({"p1": 1.0}, {16: {"p1": 1.0}, 4: {"p1": 1.0}})) as exact,
            patch.object(sim_engine, "simulate_bracket_winner") as sampled,
        ):
            sim_engine.resolve_bracket_probabilities(
                qualified,
                state,
                rng=rng,
                draw_model=draw_model,
                context=context,
            )

        exact.assert_called_once()
        self.assertEqual(len(exact.call_args.args[0]), 16)
        sampled.assert_not_called()


if __name__ == "__main__":
    unittest.main()
