import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from game_registry import (  # noqa: E402
    DEFAULT_GAME_KEY,
    GAME_REGISTRY,
    MTG_GAME,
    accepted_topdeck_formats,
    get_game_config,
    payload_format_matches,
)

VALID_IDENTITY_KINDS = {"commander", "legend", "leader", "archetype", "unknown"}


class GameRegistryTests(unittest.TestCase):
    def test_default_game_is_cedh(self) -> None:
        self.assertEqual(DEFAULT_GAME_KEY, "cedh")
        self.assertIn(DEFAULT_GAME_KEY, GAME_REGISTRY)

    def test_cedh_config_preserves_legacy_behavior(self) -> None:
        cfg = GAME_REGISTRY["cedh"]
        self.assertEqual(cfg.topdeck_game, MTG_GAME)
        self.assertEqual(cfg.topdeck_format, "EDH")
        self.assertEqual(cfg.db_game, MTG_GAME)
        self.assertEqual(cfg.db_format, "EDH")
        self.assertEqual(cfg.pod_size, 4)
        self.assertEqual(cfg.win_points, 5)
        self.assertEqual(cfg.draw_points, 1)
        self.assertTrue(cfg.derive_wld_from_points)
        self.assertEqual(cfg.small_event_top_cut_override, 4)
        self.assertEqual(cfg.identity_kind, "commander")

    def test_every_entry_is_internally_consistent(self) -> None:
        for key, cfg in GAME_REGISTRY.items():
            with self.subTest(key=key):
                self.assertEqual(cfg.key, key)
                self.assertTrue(cfg.topdeck_game)
                self.assertTrue(cfg.topdeck_format)
                self.assertTrue(cfg.db_game)
                self.assertTrue(cfg.db_format)
                self.assertIn(cfg.identity_kind, VALID_IDENTITY_KINDS)
                self.assertGreaterEqual(cfg.pod_size, 2)
                self.assertGreater(cfg.win_points, 0)
                self.assertGreaterEqual(cfg.draw_points, 0)
                if cfg.derive_wld_from_points:
                    # Points derivation assumes the cEDH 5/1/0 scoring identity.
                    self.assertEqual((cfg.win_points, cfg.draw_points), (5, 1))
                # topdeck_format must never repeat in format_aliases (would send
                # a redundant duplicate search).
                self.assertNotIn(cfg.topdeck_format, cfg.format_aliases)

    def test_accepted_topdeck_formats_includes_primary_and_aliases(self) -> None:
        cfg = GAME_REGISTRY["ygo-goat"]
        self.assertEqual(accepted_topdeck_formats(cfg), ("Goat", "GOAT", "Goat Format"))

    def test_get_game_config_rejects_unknown_key(self) -> None:
        with self.assertRaises(KeyError) as ctx:
            get_game_config("chess")
        self.assertIn("cedh", str(ctx.exception))

    def test_payload_format_matches_pinned_format_case_insensitively(self) -> None:
        cfg = GAME_REGISTRY["cedh"]
        self.assertTrue(payload_format_matches(cfg, "EDH"))
        self.assertTrue(payload_format_matches(cfg, "edh"))
        self.assertFalse(payload_format_matches(cfg, "Pauper EDH"))
        self.assertFalse(payload_format_matches(cfg, None))

    def test_payload_format_matches_any_alias(self) -> None:
        cfg = GAME_REGISTRY["ygo-edison"]
        self.assertTrue(payload_format_matches(cfg, "Edison"))
        self.assertTrue(payload_format_matches(cfg, "edison format"))
        self.assertFalse(payload_format_matches(cfg, "Goat"))
        self.assertFalse(payload_format_matches(cfg, None))


if __name__ == "__main__":
    unittest.main()
