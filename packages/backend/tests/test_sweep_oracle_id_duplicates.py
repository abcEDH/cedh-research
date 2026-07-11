import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

try:
    import requests as requests_module
except ModuleNotFoundError:
    requests_module = types.ModuleType("requests")
    requests_module.get = Mock()
    requests_module.post = Mock()
    requests_module.patch = Mock()
    requests_module.exceptions = types.SimpleNamespace(
        ConnectionError=ConnectionError,
        Timeout=TimeoutError,
        ReadTimeout=TimeoutError,
        JSONDecodeError=ValueError,
        HTTPError=RuntimeError,
        RequestException=Exception,
    )
    sys.modules["requests"] = requests_module

dateutil_module = types.ModuleType("dateutil")
dateutil_parser_module = types.ModuleType("dateutil.parser")
dateutil_parser_module.parse = lambda value: value
dateutil_module.parser = dateutil_parser_module
sys.modules.setdefault("dateutil", dateutil_module)
sys.modules.setdefault("dateutil.parser", dateutil_parser_module)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sweep_oracle_id_duplicates import (  # noqa: E402
    build_oracle_group_key,
    choose_canonical_commander,
)


class BuildOracleGroupKeyTests(unittest.TestCase):
    """Tests for the Universes Beyond oracle_id merge-key logic (issue #261).

    Two commander rows should only be treated as duplicates when every card in
    the row shares an oracle_id with every card in the other row — grouping by
    only the first matching card would incorrectly collapse distinct partner
    pairs that happen to share one commander, e.g. "Tymna / Kraum" and
    "Tymna / Thrasios".
    """

    def test_single_commander_resolves_to_its_oracle_id(self) -> None:
        name_to_oracle = {"Urza, Lord Artificer": "oracle-urza"}
        key = build_oracle_group_key(["Urza, Lord Artificer"], name_to_oracle)
        self.assertEqual(key, ("oracle-urza",))

    def test_partner_pair_key_is_order_independent(self) -> None:
        name_to_oracle = {
            "Tymna the Weaver": "oracle-tymna",
            "Kraum, Ludevic's Opus": "oracle-kraum",
        }
        forward = build_oracle_group_key(
            ["Tymna the Weaver", "Kraum, Ludevic's Opus"], name_to_oracle
        )
        reversed_ = build_oracle_group_key(
            ["Kraum, Ludevic's Opus", "Tymna the Weaver"], name_to_oracle
        )
        self.assertEqual(forward, reversed_)

    def test_different_partner_pairs_sharing_one_card_do_not_collide(self) -> None:
        # Regression test: grouping by only the first matching card would make
        # both of these pairs collapse into one "Tymna" group and incorrectly
        # merge two distinct, legal commander pairs.
        name_to_oracle = {
            "Tymna the Weaver": "oracle-tymna",
            "Kraum, Ludevic's Opus": "oracle-kraum",
            "Thrasios, Triton Hero": "oracle-thrasios",
        }
        tymna_kraum = build_oracle_group_key(
            ["Tymna the Weaver", "Kraum, Ludevic's Opus"], name_to_oracle
        )
        tymna_thrasios = build_oracle_group_key(
            ["Tymna the Weaver", "Thrasios, Triton Hero"], name_to_oracle
        )
        self.assertIsNotNone(tymna_kraum)
        self.assertIsNotNone(tymna_thrasios)
        self.assertNotEqual(tymna_kraum, tymna_thrasios)

    def test_row_with_any_unresolved_name_returns_none(self) -> None:
        # Partial resolution must not produce a group key at all, since matching
        # only the resolved half of a pair risks merging unrelated commanders.
        name_to_oracle = {"Tymna the Weaver": "oracle-tymna"}
        key = build_oracle_group_key(
            ["Tymna the Weaver", "Some Unmapped Card"], name_to_oracle
        )
        self.assertIsNone(key)

    def test_empty_commander_names_returns_none(self) -> None:
        self.assertIsNone(build_oracle_group_key([], {}))


class ChooseCanonicalCommanderTests(unittest.TestCase):
    """Tests for canonical-row selection during an oracle_id merge.

    Regression coverage for keeping an alias row (e.g. "Chief Jim Hopper") as
    canonical instead of its normalized target ("Sophina, Spearsage Deserter",
    per COMMANDER_NAME_ALIASES): a future ingestion run normalizes new entries
    straight to the canonical name, finds no row for it since it was deleted,
    and recreates the duplicate the sweep was meant to remove.
    """

    def test_prefers_already_normalized_row_over_alphabetically_first(self) -> None:
        group = [
            {
                "id": "alias-row",
                "name": "Chief Jim Hopper",
                "commander_names": ["Chief Jim Hopper"],
            },
            {
                "id": "canonical-row",
                "name": "Sophina, Spearsage Deserter",
                "commander_names": ["Sophina, Spearsage Deserter"],
            },
        ]
        chosen = choose_canonical_commander(group)
        self.assertEqual(chosen["id"], "canonical-row")

    def test_falls_back_to_first_row_when_none_are_normalized(self) -> None:
        # Neither row's stored name matches clean_commander_card_name's output
        # for itself (e.g. both are raw/unnormalized); there's no clearly-better
        # choice, so the first row (by the caller's sort order) is kept.
        group = [
            {"id": "row-a", "name": "Some Weird Name [Foo]", "commander_names": ["Urza"]},
            {"id": "row-b", "name": "Another Weird Name [Bar]", "commander_names": ["Urza"]},
        ]
        chosen = choose_canonical_commander(group)
        self.assertEqual(chosen["id"], "row-a")


if __name__ == "__main__":
    unittest.main()
