"""Tests for issue #321: caching Scryfall card art server-side.

Covers `scryfall_bulk_client.py` (the bulk-data HTTP client) and
`ingest_scryfall_cards.py` (name collection, printing selection, row
mapping, and the upsert orchestration).
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    import requests as requests_module
except ModuleNotFoundError:
    requests_module = types.ModuleType("requests")
    requests_module.get = Mock()
    requests_module.post = Mock()
    requests_module.Session = Mock
    requests_module.exceptions = types.SimpleNamespace(
        ConnectionError=ConnectionError,
        Timeout=TimeoutError,
        ReadTimeout=TimeoutError,
        JSONDecodeError=ValueError,
        HTTPError=RuntimeError,
        RequestException=Exception,
    )
    sys.modules["requests"] = requests_module

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ingest_scryfall_cards  # noqa: E402
import scryfall_bulk_client  # noqa: E402
from ingest_scryfall_cards import (  # noqa: E402
    build_scryfall_card_row,
    fetch_referenced_card_names,
    main,
    select_best_printing_per_name,
    split_commander_names,
    upsert_scryfall_cards,
)
from scryfall_bulk_client import (  # noqa: E402
    fetch_bulk_data_cards,
    fetch_bulk_data_index,
    find_bulk_data_download_uri,
)


class BulkDataIndexTests(unittest.TestCase):
    def test_fetch_bulk_data_index_returns_data_list(self) -> None:
        session = Mock()
        session.get.return_value = Mock(
            raise_for_status=Mock(),
            json=Mock(return_value={"data": [{"type": "default_cards", "download_uri": "https://x/y.json"}]}),
        )

        result = fetch_bulk_data_index(session)

        self.assertEqual(result, [{"type": "default_cards", "download_uri": "https://x/y.json"}])
        session.get.assert_called_once()
        self.assertEqual(session.get.call_args.args[0], scryfall_bulk_client.SCRYFALL_BULK_DATA_ENDPOINT)

    def test_find_bulk_data_download_uri_picks_matching_type(self) -> None:
        index = [
            {"type": "oracle_cards", "download_uri": "https://x/oracle.json"},
            {"type": "default_cards", "download_uri": "https://x/default.json"},
        ]

        uri = find_bulk_data_download_uri(index, "default_cards")

        self.assertEqual(uri, "https://x/default.json")

    def test_find_bulk_data_download_uri_raises_when_type_missing(self) -> None:
        with self.assertRaises(ValueError):
            find_bulk_data_download_uri([{"type": "oracle_cards", "download_uri": "https://x"}], "default_cards")

    def test_fetch_bulk_data_cards_downloads_and_parses(self) -> None:
        session = Mock()
        session.get.return_value = Mock(
            raise_for_status=Mock(), json=Mock(return_value=[{"id": "1", "name": "Sol Ring"}])
        )

        cards = fetch_bulk_data_cards("https://x/default.json", session)

        self.assertEqual(cards, [{"id": "1", "name": "Sol Ring"}])
        session.get.assert_called_once_with(
            "https://x/default.json", timeout=scryfall_bulk_client.DOWNLOAD_TIMEOUT_SECONDS
        )


class SplitCommanderNamesTests(unittest.TestCase):
    def test_returns_empty_set_for_none_or_empty(self) -> None:
        self.assertEqual(split_commander_names(None), set())
        self.assertEqual(split_commander_names([]), set())

    def test_flattens_partner_pair(self) -> None:
        result = split_commander_names(["Tymna the Weaver", "Kraum, Ludevic's Opus"])
        self.assertEqual(result, {"Tymna the Weaver", "Kraum, Ludevic's Opus"})

    def test_strips_and_drops_blank_entries(self) -> None:
        result = split_commander_names([" Sisay, Weatherlight Captain ", "", "   "])
        self.assertEqual(result, {"Sisay, Weatherlight Captain"})


class FetchReferencedCardNamesTests(unittest.TestCase):
    def test_flattens_commander_names_across_all_rows(self) -> None:
        client = Mock()
        client.select = Mock(
            return_value=[
                {"commander_names": ["Tymna the Weaver", "Kraum, Ludevic's Opus"]},
                {"commander_names": ["Sisay, Weatherlight Captain"]},
                {"commander_names": None},
            ]
        )

        names = fetch_referenced_card_names(client)

        self.assertEqual(names, {"Tymna the Weaver", "Kraum, Ludevic's Opus", "Sisay, Weatherlight Captain"})
        client.select.assert_called_once()
        self.assertEqual(client.select.call_args.args[0], "commanders")


class SelectBestPrintingPerNameTests(unittest.TestCase):
    def test_filters_to_referenced_names_only(self) -> None:
        cards = [
            {"id": "1", "name": "Sol Ring", "image_uris": {"art_crop": "https://x/1"}, "released_at": "2020-01-01"},
            {
                "id": "2",
                "name": "Not Referenced",
                "image_uris": {"art_crop": "https://x/2"},
                "released_at": "2020-01-01",
            },
        ]

        result = select_best_printing_per_name(cards, {"Sol Ring"})

        self.assertEqual(set(result.keys()), {"Sol Ring"})

    def test_prefers_most_recently_released_printing(self) -> None:
        cards = [
            {"id": "old", "name": "Sol Ring", "image_uris": {"art_crop": "https://x/old"}, "released_at": "2000-01-01"},
            {"id": "new", "name": "Sol Ring", "image_uris": {"art_crop": "https://x/new"}, "released_at": "2020-01-01"},
        ]

        result = select_best_printing_per_name(cards, {"Sol Ring"})

        self.assertEqual(result["Sol Ring"]["id"], "new")

    def test_skips_printings_without_image_uris_or_card_faces(self) -> None:
        cards = [
            {"id": "no-art", "name": "Sol Ring", "released_at": "2020-01-01"},
            {
                "id": "has-art",
                "name": "Sol Ring",
                "image_uris": {"art_crop": "https://x/art"},
                "released_at": "1999-01-01",
            },
        ]

        result = select_best_printing_per_name(cards, {"Sol Ring"})

        self.assertEqual(result["Sol Ring"]["id"], "has-art")

    def test_double_faced_card_without_top_level_image_uris_is_kept(self) -> None:
        cards = [
            {
                "id": "dfc",
                "name": "Fire // Ice",
                "released_at": "2020-01-01",
                "card_faces": [{"name": "Fire", "image_uris": {"art_crop": "https://x/fire"}}],
            }
        ]

        result = select_best_printing_per_name(cards, {"Fire // Ice"})

        self.assertEqual(result["Fire // Ice"]["id"], "dfc")


class BuildScryfallCardRowTests(unittest.TestCase):
    def test_maps_bulk_card_fields_onto_table_columns(self) -> None:
        card = {
            "id": "abc-123",
            "name": "Sol Ring",
            "oracle_text": "Tap: Add 2 colorless mana.",
            "mana_cost": "{1}",
            "cmc": 1.0,
            "type_line": "Artifact",
            "colors": [],
            "color_identity": [],
            "keywords": [],
            "legalities": {"commander": "legal"},
            "image_uris": {"art_crop": "https://x/art", "normal": "https://x/normal"},
            "prices": {"usd": "1.00"},
            "released_at": "1993-12-01",
            "set": "lea",
            "rarity": "uncommon",
        }

        row = build_scryfall_card_row(card)

        self.assertEqual(row["scryfall_id"], "abc-123")
        self.assertEqual(row["name"], "Sol Ring")
        self.assertEqual(row["image_uris"], {"art_crop": "https://x/art", "normal": "https://x/normal"})
        self.assertEqual(row["set_code"], "lea")

    def test_falls_back_to_front_face_image_uris_for_double_faced_cards(self) -> None:
        card = {
            "id": "dfc-1",
            "name": "Fire // Ice",
            "released_at": "2020-01-01",
            "card_faces": [
                {"name": "Fire", "image_uris": {"art_crop": "https://x/fire"}},
                {"name": "Ice", "image_uris": {"art_crop": "https://x/ice"}},
            ],
        }

        row = build_scryfall_card_row(card)

        self.assertEqual(row["image_uris"], {"art_crop": "https://x/fire"})


class UpsertScryfallCardsTests(unittest.TestCase):
    def test_chunks_upserts_and_returns_total_row_count(self) -> None:
        client = Mock()
        rows = [{"scryfall_id": str(i), "name": f"Card {i}"} for i in range(1250)]

        total = upsert_scryfall_cards(client, rows)

        self.assertEqual(total, 1250)
        # 1250 rows / 500-row chunks = 3 upsert calls (500, 500, 250).
        self.assertEqual(client.upsert.call_count, 3)
        for call_args in client.upsert.call_args_list:
            self.assertEqual(call_args.args[0], "scryfall_cards")
            self.assertEqual(call_args.kwargs["on_conflict"], "scryfall_id")

    def test_empty_rows_makes_no_upsert_calls(self) -> None:
        client = Mock()

        total = upsert_scryfall_cards(client, [])

        self.assertEqual(total, 0)
        client.upsert.assert_not_called()


class MainOrchestrationTests(unittest.TestCase):
    """End-to-end wiring: main() collects referenced names, fetches the bulk
    dump, filters/maps matches, and upserts -- or reports without writing
    under --dry-run.
    """

    def _patched(self, argv: list[str]):
        client = Mock()
        client.select = Mock(return_value=[{"commander_names": ["Sol Ring Commander"]}])

        return (
            client,
            patch.object(ingest_scryfall_cards, "load_credentials", return_value=("url", "key")),
            patch.object(ingest_scryfall_cards, "SupabaseClient", return_value=client),
            patch.object(
                ingest_scryfall_cards,
                "fetch_bulk_data_index",
                return_value=[{"type": "default_cards", "download_uri": "https://x/default.json"}],
            ),
            patch.object(
                ingest_scryfall_cards,
                "fetch_bulk_data_cards",
                return_value=[
                    {
                        "id": "match-1",
                        "name": "Sol Ring Commander",
                        "image_uris": {"art_crop": "https://x/art"},
                        "released_at": "2020-01-01",
                    },
                    {
                        "id": "unmatched",
                        "name": "Some Other Card",
                        "image_uris": {"art_crop": "https://x/other"},
                        "released_at": "2020-01-01",
                    },
                ],
            ),
            patch.object(sys, "argv", argv),
        )

    def test_dry_run_reports_matches_without_upserting(self) -> None:
        client, *patches = self._patched(["ingest_scryfall_cards.py", "--dry-run"])
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            main()

        client.upsert.assert_not_called()

    def test_live_run_upserts_only_matched_names(self) -> None:
        client, *patches = self._patched(["ingest_scryfall_cards.py"])
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            main()

        client.upsert.assert_called_once()
        upserted_rows = client.upsert.call_args.args[1]
        self.assertEqual(len(upserted_rows), 1)
        self.assertEqual(upserted_rows[0]["scryfall_id"], "match-1")


if __name__ == "__main__":
    unittest.main()
