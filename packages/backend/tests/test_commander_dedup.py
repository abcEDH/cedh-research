import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, call

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commander_dedup import (  # noqa: E402
    _merge_duplicate_commander,
    resolve_partner_order_conflicts,
)

ABBY_ELLIE_CANONICAL = "Abby, Merciless Soldier / Ellie, Brick Master"
ABBY_ELLIE_NAMES = ["Abby, Merciless Soldier", "Ellie, Brick Master"]
ABBY_ELLIE_ALT = "Ellie, Brick Master / Abby, Merciless Soldier"


class ResolvePartnerOrderConflictsNoOpTests(unittest.TestCase):
    def test_ignores_single_commander_payloads(self) -> None:
        client = Mock()
        resolve_partner_order_conflicts(client, {"Solo Commander": ["Solo Commander"]})
        client.select.assert_not_called()

    def test_does_nothing_when_no_row_exists_for_the_pair(self) -> None:
        client = Mock()
        client.select.return_value = []
        resolve_partner_order_conflicts(client, {ABBY_ELLIE_CANONICAL: ABBY_ELLIE_NAMES})
        client.update.assert_not_called()
        client.delete.assert_not_called()

    def test_does_nothing_when_canonical_row_already_exists(self) -> None:
        client = Mock()
        client.select.return_value = [
            {"id": "row-1", "name": ABBY_ELLIE_CANONICAL, "commander_names": ABBY_ELLIE_NAMES}
        ]
        resolve_partner_order_conflicts(client, {ABBY_ELLIE_CANONICAL: ABBY_ELLIE_NAMES})
        client.update.assert_not_called()
        client.delete.assert_not_called()


class ResolvePartnerOrderConflictsRenameTests(unittest.TestCase):
    def test_renames_legacy_alt_order_row_in_place_when_no_canonical_row_exists(self) -> None:
        # Reproduces issue #260's core scenario: a row was written under the
        # *reverse* order before this pair's canonical order was known. No
        # canonical-named row exists yet, so the fix must rename the
        # existing row (same id -- no FK repoint needed) rather than let the
        # upsert create a second row alongside it.
        client = Mock()
        client.select.return_value = [
            {"id": "legacy-id", "name": ABBY_ELLIE_ALT, "commander_names": list(reversed(ABBY_ELLIE_NAMES))}
        ]

        resolve_partner_order_conflicts(client, {ABBY_ELLIE_CANONICAL: ABBY_ELLIE_NAMES})

        client.update.assert_called_once_with(
            "commanders",
            {"name": ABBY_ELLIE_CANONICAL, "commander_names": ABBY_ELLIE_NAMES},
            {"id": "eq.legacy-id"},
        )
        client.delete.assert_not_called()

    def test_ignores_unrelated_two_card_rows(self) -> None:
        client = Mock()
        client.select.return_value = [
            {"id": "other-id", "name": "Tymna the Weaver / Kraum, Ludevic's Opus", "commander_names": []}
        ]
        resolve_partner_order_conflicts(client, {ABBY_ELLIE_CANONICAL: ABBY_ELLIE_NAMES})
        client.update.assert_not_called()
        client.delete.assert_not_called()


class ResolvePartnerOrderConflictsMergeTests(unittest.TestCase):
    def test_merges_true_duplicate_when_both_orders_already_exist_as_separate_rows(self) -> None:
        # A stale duplicate scenario: both the canonical row *and* a legacy
        # alt-order row already exist as separate commander ids (e.g. the
        # canonical row was created by a later, correctly-ordered ingest
        # while the older alt-order row was never cleaned up). The alt row
        # must be repointed and deleted, not left to split history further.
        client = Mock()
        client.select.return_value = [
            {"id": "legacy-id", "name": ABBY_ELLIE_ALT, "commander_names": list(reversed(ABBY_ELLIE_NAMES))},
            {"id": "canonical-id", "name": ABBY_ELLIE_CANONICAL, "commander_names": ABBY_ELLIE_NAMES},
        ]

        resolve_partner_order_conflicts(client, {ABBY_ELLIE_CANONICAL: ABBY_ELLIE_NAMES})

        client.update.assert_has_calls(
            [
                call("tournament_entries", {"commander_id": "canonical-id"}, {"commander_id": "eq.legacy-id"}),
                call("commander_matchups", {"commander_id": "canonical-id"}, {"commander_id": "eq.legacy-id"}),
                call(
                    "commander_matchups",
                    {"opponent_commander_id": "canonical-id"},
                    {"opponent_commander_id": "eq.legacy-id"},
                ),
            ]
        )
        client.delete.assert_called_once_with("commanders", {"id": "eq.legacy-id"})

    def test_merge_duplicate_commander_repoints_both_fk_columns_before_delete(self) -> None:
        client = Mock()
        _merge_duplicate_commander(client, "canonical-id", "duplicate-id")

        self.assertEqual(client.update.call_count, 3)
        client.delete.assert_called_once_with("commanders", {"id": "eq.duplicate-id"})


if __name__ == "__main__":
    unittest.main()
