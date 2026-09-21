import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from topdeck_client import (
    TopDeckClient,
    decode_firestore_value,
    flat_firestore_league_to_topdeck_payload,
    is_placeholder_player_name,
    normalize_topdeck_tournament_payload,
    should_use_firestore_tournament_fallback,
)


class TopDeckClientTests(unittest.TestCase):
    def test_decode_firestore_value(self) -> None:
        self.assertEqual(decode_firestore_value({"stringValue": "hello"}), "hello")
        self.assertEqual(decode_firestore_value({"integerValue": "42"}), 42)
        self.assertEqual(decode_firestore_value({"doubleValue": 3.14}), 3.14)
        self.assertEqual(decode_firestore_value({"booleanValue": True}), True)
        self.assertEqual(decode_firestore_value({"nullValue": None}), None)

    def test_is_placeholder_player_name(self) -> None:
        self.assertTrue(is_placeholder_player_name("Unknown"))
        self.assertTrue(is_placeholder_player_name("unknown"))
        self.assertTrue(is_placeholder_player_name("  unknown  "))
        self.assertTrue(is_placeholder_player_name(None))
        self.assertFalse(is_placeholder_player_name("John Doe"))

    def test_should_use_firestore_tournament_fallback(self) -> None:
        # True if no rounds/standings and startDate is missing or name is Unknown
        self.assertTrue(should_use_firestore_tournament_fallback({}))
        self.assertTrue(should_use_firestore_tournament_fallback({"data": {"name": "Unknown Name"}}))

        # False if rounds or standings exist
        self.assertFalse(should_use_firestore_tournament_fallback({"rounds": [{"round": 1}]}))
        self.assertFalse(should_use_firestore_tournament_fallback({"standings": [{"id": 1}]}))

    def test_normalize_topdeck_tournament_payload(self) -> None:
        # Handles nested "data"
        raw = {
            "data": {
                "id": "T123",
                "name": "My Tourney"
            },
            "standings": []
        }
        res = normalize_topdeck_tournament_payload(raw, tid="T123")
        self.assertEqual(res["id"], "T123")
        self.assertEqual(res["TID"], "T123")
        self.assertEqual(res["name"], "My Tourney")
        self.assertIn("standings", res)
        self.assertIn("rounds", res)

    def test_flat_firestore_round_keys_preserve_swiss_and_bracket_rounds(self) -> None:
        payload = flat_firestore_league_to_topdeck_payload(
            "T123",
            {
                "E1:P1": "player-1",
                "E2:P1": "player-2",
                "S1:R1:T1": {
                    "Es": [1, 2],
                    "Winner": 1,
                    "End": 123,
                },
                "S2:R1:T1": {
                    "Es": [1, 2],
                    "Winner": 1,
                    "End": 456,
                },
            },
        )

        self.assertIsNotNone(payload)
        self.assertEqual([row["round"] for row in payload["rounds"]], [1, "S2:R1"])
        self.assertEqual(payload["swissNum"], 1)
        self.assertEqual(payload["rounds"][1]["tables"][0]["winner_id"], "player-1")

    def test_legacy_flat_firestore_round_keys_remain_numeric(self) -> None:
        payload = flat_firestore_league_to_topdeck_payload(
            "T123",
            {
                "E1:P1": "player-1",
                "E2:P1": "player-2",
                "S1:T1": {"Es": [1, 2], "Winner": 1, "End": 123},
                "S2:T1": {"Es": [1, 2], "Winner": 1, "End": 456},
            },
        )

        self.assertEqual([row["round"] for row in payload["rounds"]], [1, 2])
        self.assertEqual(payload["swissNum"], 2)

    @patch("topdeck_client.requests.get")
    def test_topdeck_client_request_success(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test"}
        mock_get.return_value = mock_response

        client = TopDeckClient("test_key")
        res = client._request("GET", "http://test")
        self.assertEqual(res, {"id": "test"})
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args[1]["headers"]["Authorization"], "test_key")
