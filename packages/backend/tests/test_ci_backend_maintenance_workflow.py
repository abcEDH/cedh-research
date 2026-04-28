import unittest
from pathlib import Path


WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci-backend-maintenance.yml"


class BackendMaintenanceWorkflowTests(unittest.TestCase):
    def test_marks_queued_jobs_failed_when_any_maintenance_job_fails(self) -> None:
        workflow = WORKFLOW_PATH.read_text()

        self.assertIn("mark-job-failed:", workflow)
        self.assertIn("Mark queued job as failed when any maintenance job fails", workflow)
        self.assertIn("always()", workflow)
        self.assertIn("contains(join(needs.*.result, ','), 'failure')", workflow)
        self.assertIn("contains(join(needs.*.result, ','), 'cancelled')", workflow)
        self.assertIn('curl --fail-with-body --silent --show-error', workflow)
        self.assertIn('/rest/v1/elo_maintenance_jobs?id=eq.${JOB_ID}&status=in.(pending,dispatched,running)', workflow)


    def test_maintenance_workflow_does_not_run_ingestion(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertNotIn("ingest.py", workflow)


if __name__ == "__main__":
    unittest.main()
