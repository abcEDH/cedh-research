import unittest
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
TOURNAMENT_METADATA_MIGRATION = (
    MIGRATIONS_DIR
    / "20260501010000_player_commander_profiles_tournament_metadata.sql"
)


class PlayerCommanderProfilesTournamentMetadataMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sql = TOURNAMENT_METADATA_MIGRATION.read_text()

    def test_migration_targets_player_commander_profiles_table(self) -> None:
        self.assertIn(
            "ALTER TABLE public.player_commander_profiles",
            self.sql,
        )

    def test_adds_latest_tournament_id_column(self) -> None:
        self.assertIn(
            "ADD COLUMN IF NOT EXISTS latest_tournament_id uuid",
            self.sql,
        )

    def test_adds_latest_tournament_name_column(self) -> None:
        self.assertIn(
            "ADD COLUMN IF NOT EXISTS latest_tournament_name text",
            self.sql,
        )

    def test_adds_latest_tournament_date_column(self) -> None:
        self.assertIn(
            "ADD COLUMN IF NOT EXISTS latest_tournament_date date",
            self.sql,
        )

    def test_adds_latest_tournament_topdeck_tid_column(self) -> None:
        self.assertIn(
            "ADD COLUMN IF NOT EXISTS latest_tournament_topdeck_tid text",
            self.sql,
        )

    def test_does_not_add_foreign_key_on_latest_tournament_id(self) -> None:
        # The recompute flow rewrites these columns wholesale; an FK would
        # risk breaking rebuilds if a tournament row is removed between
        # profile rebuilds. Application-level integrity is sufficient.
        self.assertNotIn("REFERENCES tournaments", self.sql)
        self.assertNotIn("REFERENCES public.tournaments", self.sql)


if __name__ == "__main__":
    unittest.main()
