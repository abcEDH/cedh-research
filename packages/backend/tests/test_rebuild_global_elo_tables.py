from __future__ import annotations

import unittest
from datetime import datetime, timezone

import rebuild_global_elo_tables as elo


class RebuildGlobalEloTablesTest(unittest.TestCase):
    def test_parse_date_converts_datetime_to_date(self):
        self.assertEqual(
            elo.parse_date(datetime(2026, 6, 20, 23, 30, tzinfo=timezone.utc)).isoformat(),
            "2026-06-20",
        )

    def test_reconcile_rating_last_game_dates_from_events_uses_latest_event_date(self):
        ratings = {
            "player-1": {
                "player_id": "player-1",
                "last_game_date": "2026-03-08",
            },
            "player-2": {
                "player_id": "player-2",
                "last_game_date": datetime(2026, 5, 31, 19, 50, tzinfo=timezone.utc),
            },
        }
        events = [
            {
                "player_id": "player-1",
                "game_date": "2026-06-20T23:30:00+00:00",
            },
            {
                "player_id": "player-2",
                "game_date": "2026-05-30T16:00:00+00:00",
            },
        ]

        elo.reconcile_rating_last_game_dates_from_events(ratings, events)

        self.assertEqual(ratings["player-1"]["last_game_date"].isoformat(), "2026-06-20")
        self.assertEqual(ratings["player-2"]["last_game_date"].isoformat(), "2026-05-31")


if __name__ == "__main__":
    unittest.main()
