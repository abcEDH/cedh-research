import unittest
from pathlib import Path

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci-backend-ingestion-multigame.yml"
)


class MultigameIngestionWorkflowTests(unittest.TestCase):
    def test_workflow_exists(self) -> None:
        self.assertTrue(WORKFLOW_PATH.exists(), f"Workflow not found at {WORKFLOW_PATH}")

    def test_matrix_covers_all_non_cedh_registry_slugs(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertIn("game: [riftbound, gundam, ygo-edison, ygo-goat]", workflow)

    def test_workflow_passes_game_slug_to_ingest(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertIn('--game "${{ matrix.game }}"', workflow)

    def test_workflow_does_not_use_job_claiming(self) -> None:
        # Job claiming + Elo chaining belong to the cEDH pipeline only (ADR 0007/0008).
        workflow = WORKFLOW_PATH.read_text()
        self.assertNotIn("--job-id", workflow)
        self.assertNotIn("ingestion_jobs", workflow)
        self.assertNotIn("GH_PAT_ACTIONS", workflow)

    def test_workflow_has_schedule_and_dispatch(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertIn("schedule:", workflow)
        self.assertIn("workflow_dispatch:", workflow)


if __name__ == "__main__":
    unittest.main()
