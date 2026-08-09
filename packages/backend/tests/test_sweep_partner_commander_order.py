import collections
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    import requests as requests_module
except ModuleNotFoundError:
    requests_module = types.ModuleType("requests")
    requests_module.get = types.SimpleNamespace()
    requests_module.post = types.SimpleNamespace()
    requests_module.patch = types.SimpleNamespace()
    requests_module.delete = types.SimpleNamespace()
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

import sweep_partner_commander_order  # noqa: E402
from sweep_partner_commander_order import choose_target_order, main  # noqa: E402


class ChooseTargetOrderTests(unittest.TestCase):
    """PR #302: ``choose_target_order`` must consult
    ``load_legal_commander_pair_order_map()`` *before* ``PARTNER_ORDER_OVERRIDES``,
    matching ``ingest.py``'s ``normalize_partner_order()`` priority order.
    Skipping the legal-pairing map (as the pre-PR code did) let the sweep pick an
    order that disagreed with what ingestion would write for the same pair,
    re-splitting it on the next tournament import.
    """

    def test_legal_pair_order_takes_precedence_over_override(self) -> None:
        """A pair present in both the legal map and PARTNER_ORDER_OVERRIDES must
        return the legal map's order -- that's what ``ingest.py`` will write on
        the next ingestion, so the sweep must agree to avoid re-splitting.
        """
        pair_a = "Alpha, Test Commander"
        pair_b = "Beta, Test Partner"
        pair_key = tuple(sorted([pair_a, pair_b]))
        legal_order = (pair_a, pair_b)  # legal map says A first
        override_order = (pair_b, pair_a)  # override says B first (conflicts)

        with (
            patch.object(
                sweep_partner_commander_order,
                "load_legal_commander_pair_order_map",
                return_value={pair_key: legal_order},
            ),
            patch.object(
                sweep_partner_commander_order,
                "PARTNER_ORDER_OVERRIDES",
                {pair_key: override_order},
            ),
        ):
            result = choose_target_order((pair_b, pair_a), collections.Counter())

        self.assertEqual(result, legal_order)

    def test_legal_pair_order_takes_precedence_over_observations(self) -> None:
        """Even when observed decklist orders point the other way, a pair in
        the legal map must return the legal map's order -- no observation
        needed.
        """
        pair_a = "Alpha, Test Commander"
        pair_b = "Beta, Test Partner"
        pair_key = tuple(sorted([pair_a, pair_b]))
        legal_order = (pair_a, pair_b)

        observations = collections.Counter({(pair_b, pair_a): 10, (pair_a, pair_b): 1})

        with (
            patch.object(
                sweep_partner_commander_order,
                "load_legal_commander_pair_order_map",
                return_value={pair_key: legal_order},
            ),
            patch.object(
                sweep_partner_commander_order,
                "PARTNER_ORDER_OVERRIDES",
                {},
            ),
        ):
            result = choose_target_order((pair_b, pair_a), observations)

        self.assertEqual(result, legal_order)

    def test_override_used_when_pair_absent_from_legal_map(self) -> None:
        """Falls through to ``PARTNER_ORDER_OVERRIDES`` for pairs the legal map
        doesn't cover -- the second tier of the priority order.
        """
        pair_a = "Alpha, Test Commander"
        pair_b = "Beta, Test Partner"
        pair_key = tuple(sorted([pair_a, pair_b]))
        override_order = (pair_b, pair_a)

        with (
            patch.object(
                sweep_partner_commander_order,
                "load_legal_commander_pair_order_map",
                return_value={},
            ),
            patch.object(
                sweep_partner_commander_order,
                "PARTNER_ORDER_OVERRIDES",
                {pair_key: override_order},
            ),
        ):
            result = choose_target_order((pair_a, pair_b), collections.Counter())

        self.assertEqual(result, override_order)

    def test_observations_used_when_neither_legal_map_nor_override_knows_pair(self) -> None:
        """The pre-existing fallback -- observed decklist orders -- still
        applies for pairs neither authoritative source knows about.
        """
        pair_a = "Alpha, Test Commander"
        pair_b = "Beta, Test Partner"

        observations = collections.Counter({(pair_b, pair_a): 10, (pair_a, pair_b): 1})

        with (
            patch.object(
                sweep_partner_commander_order,
                "load_legal_commander_pair_order_map",
                return_value={},
            ),
            patch.object(
                sweep_partner_commander_order,
                "PARTNER_ORDER_OVERRIDES",
                {},
            ),
        ):
            result = choose_target_order((pair_a, pair_b), observations)

        # ``current_order`` isn't the top-observed one, so the function falls
        # back to the alphabetically-first of the tied top orders. There's only
        # one top order here -- (pair_b, pair_a) with count 10 -- so that's
        # what's returned (``sorted`` over a single-element list is a no-op on
        # the contents; it sorts the list of tuples, not the tuple's elements).
        self.assertEqual(result, (pair_b, pair_a))


