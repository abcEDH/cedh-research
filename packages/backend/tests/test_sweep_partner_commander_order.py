import collections
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

import sweep_partner_commander_order as sweep  # noqa: E402

ABBY = "Abby, Merciless Soldier"
ELLIE = "Ellie, Brick Master"
ABBY_ELLIE_CANONICAL = (ABBY, ELLIE)  # matches legal_commander_pairings.json's project_name order


class ChooseTargetOrderLegalMapTests(unittest.TestCase):
    def test_legal_pair_map_fixes_a_stale_row_when_no_observations_are_available(self) -> None:
        # Regression for issue #260: previously, choose_target_order only
        # consulted the small hand-maintained PARTNER_ORDER_OVERRIDES dict.
        # Any *other* legal pair stored under the wrong order (e.g. from
        # before this pair's canonical order was known) was left broken
        # forever whenever scraped observations were unavailable -- a common
        # case (dead decklist links, unresolved Moxfield URLs) -- because the
        # old code fell straight back to "keep current_order" with nothing
        # else to consult.
        stale_order = (ELLIE, ABBY)  # wrong order, as if written before the pair was known
        no_observations: collections.Counter = collections.Counter()

        target = sweep.choose_target_order(stale_order, no_observations)

        self.assertEqual(target, ABBY_ELLIE_CANONICAL)

    def test_legal_pair_map_takes_priority_over_hand_maintained_overrides(self) -> None:
        # Isolate the priority ordering itself: ingest.normalize_partner_order
        # always checks the generated legal-pairings map before
        # PARTNER_ORDER_OVERRIDES, so the sweep must agree, or the two would
        # disagree about which row is "canonical" for the same pair.
        pair_key = sweep.canonical_pair_key([ABBY, ELLIE])
        with patch.object(
            sweep,
            "load_legal_commander_pair_order_map",
            return_value={pair_key: (ELLIE, ABBY)},
        ):
            with patch.object(sweep, "PARTNER_ORDER_OVERRIDES", {pair_key: (ABBY, ELLIE)}):
                target = sweep.choose_target_order((ABBY, ELLIE), collections.Counter())

        self.assertEqual(target, (ELLIE, ABBY))

    def test_falls_back_to_overrides_when_pair_is_not_in_the_legal_map(self) -> None:
        pair_key = ("Made", "Up-Pair")
        with patch.object(sweep, "load_legal_commander_pair_order_map", return_value={}):
            with patch.object(sweep, "PARTNER_ORDER_OVERRIDES", {pair_key: ("Up-Pair", "Made")}):
                target = sweep.choose_target_order(("Made", "Up-Pair"), collections.Counter())

        self.assertEqual(target, ("Up-Pair", "Made"))

    def test_falls_back_to_observations_when_pair_is_in_neither_static_source(self) -> None:
        with patch.object(sweep, "load_legal_commander_pair_order_map", return_value={}):
            with patch.object(sweep, "PARTNER_ORDER_OVERRIDES", {}):
                observations = collections.Counter({("B", "A"): 3, ("A", "B"): 1})
                target = sweep.choose_target_order(("A", "B"), observations)

        self.assertEqual(target, ("B", "A"))

    def test_falls_back_to_current_order_when_nothing_else_is_known(self) -> None:
        with patch.object(sweep, "load_legal_commander_pair_order_map", return_value={}):
            with patch.object(sweep, "PARTNER_ORDER_OVERRIDES", {}):
                target = sweep.choose_target_order(("A", "B"), collections.Counter())

        self.assertEqual(target, ("A", "B"))


class CanonicalPairKeyTests(unittest.TestCase):
    def test_order_independent(self) -> None:
        self.assertEqual(
            sweep.canonical_pair_key([ELLIE, ABBY]),
            sweep.canonical_pair_key([ABBY, ELLIE]),
        )


class CurrentPairOrderTests(unittest.TestCase):
    def test_reads_commander_names_array_first(self) -> None:
        row = {"name": "irrelevant", "commander_names": [ELLIE, ABBY]}
        self.assertEqual(sweep.current_pair_order(row), (ELLIE, ABBY))

    def test_falls_back_to_parsing_the_display_name(self) -> None:
        row = {"name": f"{ELLIE} / {ABBY}", "commander_names": []}
        self.assertEqual(sweep.current_pair_order(row), (ELLIE, ABBY))

    def test_returns_none_for_a_single_commander_row(self) -> None:
        row = {"name": ABBY, "commander_names": [ABBY]}
        self.assertIsNone(sweep.current_pair_order(row))


if __name__ == "__main__":
    unittest.main()
