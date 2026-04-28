import os
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import regional_elo  # noqa: E402


class RegionalEloJobLifecycleTests(TestCase):
    def test_claim_job_updates_pending_row_and_sets_github_run_id(self) -> None:
        client = Mock()
        client.update.return_value = [{"id": "job-123"}]

        claimed = regional_elo.claim_job(client, "job-123", github_run_id=456)

        self.assertTrue(claimed)
        client.update.assert_called_once_with(
            regional_elo.MAINTENANCE_JOBS_TABLE,
            {
                "status": "running",
                "started_at": client.update.call_args.args[1]["started_at"],
                "heartbeat_at": client.update.call_args.args[1]["heartbeat_at"],
                "github_run_id": 456,
            },
            {"id": "eq.job-123", "status": "in.(pending,dispatched)"},
        )

    def test_claim_job_returns_false_when_no_row_was_updated(self) -> None:
        client = Mock()
        client.update.return_value = []

        claimed = regional_elo.claim_job(client, "job-123", github_run_id=0)

        self.assertFalse(claimed)

    def test_update_job_heartbeat_only_targets_running_jobs(self) -> None:
        client = Mock()

        regional_elo.update_job_heartbeat(client, "job-123")

        client.update.assert_called_once_with(
            regional_elo.MAINTENANCE_JOBS_TABLE,
            {"heartbeat_at": client.update.call_args.args[1]["heartbeat_at"]},
            {"id": "eq.job-123", "status": "eq.running"},
        )

    def test_complete_job_records_metrics_against_running_job(self) -> None:
        client = Mock()

        regional_elo.complete_job(
            client,
            "job-123",
            {
                "ratings_count": 10,
                "state_activity_count": 20,
                "duration_seconds": 30.5,
            },
        )

        client.update.assert_called_once_with(
            regional_elo.MAINTENANCE_JOBS_TABLE,
            {
                "status": "completed",
                "completed_at": client.update.call_args.args[1]["completed_at"],
                "heartbeat_at": client.update.call_args.args[1]["heartbeat_at"],
                "ratings_count": 10,
                "state_activity_count": 20,
                "duration_seconds": 30.5,
            },
            {"id": "eq.job-123", "status": "eq.running"},
        )


class RefreshMaterializedViewsTests(TestCase):
    def test_refresh_materialized_views_calls_all_functions(self) -> None:
        client = Mock()

        result = regional_elo.refresh_materialized_views(client)

        self.assertEqual(client.rpc.call_count, 3)
        client.rpc.assert_any_call("refresh_commander_trends")
        client.rpc.assert_any_call("refresh_card_frequencies")
        client.rpc.assert_any_call("refresh_card_performance")
        self.assertEqual(result, 3)

    def test_refresh_materialized_views_continues_on_failure(self) -> None:
        client = Mock()
        client.rpc.side_effect = [
            Exception("first function failed"),
            None,
            None,
        ]

        result = regional_elo.refresh_materialized_views(client)

        self.assertEqual(client.rpc.call_count, 3)
        self.assertEqual(result, 2)

    def test_refresh_materialized_views_returns_success_count(self) -> None:
        client = Mock()

        result = regional_elo.refresh_materialized_views(client)

        self.assertEqual(result, 3)


class RegionalEloCliValidationTests(TestCase):
    def test_job_id_requires_apply(self) -> None:
        with patch.object(sys, "argv", ["regional_elo.py", "--job-id", "job-123", "--dry-run"]):
            with patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"}, clear=False):
                with self.assertRaises(SystemExit) as ctx:
                    regional_elo.main()

        self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    main()
