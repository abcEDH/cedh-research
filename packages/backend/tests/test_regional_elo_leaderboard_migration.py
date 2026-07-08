import sys
import unittest
from pathlib import Path

import requests


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
STATE_ACTIVITY_MIGRATION = MIGRATIONS_DIR / "20260406010000_global_elo_state_activity.sql"
LEADERBOARD_TOPDECK_MIGRATION = (
    MIGRATIONS_DIR / "20260501000000_regional_elo_leaderboard_topdeck_fields.sql"
)


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import regional_elo  # noqa: E402


class RegionalEloLeaderboardMigrationTests(unittest.TestCase):
    def test_state_activity_migration_does_not_reference_country_key_too_early(self) -> None:
        sql = STATE_ACTIVITY_MIGRATION.read_text()

        self.assertIn("CREATE OR REPLACE VIEW regional_elo_primary_state_assignments AS", sql)
        self.assertNotIn("a.country_key", sql)

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
                "games_played": 10,
                "topdeck_elo": 2100,
            },
            {
                "region_type": "global",
                "region_key": "ALL",
                "player_name": "Bob",
                "rating": 1800,
                "games_played": 20,
                "topdeck_elo": 2300,
            },
            {
                "region_type": "global",
                "region_key": "ALL",
                "player_name": "Carol",
                "rating": 1750,
                "games_played": 15,
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
                "games_played": 10,
                "topdeck_elo": 2100,
            },
            {
                "region_type": "country",
                "region_key": "UNITED STATES",
                "player_name": "Bob",
                "rating": 1750,
                "games_played": 5,
                "topdeck_elo": None,
            },
        ]

        regional_elo.assign_topdeck_elo_ranks(rows)

        ranks_by_name = {r["player_name"]: r["topdeck_elo_rank"] for r in rows}
        self.assertEqual(ranks_by_name, {"Alice": 1, "Bob": None})

    def test_zero_games_player_with_high_topdeck_elo_receives_null_rank(self) -> None:
        # Regression test for #252 (sibling bug in the topdeck_elo_rank path):
        # TopDeck's published Elo snapshot is imported independently of this
        # app's own game data and keyed only by topdeck_id, so a player who
        # has never recorded a game here can still carry a high, non-null
        # topdeck_elo. Such a player must not be ranked -- and must never
        # outrank a real, games-backed player -- on the strength of that
        # external Elo value alone.
        rows = [
            {
                "region_type": "global",
                "region_key": "ALL",
                "player_name": "Max Sternburg",
                "rating": 1500,
                "games_played": 0,
                "topdeck_elo": 2070,
            },
            {
                "region_type": "global",
                "region_key": "ALL",
                "player_name": "Real Player",
                "rating": 1650,
                "games_played": 40,
                "topdeck_elo": 1950,
            },
        ]

        regional_elo.assign_topdeck_elo_ranks(rows)

        ranks_by_name = {r["player_name"]: r["topdeck_elo_rank"] for r in rows}
        self.assertEqual(ranks_by_name["Max Sternburg"], None)
        self.assertEqual(ranks_by_name["Real Player"], 1)

    def test_ranks_are_partitioned_by_region(self) -> None:
        rows = [
            {
                "region_type": "global",
                "region_key": "ALL",
                "player_name": "Alice",
                "rating": 1700,
                "games_played": 10,
                "topdeck_elo": 2100,
            },
            {
                "region_type": "country",
                "region_key": "UNITED STATES",
                "player_name": "Alice",
                "rating": 1700,
                "games_played": 10,
                "topdeck_elo": 2100,
            },
            {
                "region_type": "country",
                "region_key": "UNITED STATES",
                "player_name": "Bob",
                "rating": 1800,
                "games_played": 20,
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


class BuildActiveLeaderboardRowsTests(unittest.TestCase):
    def test_enriches_topdeck_elo_by_topdeck_id_not_player_id(self) -> None:
        rows = regional_elo.build_active_leaderboard_rows(
            ratings_rows=[
                {
                    "region_type": "global",
                    "region_key": "ALL",
                    "player_id": "player-1",
                    "rating": 1700,
                    "games_played": 5,
                    "wins": 3,
                    "draws": 0,
                    "losses": 2,
                }
            ],
            player_index={
                "player-1": {
                    "id": "player-1",
                    "name": "Alice",
                    "topdeck_id": "topdeck-1",
                }
            },
            topdeck_elo_by_topdeck_id={"topdeck-1": 1900.5},
            state_stats_by_player={},
            updated_at="2026-05-01T00:00:00+00:00",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["topdeck_id"], "topdeck-1")
        self.assertEqual(rows[0]["topdeck_elo"], 1900.5)
        self.assertEqual(rows[0]["topdeck_elo_rank"], 1)

    def test_rating_rank_tie_breaks_by_activity_score(self) -> None:
        rows = regional_elo.build_active_leaderboard_rows(
            ratings_rows=[
                {
                    "region_type": "global",
                    "region_key": "ALL",
                    "player_id": "player-low-activity",
                    "rating": 1700,
                    "games_played": 5,
                },
                {
                    "region_type": "global",
                    "region_key": "ALL",
                    "player_id": "player-high-activity",
                    "rating": 1700,
                    "games_played": 5,
                },
            ],
            player_index={
                "player-low-activity": {
                    "id": "player-low-activity",
                    "name": "Low Activity",
                    "topdeck_id": "topdeck-low",
                },
                "player-high-activity": {
                    "id": "player-high-activity",
                    "name": "High Activity",
                    "topdeck_id": "topdeck-high",
                },
            },
            topdeck_elo_by_topdeck_id={},
            state_stats_by_player={
                "player-low-activity": {"activity_score": 1},
                "player-high-activity": {"activity_score": 10},
            },
            updated_at="2026-05-01T00:00:00+00:00",
        )

        ranks_by_name = {
            row["player_name"]: row["rank"]
            for row in rows
            if row["region_type"] == "global"
        }
        self.assertEqual(ranks_by_name["High Activity"], 1)
        self.assertEqual(ranks_by_name["Low Activity"], 2)

    def test_zero_games_unrated_player_does_not_outrank_real_negative_rating(self) -> None:
        # Regression test for #252: a player with zero games and no rating data
        # (represented by an absent "rating" key, mirroring a fresh
        # create_empty_ratings_row entry) was landing at rank 1 ahead of a
        # player with a real, legitimately negative rating because the
        # zero-games player's DEFAULT_RATING anchor (1500) numerically beat
        # the real player's negative rating.
        rows = regional_elo.build_active_leaderboard_rows(
            ratings_rows=[
                {
                    "region_type": "global",
                    "region_key": "ALL",
                    "player_id": "player-real",
                    "rating": -75.0,
                    "games_played": 40,
                    "wins": 5,
                    "losses": 35,
                },
                {
                    "region_type": "global",
                    "region_key": "ALL",
                    "player_id": "player-ghost",
                    # No "rating" key at all: mirrors a brand new
                    # create_empty_ratings_row() entry for a player who has
                    # never actually played a processed game.
                    "games_played": 0,
                },
            ],
            player_index={
                "player-real": {
                    "id": "player-real",
                    "name": "Real Player",
                    "topdeck_id": "topdeck-real",
                },
                "player-ghost": {
                    "id": "player-ghost",
                    "name": "Ghost Player",
                    "topdeck_id": "topdeck-ghost",
                },
            },
            topdeck_elo_by_topdeck_id={},
            state_stats_by_player={},
            updated_at="2026-05-01T00:00:00+00:00",
        )

        global_rows = {
            row["player_name"]: row for row in rows if row["region_type"] == "global"
        }

        # The real, rated player must be ranked ahead of the zero-game ghost
        # player even though the ghost's sentinel rating (DEFAULT_RATING,
        # 1500) is numerically higher than the real player's negative rating.
        self.assertEqual(global_rows["Real Player"]["rank"], 1)
        self.assertEqual(global_rows["Ghost Player"]["rank"], 2)
        self.assertEqual(global_rows["Real Player"]["rating"], -75.0)

    def test_zero_rating_value_is_preserved_not_coerced_to_default(self) -> None:
        # A real player whose computed rating happens to equal exactly 0.0
        # must keep that value; `0.0 or DEFAULT_RATING` previously collapsed
        # any falsy-but-real rating back to the 1500 anchor.
        rows = regional_elo.build_active_leaderboard_rows(
            ratings_rows=[
                {
                    "region_type": "global",
                    "region_key": "ALL",
                    "player_id": "player-zero-rating",
                    "rating": 0.0,
                    "games_played": 12,
                },
            ],
            player_index={
                "player-zero-rating": {
                    "id": "player-zero-rating",
                    "name": "Zero Rating Player",
                    "topdeck_id": "topdeck-zero",
                },
            },
            topdeck_elo_by_topdeck_id={},
            state_stats_by_player={},
            updated_at="2026-05-01T00:00:00+00:00",
        )

        self.assertEqual(rows[0]["rating"], 0.0)

    def test_zero_games_player_with_topdeck_elo_does_not_outrank_real_player(self) -> None:
        # Regression test for #252 reproducing in production via the
        # homepage's "Global Leaderboard" (ordered by topdeck_elo_rank): a
        # player who has never recorded a game in this app's data (games
        # played == 0) but who has a high topdeck_elo imported independently
        # from TopDeck.gg's own snapshot must not receive a real
        # topdeck_elo_rank, and must not rank ahead of a real, games-backed
        # player.
        rows = regional_elo.build_active_leaderboard_rows(
            ratings_rows=[
                {
                    "region_type": "global",
                    "region_key": "ALL",
                    "player_id": "player-ghost",
                    "rating": 1500,
                    "games_played": 0,
                },
                {
                    "region_type": "global",
                    "region_key": "ALL",
                    "player_id": "player-real",
                    "rating": 1650,
                    "games_played": 40,
                    "wins": 25,
                    "losses": 15,
                },
            ],
            player_index={
                "player-ghost": {
                    "id": "player-ghost",
                    "name": "Max Sternburg",
                    "topdeck_id": "topdeck-ghost",
                },
                "player-real": {
                    "id": "player-real",
                    "name": "Real Player",
                    "topdeck_id": "topdeck-real",
                },
            },
            topdeck_elo_by_topdeck_id={
                "topdeck-ghost": 2070.0,
                "topdeck-real": 1950.0,
            },
            state_stats_by_player={},
            updated_at="2026-05-01T00:00:00+00:00",
        )

        global_rows = {
            row["player_name"]: row for row in rows if row["region_type"] == "global"
        }

        self.assertEqual(global_rows["Max Sternburg"]["topdeck_elo"], 2070.0)
        self.assertIsNone(global_rows["Max Sternburg"]["topdeck_elo_rank"])
        self.assertEqual(global_rows["Real Player"]["topdeck_elo_rank"], 1)

    def test_stale_cleanup_uses_minimal_return_and_runs_outside_nonempty_guard(self) -> None:
        source = Path(regional_elo.__file__).read_text()

        self.assertIn('"Prefer": "return=minimal"', source)
        self.assertIn("if all_leaderboard_rows:", source)
        self.assertIn("delete_stale_active_leaderboard_rows(client, leaderboard_run_marker)", source)
        self.assertNotIn(
            "        delete_stale_active_leaderboard_rows(client, leaderboard_run_marker)",
            source,
        )


class FetchTopdeckEloByTopdeckIdTests(unittest.TestCase):
    @staticmethod
    def _http_error(status_code: int, text: str) -> requests.exceptions.HTTPError:
        class FakeResponse:
            def __init__(self) -> None:
                self.status_code = status_code
                self.text = text

        return requests.exceptions.HTTPError(response=FakeResponse())

    def test_probes_legacy_uid_schema_then_fetches_snapshot_with_default_retries(
        self,
    ) -> None:
        class FakeClient:
            def __init__(self, missing_topdeck_id: requests.exceptions.HTTPError) -> None:
                self.calls: list[tuple[str, dict[str, object], int]] = []
                self.missing_topdeck_id = missing_topdeck_id

            def select(
                self,
                table: str,
                filters: dict[str, object] | None = None,
                max_retries: int = 8,
            ) -> list[dict[str, object]]:
                params = filters or {}
                self.calls.append((table, params, max_retries))
                selected = params.get("select")
                if selected == "topdeck_id":
                    raise self.missing_topdeck_id
                if selected == "uid":
                    return []
                if selected == "uid,elo":
                    return [{"uid": "td-1", "elo": "2034.5"}]
                return []

        client = FakeClient(
            self._http_error(
                400,
                '{"code":"PGRST204","message":"Could not find the topdeck_id column"}',
            )
        )

        result = regional_elo.fetch_topdeck_elo_by_topdeck_id(client)  # type: ignore[arg-type]

        self.assertEqual(result, {"td-1": 2034.5})
        self.assertEqual(client.calls[0][1], {"select": "topdeck_id", "limit": "1"})
        self.assertEqual(client.calls[0][2], 1)
        self.assertEqual(client.calls[1][1], {"select": "uid", "limit": "1"})
        self.assertEqual(client.calls[1][2], 1)
        self.assertEqual(
            client.calls[2][1],
            {"select": "uid,elo", "limit": 1000, "offset": 0},
        )
        self.assertEqual(client.calls[2][2], 8)

    def test_transient_probe_error_is_not_treated_as_schema_fallback(self) -> None:
        class FakeClient:
            def select(
                self,
                table: str,
                filters: dict[str, object] | None = None,
                max_retries: int = 8,
            ) -> list[dict[str, object]]:
                raise FetchTopdeckEloByTopdeckIdTests._http_error(
                    500,
                    '{"message":"temporarily unavailable for topdeck_id"}',
                )

        with self.assertRaises(requests.exceptions.HTTPError):
            regional_elo.fetch_topdeck_elo_by_topdeck_id(FakeClient())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
