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

    def test_chain_elo_requires_positive_ingestion_claim_signal(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertIn("outputs:", workflow)
        self.assertIn("claimed: ${{ steps.run-ingestion.outputs.claimed }}", workflow)
        self.assertIn("needs.ingest.outputs.claimed == 'true'", workflow)
        self.assertIn("needs.ingest.outputs.claimed != 'false'", workflow)
        self.assertIn('if [ "$status" -eq 20 ]; then', workflow)

    def test_run_ingestion_step_sets_claimed_output(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertIn('echo "claimed=true" >> "$GITHUB_OUTPUT"', workflow)
        self.assertIn('echo "claimed=false" >> "$GITHUB_OUTPUT"', workflow)

    def test_workflow_accepts_targeted_tournament_input(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertIn("tournament_id:", workflow)
        self.assertIn('INGEST_FLAGS="--tournament-id $TOURNAMENT_ID"', workflow)
        self.assertIn('INGEST_FLAGS="--days 7 --min-players 32"', workflow)

    def test_targeted_runs_do_not_cancel_daily_sweep(self) -> None:
        workflow = WORKFLOW_PATH.read_text()
        self.assertIn(
            "group: backend-ingestion-${{ github.ref }}-${{ inputs.tournament_id }}",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
