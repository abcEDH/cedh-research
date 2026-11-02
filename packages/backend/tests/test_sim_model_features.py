from __future__ import annotations

import unittest

from sim_types import (
    COMMANDER_DRAW_FEATURES,
    DEFAULT_DRAW_MODEL_FEATURES,
    LIVE_DEFAULTED_DRAW_FEATURES,
    TOPDECK_ELO_DRAW_FEATURES,
)


class SimModelFeatureTest(unittest.TestCase):
    def test_default_draw_model_features_exclude_live_unavailable_inputs(self) -> None:
        selected = set(DEFAULT_DRAW_MODEL_FEATURES)

        self.assertFalse(selected & COMMANDER_DRAW_FEATURES)
        self.assertFalse(selected & LIVE_DEFAULTED_DRAW_FEATURES)
        self.assertFalse(selected & TOPDECK_ELO_DRAW_FEATURES)

    def test_default_draw_model_features_keep_live_derivable_internal_elo(self) -> None:
        selected = set(DEFAULT_DRAW_MODEL_FEATURES)

        self.assertIn("mean_elo", selected)
        self.assertIn("elo_std", selected)
        self.assertIn("decisive_win_probability_entropy", selected)


if __name__ == "__main__":
    unittest.main()
