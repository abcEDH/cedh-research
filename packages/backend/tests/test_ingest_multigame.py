import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from game_registry import GAME_REGISTRY  # noqa: E402
from ingest import DataIngester  # noqa: E402


class FakeSupabase:
    """Records upserts and hands back rows with synthetic ids."""

    def __init__(self) -> None:
        self.upserts: list[tuple[str, object, str | None]] = []
        self._counter = 0

    def upsert(self, table, data, on_conflict=None, **kwargs):
        self.upserts.append((table, data, on_conflict))
        rows = data if isinstance(data, list) else [data]
        result = []
        for row in rows:
            self._counter += 1
            copy = dict(row)
            copy.setdefault("id", f"{table}-{self._counter}")
            result.append(copy)
        return result

    def select(self, *args, **kwargs):
        return []

    def rows_for(self, table):
        collected = []
        for name, data, _ in self.upserts:
            if name != table:
                continue
            collected.extend(data if isinstance(data, list) else [data])
        return collected

    def conflict_for(self, table):
        return [conflict for name, _, conflict in self.upserts if name == table]


RIFTBOUND_TOURNAMENT = {
    "id": "riftbound-weekly-1",
    "name": "Riftbound Weekly",
    "startDate": 1750000000,
    "swissNum": 4,
    "topCut": 8,
    "game": "Riftbound",
    "format": "Constructed",
    "eventData": {},
    "standings": [
        {
            "id": "p1",
            "name": "Alice",
            "standing": 1,
            "points": 9,
            "wins": 3,
            "losses": 1,
            "draws": 0,
            "decklist": "",
            "deckObj": {
                "Commanders": {"Jinx, Loose Cannon": {"id": "aaa", "count": 1}},
                "Mainboard": {"Get Excited!": {"id": "bbb", "count": 3}},
            },
        },
        {
            "id": "p2",
            "name": "Bob",
            "standing": 2,
            "points": 6,
            "decklist": "",
            "deckObj": {
                "Commanders": {"Viktor, Herald of the Arcane": {"id": "ccc", "count": 1}},
                "Mainboard": {"Hextech Upgrade": {"id": "ddd", "count": 2}},
            },
        },
    ],
    "rounds": [
        {
            "round": 1,
            "tables": [
                {"table": 1, "players": [{"id": "p1"}, {"id": "p2"}], "winner_id": "p1"},
                {"table": "Byes", "players": [{"id": "p1"}]},
            ],
        }
    ],
}


class RiftboundIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.supabase = FakeSupabase()
        topdeck = Mock()
        topdeck.get_tournament_tier.return_value = None
        self.ingester = DataIngester(topdeck, self.supabase, game_config=GAME_REGISTRY["riftbound"])
        self.result = self.ingester.process_tournament(dict(RIFTBOUND_TOURNAMENT))

    def test_tournament_row_carries_configured_game_and_format(self) -> None:
        tournament_rows = self.supabase.rows_for("tournaments")
        self.assertEqual(len(tournament_rows), 1)
        row = tournament_rows[0]
        self.assertEqual(row["game"], "Riftbound")
        # TopDeck requires a format on every search, so every config always
        # persists its own db_format regardless of what the payload reports
        # (the fixture's "Constructed" is a mismatch that only logs a warning).
        self.assertEqual(row["format"], "Standard")
        # No small-event top-cut override for 1v1 games.
        self.assertEqual(row["top_cut"], 8)

    def test_deck_identities_are_game_scoped_legends(self) -> None:
        commander_rows = self.supabase.rows_for("commanders")
        names = {row["name"] for row in commander_rows}
        self.assertEqual(names, {"Jinx, Loose Cannon", "Viktor, Herald of the Arcane"})
        for row in commander_rows:
            self.assertEqual(row["game"], "Riftbound")
            self.assertEqual(row["identity_kind"], "legend")
        self.assertEqual(set(self.supabase.conflict_for("commanders")), {"game,name"})

    def test_entries_persist_deck_obj_and_never_derive_wld(self) -> None:
        entries = self.supabase.rows_for("tournament_entries")
        self.assertEqual(len(entries), 2)
        by_standing = {entry["final_standing"]: entry for entry in entries}
        self.assertIn("decklist_obj", by_standing[1])
        self.assertIn("Commanders", by_standing[1]["decklist_obj"])
        # Explicit W/L/D passes through.
        self.assertEqual(by_standing[1]["wins"], 3)
        # points=6 with no explicit W/L/D must NOT be derived for non-cEDH scoring.
        self.assertNotIn("wins", by_standing[2])
        self.assertNotIn("draws", by_standing[2])
        self.assertNotIn("losses", by_standing[2])

    def test_bye_tables_are_skipped_and_1v1_seats_recorded(self) -> None:
        games = self.supabase.rows_for("games")
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["table_number"], 1)

        participants = self.supabase.rows_for("game_participants")
        self.assertEqual(len(participants), 2)
        self.assertEqual(sorted(p["seat_position"] for p in participants), [0, 1])
        points = sorted(p["points_earned"] for p in participants)
        self.assertEqual(points, [0, 3])  # riftbound win_points=3, loss=0


