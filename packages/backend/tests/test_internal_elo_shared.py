"""Regression tests: changing one Elo setting must affect every consumer."""

import unittest
from datetime import date, datetime
from unittest.mock import patch

import internal_elo
import rebuild_global_elo_tables as rebuild
import recompute_global_elo_all_games as recompute
from run_topdeck_ongoing_tournament_sim import tournament_state_fingerprint, update_elos_for_result
from sim_engine import initialize_state
from sim_models import predict_decisive_win_probs
from sim_types import Pod, PodResult, SimPlayer, TournamentSpec


class SharedInternalEloTests(unittest.TestCase):
    def compare_consumers(self, top_cut=False, league=False, draw=False):
        ids = ["a", "b", "c", "d"]
        state = initialize_state(
            TournamentSpec("event", "Event", datetime(2026, 9, 19), 3, 4, 4, is_league=league),
            [SimPlayer(pid, pid, 1500 + 30 * i) for i, pid in enumerate(ids)],
        )
        pod = Pod(3 if top_cut else 0, 1, ids, seats_by_player=dict(zip(ids, [1, 2, 3, 4], strict=True)))
        rows = [
            {
                "player_id": pid,
                "entry_id": pid,
                "game_id": "game",
                "tournament_id": "event",
                "start_date": "2026-09-19T00:00:00+00:00",
                "seat_position": i,
                "result": "draw" if draw else "win" if i == 0 else "loss",
                "is_league": league,
                "round_number": None if top_cut else 1,
                "round_name": "Top 4" if top_cut else None,
            }
            for i, pid in enumerate(ids)
        ]
        ratings = {pid: dict(rebuild.empty_rating(pid), rating=state.players[pid].elo) for pid in ids}
        legacy = {pid: dict(recompute.create_rating(pid), rating=state.players[pid].elo) for pid in ids}
        probabilities = predict_decisive_win_probs(pod, state)
        events = rebuild.apply_game(rows, ratings, {}, {}, date(2026, 9, 19), update_activity=False)
        recompute.apply_game(legacy, rows)
        update_elos_for_result(state, pod, PodResult(pod.round_index, 1, ids, draw, None if draw else "a", (), 0))
        for event in events:
            pid = event["player_id"]
            self.assertAlmostEqual(event["expected_score"], probabilities[pid], places=6)
            self.assertAlmostEqual(event["rating_after"], state.players[pid].elo, places=6)
            self.assertAlmostEqual(legacy[pid]["rating"], round(event["rating_after"], 3), places=3)
        return probabilities

    def test_swiss_consumers_follow_changes_without_reimport(self):
        original = self.compare_consumers()
        with (
            patch.object(internal_elo, "SWISS_SEAT_OFFSETS", {1: 0.0, 2: -200.0, 3: -400.0, 4: -600.0}),
            patch.object(internal_elo, "SWISS_WIN_K", 17.0),
            patch.object(internal_elo, "ELO_DIVISOR", 300.0),
        ):
            changed = self.compare_consumers()
        self.assertNotAlmostEqual(original["a"], changed["a"])

    def test_topcut_consumers_follow_changes_without_reimport(self):
        original = self.compare_consumers(True)
        with (
            patch.object(internal_elo, "TOPCUT_SEAT_OFFSETS", {1: 0.0, 2: -300.0, 3: -500.0, 4: -700.0}),
            patch.object(internal_elo, "TOPCUT_WIN_K", 23.0),
            patch.object(internal_elo, "ELO_BASE", 3.0),
        ):
            changed = self.compare_consumers(True)
        self.assertNotAlmostEqual(original["a"], changed["a"])

    def test_league_consumers_follow_shared_multiplier(self):
        with patch.object(internal_elo, "LEAGUE_MULTIPLIER", 0.25):
            self.compare_consumers(league=True)
            self.compare_consumers(top_cut=True, league=True)

    def test_swiss_draw_consumers_follow_shared_learning_rate(self):
        with patch.object(internal_elo, "SWISS_DRAW_K", 11.0):
            self.compare_consumers(draw=True)
            self.compare_consumers(draw=True, league=True)

    def test_cache_key_tracks_every_parameter_without_version_bump(self):
        def fingerprint():
            return tournament_state_fingerprint({"id": "event"}, swiss_rounds=3, top_cut=4)

        original = fingerprint()
        for name in ["ELO_BASE", "ELO_DIVISOR", "SWISS_WIN_K", "SWISS_DRAW_K", "TOPCUT_WIN_K", "LEAGUE_MULTIPLIER"]:
            with self.subTest(parameter=name), patch.object(internal_elo, name, getattr(internal_elo, name) + 1):
                self.assertNotEqual(original, fingerprint())
        for name in ["SWISS_SEAT_OFFSETS", "TOPCUT_SEAT_OFFSETS"]:
            with self.subTest(parameter=name), patch.dict(getattr(internal_elo, name), {4: -999.0}):
                self.assertNotEqual(original, fingerprint())
        self.assertEqual(original, fingerprint())


if __name__ == "__main__":
    unittest.main()
