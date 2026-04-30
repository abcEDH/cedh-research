import sys
import unittest
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
LEADERBOARD_TOPDECK_MIGRATION = (
    MIGRATIONS_DIR / "20260501000000_regional_elo_leaderboard_topdeck_fields.sql"
)


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import regional_elo  # noqa: E402


class RegionalEloLeaderboardMigrationTests(unittest.TestCase):
    def test_migration_adds_topdeck_elo_columns_idempotently(self) -> None:
        sql = LEADERBOARD_TOPDECK_MIGRATION.read_text()

        self.assertIn(
            "ALTER TABLE public.global_elo_active_leaderboard", sql
        )
        self.assertIn("ADD COLUMN IF NOT EXISTS topdeck_elo numeric", sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS topdeck_elo_rank integer", sql)

    def test_migration_creates_partial_index_for_topdeck_rank_lookups(self) -> None:
        sql = LEADERBOARD_TOPDECK_MIGRATION.read_text()

        self.assertIn(
            "CREATE INDEX IF NOT EXISTS global_elo_active_leaderboard_region_topdeck_rank_idx",
            sql,
        )
        self.assertIn(
            "ON public.global_elo_active_leaderboard (region_type, region_key, topdeck_elo_rank)",
            sql,
        )
        self.assertIn("WHERE topdeck_elo_rank IS NOT NULL", sql)

    def test_migration_recreates_alias_view_with_security_invoker(self) -> None:
        sql = LEADERBOARD_TOPDECK_MIGRATION.read_text()

        self.assertIn(
            "CREATE OR REPLACE VIEW public.regional_elo_active_leaderboard AS", sql
        )
        self.assertIn("SELECT * FROM public.global_elo_active_leaderboard", sql)
        self.assertIn(
            "ALTER VIEW public.regional_elo_active_leaderboard SET (security_invoker = true)",
            sql,
        )
        self.assertIn(
            "GRANT SELECT ON public.regional_elo_active_leaderboard TO anon, authenticated",
            sql,
        )


class AssignTopdeckEloRanksTests(unittest.TestCase):
    def test_ranks_descend_by_topdeck_elo_within_partition(self) -> None:
        rows = [
            {
                "region_type": "global",
                "region_key": "ALL",
                "player_name": "Alice",
                "rating": 1700,
                "topdeck_elo": 2100,
            },
            {
                "region_type": "global",
                "region_key": "ALL",
                "player_name": "Bob",
                "rating": 1800,
                "topdeck_elo": 2300,
            },
            {
                "region_type": "global",
                "region_key": "ALL",
                "player_name": "Carol",
                "rating": 1750,
                "topdeck_elo": 2200,
            },
        ]

        regional_elo.assign_topdeck_elo_ranks(rows)

        ranks_by_name = {r["player_name"]: r["topdeck_elo_rank"] for r in rows}
        self.assertEqual(ranks_by_name, {"Bob": 1, "Carol": 2, "Alice": 3})

    def test_null_topdeck_elo_receives_null_rank(self) -> None:
        rows = [
            {
                "region_type": "country",
                "region_key": "UNITED STATES",
                "player_name": "Alice",
                "rating": 1700,
                "topdeck_elo": 2100,
            },
            {
                "region_type": "country",
                "region_key": "UNITED STATES",
                "player_name": "Bob",
                "rating": 1750,
                "topdeck_elo": None,
            },
        ]

        regional_elo.assign_topdeck_elo_ranks(rows)

        ranks_by_name = {r["player_name"]: r["topdeck_elo_rank"] for r in rows}
        self.assertEqual(ranks_by_name, {"Alice": 1, "Bob": None})

    def test_ranks_are_partitioned_by_region(self) -> None:
        rows = [
            {
                "region_type": "global",
                "region_key": "ALL",
                "player_name": "Alice",
                "rating": 1700,
                "topdeck_elo": 2100,
            },
            {
                "region_type": "country",
                "region_key": "UNITED STATES",
                "player_name": "Alice",
                "rating": 1700,
                "topdeck_elo": 2100,
            },
            {
                "region_type": "country",
                "region_key": "UNITED STATES",
                "player_name": "Bob",
                "rating": 1800,
                "topdeck_elo": 2300,
            },
        ]

        regional_elo.assign_topdeck_elo_ranks(rows)

        country_ranks = {
            r["player_name"]: r["topdeck_elo_rank"]
            for r in rows
            if r["region_type"] == "country"
        }
        self.assertEqual(country_ranks, {"Bob": 1, "Alice": 2})

        global_ranks = [
            r["topdeck_elo_rank"] for r in rows if r["region_type"] == "global"
        ]
        self.assertEqual(global_ranks, [1])


if __name__ == "__main__":
    unittest.main()
