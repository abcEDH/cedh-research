import unittest
from pathlib import Path


WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci-backend-maintenance.yml"


class BackendMaintenanceWorkflowTests(unittest.TestCase):
    def test_marks_queued_jobs_failed_on_full_refresh_failure(self) -> None:
        workflow = WORKFLOW_PATH.read_text()

        self.assertIn("Mark queued job as failed when maintenance workflow fails", workflow)
        self.assertIn("failure() && inputs.refresh_mode == 'full' && inputs.job_id != ''", workflow)
        self.assertIn('fail_job(client, os.environ["JOB_ID"], os.environ["JOB_ERROR"])', workflow)


if __name__ == "__main__":
    unittest.main()
