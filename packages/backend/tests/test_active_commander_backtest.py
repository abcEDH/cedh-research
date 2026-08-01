import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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


class ActiveCommanderBacktestTests(unittest.TestCase):
    def test_build_backtest_examples_only_uses_prior_history(self) -> None:
        rows = [
            usage_row("A", "2026-01-01T00:00:00+00:00"),
            usage_row("B", "2026-02-01T00:00:00+00:00"),
            usage_row("B", "2026-03-01T00:00:00+00:00"),
        ]

        examples = backtest.build_backtest_examples(rows, min_history=1)

        self.assertEqual(len(examples), 2)
        self.assertEqual(examples[0]["actual"], "B")
        self.assertEqual([row["commander_name"] for row in examples[0]["history_rows"]], ["A"])
        self.assertEqual(examples[1]["actual"], "B")
        self.assertEqual(
            [row["commander_name"] for row in examples[1]["history_rows"]],
            ["A", "B"],
        )

    def test_hybrid_distribution_blends_recent_and_lifetime_signals(self) -> None:
        history = [
            usage_row("A", "2026-01-01T00:00:00+00:00"),
            usage_row("A", "2026-02-01T00:00:00+00:00"),
            usage_row("B", "2026-03-01T00:00:00+00:00", decklist_url="https://example.test/deck"),
            usage_row("B", "2026-03-15T00:00:00+00:00", decklist_url="https://example.test/deck-2"),
        ]

        distribution = backtest.hybrid_distribution(history, date(2026, 4, 1))

        self.assertGreater(distribution["B"], distribution["A"])
        self.assertAlmostEqual(sum(distribution.values()), 1.0)

    def test_run_backtest_reports_model_metrics(self) -> None:
        rows = [
            usage_row("A", "2026-01-01T00:00:00+00:00"),
            usage_row("A", "2026-02-01T00:00:00+00:00"),
            usage_row("B", "2026-03-01T00:00:00+00:00"),
            usage_row("B", "2026-04-01T00:00:00+00:00"),
        ]
        examples = backtest.build_backtest_examples(rows, min_history=1)

        summary = backtest.run_backtest(examples)

        self.assertEqual(set(summary), {"current", "production", "last_played", "most_played", "hybrid"})
        for model_summary in summary.values():
            self.assertEqual(model_summary["targets"], 3)
            self.assertGreaterEqual(model_summary["top1_accuracy"], 0.0)
            self.assertGreaterEqual(model_summary["top3_accuracy"], 0.0)
            self.assertGreaterEqual(model_summary["log_loss"], 0.0)

    def test_production_distribution_matches_profile_rebuild_top_choice(self) -> None:
        history = [
            usage_row("A", "2026-01-01T00:00:00+00:00"),
            usage_row("A", "2026-02-01T00:00:00+00:00"),
            usage_row("B", "2026-03-25T00:00:00+00:00"),
        ]

        self.assertTrue(backtest.production_matches_rebuild_top_choice(history, date(2026, 4, 1)))

    def test_latest_weight_sweep_reports_each_weight(self) -> None:
        rows = [
            usage_row("A", "2026-01-01T00:00:00+00:00"),
            usage_row("A", "2026-02-01T00:00:00+00:00"),
            usage_row("B", "2026-03-01T00:00:00+00:00"),
        ]
        examples = backtest.build_backtest_examples(rows, min_history=1)

        summary = backtest.latest_weight_sweep(examples, [0.0, 0.2])

        self.assertEqual(set(summary), {"latest_weight_0.00", "latest_weight_0.20"})
        self.assertEqual(summary["latest_weight_0.20"]["targets"], 2)

    def test_bucket_backtest_reports_history_and_latest_age_buckets(self) -> None:
        rows = [
            usage_row("A", "2026-01-01T00:00:00+00:00"),
            usage_row("A", "2026-01-15T00:00:00+00:00"),
            usage_row("B", "2026-04-01T00:00:00+00:00"),
        ]
        examples = backtest.build_backtest_examples(rows, min_history=1)

        summary = backtest.run_bucket_backtest(examples)

        self.assertIn("history_count=2", summary)
        self.assertIn("latest_age=31-90d", summary)

    def test_load_usage_rows_uses_scoped_db_query_for_windowed_backtest(self) -> None:
        with (
            patch.dict(
                backtest.os.environ,
                {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_KEY": "service-key",
                    "SUPABASE_DB_URL": "postgresql://example",
                },
                clear=False,
            ),
            patch.object(backtest, "load_local_env"),
            patch.object(
                backtest,
                "fetch_usage_rows_for_target_window_via_db",
                return_value=[usage_row("A", "2026-01-01T00:00:00+00:00")],
            ) as scoped_fetch,
            patch.object(backtest, "fetch_usage_rows_via_db") as full_fetch,
        ):
            rows = backtest.load_usage_rows(since=date(2026, 1, 1), limit_targets=25)

        self.assertEqual(len(rows), 1)
        scoped_fetch.assert_called_once()
        self.assertEqual(scoped_fetch.call_args.kwargs["since"], date(2026, 1, 1))
        self.assertEqual(scoped_fetch.call_args.kwargs["limit_targets"], 25)
        full_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
