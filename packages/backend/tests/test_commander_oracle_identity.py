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
    is_commander_eligible,
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

# Regression fixture for the Codex review comment on PR #265: some UB
# rebrands use `printed_name` (normally a foreign-language localization
# field) instead of `flavor_name`, while still being tagged `lang: "en"`.
# The real example is Sophina, Spearsage Deserter's Secret Lair x Stranger
# Things printing, which has `printed_name: "Chief Jim Hopper"` with no
# `flavor_name` at all.
PRINTED_NAME_ALT_PRINTING = {
    "name": "Nadier, Agent of the Duskenel",
    "printed_name": "Chief Jim Hopper",
    "lang": "en",
    "oracle_id": UB_ALT_NAME_ORACLE_ID,
    "type_line": "Legendary Creature — Human Warlock",
    "legalities": {"commander": "legal"},
}

NOT_COMMANDER_LEGAL_ALT_PRINTING = {
    "name": "Some Un-Legal Card",
    "flavor_name": "Definitely Not Legal Flavor Name",
    "oracle_id": "33333333-3333-3333-3333-333333333333",
    "type_line": "Creature — Human",
    "legalities": {"commander": "not_legal"},
}

# `legalities.commander == "legal"` means "legal in a Commander deck's 99",
# which is true of an ordinary 99-deck card too -- it says nothing about
# whether the card can occupy the command zone. This fixture has a flavor
# name that collides with a *real* commander's true Oracle name
# ("Tymna the Weaver", see UNRELATED_PRINTING above); without an
# eligibility filter beyond format-legality, this would generate an alias
# that silently rewrites that commander's name via
# `clean_commander_card_name()`.
ORDINARY_99_DECK_CARD_WITH_COLLIDING_FLAVOR_NAME = {
    "name": "Sample Instant Spell",
    "flavor_name": "Tymna the Weaver",
    "oracle_id": "55555555-5555-5555-5555-555555555555",
    "type_line": "Instant",
    "legalities": {"commander": "legal"},
}

# A commander-eligible (Legendary Creature) card whose flavor name happens
# to collide with a *different* real card's true Oracle name. Even though
# this card itself passes the eligibility filter, the flavor name must
# still be rejected because it is ambiguous with another card's real name.
COMMANDER_ELIGIBLE_CARD_WITH_FLAVOR_NAME_COLLIDING_WITH_OTHER_ORACLE_NAME = {
    "name": "Marchesa, the Black Rose",
    "flavor_name": "Tymna the Weaver",
    "oracle_id": "77777777-7777-7777-7777-777777777777",
    "type_line": "Legendary Creature — Human Assassin",
    "legalities": {"commander": "legal"},
}

LEGENDARY_BACKGROUND = {
    "name": "Test Background",
    "type_line": "Legendary Enchantment — Background",
    "oracle_text": "",
    "legalities": {"commander": "legal"},
}

PLANESWALKER_COMMANDER = {
    "name": "Test Planeswalker Commander",
    "type_line": "Legendary Planeswalker — TestWalker",
    "oracle_text": "Test Planeswalker Commander can be your commander.\n+1: Draw a card.",
    "legalities": {"commander": "legal"},
}

ORDINARY_NON_LEGENDARY_CREATURE = {
    "name": "Ordinary Creature",
    "type_line": "Creature — Human Wizard",
    "oracle_text": "",
    "legalities": {"commander": "legal"},
}


