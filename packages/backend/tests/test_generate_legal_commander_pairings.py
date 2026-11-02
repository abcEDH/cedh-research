import gzip
import unittest
from unittest.mock import Mock, patch

from generate_legal_commander_pairings import build_commander_card, build_pairings, fetch_oracle_cards


def card(name, text, type_line="Legendary Creature — Human", **extra):
    return build_commander_card(
        dict(name=name, oracle_text=text, type_line=type_line, legalities={"commander": "legal"}, **extra)
    )


class LegalPairingsTests(unittest.TestCase):
    def test_nonlegendary_partner_with_is_not_a_commander(self):
        cards = [
            card("Chakram Retriever", "Partner with Chakram Slinger", "Creature — Elemental Hound"),
            card("Chakram Slinger", "Partner with Chakram Retriever", "Creature — Goblin Warrior"),
        ]
        self.assertEqual(build_pairings(cards), {})

    def test_partner_and_designators_are_separate(self):
        cards = [
            card("Plain A", "Partner"),
            card("Plain B", "Partner"),
            card("Survivor A", "Partner—Survivors"),
            card("Survivor B", "Partner—Survivors"),
            card("Friend A", "Partner—Friends forever"),
            card("Friend B", "Friends forever"),
        ]
        pairs = build_pairings(cards)
        self.assertEqual(set(pairs), {("Plain A", "Plain B"), ("Survivor A", "Survivor B"), ("Friend A", "Friend B")})

    def test_doctor_requires_exact_creature_types(self):
        cards = [
            card("Companion", "Doctor's companion"),
            card("Doctor", "", "Legendary Creature — Time Lord Doctor"),
            card("Extra Type", "", "Legendary Creature — Human Time Lord Doctor"),
        ]
        self.assertEqual(set(build_pairings(cards)), {("Companion", "Doctor")})

    def test_front_face_only_and_planeswalker_permission(self):
        dfc = card(
            "Front // Back",
            "",
            card_faces=[
                {"name": "Front", "type_line": "Legendary Creature — Human", "oracle_text": "Partner"},
                {"name": "Back", "type_line": "Legendary Creature — Human", "oracle_text": "Partner with Fake"},
            ],
        )
        walker = card("Walker", "Partner\nWalker can be your commander.", "Legendary Planeswalker — Walker")
        pairs = build_pairings([dfc, walker])
        self.assertEqual(set(pairs), {("Front", "Walker")})
        self.assertNotIn("Back", next(iter(pairs.values()))["project_name"])

    def test_background_pair_and_banned_exclusion(self):
        chooser = card("Chooser", "Choose a Background")
        background = card("Background", "", "Legendary Enchantment — Background")
        banned = build_commander_card(
            {
                "name": "Banned",
                "oracle_text": "Choose a Background",
                "type_line": "Legendary Creature — Human",
                "legalities": {"commander": "banned"},
            }
        )
        self.assertEqual(set(build_pairings([chooser, background, banned])), {("Background", "Chooser")})

    def test_saved_order_is_preserved(self):
        pairs = build_pairings([card("Tymna the Weaver", "Partner"), card("Kraum, Ludevic's Opus", "Partner")])
        self.assertEqual(next(iter(pairs.values()))["project_name"], "Tymna the Weaver / Kraum, Ludevic's Opus")

    def test_current_compressed_jsonl_bulk_format(self):
        metadata = Mock()
        metadata.json.return_value = {
            "data": [{"type": "oracle_cards", "jsonl_download_uri": "https://example.test/cards.gz"}]
        }
        cards = Mock()
        cards.content = gzip.compress(b'{"name":"One"}\n{"name":"Two"}\n')
        with patch("generate_legal_commander_pairings.requests.get", side_effect=[metadata, cards]):
            self.assertEqual(fetch_oracle_cards(10), [{"name": "One"}, {"name": "Two"}])

    def test_legacy_bulk_format(self):
        metadata = Mock()
        metadata.json.return_value = {
            "data": [{"type": "oracle_cards", "download_uri": "https://example.test/cards.json"}]
        }
        cards = Mock()
        cards.json.return_value = [{"name": "One"}]
        with patch("generate_legal_commander_pairings.requests.get", side_effect=[metadata, cards]):
            self.assertEqual(fetch_oracle_cards(10), [{"name": "One"}])
