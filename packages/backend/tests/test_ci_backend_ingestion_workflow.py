import unittest
from pathlib import Path

WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci-backend-ingestion.yml"


class BackendIngestionWorkflowTests(unittest.TestCase):
    def test_workflow_exists(self) -> None:
        self.assertTrue(WORKFLOW_PATH.exists(), f"Workflow not found at {WORKFLOW_PATH}")

    def test_ingestion_workflow_references_ingestion_jobs(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertIn("ingestion_jobs", workflow)
        self.assertNotIn("elo_maintenance_jobs", workflow)

    def test_ingestion_workflow_chains_elo(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertIn("chain-elo", workflow)
        self.assertIn("enqueue_elo_refresh", workflow)
        self.assertIn("ci-backend-maintenance.yml", workflow)

    def test_ingestion_workflow_has_failure_handler(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertIn("mark-ingestion-failed", workflow)
        self.assertIn("always()", workflow)


if __name__ == "__main__":
    unittest.main()
