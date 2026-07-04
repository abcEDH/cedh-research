import unittest
from pathlib import Path


FUNCTION_PATH = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "functions"
    / "trigger-ingestion-refresh"
    / "index.ts"
)


class TriggerIngestionRefreshFunctionTests(unittest.TestCase):
    def test_marks_job_dispatched_before_dispatching_workflow(self) -> None:
        source = FUNCTION_PATH.read_text()

        mark_index = source.index("await markDispatched(jobId);")
        dispatch_index = source.index("await dispatchWorkflow(jobId")

        self.assertLess(mark_index, dispatch_index)

    def test_passes_target_tid_through_to_workflow(self) -> None:
        source = FUNCTION_PATH.read_text()
        self.assertIn("select=id,status,target_tid", source)
        self.assertIn("tournament_id: targetTid ?? \"\"", source)


if __name__ == "__main__":
    unittest.main()
