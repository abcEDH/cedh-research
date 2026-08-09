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
    build_arg_parser,
    canonical_pair_key,
    choose_target_order,
    current_pair_order,
    main,
)


class CanonicalPairKeyTests(unittest.TestCase):
    def test_sorts_and_cleans_regardless_of_input_order(self) -> None:
        self.assertEqual(
            canonical_pair_key(["Tymna the Weaver", "Kraum, Ludevic's Opus"]),
            canonical_pair_key(["Kraum, Ludevic's Opus", "Tymna the Weaver"]),
        )


class CurrentPairOrderTests(unittest.TestCase):
    def test_reads_commander_names_array_when_present(self) -> None:
        row = {"name": "ignored", "commander_names": ["Abby, Merciless Soldier", "Ellie, Brick Master"]}
        self.assertEqual(
            current_pair_order(row),
            ("Abby, Merciless Soldier", "Ellie, Brick Master"),
        )

    def test_falls_back_to_parsing_slash_delimited_name(self) -> None:
        row = {"name": "Abby, Merciless Soldier / Ellie, Brick Master"}
        self.assertEqual(
            current_pair_order(row),
            ("Abby, Merciless Soldier", "Ellie, Brick Master"),
        )


class ChooseTargetOrderTests(unittest.TestCase):
    def test_prefers_legal_pairings_order_over_observed_majority_vote(self) -> None:
        # Regression test for #260. Before this fix, `choose_target_order`
        # never consulted `load_legal_commander_pair_order_map()` and fell
        # straight through to observation-based voting for any pair without
        # a hardcoded `PARTNER_ORDER_OVERRIDES` entry. If TopDeck decks for a
        # pair happened to mostly list it as "Ellie, Brick Master / Abby,
        # Merciless Soldier" (the *observed* order), the sweep would rename
        # the commander row to that order -- but ingest.py's
        # `sanitize_commander_payload` independently canonicalizes every new
        # entry for this pair to the legal-pairings ("project_name") order,
        # "Abby, Merciless Soldier / Ellie, Brick Master". The next ingested
        # entry would then create a brand new duplicate row under that name,
        # splitting the pair right back apart.
        current_order = ("Ellie, Brick Master", "Abby, Merciless Soldier")
        observations = collections.Counter({("Ellie, Brick Master", "Abby, Merciless Soldier"): 5})

        target_order = choose_target_order(current_order, observations)

        self.assertEqual(target_order, ("Abby, Merciless Soldier", "Ellie, Brick Master"))

    def test_hardcoded_override_still_wins_over_legal_pairings_order(self) -> None:
        current_order = ("Kraum, Ludevic's Opus", "Tymna the Weaver")

        target_order = choose_target_order(current_order, collections.Counter())

        self.assertEqual(target_order, ("Tymna the Weaver", "Kraum, Ludevic's Opus"))

    def test_falls_back_to_observed_majority_vote_for_pairs_without_static_order(self) -> None:
        # A pair absent from both PARTNER_ORDER_OVERRIDES and the generated
        # legal-pairings data file still needs *some* deterministic answer;
        # observed TopDeck deck ordering remains the fallback authority.
        current_order = ("Zzyzx Test Commander One", "Zzyzx Test Commander Two")
        observations = collections.Counter({("Zzyzx Test Commander Two", "Zzyzx Test Commander One"): 3})

        target_order = choose_target_order(current_order, observations)

        self.assertEqual(target_order, ("Zzyzx Test Commander Two", "Zzyzx Test Commander One"))

    def test_keeps_current_order_when_no_static_order_or_observations_exist(self) -> None:
        current_order = ("Zzyzx Test Commander One", "Zzyzx Test Commander Two")

        target_order = choose_target_order(current_order, collections.Counter())

        self.assertEqual(target_order, current_order)


class MainMergeOrchestrationTests(unittest.TestCase):
    """Regression test for the live-merge branch of main().

    ``commander_matchups`` has foreign keys from both ``commander_id`` and
    ``opponent_commander_id`` to ``commanders(id)``, so a duplicate commander
    row can only be deleted after *both* ``tournament_entries`` and
    ``commander_matchups`` have been repointed to the canonical row. Calling
    delete before repointing matchups raises a foreign-key violation in
    Postgres.
    """

    def test_repoints_tournament_entries_and_matchups_before_deleting_duplicate(self) -> None:
        canonical_row = {"id": "id-canonical", "name": "Alice / Bob", "commander_names": ["Alice", "Bob"]}
        duplicate_row = {"id": "id-dup", "name": "Bob / Alice", "commander_names": ["Bob", "Alice"]}
        mock_client = Mock()
        mock_client.select.return_value = [canonical_row, duplicate_row]

        call_order: list[str] = []

        def record(name):
            def _record(*_args, **_kwargs):
                call_order.append(name)

            return _record

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = str(Path(tmp_dir) / "report.csv")
            with (
                patch("sweep_partner_commander_order.load_credentials", return_value=("url", "key")),
                patch("sweep_partner_commander_order.SupabaseClient", return_value=mock_client),
                patch(
                    "sweep_partner_commander_order.load_legal_commander_pair_order_map",
                    return_value={canonical_pair_key(["Alice", "Bob"]): ("Alice", "Bob")},
                ),
                patch("sweep_partner_commander_order.PARTNER_ORDER_OVERRIDES", {}),
                patch(
                    "sweep_partner_commander_order.repoint_tournament_entries",
                    side_effect=record("repoint_tournament_entries"),
                ) as mock_repoint_entries,
                patch(
                    "sweep_partner_commander_order.repoint_commander_matchups",
                    side_effect=record("repoint_commander_matchups"),
                ) as mock_repoint_matchups,
                patch(
                    "sweep_partner_commander_order.delete_commander_row",
                    side_effect=record("delete_commander_row"),
                ) as mock_delete,
                patch("sweep_partner_commander_order.update_commander_row") as mock_update,
                patch("sys.argv", ["sweep_partner_commander_order.py", "--report", report_path]),
            ):
                main()

        mock_repoint_entries.assert_called_once_with(mock_client, "id-dup", "id-canonical")
        mock_repoint_matchups.assert_called_once_with(mock_client, "id-dup", "id-canonical")
        mock_delete.assert_called_once_with(mock_client, "id-dup")
        mock_update.assert_not_called()
        self.assertEqual(
            call_order,
            ["repoint_tournament_entries", "repoint_commander_matchups", "delete_commander_row"],
        )


class BuildArgParserTests(unittest.TestCase):
    def test_defaults(self) -> None:
        args = build_arg_parser().parse_args([])
        self.assertFalse(args.dry_run)
        self.assertEqual(args.sample_limit, 40)
        self.assertEqual(args.observation_limit, 10)
        self.assertEqual(args.report, "logs/sweep_partner_commander_order_20260409.csv")

    def test_dry_run_flag(self) -> None:
        args = build_arg_parser().parse_args(["--dry-run"])
        self.assertTrue(args.dry_run)


if __name__ == "__main__":
    unittest.main()
