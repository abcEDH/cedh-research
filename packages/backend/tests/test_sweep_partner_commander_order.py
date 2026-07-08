import collections
import unittest
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch


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
    requests_module.RequestException = Exception
    sys.modules["requests"] = requests_module

dateutil_module = types.ModuleType("dateutil")
dateutil_parser_module = types.ModuleType("dateutil.parser")
dateutil_parser_module.parse = lambda value: value
dateutil_module.parser = dateutil_parser_module
sys.modules.setdefault("dateutil", dateutil_module)
sys.modules.setdefault("dateutil.parser", dateutil_parser_module)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sweep_partner_commander_order import (  # noqa: E402
    canonical_pair_key,
    choose_target_order,
    current_pair_order,
    resolve_authoritative_order,
)


class CanonicalPairKeyTests(unittest.TestCase):
    def test_order_independent_for_reversed_pair(self) -> None:
        self.assertEqual(
            canonical_pair_key(["Beta Commander", "Alpha Commander"]),
            canonical_pair_key(["Alpha Commander", "Beta Commander"]),
        )

    def test_current_pair_order_agrees_across_storage_shapes(self) -> None:
        """Rows stored via `commander_names` or a `name` string must resolve
        to the same canonical pair key regardless of which order the raw data
        happens to preserve — this is what lets the sweep recognize two
        differently-ordered rows as the same underlying partner pair."""
        row_ab = {"commander_names": ["Alpha Commander", "Beta Commander"]}
        row_ba = {"name": "Beta Commander / Alpha Commander"}

        self.assertEqual(
            canonical_pair_key(list(current_pair_order(row_ab))),
            canonical_pair_key(list(current_pair_order(row_ba))),
        )


class ChooseTargetOrderTests(unittest.TestCase):
    """Regression coverage for #260.

    Before this fix, `choose_target_order()` only consulted the small
    hand-maintained `PARTNER_ORDER_OVERRIDES` table before falling back to
    observed decklist orderings. It never checked the much larger
    Scryfall-derived `legal_commander_pairings.json` order map that
    `ingest.py`'s `normalize_partner_order()` uses at write time. That gap
    meant the sweep could leave (or re-choose) an order that disagreed with
    what fresh ingestion would assign to the very same pair, so the pair
    would split into two rows again on the next ingest.
    """

    @patch("sweep_partner_commander_order.load_legal_commander_pair_order_map")
    def test_prefers_legal_pair_order_over_raw_current_order(self, mock_legal_map: Mock) -> None:
        mock_legal_map.return_value = {
            ("Alpha Commander", "Beta Commander"): ("Beta Commander", "Alpha Commander"),
        }

        result = choose_target_order(("Alpha Commander", "Beta Commander"), collections.Counter())

        self.assertEqual(result, ("Beta Commander", "Alpha Commander"))

    @patch("sweep_partner_commander_order.load_legal_commander_pair_order_map")
    def test_legal_pair_order_wins_over_conflicting_observations(self, mock_legal_map: Mock) -> None:
        mock_legal_map.return_value = {
            ("Alpha Commander", "Beta Commander"): ("Beta Commander", "Alpha Commander"),
        }
        # Observed decklists overwhelmingly show the *other* order, but the
        # authoritative legal-pairings order must still win so the sweep
        # agrees with what ingest.py would compute for this pair.
        observations = collections.Counter({("Alpha Commander", "Beta Commander"): 5})

        result = choose_target_order(("Alpha Commander", "Beta Commander"), observations)

        self.assertEqual(result, ("Beta Commander", "Alpha Commander"))

    @patch("sweep_partner_commander_order.load_legal_commander_pair_order_map")
    def test_falls_back_to_manual_override_when_no_legal_pair_entry(self, mock_legal_map: Mock) -> None:
        mock_legal_map.return_value = {}

        result = choose_target_order(
            ("Kraum, Ludevic's Opus", "Tymna the Weaver"), collections.Counter()
        )

        self.assertEqual(result, ("Tymna the Weaver", "Kraum, Ludevic's Opus"))

    @patch("sweep_partner_commander_order.load_legal_commander_pair_order_map")
    def test_falls_back_to_observations_when_pair_is_unlisted(self, mock_legal_map: Mock) -> None:
        mock_legal_map.return_value = {}
        observations = collections.Counter({("Gamma Commander", "Delta Commander"): 3})

        result = choose_target_order(("Delta Commander", "Gamma Commander"), observations)

        self.assertEqual(result, ("Gamma Commander", "Delta Commander"))

    @patch("sweep_partner_commander_order.load_legal_commander_pair_order_map")
    def test_keeps_current_order_with_no_authoritative_source_or_observations(
        self, mock_legal_map: Mock
    ) -> None:
        mock_legal_map.return_value = {}

        result = choose_target_order(("Delta Commander", "Gamma Commander"), collections.Counter())

        self.assertEqual(result, ("Delta Commander", "Gamma Commander"))


class ResolveAuthoritativeOrderTests(unittest.TestCase):
    @patch("sweep_partner_commander_order.load_legal_commander_pair_order_map")
    def test_returns_none_when_pair_unknown(self, mock_legal_map: Mock) -> None:
        mock_legal_map.return_value = {}

        result = resolve_authoritative_order(("Gamma Commander", "Delta Commander"))

        self.assertIsNone(result)

    @patch("sweep_partner_commander_order.load_legal_commander_pair_order_map")
    def test_is_order_independent_on_input(self, mock_legal_map: Mock) -> None:
        mock_legal_map.return_value = {
            ("Alpha Commander", "Beta Commander"): ("Beta Commander", "Alpha Commander"),
        }

        forward = resolve_authoritative_order(("Alpha Commander", "Beta Commander"))
        reversed_order = resolve_authoritative_order(("Beta Commander", "Alpha Commander"))

        self.assertEqual(forward, reversed_order)
        self.assertEqual(forward, ("Beta Commander", "Alpha Commander"))


if __name__ == "__main__":
    unittest.main()
