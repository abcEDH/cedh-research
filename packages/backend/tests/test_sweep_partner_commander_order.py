import collections
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
    requests_module.delete = Mock()
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

dateutil_module = types.ModuleType("dateutil")
dateutil_parser_module = types.ModuleType("dateutil.parser")
dateutil_parser_module.parse = lambda value: value
dateutil_module.parser = dateutil_parser_module
sys.modules.setdefault("dateutil", dateutil_module)
sys.modules.setdefault("dateutil.parser", dateutil_parser_module)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sweep_partner_commander_order import (  # noqa: E402
    build_arg_parser,
    canonical_pair_key,
    choose_target_order,
    current_pair_order,
    known_canonical_order,
)

# A real legal partner pair from data/legal_commander_pairings.json whose
# project_name equals its alphabetically-sorted name (i.e. it is covered by
# the legal pair order map but has no PARTNER_ORDER_OVERRIDES entry).
LEGAL_MAP_ONLY_PAIR = ("Abby, Merciless Soldier", "Ellie, Brick Master")

# A pair with a hardcoded PARTNER_ORDER_OVERRIDES entry that intentionally
# reverses alphabetical order.
OVERRIDE_PAIR_REVERSED = ("Kraum, Ludevic's Opus", "Tymna the Weaver")
OVERRIDE_PAIR_CANONICAL = ("Tymna the Weaver", "Kraum, Ludevic's Opus")


class CanonicalPairKeyTests(unittest.TestCase):
    def test_sorts_and_cleans_names(self) -> None:
        self.assertEqual(
            canonical_pair_key(["Tymna the Weaver", "Kraum, Ludevic\\'s Opus"]),
            canonical_pair_key(["Kraum, Ludevic's Opus", "Tymna the Weaver"]),
        )


class CurrentPairOrderTests(unittest.TestCase):
    def test_reads_commander_names_list(self) -> None:
        row = {"commander_names": ["Tymna the Weaver", "Kraum, Ludevic's Opus"]}
        self.assertEqual(current_pair_order(row), ("Tymna the Weaver", "Kraum, Ludevic's Opus"))

    def test_falls_back_to_slash_separated_name(self) -> None:
        row = {"name": "Tymna the Weaver / Kraum, Ludevic's Opus"}
        self.assertEqual(current_pair_order(row), ("Tymna the Weaver", "Kraum, Ludevic's Opus"))

    def test_returns_none_for_non_pair(self) -> None:
        self.assertIsNone(current_pair_order({"name": "K'rrik, Son of Yawgmoth"}))


class KnownCanonicalOrderTests(unittest.TestCase):
    def test_consults_legal_pair_order_map_even_without_an_override(self) -> None:
        # Regression test for issue #260: before this helper existed,
        # choose_target_order only checked PARTNER_ORDER_OVERRIDES, so a pair
        # covered solely by legal_commander_pairings.json's order map (like
        # this one) fell through to per-decklist observation instead of the
        # authoritative order ingest.normalize_partner_order would assign it.
        reversed_order = (LEGAL_MAP_ONLY_PAIR[1], LEGAL_MAP_ONLY_PAIR[0])
        self.assertEqual(known_canonical_order(reversed_order), LEGAL_MAP_ONLY_PAIR)
        self.assertEqual(known_canonical_order(LEGAL_MAP_ONLY_PAIR), LEGAL_MAP_ONLY_PAIR)

    def test_falls_back_to_partner_order_overrides(self) -> None:
        self.assertEqual(known_canonical_order(OVERRIDE_PAIR_REVERSED), OVERRIDE_PAIR_CANONICAL)
        self.assertEqual(known_canonical_order(OVERRIDE_PAIR_CANONICAL), OVERRIDE_PAIR_CANONICAL)

    def test_returns_none_for_pair_not_in_either_source(self) -> None:
        self.assertIsNone(known_canonical_order(("Nonexistent Commander A", "Nonexistent Commander B")))


class ChooseTargetOrderTests(unittest.TestCase):
    def test_prefers_legal_pair_order_map_over_observations(self) -> None:
        # Even if observation happened to favor the "wrong" (non-canonical)
        # order, the authoritative legal order map must win so the merge this
        # sweep performs can never disagree with what ingestion will assign
        # the pair the next time a new entry for it is ingested.
        reversed_order = (LEGAL_MAP_ONLY_PAIR[1], LEGAL_MAP_ONLY_PAIR[0])
        observations: collections.Counter[tuple[str, str]] = collections.Counter({reversed_order: 5})
        self.assertEqual(choose_target_order(reversed_order, observations), LEGAL_MAP_ONLY_PAIR)

    def test_falls_back_to_observation_when_no_known_order_exists(self) -> None:
        current_order = ("Nonexistent Commander B", "Nonexistent Commander A")
        observed = ("Nonexistent Commander A", "Nonexistent Commander B")
        observations: collections.Counter[tuple[str, str]] = collections.Counter({observed: 3})
        self.assertEqual(choose_target_order(current_order, observations), observed)

    def test_falls_back_to_current_order_when_no_observations_or_known_order(self) -> None:
        current_order = ("Nonexistent Commander B", "Nonexistent Commander A")
        self.assertEqual(choose_target_order(current_order, collections.Counter()), current_order)


class BuildArgParserTests(unittest.TestCase):
    def test_defaults(self) -> None:
        args = build_arg_parser().parse_args([])
        self.assertFalse(args.dry_run)
        self.assertEqual(args.sample_limit, 40)
        self.assertEqual(args.observation_limit, 10)
        self.assertEqual(args.report, "logs/sweep_partner_commander_order.csv")

    def test_dry_run_flag(self) -> None:
        args = build_arg_parser().parse_args(["--dry-run"])
        self.assertTrue(args.dry_run)


if __name__ == "__main__":
    unittest.main()