class MergeForeignKeySafetyTests(unittest.TestCase):
    """``main()``'s merge branch must repoint ``commander_matchups`` before deleting.

    ``repoint_commander_matchups()`` was defined but never called: the merge
    path went straight from ``repoint_tournament_entries()`` to
    ``delete_commander_row()``. ``commander_matchups`` holds two foreign keys
    to ``commanders(id)`` -- ``commander_id`` and ``opponent_commander_id`` --
    so deleting a duplicate that still had matchup rows raised a Postgres
    foreign-key violation, aborting the sweep and leaving that pair and every
    later one in the run unmerged.
    """

    PAIR_A = "Alpha, Test Commander"
    PAIR_B = "Beta, Test Partner"

    def _run_main(self) -> None:
        canonical_name = f"{self.PAIR_A} / {self.PAIR_B}"
        duplicate_name = f"{self.PAIR_B} / {self.PAIR_A}"
        commander_rows = [
            {"id": "canonical-id", "name": canonical_name, "commander_names": [self.PAIR_A, self.PAIR_B]},
            {"id": "duplicate-id", "name": duplicate_name, "commander_names": [self.PAIR_B, self.PAIR_A]},
        ]
        client = Mock()
        client.url = "https://example.supabase.co"
        client.headers = {"apikey": "test"}
        client.select = Mock(return_value=commander_rows)

        pair_key = tuple(sorted((self.PAIR_A, self.PAIR_B)))
        with tempfile.TemporaryDirectory() as tmpdir:
            argv = ["sweep_partner_commander_order.py", "--report", str(Path(tmpdir) / "report.csv")]
            with (
                patch.object(sweep_partner_commander_order, "load_credentials", return_value=("url", "key")),
                patch.object(sweep_partner_commander_order, "SupabaseClient", return_value=client),
                patch.object(
                    sweep_partner_commander_order,
                    "load_legal_commander_pair_order_map",
                    return_value={pair_key: (self.PAIR_A, self.PAIR_B)},
                ),
                patch.object(sys, "argv", argv),
            ):
                main()

    def test_merge_repoints_both_matchup_columns_before_delete(self) -> None:
        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            mock_requests.patch.return_value = Mock(raise_for_status=Mock())
            mock_requests.delete.return_value = Mock(raise_for_status=Mock())

            self._run_main()

            # tournament_entries.commander_id, then commander_matchups.commander_id,
            # then commander_matchups.opponent_commander_id -- all before the delete.
            self.assertEqual(mock_requests.patch.call_count, 3)
            entries_call, commander_id_call, opponent_id_call = mock_requests.patch.call_args_list

            self.assertIn("tournament_entries", entries_call.args[0])
            self.assertEqual(entries_call.kwargs["params"], {"commander_id": "eq.duplicate-id"})
            self.assertEqual(entries_call.kwargs["json"], {"commander_id": "canonical-id"})

            self.assertIn("commander_matchups", commander_id_call.args[0])
            self.assertEqual(commander_id_call.kwargs["params"], {"commander_id": "eq.duplicate-id"})
            self.assertEqual(commander_id_call.kwargs["json"], {"commander_id": "canonical-id"})

            self.assertIn("commander_matchups", opponent_id_call.args[0])
            self.assertEqual(opponent_id_call.kwargs["params"], {"opponent_commander_id": "eq.duplicate-id"})
            self.assertEqual(opponent_id_call.kwargs["json"], {"opponent_commander_id": "canonical-id"})

            self.assertEqual(mock_requests.delete.call_args.kwargs["params"], {"id": "eq.duplicate-id"})

    def test_repoint_failure_prevents_delete(self) -> None:
        """A failed repoint must abort before the delete -- deleting anyway would
        orphan the matchup rows the repoint was supposed to move.
        """
        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            mock_requests.patch.return_value = Mock(raise_for_status=Mock(side_effect=RuntimeError("boom")))

            with self.assertRaises(RuntimeError):
                self._run_main()

            mock_requests.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
