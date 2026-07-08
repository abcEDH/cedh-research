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

import sweep_partner_commander_order  # noqa: E402
from sweep_ub_alt_name_commander_dedup import (  # noqa: E402
    build_arg_parser,
    fetch_commander_rows,
    merge_duplicate_group,
    run_sweep,
)

UB_ALT_NAME_ORACLE_ID = "11111111-1111-1111-1111-111111111111"

TRUE_PRINTING = {
    "name": "Nadier, Agent of the Duskenel",
    "oracle_id": UB_ALT_NAME_ORACLE_ID,
    "legalities": {"commander": "legal"},
}

UB_ALT_NAME_PRINTING = {
    "name": "Nadier, Agent of the Duskenel",
    "flavor_name": "Totally Radical Skater",
    "oracle_id": UB_ALT_NAME_ORACLE_ID,
    "legalities": {"commander": "legal"},
}

CARD_FIXTURE = [TRUE_PRINTING, UB_ALT_NAME_PRINTING]

TRUE_ROW = {
    "id": "true-id",
    "name": "Nadier, Agent of the Duskenel",
    "commander_names": ["Nadier, Agent of the Duskenel"],
}
ALT_ROW = {"id": "alt-id", "name": "Totally Radical Skater", "commander_names": ["Totally Radical Skater"]}
UNRELATED_ROW = {"id": "unrelated-id", "name": "Tymna the Weaver", "commander_names": ["Tymna the Weaver"]}


def make_fake_client(commander_rows: list[dict]) -> Mock:
    client = Mock()
    client.url = "https://example.supabase.co"
    client.headers = {"apikey": "test"}
    client.select = Mock(return_value=commander_rows)
    return client


class FetchCommanderRowsTests(unittest.TestCase):
    def test_selects_expected_columns_and_limit(self) -> None:
        client = make_fake_client([TRUE_ROW])
        rows = fetch_commander_rows(client, 500)

        client.select.assert_called_once_with(
            "commanders",
            {"select": "id,name,commander_names", "limit": 500, "order": "name.asc"},
        )
        self.assertEqual(rows, [TRUE_ROW])


class MergeDuplicateGroupTests(unittest.TestCase):
    def test_dry_run_does_not_call_repoint_or_delete(self) -> None:
        client = make_fake_client([])
        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            canonical, duplicates = merge_duplicate_group(
                client,
                (UB_ALT_NAME_ORACLE_ID,),
                [ALT_ROW, TRUE_ROW],
                {"Nadier, Agent of the Duskenel"},
                dry_run=True,
            )

        mock_requests.patch.assert_not_called()
        mock_requests.delete.assert_not_called()
        self.assertEqual(canonical["id"], "true-id")
        self.assertEqual([row["id"] for row in duplicates], ["alt-id"])

    def test_live_run_repoints_entries_then_deletes_duplicate_row(self) -> None:
        client = make_fake_client([])
        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            mock_requests.patch.return_value = Mock(raise_for_status=Mock())
            mock_requests.delete.return_value = Mock(raise_for_status=Mock())

            canonical, duplicates = merge_duplicate_group(
                client,
                (UB_ALT_NAME_ORACLE_ID,),
                [ALT_ROW, TRUE_ROW],
                {"Nadier, Agent of the Duskenel"},
                dry_run=False,
            )

            # First patch call repoints tournament_entries; the
            # commander_matchups repoints (covered in detail by the test
            # below) follow before the delete.
            patch_call = mock_requests.patch.call_args_list[0]
            self.assertEqual(patch_call.kwargs["params"], {"commander_id": "eq.alt-id"})
            self.assertEqual(patch_call.kwargs["json"], {"commander_id": "true-id"})

            delete_call = mock_requests.delete.call_args
            self.assertEqual(delete_call.kwargs["params"], {"id": "eq.alt-id"})

        self.assertEqual(canonical["id"], "true-id")
        self.assertEqual([row["id"] for row in duplicates], ["alt-id"])

    def test_live_run_repoints_commander_matchups_on_both_fk_columns_before_delete(self) -> None:
        # Regression test: `commander_matchups` has foreign keys from both
        # `commander_id` and `opponent_commander_id` to `commanders`. If the
        # duplicate row being merged away has matchup rows on either side,
        # deleting it without repointing those columns first raises a
        # Postgres FK violation. Assert both columns get repointed, in order,
        # before the delete call is made.
        client = make_fake_client([])
        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            mock_requests.patch.return_value = Mock(raise_for_status=Mock())
            mock_requests.delete.return_value = Mock(raise_for_status=Mock())

            canonical, duplicates = merge_duplicate_group(
                client,
                (UB_ALT_NAME_ORACLE_ID,),
                [ALT_ROW, TRUE_ROW],
                {"Nadier, Agent of the Duskenel"},
                dry_run=False,
            )

            self.assertEqual(mock_requests.patch.call_count, 3)
            tournament_entries_call, commander_id_call, opponent_commander_id_call = (
                mock_requests.patch.call_args_list
            )

            self.assertIn("tournament_entries", tournament_entries_call.args[0])
            self.assertEqual(tournament_entries_call.kwargs["params"], {"commander_id": "eq.alt-id"})
            self.assertEqual(tournament_entries_call.kwargs["json"], {"commander_id": "true-id"})

            self.assertIn("commander_matchups", commander_id_call.args[0])
            self.assertEqual(commander_id_call.kwargs["params"], {"commander_id": "eq.alt-id"})
            self.assertEqual(commander_id_call.kwargs["json"], {"commander_id": "true-id"})

            self.assertIn("commander_matchups", opponent_commander_id_call.args[0])
            self.assertEqual(
                opponent_commander_id_call.kwargs["params"], {"opponent_commander_id": "eq.alt-id"}
            )
            self.assertEqual(
                opponent_commander_id_call.kwargs["json"], {"opponent_commander_id": "true-id"}
            )

            # The delete must only fire after every repoint call above.
            delete_call = mock_requests.delete.call_args
            self.assertEqual(delete_call.kwargs["params"], {"id": "eq.alt-id"})

        self.assertEqual(canonical["id"], "true-id")
        self.assertEqual([row["id"] for row in duplicates], ["alt-id"])

    def test_repoint_failure_prevents_delete(self) -> None:
        # If a repoint call fails (e.g. a transient network error), the
        # duplicate commander row must not be deleted, so a retry can safely
        # pick up where the sweep left off instead of failing on an FK
        # violation against already-repointed rows.
        client = make_fake_client([])
        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            mock_requests.patch.return_value = Mock(raise_for_status=Mock(side_effect=RuntimeError("boom")))

            with self.assertRaises(RuntimeError):
                merge_duplicate_group(
                    client,
                    (UB_ALT_NAME_ORACLE_ID,),
                    [ALT_ROW, TRUE_ROW],
                    {"Nadier, Agent of the Duskenel"},
                    dry_run=False,
                )

            mock_requests.delete.assert_not_called()


