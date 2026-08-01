import sys
import unittest
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import train_active_commander_ml as ml  # noqa: E402
import backtest_active_commander_model as backtest  # noqa: E402


def usage_row(
    commander: str,
    start_date: str,
    *,
    topdeck_id: str = "player-1",
    decklist_url: str | None = None,
) -> dict:
    return {
        "player_id": topdeck_id,
        "topdeck_id": topdeck_id,
        "player_name": "Player One",
        "commander_name": commander,
        "start_date": start_date,
        "decklist_url": decklist_url,
        "topdeck_decklist_url": None,
        "tournament_id": f"event-{start_date}",
        "tournament_name": f"Event {start_date}",
        "tournament_topdeck_tid": f"event-{start_date}",
    }


class ActiveCommanderMlTests(unittest.TestCase):
    def test_build_candidate_rows_includes_baseline_features_and_labels(self) -> None:
        example = {
            "topdeck_id": "player-1",
            "player_name": "Player One",
            "target_date": date(2026, 4, 1),
            "actual": "B",
            "history_rows": [
                usage_row("A", "2026-01-01T00:00:00+00:00"),
                usage_row("B", "2026-03-01T00:00:00+00:00", decklist_url="https://example.test/deck"),
            ],
        }

        rows = ml.build_candidate_rows(example)

        self.assertEqual({row["commander"] for row in rows}, {"A", "B"})
        self.assertEqual(sum(row["label"] for row in rows), 1)
        self.assertTrue(all(len(row["features"]) == len(ml.FEATURE_NAMES) for row in rows))
        b_row = next(row for row in rows if row["commander"] == "B")
        self.assertEqual(b_row["features"][ml.FEATURE_NAMES.index("latest_bonus")], 1.0)
        self.assertEqual(b_row["features"][ml.FEATURE_NAMES.index("has_recent_decklist")], 1.0)
        self.assertEqual(b_row["features"][ml.FEATURE_NAMES.index("distinct_prior_tournaments")], 2.0)
        self.assertEqual(b_row["features"][ml.FEATURE_NAMES.index("hidden_elo_before")], 1500.0)

    def test_split_examples_by_time_preserves_chronology(self) -> None:
        examples = [
            {"target_date": date(2026, 3, 1), "topdeck_id": "c"},
            {"target_date": date(2026, 1, 1), "topdeck_id": "a"},
            {"target_date": date(2026, 2, 1), "topdeck_id": "b"},
            {"target_date": date(2026, 4, 1), "topdeck_id": "d"},
        ]

        train, test = ml.split_examples_by_time(examples, train_fraction=0.5)

        self.assertEqual([row["topdeck_id"] for row in train], ["a", "b"])
        self.assertEqual([row["topdeck_id"] for row in test], ["c", "d"])

    def test_enrich_examples_with_hidden_elo_uses_latest_prior_event(self) -> None:
        examples = [
            {
                "topdeck_id": "player-1",
                "target_date": date(2026, 2, 1),
                "history_rows": [usage_row("A", "2026-01-01T00:00:00+00:00")],
            },
            {
                "topdeck_id": "player-1",
                "target_date": date(2026, 3, 1),
                "history_rows": [usage_row("A", "2026-01-01T00:00:00+00:00")],
            },
        ]
        events_by_player = {
            "player-1": [
                {
                    "player_id": "player-1",
                    "game_date": "2026-01-15T00:00:00+00:00",
                    "rating_before": 1500,
                    "rating_after": 1512,
                },
                {
                    "player_id": "player-1",
                    "game_date": "2026-02-15T00:00:00+00:00",
                    "rating_before": 1512,
                    "rating_after": 1504,
                },
            ]
        }

        enriched = ml.enrich_examples_with_hidden_elo(examples, events_by_player)

        self.assertEqual(enriched[0]["hidden_elo_before"], 1512.0)
        self.assertEqual(enriched[0]["hidden_elo_games_before"], 1)
        self.assertEqual(enriched[1]["hidden_elo_before"], 1504.0)
        self.assertEqual(enriched[1]["hidden_elo_games_before"], 2)

    def test_run_ml_backtest_reports_ml_and_baselines(self) -> None:
        rows = [
            usage_row("A", "2026-01-01T00:00:00+00:00", topdeck_id="player-1"),
            usage_row("A", "2026-02-01T00:00:00+00:00", topdeck_id="player-1"),
            usage_row("B", "2026-03-01T00:00:00+00:00", topdeck_id="player-1"),
            usage_row("B", "2026-04-01T00:00:00+00:00", topdeck_id="player-1"),
            usage_row("C", "2026-01-01T00:00:00+00:00", topdeck_id="player-2"),
            usage_row("D", "2026-02-01T00:00:00+00:00", topdeck_id="player-2"),
            usage_row("D", "2026-03-01T00:00:00+00:00", topdeck_id="player-2"),
            usage_row("C", "2026-04-01T00:00:00+00:00", topdeck_id="player-2"),
        ]
        examples = backtest.build_backtest_examples(rows, min_history=1)

        result = ml.run_ml_backtest(examples, model_type="logistic", train_fraction=0.85)

        self.assertEqual(set(result["summary"]), {"current", "production", "ml_logistic"})
        self.assertIn("ml_weight_0.00", result["ensemble_sweep"])
        self.assertIn("ml_weight_1.00", result["ensemble_sweep"])
        self.assertGreater(result["train"]["candidate_rows"], 0)
        self.assertGreater(result["test_examples"], 0)


if __name__ == "__main__":
    unittest.main()
