"""Unit tests for the "top 2" placement derivation used by get_pod_metrics (#148).

game_participants.result only distinguishes 'win' / 'draw' / 'loss' / 'bye' -- there is no
per-game numeric finish position anywhere in the schema. The RPC
(``supabase/migrations/20260906000000_winrate_matrix_and_pod_metrics_rpc.sql``, see the
``x_placements`` CTE inside ``get_pod_metrics``) derives it by ranking each game's participants
by result (win, then draw, then loss) and breaking ties on seat_position ascending, then taking
the best two of that ranking.

This reimplements that exact ranking in pure Python (no live Postgres needed for
``unittest discover`` in CI) and exercises the four "which seat won" fixtures the issue asks
for. Numeric correctness against the real SQL (RANK() OVER (PARTITION BY game_id ORDER BY ...))
was additionally verified by hand against a seeded local Postgres instance, including the
all-draw case.
"""

import unittest

RESULT_RANK = {"win": 0, "draw": 1, "loss": 2}


def derive_placements(participants: list[dict]) -> list[dict]:
    """Mirror of the x_placements CTE's RANK() OVER (... ORDER BY result_rank, seat) window.

    ``participants`` is a list of {"seat": int, "result": str} dicts for one game (byes already
    excluded, as the SQL does via ``WHERE gp.result <> 'bye'``). Returns the same dicts with a
    "placement" key added (1-based, ties only possible if two rows share both result and seat,
    which the schema's UNIQUE(game_id, seat_position) constraint prevents).
    """
    ordered = sorted(participants, key=lambda p: (RESULT_RANK[p["result"]], p["seat"]))
    return [{**p, "placement": i + 1} for i, p in enumerate(ordered)]


def top_two_seats(participants: list[dict]) -> set[int]:
    return {p["seat"] for p in derive_placements(participants) if p["placement"] <= 2}


class TopTwoDerivationAllFourSeatOrderingsTests(unittest.TestCase):
    """A decisive 4-player pod: one winner, three losers. The winner is always placement 1;
    among the three losers (tied on result), seat_position ascending breaks the tie for 2nd.
    Covers all four "which seat won" fixtures, per #148's acceptance criteria."""

    def _decisive_pod(self, winner_seat: int) -> list[dict]:
        return [{"seat": seat, "result": "win" if seat == winner_seat else "loss"} for seat in range(4)]

    def test_seat_0_wins(self) -> None:
        self.assertEqual(top_two_seats(self._decisive_pod(0)), {0, 1})

    def test_seat_1_wins(self) -> None:
        # Winner (seat 1) is placement 1; among losers {0, 2, 3}, seat 0 is the lowest-seat
        # loser and takes 2nd.
        self.assertEqual(top_two_seats(self._decisive_pod(1)), {1, 0})

    def test_seat_2_wins(self) -> None:
        self.assertEqual(top_two_seats(self._decisive_pod(2)), {2, 0})

    def test_seat_3_wins(self) -> None:
        self.assertEqual(top_two_seats(self._decisive_pod(3)), {3, 0})


class TopTwoDerivationDrawAndByeEdgeCasesTests(unittest.TestCase):
    def test_all_draw_pod_breaks_ties_purely_on_seat(self) -> None:
        pod = [{"seat": seat, "result": "draw"} for seat in range(4)]

        self.assertEqual(top_two_seats(pod), {0, 1})

    def test_win_always_outranks_draw_which_outranks_loss(self) -> None:
        pod = [
            {"seat": 0, "result": "loss"},
            {"seat": 1, "result": "draw"},
            {"seat": 2, "result": "win"},
            {"seat": 3, "result": "loss"},
        ]

        placements = {p["seat"]: p["placement"] for p in derive_placements(pod)}
        self.assertEqual(placements[2], 1)  # win
        self.assertEqual(placements[1], 2)  # draw
        self.assertIn(placements[0], (3, 4))  # loss, tied with seat 3
        self.assertIn(placements[3], (3, 4))
        self.assertEqual(top_two_seats(pod), {2, 1})

    def test_three_player_pod_after_a_bye_is_removed_still_ranks_cleanly(self) -> None:
        # A bye round leaves <4 real participants; the RPC filters byes out before ranking
        # (WHERE gp.result <> 'bye'), so only the real participants are ranked here.
        pod = [
            {"seat": 0, "result": "win"},
            {"seat": 2, "result": "loss"},
            {"seat": 3, "result": "loss"},
        ]

        self.assertEqual(top_two_seats(pod), {0, 2})


if __name__ == "__main__":
    unittest.main()
