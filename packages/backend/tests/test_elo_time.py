from datetime import UTC, datetime, timedelta
from unittest import TestCase

from elo_time import exclude_future_games


class EloTimeTests(TestCase):
    def test_excludes_future_today_and_2030_but_keeps_exact_cutoff(self):
        now = datetime(2026, 9, 15, 12, tzinfo=UTC)
        rows = [
            {"game_id": "past", "start_date": "2026-09-14"},
            {"game_id": "now", "start_date": now},
            {"game_id": "later", "start_date": now + timedelta(seconds=1)},
            {"game_id": "2030", "start_date": "2030-10-26T16:00:00Z"},
        ]
        self.assertEqual([r["game_id"] for r in exclude_future_games(rows, as_of=now)], ["past", "now"])

    def test_timezone_offsets_are_compared_as_instants(self):
        rows = [{"start_date": "2026-09-15T06:00:00-07:00"}]
        self.assertEqual(exclude_future_games(rows, as_of=datetime(2026, 9, 15, 12, tzinfo=UTC)), [])

    def test_rejects_whole_game_instead_of_scoring_partial_pod(self):
        rows = [{"game_id": "g", "start_date": "2026-09-14"}, {"game_id": "g", "start_date": "2030-01-01"}]
        self.assertEqual(exclude_future_games(rows, as_of=datetime(2026, 9, 15, tzinfo=UTC)), [])

    def test_event_history_is_also_bounded(self):
        self.assertEqual(exclude_future_games([{"game_date": "2030-01-01"}], date_key="game_date", as_of=datetime(2026, 9, 15, tzinfo=UTC)), [])

    def test_invalid_dates_fail_closed(self):
        with self.assertRaises(ValueError):
            exclude_future_games([{"start_date": "invalid"}])