DUO_LEGEND_TOURNAMENT = {
    "id": "riftbound-duo-1",
    "name": "Riftbound Duo Weekly",
    "startDate": 1750000000,
    "swissNum": 3,
    "topCut": 8,
    "game": "Riftbound",
    "format": "Standard",
    "eventData": {},
    "standings": [
        {
            "id": "p1",
            "name": "Alice",
            "standing": 1,
            "points": 6,
            "decklist": "",
            "deckObj": {
                "Commanders": {
                    "Jinx, Loose Cannon": {"id": "aaa", "count": 1},
                    "Viktor, Herald of the Arcane": {"id": "ccc", "count": 1},
                },
                "Mainboard": {"Get Excited!": {"id": "bbb", "count": 3}},
            },
        },
        {
            "id": "p2",
            "name": "Bob",
            "standing": 2,
            "points": 3,
            "decklist": "",
            "deckObj": {
                "Commanders": {"Ekko, the Boy Who Shattered Time": {"id": "eee", "count": 1}},
                "Mainboard": {},
            },
        },
    ],
    "rounds": [
        {
            "round": 1,
            "tables": [{"table": 1, "players": [{"id": "p1"}, {"id": "p2"}], "winner_id": "p1"}],
        }
    ],
}


class RiftboundDuoLegendRegressionTests(unittest.TestCase):
    """A two-component non-cEDH identity must not be rewritten to "Unknown
    Commander" by the MTG partner-pair legality check (PR #247 review)."""

    def setUp(self) -> None:
        self.supabase = FakeSupabase()
        topdeck = Mock()
        topdeck.get_tournament_tier.return_value = None
        self.ingester = DataIngester(topdeck, self.supabase, game_config=GAME_REGISTRY["riftbound"])
        self.ingester.process_tournament(dict(DUO_LEGEND_TOURNAMENT))

    def test_duo_legend_identity_is_not_rewritten_to_unknown(self) -> None:
        commander_rows = self.supabase.rows_for("commanders")
        names = {row["name"] for row in commander_rows}
        self.assertNotIn("Unknown Commander", names)
        self.assertIn("Jinx, Loose Cannon / Viktor, Herald of the Arcane", names)

    def test_duo_legend_entry_is_not_dropped(self) -> None:
        entries = self.supabase.rows_for("tournament_entries")
        # Both standings must resolve a commander_id and produce an entry —
        # the bug silently dropped entries whose id-map lookup missed.
        self.assertEqual(len(entries), 2)


YGO_ARCHETYPE_TOURNAMENT = {
    "id": "goat-classic-1",
    "name": "Goat Classic",
    "startDate": 1750000000,
    "swissNum": 3,
    "topCut": 8,
    "game": "Yu-Gi-Oh",
    "format": "Goat",
    "eventData": {},
    "standings": [
        {
            "id": "p1",
            "name": "Carol",
            "standing": 1,
            "points": 6,
            "decklist": "",
            "deckObj": {
                "Mainboard": {
                    "Scapegoat": {"id": "s1", "count": 1},
                    "Metamorphosis": {"id": "s2", "count": 1},
                    "Pot of Greed": {"id": "s3", "count": 1},
                }
            },
        },
        {
            "id": "p2",
            "name": "Dave",
            "standing": 2,
            "points": 3,
            "decklist": "",
            "deckObj": {"Mainboard": {"Sangan": {"id": "s4", "count": 1}}},
        },
    ],
    "rounds": [
        {
            "round": 1,
            "tables": [{"table": 1, "players": [{"id": "p1"}, {"id": "p2"}], "winner_id": "p1"}],
        }
    ],
}


class YgoArchetypeRegressionTests(unittest.TestCase):
    """Signature-card matches (2+ components) must not be sanitized as an MTG
    commander pair, which orphaned the entry's commander_id (PR #247 review)."""

    def setUp(self) -> None:
        self.supabase = FakeSupabase()
        topdeck = Mock()
        topdeck.get_tournament_tier.return_value = None
        self.ingester = DataIngester(topdeck, self.supabase, game_config=GAME_REGISTRY["ygo-goat"])
        self.ingester.process_tournament(dict(YGO_ARCHETYPE_TOURNAMENT))

    def test_archetype_identity_is_not_rewritten_to_unknown(self) -> None:
        commander_rows = self.supabase.rows_for("commanders")
        names = {row["name"] for row in commander_rows}
        self.assertIn("Goat Control", names)
        self.assertNotIn("Unknown Commander", names)
        goat_control = next(row for row in commander_rows if row["name"] == "Goat Control")
        self.assertEqual(goat_control["identity_kind"], "archetype")

    def test_classified_entry_keeps_its_commander_id(self) -> None:
        entries = self.supabase.rows_for("tournament_entries")
        self.assertEqual(len(entries), 2)
        classified = next(e for e in entries if e["final_standing"] == 1)
        self.assertIsNotNone(classified.get("commander_id"))


if __name__ == "__main__":
    unittest.main()
