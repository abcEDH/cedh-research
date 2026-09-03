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
from sweep_partner_commander_order import (  # noqa: E402
    choose_target_order,
    main,
    merge_commander_metadata,
)


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
        client.postgrest.base_url = "https://example.supabase.co/rest/v1"
        client.postgrest.headers = {"apikey": "test"}
        select_chain = client.table.return_value.select.return_value.order.return_value.limit.return_value
        select_chain.execute.return_value.data = commander_rows

        pair_key = tuple(sorted((self.PAIR_A, self.PAIR_B)))
        with tempfile.TemporaryDirectory() as tmpdir:
            argv = ["sweep_partner_commander_order.py", "--report", str(Path(tmpdir) / "report.csv")]
            with (
                patch.object(sweep_partner_commander_order, "load_credentials", return_value=("url", "key")),
                patch.object(sweep_partner_commander_order, "get_supabase_client", return_value=client),
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


class MergeCommanderMetadataTests(unittest.TestCase):
    """Issue #316: the merge branch discarded ``commanders``' five non-key
    columns (``scryfall_ids``, ``color_identity``, ``archetype``,
    ``win_condition``, ``notes``) outright when it deleted the duplicate row.
    ``merge_commander_metadata`` computes the patch that must land on the
    retained row first -- filling gaps from the duplicate, never overwriting
    a value the retained row already has.
    """

    def test_fills_every_gap_from_duplicate(self) -> None:
        retained = {
            "scryfall_ids": None,
            "color_identity": None,
            "archetype": None,
            "win_condition": None,
            "notes": None,
        }
        duplicate = {
            "scryfall_ids": ["abc123"],
            "color_identity": ["U", "B"],
            "archetype": "stax",
            "win_condition": "Thassa's Oracle combo",
            "notes": "Merged from duplicate row",
        }

        patch = merge_commander_metadata(retained, duplicate)

        self.assertEqual(
            patch,
            {
                "scryfall_ids": ["abc123"],
                "color_identity": ["U", "B"],
                "archetype": "stax",
                "win_condition": "Thassa's Oracle combo",
                "notes": "Merged from duplicate row",
            },
        )

    def test_never_overwrites_existing_non_null_value(self) -> None:
        retained = {
            "scryfall_ids": ["existing"],
            "color_identity": ["W"],
            "archetype": "midrange",
            "win_condition": "existing win con",
            "notes": "existing notes",
        }
        duplicate = {
            "scryfall_ids": ["dup"],
            "color_identity": ["U", "B"],
            "archetype": "stax",
            "win_condition": "dup win con",
            "notes": "dup notes",
        }

        patch = merge_commander_metadata(retained, duplicate)

        self.assertEqual(patch, {})

    def test_only_null_columns_are_patched_when_gaps_are_partial(self) -> None:
        retained = {
            "scryfall_ids": ["existing"],
            "color_identity": None,
            "archetype": "midrange",
            "win_condition": None,
            "notes": "existing notes",
        }
        duplicate = {
            "scryfall_ids": ["dup"],
            "color_identity": ["U", "B"],
            "archetype": "stax",
            "win_condition": "dup win con",
            "notes": "dup notes",
        }

        patch = merge_commander_metadata(retained, duplicate)

        self.assertEqual(patch, {"color_identity": ["U", "B"], "win_condition": "dup win con"})

    def test_duplicate_null_leaves_gap_unfilled(self) -> None:
        """Both sides null for a column is not itself a bug -- there's simply
        nothing to reconcile, and the patch must omit that column rather than
        writing null-over-null.
        """
        all_null = {
            "scryfall_ids": None,
            "color_identity": None,
            "archetype": None,
            "win_condition": None,
            "notes": None,
        }
        retained = dict(all_null)
        duplicate = dict(all_null)

        patch = merge_commander_metadata(retained, duplicate)

        self.assertEqual(patch, {})


class MergeReconcilesMetadataInMainTests(unittest.TestCase):
    """Issue #316, end-to-end: ``main()``'s merge branch must patch the
    retained row's metadata gaps before repointing FKs and deleting the
    duplicate -- otherwise the duplicate's metadata is gone the moment the
    delete commits.
    """

    PAIR_A = "Alpha, Test Commander"
    PAIR_B = "Beta, Test Partner"

    def _run_main(self, canonical_row: dict, duplicate_row: dict) -> None:
        commander_rows = [canonical_row, duplicate_row]
        client = Mock()
        client.postgrest.base_url = "https://example.supabase.co/rest/v1"
        client.postgrest.headers = {"apikey": "test"}
        select_chain = client.table.return_value.select.return_value.order.return_value.limit.return_value
        select_chain.execute.return_value.data = commander_rows

        pair_key = tuple(sorted((self.PAIR_A, self.PAIR_B)))
        with tempfile.TemporaryDirectory() as tmpdir:
            argv = ["sweep_partner_commander_order.py", "--report", str(Path(tmpdir) / "report.csv")]
            with (
                patch.object(sweep_partner_commander_order, "load_credentials", return_value=("url", "key")),
                patch.object(sweep_partner_commander_order, "get_supabase_client", return_value=client),
                patch.object(
                    sweep_partner_commander_order,
                    "load_legal_commander_pair_order_map",
                    return_value={pair_key: (self.PAIR_A, self.PAIR_B)},
                ),
                patch.object(sys, "argv", argv),
            ):
                main()

    def test_metadata_gaps_filled_before_delete_without_overwriting_existing(self) -> None:
        canonical_name = f"{self.PAIR_A} / {self.PAIR_B}"
        duplicate_name = f"{self.PAIR_B} / {self.PAIR_A}"
        canonical_row = {
            "id": "canonical-id",
            "name": canonical_name,
            "commander_names": [self.PAIR_A, self.PAIR_B],
            "scryfall_ids": None,
            "color_identity": ["W", "U"],  # already set -- must survive untouched
            "archetype": None,
            "win_condition": None,
            "notes": None,
        }
        duplicate_row = {
            "id": "duplicate-id",
            "name": duplicate_name,
            "commander_names": [self.PAIR_B, self.PAIR_A],
            "scryfall_ids": ["abc123"],
            "color_identity": ["U", "B"],  # conflicts with canonical -- must NOT overwrite
            "archetype": "stax",
            "win_condition": "combo",
            "notes": "from duplicate",
        }

        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            mock_requests.patch.return_value = Mock(raise_for_status=Mock())
            mock_requests.delete.return_value = Mock(raise_for_status=Mock())

            self._run_main(canonical_row, duplicate_row)

            # metadata patch, then tournament_entries, then the two matchup columns.
            self.assertEqual(mock_requests.patch.call_count, 4)
            metadata_call = mock_requests.patch.call_args_list[0]

            self.assertIn("commanders", metadata_call.args[0])
            self.assertEqual(metadata_call.kwargs["params"], {"id": "eq.canonical-id"})
            self.assertEqual(
                metadata_call.kwargs["json"],
                {
                    "scryfall_ids": ["abc123"],
                    "archetype": "stax",
                    "win_condition": "combo",
                    "notes": "from duplicate",
                },
            )
            # color_identity was already set on the canonical row -- never overwritten.
            self.assertNotIn("color_identity", metadata_call.kwargs["json"])

            entries_call, commander_id_call, opponent_id_call = mock_requests.patch.call_args_list[1:]
            self.assertIn("tournament_entries", entries_call.args[0])
            self.assertIn("commander_matchups", commander_id_call.args[0])
            self.assertIn("commander_matchups", opponent_id_call.args[0])

            self.assertEqual(mock_requests.delete.call_args.kwargs["params"], {"id": "eq.duplicate-id"})

    def test_no_metadata_patch_call_when_duplicate_has_nothing_to_offer(self) -> None:
        """Preserves the pre-#316 request count when there's no metadata gap to
        fill, so this change doesn't add a network round-trip to the common case.
        """
        canonical_name = f"{self.PAIR_A} / {self.PAIR_B}"
        duplicate_name = f"{self.PAIR_B} / {self.PAIR_A}"
        canonical_row = {
            "id": "canonical-id",
            "name": canonical_name,
            "commander_names": [self.PAIR_A, self.PAIR_B],
        }
        duplicate_row = {
            "id": "duplicate-id",
            "name": duplicate_name,
            "commander_names": [self.PAIR_B, self.PAIR_A],
        }

        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            mock_requests.patch.return_value = Mock(raise_for_status=Mock())
            mock_requests.delete.return_value = Mock(raise_for_status=Mock())

            self._run_main(canonical_row, duplicate_row)

            self.assertEqual(mock_requests.patch.call_count, 3)


class MarkSweepPendingTests(unittest.TestCase):
    """Issue #314: a live merge must flag the pending-sweep marker so a
    maintenance run that would otherwise miss the follow-up refresh (chain-elo
    skipping because an Elo job is already in flight) still guarantees one on
    its next run. See ``consume_partner_commander_sweep_pending.py`` for the
    consuming side.
    """

    def test_posts_merged_count_to_rpc(self) -> None:
        client = Mock()
        client.postgrest.base_url = "https://example.supabase.co/rest/v1"
        client.postgrest.headers = {"apikey": "test"}

        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            mock_requests.post.return_value = Mock(raise_for_status=Mock())
            mock_requests.RequestException = Exception

            sweep_partner_commander_order.mark_sweep_pending(client, 3)

            mock_requests.post.assert_called_once()
            call = mock_requests.post.call_args
            self.assertIn("mark_partner_commander_sweep_pending", call.args[0])
            self.assertEqual(call.kwargs["json"], {"p_merged_count": 3})

    def test_rpc_failure_does_not_raise(self) -> None:
        """Best-effort: a failed mark-pending call must not fail the sweep,
        which has already committed real merges by this point.
        """
        client = Mock()
        client.postgrest.base_url = "https://example.supabase.co/rest/v1"
        client.postgrest.headers = {"apikey": "test"}

        with patch.object(sweep_partner_commander_order, "requests") as mock_requests:
            mock_requests.RequestException = RuntimeError
            mock_requests.post.side_effect = RuntimeError("network down")

            sweep_partner_commander_order.mark_sweep_pending(client, 1)  # must not raise

    def test_main_marks_pending_after_a_live_merge(self) -> None:
        pair_a, pair_b = MergeForeignKeySafetyTests.PAIR_A, MergeForeignKeySafetyTests.PAIR_B
        canonical_name = f"{pair_a} / {pair_b}"
        duplicate_name = f"{pair_b} / {pair_a}"
        commander_rows = [
            {"id": "canonical-id", "name": canonical_name, "commander_names": [pair_a, pair_b]},
            {"id": "duplicate-id", "name": duplicate_name, "commander_names": [pair_b, pair_a]},
        ]
        client = Mock()
        client.postgrest.base_url = "https://example.supabase.co/rest/v1"
        client.postgrest.headers = {"apikey": "test"}
        select_chain = client.table.return_value.select.return_value.order.return_value.limit.return_value
        select_chain.execute.return_value.data = commander_rows

        pair_key = tuple(sorted((pair_a, pair_b)))
        with tempfile.TemporaryDirectory() as tmpdir:
            argv = ["sweep_partner_commander_order.py", "--report", str(Path(tmpdir) / "report.csv")]
            with (
                patch.object(sweep_partner_commander_order, "load_credentials", return_value=("url", "key")),
                patch.object(sweep_partner_commander_order, "get_supabase_client", return_value=client),
                patch.object(
                    sweep_partner_commander_order,
                    "load_legal_commander_pair_order_map",
                    return_value={pair_key: (pair_a, pair_b)},
                ),
                patch.object(sys, "argv", argv),
                patch.object(sweep_partner_commander_order, "requests") as mock_requests,
            ):
                mock_requests.patch.return_value = Mock(raise_for_status=Mock())
                mock_requests.post.return_value = Mock(raise_for_status=Mock())
                mock_requests.delete.return_value = Mock(raise_for_status=Mock())

                main()

                mock_requests.post.assert_called_once()
                call = mock_requests.post.call_args
                self.assertIn("mark_partner_commander_sweep_pending", call.args[0])
                self.assertEqual(call.kwargs["json"], {"p_merged_count": 1})

    def test_main_does_not_mark_pending_on_dry_run(self) -> None:
        """A dry run reports what *would* merge but changes nothing -- there's
        nothing for a maintenance run to pick up, so the flag must stay clear.
        """
        pair_a, pair_b = MergeForeignKeySafetyTests.PAIR_A, MergeForeignKeySafetyTests.PAIR_B
        canonical_name = f"{pair_a} / {pair_b}"
        duplicate_name = f"{pair_b} / {pair_a}"
        commander_rows = [
            {"id": "canonical-id", "name": canonical_name, "commander_names": [pair_a, pair_b]},
            {"id": "duplicate-id", "name": duplicate_name, "commander_names": [pair_b, pair_a]},
        ]
        client = Mock()
        client.postgrest.base_url = "https://example.supabase.co/rest/v1"
        client.postgrest.headers = {"apikey": "test"}
        select_chain = client.table.return_value.select.return_value.order.return_value.limit.return_value
        select_chain.execute.return_value.data = commander_rows

        pair_key = tuple(sorted((pair_a, pair_b)))
        with tempfile.TemporaryDirectory() as tmpdir:
            argv = ["sweep_partner_commander_order.py", "--dry-run", "--report", str(Path(tmpdir) / "report.csv")]
            with (
                patch.object(sweep_partner_commander_order, "load_credentials", return_value=("url", "key")),
                patch.object(sweep_partner_commander_order, "get_supabase_client", return_value=client),
                patch.object(
                    sweep_partner_commander_order,
                    "load_legal_commander_pair_order_map",
                    return_value={pair_key: (pair_a, pair_b)},
                ),
                patch.object(sys, "argv", argv),
                patch.object(sweep_partner_commander_order, "requests") as mock_requests,
            ):
                main()

                mock_requests.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
