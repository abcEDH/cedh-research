import unittest

from ongoing_tournament_inputs import infer_structure


class SimulationStructureReviewTests(unittest.TestCase):
    def test_zero_override_survives_conflicting_event_cut(self):
        self.assertEqual(
            infer_structure(
                {"swissRounds": 4, "topCut": 16}, "Top 40 Cut", swiss_rounds_override=None, top_cut_override=0
            ),
            (4, 0),
        )

    def test_zero_from_payload_survives_event_fallback(self):
        self.assertEqual(
            infer_structure(
                {"swissRounds": 2, "topCut": 0, "eventData": {"topCut": 16}},
                "Top 40 Cut",
                swiss_rounds_override=None,
                top_cut_override=None,
            ),
            (2, 0),
        )
