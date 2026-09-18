from __future__ import annotations

import unittest
from unittest.mock import patch

from run_historical_tournament_sim import fetch_pre_tournament_elos, parse_database_datetime


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def fetch(self, client, table, *, columns, filters, order=None):
        params = {column: value for column, _operator, value in filters}
        self.calls.append((table, dict(params)))
        if table == "global_elo_ratings":
            return [
                {
                    "player_id": "finalized",
                    "rating": 2151.627,
                    "last_game_date": "2026-06-20",
                },
                {
                    "player_id": "historical",
                    "rating": 2200.0,
                    "last_game_date": "2026-06-30",
                },
            ]
        if table == "global_elo_game_events":
            return [
                {
                    "player_id": "finalized",
                    "game_date": "2026-06-20T16:30:00+00:00",
                    "rating_after": 2186.764,
                },
                {
                    "player_id": "historical",
                    "game_date": "2026-06-19T18:00:00+00:00",
                    "rating_after": 1800.0,
                    "games": {"round_number": 1, "table_number": 1},
                },
                {
                    "player_id": "historical",
                    "game_date": "2026-06-19T18:00:00+00:00",
                    "rating_after": 2000.0,
                    "games": {"round_number": 2, "table_number": 1},
                },
            ]
        return []


class HistoricalTournamentSimTest(unittest.TestCase):
    def test_parse_database_datetime_pads_short_fractional_seconds(self):
        parsed = parse_database_datetime("2022-12-03T07:40:22.92+00:00")

        self.assertEqual(parsed.isoformat(), "2022-12-03T07:40:22.920000+00:00")

    def test_fetch_pre_tournament_elos_prefers_finalized_rating_before_start(self):
        client = FakeSupabaseClient()

        with patch("run_historical_tournament_sim.fetch_all", side_effect=client.fetch):
            ratings = fetch_pre_tournament_elos(
                client,
                ["finalized", "historical"],
                "2026-06-27T09:00:00-07:00",
            )

        self.assertEqual(ratings["finalized"], 2151.627)
        self.assertEqual(ratings["historical"], 2000.0)
        event_calls = [params for table, params in client.calls if table == "global_elo_game_events"]
        self.assertEqual(len(event_calls), 1)
        self.assertEqual(event_calls[0]['player_id'], ['historical'])


if __name__ == "__main__":
    unittest.main()
