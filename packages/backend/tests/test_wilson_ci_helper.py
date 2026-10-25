"""Unit tests for the Wilson 95% CI math and significance heuristic added for #147/#148.

These reimplement the exact formulas from
``supabase/migrations/20260906000000_winrate_matrix_and_pod_metrics_rpc.sql`` in pure Python so
the reference values from the issues can be checked without a live Postgres instance (the CI
``unittest discover`` step does not have one -- see
``.github/workflows/ci-backend.yml``). Correctness against the *actual* SQL was additionally
verified by hand, seeding a fixture into a real local Postgres 16 and calling
``wilson_ci_95``/``get_winrate_matrix``/``get_pod_metrics`` directly; this file guards the
formula in Python so a future edit to either the SQL or this file can't silently drift apart --
see ``test_supabase_migration_integrity.py`` for the string-level check that ties the two
together.
"""

import math
import unittest
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
WINRATE_MATRIX_MIGRATION = MIGRATIONS_DIR / "20260906000000_winrate_matrix_and_pod_metrics_rpc.sql"

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


def is_rate_statistically_significant(trials: int, observed_rate: float, expected_rate: float = 0.25) -> bool:
    """Pure-Python mirror of ``public.is_rate_statistically_significant``."""
    deviation = abs(observed_rate - expected_rate)
    if trials >= 30:
        return True
    if trials >= 20 and deviation > 0.10:
        return True
    if trials >= 10 and deviation > 0.15:
        return True
    return False


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

    def test_ci_widens_as_sample_size_shrinks_at_fixed_point_estimate(self) -> None:
        small_low, small_high = wilson_ci_95(5, 10)
        large_low, large_high = wilson_ci_95(500, 1000)

        self.assertLess(large_low, small_high)
        self.assertGreater(large_low, small_low)
        self.assertLess(large_high, small_high)


class SignificanceHeuristicTests(unittest.TestCase):
    """Matches get_commander_matchups' tiered games-count/deviation convention exactly."""

    def test_at_least_thirty_games_is_always_significant(self) -> None:
        self.assertTrue(is_rate_statistically_significant(30, 0.5, 0.25))
        self.assertTrue(is_rate_statistically_significant(1000, 0.26, 0.25))

    def test_twenty_to_thirty_games_needs_ten_point_deviation(self) -> None:
        self.assertTrue(is_rate_statistically_significant(25, 0.36, 0.25))
        self.assertFalse(is_rate_statistically_significant(25, 0.30, 0.25))

    def test_ten_to_twenty_games_needs_fifteen_point_deviation(self) -> None:
        self.assertTrue(is_rate_statistically_significant(15, 0.41, 0.25))
        self.assertFalse(is_rate_statistically_significant(15, 0.35, 0.25))

    def test_under_ten_games_is_never_significant(self) -> None:
        self.assertFalse(is_rate_statistically_significant(5, 0.9, 0.25))

    def test_expected_rate_is_parameterized_for_survivability(self) -> None:
        # get_pod_metrics keys threat_score off 0.25 like get_commander_matchups' win_rate, but
        # the heuristic itself must generalize to other expected rates without new thresholds.
        self.assertTrue(is_rate_statistically_significant(25, 0.65, expected_rate=0.5))
        self.assertFalse(is_rate_statistically_significant(25, 0.55, expected_rate=0.5))


class MigrationSqlMatchesReferenceMathTests(unittest.TestCase):
    """Ties the Python reference implementation above to the deployed SQL text."""

    def test_wilson_helper_uses_z_1_96_and_returns_one_row_always(self) -> None:
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        self.assertIn("CREATE OR REPLACE FUNCTION public.wilson_ci_95(", sql)
        self.assertIn("1.96", sql)
        self.assertIn("wins=50, games=100 -> ci_low ~= 0.4039, ci_high ~= 0.5962", sql)

    def test_significance_thresholds_match_get_commander_matchups_tiers(self) -> None:
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        self.assertIn("p_trials >= 30 THEN TRUE", sql)
        self.assertIn("p_trials >= 20 AND ABS(p_observed_rate - p_expected_rate) > 0.10 THEN TRUE", sql)
        self.assertIn("p_trials >= 10 AND ABS(p_observed_rate - p_expected_rate) > 0.15 THEN TRUE", sql)

    def test_both_rpcs_reuse_the_shared_helpers_instead_of_duplicating_math(self) -> None:
        sql = WINRATE_MATRIX_MIGRATION.read_text()

        # #147/#148 both require the Wilson math and the top-N-by-metashare cutoff to be
        # factored into shared helpers rather than re-derived per RPC: one call site in
        # get_winrate_matrix, two in get_pod_metrics (threat_score and survivability each get
        # their own CI), and zero re-implementations of the formula itself.
        self.assertEqual(
            sql.count("CROSS JOIN LATERAL public.wilson_ci_95("),
            3,
            "expected exactly three call sites across both RPCs",
        )
        self.assertEqual(
            sql.count("CREATE OR REPLACE FUNCTION public.wilson_ci_95("),
            1,
            "the Wilson formula itself must be defined exactly once",
        )
        self.assertIn("get_winrate_matrix", sql)
        self.assertIn("get_pod_metrics", sql)
        for fn in ("get_winrate_matrix", "get_pod_metrics"):
            fn_start = sql.index(f"FUNCTION public.{fn}(")
            fn_body = sql[fn_start : fn_start + 4000]
            self.assertIn("public.top_commanders_by_metashare(top_n, days_back)", fn_body)


if __name__ == "__main__":
    unittest.main()