class IsCommanderEligibleTests(unittest.TestCase):
    def test_legendary_creature_is_eligible(self) -> None:
        self.assertTrue(is_commander_eligible(TRUE_PRINTING))

    def test_ordinary_commander_legal_card_is_not_eligible(self) -> None:
        # This is the exact landmine from the review comment: a card that's
        # merely legal to *play* in Commander (true of most Magic cards) is
        # not thereby eligible to *be* a commander.
        self.assertFalse(is_commander_eligible(ORDINARY_99_DECK_CARD_WITH_COLLIDING_FLAVOR_NAME))
        self.assertFalse(is_commander_eligible(ORDINARY_NON_LEGENDARY_CREATURE))

    def test_legendary_background_is_eligible(self) -> None:
        self.assertTrue(is_commander_eligible(LEGENDARY_BACKGROUND))

    def test_planeswalker_with_can_be_your_commander_text_is_eligible(self) -> None:
        self.assertTrue(is_commander_eligible(PLANESWALKER_COMMANDER))

    def test_non_commander_legal_card_is_not_eligible_regardless_of_type_line(self) -> None:
        self.assertFalse(is_commander_eligible(NOT_COMMANDER_LEGAL_ALT_PRINTING))


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

    def test_indexes_printed_name_alongside_flavor_name(self) -> None:
        mapping = build_name_to_oracle_id_map([TRUE_PRINTING, PRINTED_NAME_ALT_PRINTING])
        self.assertEqual(mapping["Chief Jim Hopper"], UB_ALT_NAME_ORACLE_ID)


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

    def test_excludes_ordinary_99_deck_card_even_though_format_legal(self) -> None:
        # Regression test for the review comment: `legalities.commander ==
        # "legal"` alone must not be enough to emit an alias. This ordinary
        # Instant is legal to run in a Commander deck's 99 (like almost
        # every card), but it can never itself be a commander, so no alias
        # should be generated even though its flavor name collides with a
        # real commander's true Oracle name.
        alias_map = build_alias_map([ORDINARY_99_DECK_CARD_WITH_COLLIDING_FLAVOR_NAME])
        self.assertEqual(alias_map, {})

    def test_excludes_flavor_name_that_is_a_real_oracle_name_of_another_card(self) -> None:
        # Regression test: even a commander-eligible card must not have its
        # flavor name aliased if that exact string is itself the real
        # Oracle name of some other card -- aliasing it would be ambiguous
        # and could rewrite that other card's name via
        # `clean_commander_card_name()`.
        alias_map = build_alias_map(
            [UNRELATED_PRINTING, COMMANDER_ELIGIBLE_CARD_WITH_FLAVOR_NAME_COLLIDING_WITH_OTHER_ORACLE_NAME]
        )
        self.assertEqual(alias_map, {})

    def test_still_generates_aliases_for_legitimate_commander_eligible_ub_cards(self) -> None:
        # Confirms the eligibility + oracle-name filters don't regress the
        # actual feature: a genuine UB alternate-name commander printing
        # (Legendary Creature, distinct flavor name, no collisions) must
        # still produce its alias.
        alias_map = build_alias_map([TRUE_PRINTING, UB_ALT_NAME_PRINTING, UNRELATED_PRINTING])
        self.assertEqual(alias_map, {"Totally Radical Skater": "Nadier, Agent of the Duskenel"})

    def test_maps_printed_name_to_true_name_alongside_flavor_name(self) -> None:
        # Regression test for the Codex review comment on PR #265: a UB
        # rebrand recorded via `printed_name` (not `flavor_name`) must still
        # produce an alias -- an earlier pass only checked `flavor_name` and
        # incorrectly concluded these names didn't exist in Scryfall's data.
        alias_map = build_alias_map([TRUE_PRINTING, UB_ALT_NAME_PRINTING, PRINTED_NAME_ALT_PRINTING])
        self.assertEqual(
            alias_map,
            {
                "Totally Radical Skater": "Nadier, Agent of the Duskenel",
                "Chief Jim Hopper": "Nadier, Agent of the Duskenel",
            },
        )


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

    def test_prefers_canonical_partner_order_over_alphabetical_fallback(self) -> None:
        # Regression test: when the database already has the same two
        # true-named partners in both orders, the alphabetical fallback used
        # to win regardless of the canonical order enforced by
        # `PARTNER_ORDER_OVERRIDES`/`normalize_partner_order` elsewhere in the
        # ingest pipeline. "Kraum, Ludevic's Opus" sorts before "Tymna the
        # Weaver" alphabetically, but the canonical override for this pair is
        # ("Tymna the Weaver", "Kraum, Ludevic's Opus").
        non_canonical_row = {
            "id": "non-canonical-id",
            "name": "Kraum, Ludevic's Opus / Tymna the Weaver",
            "commander_names": ["Kraum, Ludevic's Opus", "Tymna the Weaver"],
        }
        canonical_row = {
            "id": "canonical-id",
            "name": "Tymna the Weaver / Kraum, Ludevic's Opus",
            "commander_names": ["Tymna the Weaver", "Kraum, Ludevic's Opus"],
        }
        true_oracle_names = {"Kraum, Ludevic's Opus", "Tymna the Weaver"}

        canonical, duplicates = choose_canonical_row(
            [non_canonical_row, canonical_row], true_oracle_names
        )

        self.assertEqual(canonical["id"], "canonical-id")
        self.assertEqual([row["id"] for row in duplicates], ["non-canonical-id"])


if __name__ == "__main__":
    unittest.main()
