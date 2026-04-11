import unittest

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ci_backend_checks import benchmark_specs  # noqa: E402


class BenchmarkSpecTests(unittest.TestCase):
    def test_includes_key_surfaces(self) -> None:
        spec_names = {spec.name for spec in benchmark_specs()}

        expected = {
            "commander_stats",
            "regional_elo_leaderboard_state",
            "regional_elo_player_stats",
            "card_frequencies_global",
            "card_performance_by_commander",
            "get_commander_matchups",
            "get_notable_players_for_commander",
        }

        self.assertTrue(expected.issubset(spec_names))

    def test_expected_columns_are_defined(self) -> None:
        for spec in benchmark_specs():
            self.assertGreater(
                len(spec.expected_columns),
                0,
                msg=f"{spec.name} should define expected columns",
            )

    def test_regional_validity_is_excluded_from_smoke(self) -> None:
        smoke_specs = {spec.name for spec in benchmark_specs() if spec.smoke}

        self.assertNotIn("regional_elo_data_validity", smoke_specs)


if __name__ == "__main__":
    unittest.main()
