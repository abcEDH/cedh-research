import unittest
from pathlib import Path


WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci-backend-maintenance.yml"


class BackendMaintenanceWorkflowTests(unittest.TestCase):
    def test_marks_queued_jobs_failed_on_full_refresh_failure(self) -> None:
        workflow = WORKFLOW_PATH.read_text()

        self.assertIn("Mark queued job as failed when maintenance workflow fails", workflow)
        self.assertIn("failure() && inputs.refresh_mode == 'full' && inputs.job_id != ''", workflow)
        self.assertIn('curl --fail-with-body --silent --show-error', workflow)
        self.assertIn('/rest/v1/elo_maintenance_jobs?id=eq.${JOB_ID}&status=in.(pending,dispatched,running)', workflow)


if __name__ == "__main__":
    unittest.main()
