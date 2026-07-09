import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from deck_identity import (  # noqa: E402
    DeckSource,
    deck_obj_section_names,
    extract_commanders,
    extract_identity_cedh,
    get_identity_extractor,
    normalize_commander_name,
    sanitize_identity_payload,
)
from game_registry import GAME_REGISTRY  # noqa: E402

PARTNER_DECKLIST = """~~Commanders~~
1 Thrasios, Triton Hero
1 Tymna the Weaver

~~Mainboard~~
1 Sol Ring
1 Mana Crypt
"""


class CedhExtractorGoldenParityTests(unittest.TestCase):
    """The cEDH extractor must reproduce the legacy text pipeline exactly."""

    def test_matches_legacy_text_pipeline_for_partner_pair(self) -> None:
        legacy_commanders = extract_commanders(PARTNER_DECKLIST)
        legacy_name = normalize_commander_name(legacy_commanders)

        name, commanders = extract_identity_cedh(DeckSource(decklist_text=PARTNER_DECKLIST))

        self.assertEqual(name, legacy_name)
        self.assertEqual(commanders, legacy_commanders)
        self.assertEqual(name, "Tymna the Weaver / Thrasios, Triton Hero")

    def test_matches_legacy_pipeline_for_empty_decklist(self) -> None:
        name, commanders = extract_identity_cedh(DeckSource(decklist_text=""))
        self.assertEqual(name, normalize_commander_name([]))
        self.assertEqual(name, "Unknown Commander")
        self.assertEqual(commanders, [])

    def test_registry_dispatch_returns_cedh_extractor(self) -> None:
        extractor = get_identity_extractor(GAME_REGISTRY["cedh"])
        self.assertIs(extractor, extract_identity_cedh)


class CedhDeckObjFallbackTests(unittest.TestCase):
    def test_url_only_decklist_falls_back_to_deck_obj(self) -> None:
        deck_obj = {
            "Commanders": {
                "Tymna the Weaver": {"id": "abc", "count": 1},
                "Thrasios, Triton Hero": {"id": "def", "count": 1},
            },
            "Mainboard": {"Sol Ring": {"id": "ghi", "count": 1}},
        }
        name, commanders = extract_identity_cedh(
            DeckSource(decklist_text="https://moxfield.com/decks/abc123", deck_obj=deck_obj)
        )
        self.assertEqual(name, "Tymna the Weaver / Thrasios, Triton Hero")
        self.assertEqual(sorted(commanders), ["Thrasios, Triton Hero", "Tymna the Weaver"])

    def test_text_section_wins_over_deck_obj(self) -> None:
        deck_obj = {"Commanders": {"Kinnan, Bonder Prodigy": {"id": "x", "count": 1}}}
        name, _ = extract_identity_cedh(DeckSource(decklist_text=PARTNER_DECKLIST, deck_obj=deck_obj))
        self.assertEqual(name, "Tymna the Weaver / Thrasios, Triton Hero")


class DeckObjSectionTests(unittest.TestCase):
    def test_returns_names_for_valid_section(self) -> None:
        deck_obj = {"Mainboard": {"Sol Ring": {"id": "a", "count": 1}, "Brainstorm": {"id": "b", "count": 1}}}
        self.assertEqual(sorted(deck_obj_section_names(deck_obj, "Mainboard")), ["Brainstorm", "Sol Ring"])

    def test_handles_missing_or_malformed_sections(self) -> None:
        self.assertEqual(deck_obj_section_names(None, "Commanders"), [])
        self.assertEqual(deck_obj_section_names({}, "Commanders"), [])
        self.assertEqual(deck_obj_section_names({"Commanders": "not-a-dict"}, "Commanders"), [])


class SanitizeIdentityPayloadTests(unittest.TestCase):
    """PR #247 review: non-cEDH two-component identities must not be run
    through the MTG partner-pair legality check."""

    def test_commander_kind_delegates_to_mtg_sanitizer(self) -> None:
        name, components = sanitize_identity_payload(
            "Thrasios, Triton Hero / Tymna the Weaver",
            ["Thrasios, Triton Hero", "Tymna the Weaver"],
            "commander",
        )
        self.assertEqual(name, "Tymna the Weaver / Thrasios, Triton Hero")

    def test_commander_kind_still_rejects_illegal_mtg_pairs(self) -> None:
        name, components = sanitize_identity_payload("A / B", ["Sol Ring", "Brainstorm"], "commander")
        self.assertEqual(name, "Unknown Commander")
        self.assertEqual(components, ["Unknown Commander"])

    def test_archetype_kind_passes_two_components_through_unchanged(self) -> None:
        name, components = sanitize_identity_payload("Goat Control", ["Scapegoat", "Metamorphosis"], "archetype")
        self.assertEqual(name, "Goat Control")
        self.assertEqual(components, ["Scapegoat", "Metamorphosis"])

    def test_legend_kind_passes_duo_components_through_unchanged(self) -> None:
        name, components = sanitize_identity_payload(
            "Jinx, Loose Cannon / Viktor, Herald of the Arcane",
            ["Jinx, Loose Cannon", "Viktor, Herald of the Arcane"],
            "legend",
        )
        self.assertEqual(name, "Jinx, Loose Cannon / Viktor, Herald of the Arcane")
        self.assertEqual(components, ["Jinx, Loose Cannon", "Viktor, Herald of the Arcane"])

    def test_non_commander_kind_falls_back_to_unknown_identity_for_blank_name(self) -> None:
        name, components = sanitize_identity_payload("", [], "leader")
        self.assertEqual(name, "Unknown Commander")
        self.assertEqual(components, [])


if __name__ == "__main__":
    unittest.main()
