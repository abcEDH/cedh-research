import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deck_identity import (  # noqa: E402
    DeckSource,
    classify_ygo_archetype,
    load_ygo_archetype_rules,
    make_ygo_extractor,
)


class YgoArchetypeRulesTests(unittest.TestCase):
    def test_rules_files_load_for_both_formats(self) -> None:
        for format_key in ("edison", "goat"):
            rules = load_ygo_archetype_rules(format_key)
            self.assertGreater(len(rules), 0, f"no rules for {format_key}")
            for rule in rules:
                self.assertTrue(rule.get("name"))
                self.assertTrue(rule.get("signature_cards"))

    def test_missing_format_returns_no_rules(self) -> None:
        self.assertEqual(load_ygo_archetype_rules("nonexistent-format"), ())


class YgoClassifierTests(unittest.TestCase):
    def test_goat_control_classified_from_signature_cards(self) -> None:
        name, matches = classify_ygo_archetype(
            "goat",
            ["Scapegoat", "Metamorphosis", "Sangan", "Pot of Greed"],
        )
        self.assertEqual(name, "Goat Control")
        self.assertEqual(sorted(matches), ["Metamorphosis", "Scapegoat"])

    def test_match_is_case_insensitive(self) -> None:
        name, _ = classify_ygo_archetype("goat", ["scapegoat", "METAMORPHOSIS"])
        self.assertEqual(name, "Goat Control")

    def test_single_signature_card_is_not_enough_when_min_matches_two(self) -> None:
        name, _ = classify_ygo_archetype("goat", ["Scapegoat", "Sangan"])
        self.assertEqual(name, "Unknown Archetype")

    def test_unknown_for_empty_mainboard(self) -> None:
        name, matches = classify_ygo_archetype("edison", [])
        self.assertEqual(name, "Unknown Archetype")
        self.assertEqual(matches, [])


class YgoExtractorTests(unittest.TestCase):
    def test_extractor_reads_deck_obj_mainboard(self) -> None:
        extractor = make_ygo_extractor("edison")
        deck_obj = {
            "Mainboard": {
                "Blackwing - Shura the Blue Flame": {"id": "a", "count": 3},
                "Blackwing - Kalut the Moon Shadow": {"id": "b", "count": 3},
            }
        }
        name, _ = extractor(DeckSource(deck_obj=deck_obj))
        self.assertEqual(name, "Blackwing")

    def test_extractor_unknown_without_deck_obj(self) -> None:
        extractor = make_ygo_extractor("edison")
        name, matches = extractor(DeckSource(decklist_text="just text"))
        self.assertEqual(name, "Unknown Archetype")
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
