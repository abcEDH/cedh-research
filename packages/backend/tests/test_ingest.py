import sys
import types
from pathlib import Path
import unittest


sys.modules.setdefault("requests", types.ModuleType("requests"))

dateutil_module = types.ModuleType("dateutil")
dateutil_parser_module = types.ModuleType("dateutil.parser")
dateutil_parser_module.parse = lambda value: value
dateutil_module.parser = dateutil_parser_module
sys.modules.setdefault("dateutil", dateutil_module)
sys.modules.setdefault("dateutil.parser", dateutil_parser_module)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import clean_commander_card_name, extract_standing_rates, normalize_commander_name, sanitize_commander_payload  # noqa: E402


class ExtractStandingRatesTests(unittest.TestCase):
    def test_uses_primary_and_opponent_fallbacks_independently(self) -> None:
        standing = {
            "successRate": 0.72,
            "opponentWinRate": 0.41,
        }

        win_rate, opponent_win_rate = extract_standing_rates(standing)

        self.assertEqual(win_rate, 0.72)
        self.assertEqual(opponent_win_rate, 0.41)

    def test_accepts_percent_values_for_both_fields(self) -> None:
        standing = {
            "winRate": 71,
            "opponentSuccessRate": 48,
        }

        win_rate, opponent_win_rate = extract_standing_rates(standing)

        self.assertEqual(win_rate, 0.71)
        self.assertEqual(opponent_win_rate, 0.48)


class CommanderNormalizationTests(unittest.TestCase):
    def test_clean_commander_card_name_maps_stranger_things_to_in_universe(self) -> None:
        self.assertEqual(clean_commander_card_name("Lucas, the Sharpshooter"), "Bjorna, Nightfall Alchemist")

    def test_clean_commander_card_name_unescapes_quotes(self) -> None:
        self.assertEqual(clean_commander_card_name("K\\'rrik, Son of Yawgmoth"), "K'rrik, Son of Yawgmoth")

    def test_clean_commander_card_name_strips_double_faced_backside(self) -> None:
        self.assertEqual(
            clean_commander_card_name("Etali, Primal Conqueror // Etali, Primal Sickness"),
            "Etali, Primal Conqueror",
        )

    def test_normalize_commander_name_strips_back_faces_from_partner_pair(self) -> None:
        self.assertEqual(
            normalize_commander_name(
                [
                    "Etali, Primal Conqueror // Etali, Primal Sickness",
                    "Vivi Ornitier",
                ]
            ),
            "Etali, Primal Conqueror / Vivi Ornitier",
        )

    def test_sanitize_commander_payload_canonicalizes_name_and_components(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Kraum, Ludevic\\'s Opus / Tymna the Weaver",
                ["Kraum, Ludevic\\'s Opus", "Tymna the Weaver"],
            ),
            (
                "Tymna the Weaver / Kraum, Ludevic's Opus",
                ["Tymna the Weaver", "Kraum, Ludevic's Opus"],
            ),
        )

    def test_sanitize_commander_payload_maps_stranger_things_pair(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Lucas, the Sharpshooter / Will the Wise",
                ["Lucas, the Sharpshooter", "Will the Wise"],
            ),
            (
                "Bjorna, Nightfall Alchemist / Wernog, Rider's Chaplain",
                ["Bjorna, Nightfall Alchemist", "Wernog, Rider's Chaplain"],
            ),
        )

    def test_sanitize_commander_payload_rejects_illegal_pair(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Etali, Primal Conqueror / Kinnan, Bonder Prodigy",
                ["Etali, Primal Conqueror", "Kinnan, Bonder Prodigy"],
            ),
            ("Unknown Commander", ["Unknown Commander"]),
        )

    def test_normalize_commander_name_uses_canonical_legal_pair_order(self) -> None:
        self.assertEqual(
            normalize_commander_name(["Haldan, Avid Arcanist", "Pako, Arcane Retriever"]),
            "Pako, Arcane Retriever / Haldan, Avid Arcanist",
        )


if __name__ == "__main__":
    unittest.main()
