import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

try:
    import requests as requests_module  # noqa: F401
except ModuleNotFoundError:
    requests_module = types.ModuleType("requests")
    requests_module.get = Mock()
    requests_module.post = Mock()
    requests_module.patch = Mock()
    requests_module.delete = Mock()
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

from commander_oracle_identity import (  # noqa: E402
    build_alias_map,
    build_name_to_oracle_id_map,
    choose_canonical_row,
    collect_true_oracle_names,
    commander_names_from_row,
    group_duplicate_commander_rows,
    oracle_signature_for_names,
)

# A realistic fixture: a Universes Beyond alternate-name printing of a
# commander-legal card, plus its original ("true") printing sharing the same
# oracle_id, plus an unrelated legendary creature to make sure grouping stays
# scoped to matching oracle_ids only.
UB_ALT_NAME_ORACLE_ID = "11111111-1111-1111-1111-111111111111"
UNRELATED_ORACLE_ID = "22222222-2222-2222-2222-222222222222"

TRUE_PRINTING = {
    "name": "Nadier, Agent of the Duskenel",
    "oracle_id": UB_ALT_NAME_ORACLE_ID,
    "type_line": "Legendary Creature — Human Warlock",
    "legalities": {"commander": "legal"},
}

UB_ALT_NAME_PRINTING = {
    "name": "Nadier, Agent of the Duskenel",
    "flavor_name": "Totally Radical Skater",
    "oracle_id": UB_ALT_NAME_ORACLE_ID,
    "type_line": "Legendary Creature — Human Warlock",
    "legalities": {"commander": "legal"},
}

UNRELATED_PRINTING = {
    "name": "Tymna the Weaver",
    "oracle_id": UNRELATED_ORACLE_ID,
    "type_line": "Legendary Creature — Human Cleric",
    "legalities": {"commander": "legal"},
}

NOT_COMMANDER_LEGAL_ALT_PRINTING = {
    "name": "Some Un-Legal Card",
    "flavor_name": "Definitely Not Legal Flavor Name",
    "oracle_id": "33333333-3333-3333-3333-333333333333",
    "type_line": "Creature — Human",
    "legalities": {"commander": "not_legal"},
}


class BuildNameToOracleIdMapTests(unittest.TestCase):
    def test_indexes_true_name_and_flavor_name_to_same_oracle_id(self) -> None:
        mapping = build_name_to_oracle_id_map([TRUE_PRINTING, UB_ALT_NAME_PRINTING, UNRELATED_PRINTING])

        self.assertEqual(mapping["Nadier, Agent of the Duskenel"], UB_ALT_NAME_ORACLE_ID)
        self.assertEqual(mapping["Totally Radical Skater"], UB_ALT_NAME_ORACLE_ID)
        self.assertEqual(mapping["Tymna the Weaver"], UNRELATED_ORACLE_ID)

    def test_true_name_is_never_shadowed_by_a_flavor_name_collision(self) -> None:
        colliding_flavor_printing = {
            "name": "Some Other Card",
            "flavor_name": "Tymna the Weaver",
            "oracle_id": "44444444-4444-4444-4444-444444444444",
            "legalities": {"commander": "legal"},
        }

        mapping = build_name_to_oracle_id_map([UNRELATED_PRINTING, colliding_flavor_printing])

        self.assertEqual(mapping["Tymna the Weaver"], UNRELATED_ORACLE_ID)

    def test_skips_cards_missing_oracle_id(self) -> None:
        mapping = build_name_to_oracle_id_map([{"name": "No Oracle Id Card"}])
        self.assertEqual(mapping, {})


class BuildAliasMapTests(unittest.TestCase):
    def test_maps_flavor_name_to_true_name_for_commander_legal_cards(self) -> None:
        alias_map = build_alias_map([TRUE_PRINTING, UB_ALT_NAME_PRINTING])
        self.assertEqual(alias_map, {"Totally Radical Skater": "Nadier, Agent of the Duskenel"})

    def test_excludes_non_commander_legal_cards(self) -> None:
        alias_map = build_alias_map([NOT_COMMANDER_LEGAL_ALT_PRINTING])
        self.assertEqual(alias_map, {})

    def test_excludes_printings_without_a_distinct_flavor_name(self) -> None:
        alias_map = build_alias_map([TRUE_PRINTING, UNRELATED_PRINTING])
        self.assertEqual(alias_map, {})


class CollectTrueOracleNamesTests(unittest.TestCase):
    def test_collects_only_true_names_not_flavor_names(self) -> None:
        names = collect_true_oracle_names([TRUE_PRINTING, UB_ALT_NAME_PRINTING, UNRELATED_PRINTING])
        self.assertEqual(names, {"Nadier, Agent of the Duskenel", "Tymna the Weaver"})


class CommanderNamesFromRowTests(unittest.TestCase):
    def test_prefers_commander_names_list(self) -> None:
        row = {"name": "A / B", "commander_names": ["A", "B"]}
        self.assertEqual(commander_names_from_row(row), ["A", "B"])

    def test_falls_back_to_splitting_name_field(self) -> None:
        row = {"name": "Tymna the Weaver / Thrasios, Triton Hero", "commander_names": []}
        self.assertEqual(
            commander_names_from_row(row),
            ["Tymna the Weaver", "Thrasios, Triton Hero"],
        )

    def test_single_commander_row(self) -> None:
        row = {"name": "Totally Radical Skater", "commander_names": ["Totally Radical Skater"]}
        self.assertEqual(commander_names_from_row(row), ["Totally Radical Skater"])


class OracleSignatureForNamesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.name_to_oracle_id = build_name_to_oracle_id_map(
            [TRUE_PRINTING, UB_ALT_NAME_PRINTING, UNRELATED_PRINTING]
        )

    def test_alt_name_and_true_name_share_a_signature(self) -> None:
        alt_signature = oracle_signature_for_names(["Totally Radical Skater"], self.name_to_oracle_id)
        true_signature = oracle_signature_for_names(["Nadier, Agent of the Duskenel"], self.name_to_oracle_id)
        self.assertEqual(alt_signature, true_signature)
        self.assertEqual(alt_signature, (UB_ALT_NAME_ORACLE_ID,))

    def test_returns_none_for_unresolvable_name(self) -> None:
        self.assertIsNone(oracle_signature_for_names(["Some Unknown Card"], self.name_to_oracle_id))

    def test_returns_none_for_empty_names(self) -> None:
        self.assertIsNone(oracle_signature_for_names([], self.name_to_oracle_id))

    def test_sorts_multi_card_signature_deterministically(self) -> None:
        signature = oracle_signature_for_names(
            ["Tymna the Weaver", "Totally Radical Skater"], self.name_to_oracle_id
        )
        self.assertEqual(signature, tuple(sorted([UNRELATED_ORACLE_ID, UB_ALT_NAME_ORACLE_ID])))


class GroupDuplicateCommanderRowsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.name_to_oracle_id = build_name_to_oracle_id_map(
            [TRUE_PRINTING, UB_ALT_NAME_PRINTING, UNRELATED_PRINTING]
        )

    def test_groups_alt_name_row_with_true_name_row(self) -> None:
        true_row = {"id": "true-id", "name": "Nadier, Agent of the Duskenel", "commander_names": []}
        alt_row = {"id": "alt-id", "name": "Totally Radical Skater", "commander_names": []}
        unrelated_row = {"id": "unrelated-id", "name": "Tymna the Weaver", "commander_names": []}

        groups = group_duplicate_commander_rows(
            [true_row, alt_row, unrelated_row], self.name_to_oracle_id
        )

        self.assertEqual(len(groups), 1)
        (signature, rows), = groups.items()
        self.assertEqual(signature, (UB_ALT_NAME_ORACLE_ID,))
        self.assertCountEqual([row["id"] for row in rows], ["true-id", "alt-id"])

    def test_singleton_signatures_are_not_returned(self) -> None:
        unrelated_row = {"id": "unrelated-id", "name": "Tymna the Weaver", "commander_names": []}
        groups = group_duplicate_commander_rows([unrelated_row], self.name_to_oracle_id)
        self.assertEqual(groups, {})

    def test_rows_with_unresolvable_names_are_ignored(self) -> None:
        unknown_row = {"id": "unknown-id", "name": "Some Unknown Card", "commander_names": []}
        groups = group_duplicate_commander_rows([unknown_row], self.name_to_oracle_id)
        self.assertEqual(groups, {})


class ChooseCanonicalRowTests(unittest.TestCase):
    def test_prefers_true_oracle_name_over_flavor_name(self) -> None:
        true_row = {"id": "true-id", "name": "Nadier, Agent of the Duskenel"}
        alt_row = {"id": "alt-id", "name": "Totally Radical Skater"}
        true_oracle_names = {"Nadier, Agent of the Duskenel", "Tymna the Weaver"}

        canonical, duplicates = choose_canonical_row([alt_row, true_row], true_oracle_names)

        self.assertEqual(canonical["id"], "true-id")
        self.assertEqual([row["id"] for row in duplicates], ["alt-id"])

    def test_falls_back_to_alphabetical_order_when_neither_is_a_true_name(self) -> None:
        row_b = {"id": "b-id", "name": "B Flavor Name"}
        row_a = {"id": "a-id", "name": "A Flavor Name"}

        canonical, duplicates = choose_canonical_row([row_b, row_a], true_oracle_names=set())

        self.assertEqual(canonical["id"], "a-id")
        self.assertEqual([row["id"] for row in duplicates], ["b-id"])

    def test_prefers_true_named_row_for_partner_pair_composite_names(self) -> None:
        # Regression test: a two-card commander row's `name` is a composite
        # display string like "Sophina, Spearsage Deserter / Hargilde, Kindly
        # Runechanter", which never appears verbatim in `true_oracle_names`
        # (that set only contains individual card names). Before the fix,
        # this made every partner row look flavor-named, so a flavor-named
        # row alphabetically earlier than the true-named row (e.g. "Chief Jim
        # Hopper / Dustin, Gadget Genius") would incorrectly win as canonical.
        true_row = {
            "id": "true-id",
            "name": "Sophina, Spearsage Deserter / Hargilde, Kindly Runechanter",
            "commander_names": ["Sophina, Spearsage Deserter", "Hargilde, Kindly Runechanter"],
        }
        flavor_row = {
            "id": "flavor-id",
            "name": "Chief Jim Hopper / Dustin, Gadget Genius",
            "commander_names": ["Chief Jim Hopper", "Hargilde, Kindly Runechanter"],
        }
        true_oracle_names = {
            "Sophina, Spearsage Deserter",
            "Hargilde, Kindly Runechanter",
        }

        canonical, duplicates = choose_canonical_row([flavor_row, true_row], true_oracle_names)

        self.assertEqual(canonical["id"], "true-id")
        self.assertEqual([row["id"] for row in duplicates], ["flavor-id"])


if __name__ == "__main__":
    unittest.main()