class RunSweepTests(unittest.TestCase):
    def test_dry_run_reports_merge_without_mutating(self) -> None:
        client = make_fake_client([TRUE_ROW, ALT_ROW, UNRELATED_ROW])

        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            report_lines = run_sweep(client, CARD_FIXTURE, commander_limit=5000, dry_run=True)

        mock_requests.patch.assert_not_called()
        mock_requests.delete.assert_not_called()
        self.assertEqual(len(report_lines), 2)  # header + one merged duplicate
        self.assertIn("alt-id", report_lines[1])
        self.assertIn("true-id", report_lines[1])
        self.assertTrue(report_lines[1].endswith(",no"))

    def test_live_run_merges_and_reports_yes(self) -> None:
        client = make_fake_client([TRUE_ROW, ALT_ROW, UNRELATED_ROW])

        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            mock_requests.patch.return_value = Mock(raise_for_status=Mock())
            mock_requests.delete.return_value = Mock(raise_for_status=Mock())

            report_lines = run_sweep(client, CARD_FIXTURE, commander_limit=5000, dry_run=False)

            # One patch for tournament_entries.commander_id, plus two for
            # commander_matchups (commander_id and opponent_commander_id).
            self.assertEqual(mock_requests.patch.call_count, 3)
            self.assertEqual(mock_requests.delete.call_count, 1)

        self.assertEqual(len(report_lines), 2)
        self.assertTrue(report_lines[1].endswith(",yes"))

    def test_no_duplicates_produces_header_only_report(self) -> None:
        client = make_fake_client([TRUE_ROW, UNRELATED_ROW])

        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            report_lines = run_sweep(client, CARD_FIXTURE, commander_limit=5000, dry_run=True)

        mock_requests.patch.assert_not_called()
        mock_requests.delete.assert_not_called()
        self.assertEqual(len(report_lines), 1)


class BuildArgParserTests(unittest.TestCase):
    def test_defaults(self) -> None:
        args = build_arg_parser().parse_args([])
        self.assertFalse(args.dry_run)
        self.assertEqual(args.commander_limit, 5000)
        self.assertEqual(args.report, "logs/sweep_ub_alt_name_commander_dedup.csv")

    def test_dry_run_flag(self) -> None:
        args = build_arg_parser().parse_args(["--dry-run"])
        self.assertTrue(args.dry_run)


if __name__ == "__main__":
    unittest.main()
