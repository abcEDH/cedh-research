import math
import unittest
from datetime import date, datetime

from internal_elo import learning_rate, resolve_topcut_draws, seat_offsets
from rebuild_global_elo_tables import apply_game, build_state_from_results
from sim_models import predict_decisive_win_probabilities, predict_decisive_win_probs
from sim_types import Pod, SimPlayer, TournamentSpec, TournamentState


def rows(label="Top 16", draw=True, league=False):
    return [
        {
            "game_id": "g",
            "tournament_id": "t",
            "player_id": f"p{i}",
            "entry_id": f"e{i}",
            "start_date": "2026-01-01T00:00:00Z",
            "round_name": label,
            "round_number": None,
            "table_number": 1,
            "seat_position": i,
            "result": "draw" if draw else "win" if i == 0 else "loss",
            "is_draw": draw,
            "is_league": league,
        }
        for i in range(4)
    ]


class InternalEloTests(unittest.TestCase):
    def test_advancer_overrides_seat_one_without_mutating_source(self):
        original = rows()
        final = [
            dict(row, game_id="final", round_name="Top 4", player_id=f"x{i}", result="loss", is_draw=False)
            for i, row in enumerate(original)
        ]
        final[0]["player_id"] = "p3"
        final[0]["result"] = "win"
        resolved = resolve_topcut_draws(original + final)
        self.assertEqual([r["player_id"] for r in resolved[:4] if r["result"] == "win"], ["p3"])
        self.assertTrue(all(r["result"] == "draw" for r in original))
        _, _, _, events = build_state_from_results(original + final, update_activity=False)
        self.assertEqual(
            next(e for e in events if e["game_id"] == "g" and e["player_id"] == "p3")["game_result"], "win"
        )
        self.assertFalse(any(e["is_draw"] for e in events))

    def test_final_draw_becomes_seat_one_win(self):
        events = apply_game(rows("Finals"), {}, {}, {}, date(2026, 1, 2), update_activity=False)
        self.assertEqual([e["game_result"] for e in events], ["win", "loss", "loss", "loss"])
        self.assertAlmostEqual(
            events[0]["rating_delta"], learning_rate(top_cut=True) * (1 - events[0]["expected_score"]), places=4
        )

    def test_swiss_draw_remains_draw(self):
        source = rows("Round 1")
        for r in source:
            r["round_number"] = 1
        events = apply_game(source, {}, {}, {}, date(2026, 1, 2), update_activity=False)
        self.assertTrue(all(e["game_result"] == "draw" for e in events))
        self.assertEqual([e["actual_score"] for e in events], [0.25] * 4)

    def test_league_multiplier_scales_updates_only(self):
        regular = apply_game(rows(draw=False), {}, {}, {}, date(2026, 1, 2), update_activity=False)
        league = apply_game(rows(draw=False, league=True), {}, {}, {}, date(2026, 1, 2), update_activity=False)
        for a, b in zip(regular, league, strict=True):
            self.assertEqual(a["expected_score"], b["expected_score"])
            self.assertAlmostEqual(b["rating_delta"] / a["rating_delta"], 0.5794326409119744, places=6)

    def test_missing_seat_and_ambiguous_advancement_fail_closed(self):
        source = rows()
        for r in source:
            r["seat_position"] = None
        with self.assertRaises(ValueError):
            resolve_topcut_draws(source)
        source = rows()
        final = [dict(r, game_id="f", round_name="Top 4", result="loss") for r in source]
        with self.assertRaises(ValueError):
            resolve_topcut_draws(source + final)

    def test_future_games_never_update_ratings(self):
        source = rows()
        source[0]["start_date"] = "2999-01-01T00:00:00Z"
        self.assertEqual(apply_game(source, {}, {}, {}, date(2026, 1, 2)), [])

    def test_simulation_uses_stage_specific_offsets(self):
        players = {f"p{i}": SimPlayer(player_id=f"p{i}", name=str(i), elo=1500) for i in range(4)}
        state = TournamentState(
            spec=TournamentSpec("t", "Test", datetime(2026, 1, 1), 4, 16, 16), players=players, standings={}
        )
        for label, cut in [("Round 1", False), ("Top 16", True)]:
            pod = Pod(0, 1, list(players), round_name=label, seats_by_player={f"p{i}": i + 1 for i in range(4)})
            expected = [math.pow(2, offset / 200) for offset in seat_offsets(cut).values()]
            expected = [p / sum(expected) for p in expected]
            actual = predict_decisive_win_probs(pod, state)
            batch = predict_decisive_win_probabilities([pod], state)[(0, 1)]
            for i, pid in enumerate(players):
                self.assertAlmostEqual(actual[pid], expected[i])
                self.assertAlmostEqual(batch[i], expected[i])
            events = apply_game(rows(label, draw=False), {}, {}, {}, date(2026, 1, 2), update_activity=False)
            for i, e in enumerate(events):
                self.assertAlmostEqual(e["expected_score"], expected[i], places=6)

    def test_unresolved_topcut_draw_cannot_use_draw_k(self):
        with self.assertRaises(ValueError):
            learning_rate(top_cut=True, draw=True)


if __name__ == "__main__":
    unittest.main()
