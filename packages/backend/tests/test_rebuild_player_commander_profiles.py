import sys
import types
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import MagicMock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.modules["psycopg2"] = None

_real_ingest = sys.modules.get("ingest")

fake_ingest = types.ModuleType("ingest")
fake_ingest.SUPABASE_REST_BASE = "https://example.supabase.co"
fake_ingest.SupabaseClient = MagicMock
fake_ingest.load_local_env = MagicMock
sys.modules["ingest"] = fake_ingest

import rebuild_player_commander_profiles as profiles  # noqa: E402

# Restore the real ingest module so @patch("ingest.X") in other test files
# targets the real module's namespace, not this stub.
if _real_ingest is not None:
    sys.modules["ingest"] = _real_ingest
else:
    del sys.modules["ingest"]


class RebuildPlayerCommanderProfilesTests(TestCase):
    def test_normalize_usage_rows_converts_db_datetime_start_dates(self) -> None:
        raw_rows = [
            {
                "player_id": "player-1",
                "topdeck_id": "topdeck-1",
                "player_name": "Player One",
                "commander_name": "Tivit, Seller of Secrets",
                "start_date": datetime(2026, 6, 14, 18, 30, tzinfo=timezone.utc),
                "topdeck_tid": "tournament-slug",
                "tournament_id": "tournament-1",
                "tournament_name": "Test Tournament",
            }
        ]

        rows = profiles.normalize_usage_rows(raw_rows, date(2026, 8, 15))

        self.assertEqual(rows[0]["start_date"], "2026-06-14T18:30:00+00:00")

    def test_normalize_usage_rows_excludes_future_dated_entries(self) -> None:
        raw_rows = [
            {
                "player_id": "player-1",
                "topdeck_id": "topdeck-1",
                "player_name": "Player One",
                "commander_name": "Tivit, Seller of Secrets",
                "start_date": datetime(2030, 10, 26, tzinfo=timezone.utc),
                "topdeck_tid": "test-event-for-dan-and-noam",
                "tournament_id": "tournament-1",
                "tournament_name": "Test Event for Dan and Noam",
            }
        ]

        rows = profiles.normalize_usage_rows(raw_rows, date(2026, 8, 15))

        self.assertEqual(rows, [])

    def test_select_commander_forecast_rows_handles_mixed_start_date_types(self) -> None:
        rows_by_topdeck_id = {
            "topdeck-1": [
                {
                    "commander_name": "Kinnan, Bonder Prodigy",
                    "start_date": datetime(2026, 6, 1, tzinfo=timezone.utc),
                },
                {
                    "commander_name": "Rograkh, Son of Rohgahh",
                    "start_date": date(2026, 5, 20),
                },
                {
                    "commander_name": "Tymna the Weaver",
                    "start_date": "2026-04-01",
                },
            ]
        }

        selected = profiles.select_commander_forecast_rows(rows_by_topdeck_id, date(2026, 6, 15))

        self.assertEqual(len(selected["topdeck-1"]), 3)
        self.assertTrue(all(isinstance(row["start_date"], str) for row in selected["topdeck-1"]))

    def test_build_profile_rows_handles_mixed_start_date_types(self) -> None:
        usage_rows = [
            {
                "player_id": "player-1",
                "topdeck_id": "topdeck-1",
                "player_name": "Player One",
                "commander_name": "Kinnan, Bonder Prodigy",
                "start_date": datetime(2026, 6, 1, tzinfo=timezone.utc),
            },
            {
                "player_id": "player-1",
                "topdeck_id": "topdeck-1",
                "player_name": "Player One",
                "commander_name": "Kinnan, Bonder Prodigy",
                "start_date": "2026-05-01",
            },
        ]

        rows = profiles.build_profile_rows(usage_rows, date(2026, 6, 15))

        self.assertEqual(rows[0]["active_commander"], "Kinnan, Bonder Prodigy")
        self.assertEqual(rows[0]["latest_commander_date"], "2026-06-01")


if __name__ == "__main__":
    main()
