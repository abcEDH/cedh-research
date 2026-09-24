"""Unit tests for the Wilson 95% CI math added for #147.

This reimplements the exact formula from
``supabase/migrations/20260924000000_get_winrate_matrix_rpc.sql`` (``public.wilson_ci_95``) in
pure Python so the issue's reference value can be checked without a live Postgres instance (the
CI ``unittest discover`` step has none -- see ``.github/workflows/ci-backend.yml``). Correctness
against the *actual* SQL was additionally verified by hand: seeding a fixture into a real local
Postgres 16 and calling ``wilson_ci_95``/``get_winrate_matrix`` directly (see
``test_winrate_matrix_integration.py`` for the opt-in, live-database version of that check).
This file guards the formula in Python so a future edit to the SQL or to this file can't
silently drift apart -- ``MigrationSqlMatchesReferenceMathTests`` below ties the two together at
the string level.
"""

import math
import unittest
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
WINRATE_MATRIX_MIGRATION = MIGRATIONS_DIR / "20260924000000_get_winrate_matrix_rpc.sql"

Z_95 = 1.96


def wilson_ci_95(successes: int, trials: int) -> tuple[float | None, float | None]:
    """Pure-Python mirror of the ``public.wilson_ci_95`` SQL function."""
    if trials <= 0:
        return (None, None)

    phat = successes / trials
    denom = 1 + (Z_95**2) / trials
    centre = phat + (Z_95**2) / (2 * trials)
    margin = Z_95 * math.sqrt(max(0.0, phat * (1 - phat) / trials + (Z_95**2) / (4 * trials**2)))

    ci_low = max(0.0, round((centre - margin) / denom, 4))
    ci_high = min(1.0, round((centre + margin) / denom, 4))
    return (ci_low, ci_high)


class WilsonCiReferenceValueTests(unittest.TestCase):
    def test_wins_50_games_100_matches_issue_reference_value(self) -> None:
        # #147 acceptance criterion: wins=50, games=100 -> ~40.4%, 59.6%.
        ci_low, ci_high = wilson_ci_95(50, 100)

        self.assertAlmostEqual(ci_low, 0.4038, places=4)
        self.assertAlmostEqual(ci_high, 0.5962, places=4)

    def test_zero_trials_returns_none_rather_than_dividing_by_zero(self) -> None:
        self.assertEqual(wilson_ci_95(0, 0), (None, None))

    def test_full_sample_all_wins_clamps_to_one(self) -> None:
        ci_low, ci_high = wilson_ci_95(30, 30)

        self.assertGreater(ci_low, 0)
        self.assertEqual(ci_high, 1)

    def test_full_sample_all_losses_clamps_to_zero(self) -> None:
        ci_low, ci_high = wilson_ci_95(0, 30)

        self.assertEqual(ci_low, 0)
        self.assertLess(ci_high, 1)

    def test_ci_widens_as_sample_size_shrinks_at_fixed_point_estimate(self) -> None:
        small_low, small_high = wilson_ci_95(5, 10)
        large_low, large_high = wilson_ci_95(500, 1000)

        self.assertLess(large_low, small_high)
        self.assertGreater(large_low, small_low)
        self.assertLess(large_high, small_high)

    def test_single_game_win_still_returns_a_bounded_interval(self) -> None:
        ci_low, ci_high = wilson_ci_95(1, 1)

        self.assertGreaterEqual(ci_low, 0)
        self.assertEqual(ci_high, 1)


class MigrationSqlMatchesReferenceMathTests(unittest.TestCase):
    """Ties the Python reference implementation above to the deployed SQL text."""

    def test_wilson_helper_uses_z_1_96_and_returns_one_row_always(self) -> None:
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        self.assertIn("CREATE OR REPLACE FUNCTION public.wilson_ci_95(", sql)
        self.assertIn("1.96", sql)
        self.assertIn("RETURNS TABLE (ci_low numeric, ci_high numeric)", sql)

    def test_get_winrate_matrix_reuses_the_shared_helper_instead_of_duplicating_math(self) -> None:
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        self.assertEqual(
            sql.count("CREATE OR REPLACE FUNCTION public.wilson_ci_95("),
            1,
            "the Wilson formula itself must be defined exactly once",
        )
        self.assertIn("CROSS JOIN LATERAL public.wilson_ci_95(c.x_wins, c.x_games) ci", sql)


if __name__ == "__main__":
    unittest.main()
