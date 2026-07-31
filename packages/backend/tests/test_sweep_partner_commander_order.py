"""Regression tests for #260: partner-commander "A, B" vs "B, A" dedup.

Root cause: ``choose_target_order()`` only consulted ``PARTNER_ORDER_OVERRIDES``
(~26 hand-maintained entries) before falling back to per-run TopDeck deck-page
observation. ``ingest.py``'s ``normalize_partner_order()`` -- the function that
decides display order for *every future* partner-pair write -- checks the
generated legal-pair order map first (~3,100 pairs) and only falls back to
``PARTNER_ORDER_OVERRIDES`` after that. Because the sweep never consulted the
legal-pair order map, it could pick a different order than fresh ingestion for
the same pair, so a pair "fixed" by the sweep would re-split the next time it
was ingested. These tests prove both name orderings now collapse to the same
canonical order via the same source ingestion uses.
"""

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

from ingest import normalize_partner_order  # noqa: E402
from sweep_partner_commander_order import (  # noqa: E402
    canonical_pair_key,
    choose_target_order,
    current_pair_order,
)

# A legal partner pair with no PARTNER_ORDER_OVERRIDES entry -- its canonical
# order comes solely from the generated legal-pair order map (alphabetical
# for this pair).
NEW_PAIR_LEFT = "Abby, Merciless Soldier"
NEW_PAIR_RIGHT = "Ellie, Brick Master"

# A pair with an explicit PARTNER_ORDER_OVERRIDES entry (non-alphabetical
# display order).
OVERRIDE_PAIR_A = "Kraum, Ludevic's Opus"
OVERRIDE_PAIR_B = "Tymna the Weaver"
OVERRIDE_TARGET = ("Tymna the Weaver", "Kraum, Ludevic's Opus")


class ChooseTargetOrderLegalPairMapTests(unittest.TestCase):
    """Pairs covered by the generated legal-pair order map."""

    def test_dedupes_both_input_orderings_to_the_same_order(self) -> None:
        forward = choose_target_order((NEW_PAIR_LEFT, NEW_PAIR_RIGHT), collections.Counter())
        reverse = choose_target_order((NEW_PAIR_RIGHT, NEW_PAIR_LEFT), collections.Counter())
        self.assertEqual(forward, reverse)

    def test_matches_what_ingestion_would_produce_for_a_new_row(self) -> None:
        # This is the crux of the bug: whatever the sweep decides for an
        # *existing* duplicate row must equal what ingest.py's
        # normalize_partner_order() decides for a *newly ingested* row of the
        # same pair, or the two will drift apart again.
        target = choose_target_order((NEW_PAIR_RIGHT, NEW_PAIR_LEFT), collections.Counter())
        self.assertEqual(target, tuple(normalize_partner_order([NEW_PAIR_LEFT, NEW_PAIR_RIGHT])))
        self.assertEqual(target, (NEW_PAIR_LEFT, NEW_PAIR_RIGHT))

    def test_prefers_legal_pair_map_over_conflicting_observations(self) -> None:
        # Even if TopDeck deck pages were observed writing the pair
        # "backwards" most often, the sweep must still converge on the same
        # order ingestion uses -- observation only breaks ties for pairs with
        # no canonical source at all.
        misleading_observations = collections.Counter({(NEW_PAIR_RIGHT, NEW_PAIR_LEFT): 5})
        target = choose_target_order((NEW_PAIR_LEFT, NEW_PAIR_RIGHT), misleading_observations)
        self.assertEqual(target, (NEW_PAIR_LEFT, NEW_PAIR_RIGHT))


class ChooseTargetOrderOverrideTests(unittest.TestCase):
    """Pairs covered by PARTNER_ORDER_OVERRIDES."""

    def test_dedupes_both_input_orderings_to_the_override_order(self) -> None:
        forward = choose_target_order((OVERRIDE_PAIR_A, OVERRIDE_PAIR_B), collections.Counter())
        reverse = choose_target_order((OVERRIDE_PAIR_B, OVERRIDE_PAIR_A), collections.Counter())
        self.assertEqual(forward, OVERRIDE_TARGET)
        self.assertEqual(reverse, OVERRIDE_TARGET)


class ChooseTargetOrderObservationFallbackTests(unittest.TestCase):
    """Pairs with neither a legal-pair-map nor an overrides entry still fall
    back to the historical TopDeck-observation heuristic."""

    def test_falls_back_to_observed_majority_order_when_no_canonical_source(self) -> None:
        current_order = ("Zzyzx Unlisted Card One", "Zzyzx Unlisted Card Two")
        observations = collections.Counter(
            {
                ("Zzyzx Unlisted Card Two", "Zzyzx Unlisted Card One"): 3,
                current_order: 1,
            }
        )
        target = choose_target_order(current_order, observations)
        self.assertEqual(target, ("Zzyzx Unlisted Card Two", "Zzyzx Unlisted Card One"))

    def test_keeps_current_order_when_no_canonical_source_and_no_observations(self) -> None:
        current_order = ("Zzyzx Unlisted Card One", "Zzyzx Unlisted Card Two")
        target = choose_target_order(current_order, collections.Counter())
        self.assertEqual(target, current_order)


class CanonicalPairKeyTests(unittest.TestCase):
    def test_same_key_regardless_of_input_order(self) -> None:
        self.assertEqual(
            canonical_pair_key([NEW_PAIR_LEFT, NEW_PAIR_RIGHT]),
            canonical_pair_key([NEW_PAIR_RIGHT, NEW_PAIR_LEFT]),
        )


class CurrentPairOrderTests(unittest.TestCase):
    def test_reads_commander_names_array_when_present(self) -> None:
        row = {"name": f"{NEW_PAIR_RIGHT} / {NEW_PAIR_LEFT}", "commander_names": [NEW_PAIR_LEFT, NEW_PAIR_RIGHT]}
        self.assertEqual(current_pair_order(row), (NEW_PAIR_LEFT, NEW_PAIR_RIGHT))

    def test_falls_back_to_splitting_the_display_name(self) -> None:
        row = {"name": f"{NEW_PAIR_RIGHT} / {NEW_PAIR_LEFT}"}
        self.assertEqual(current_pair_order(row), (NEW_PAIR_RIGHT, NEW_PAIR_LEFT))


if __name__ == "__main__":
    unittest.main()
