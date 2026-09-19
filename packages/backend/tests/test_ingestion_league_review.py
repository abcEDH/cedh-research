"""Regression coverage for the league/backfill PR review findings."""

from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock, patch

from ingest import DataIngester, build_arg_parser
from rebuild_player_commander_profiles import build_profile_rows
from supabase_client import DirectPostgresClient
from topdeck_client import TopDeckClient, normalize_topdeck_tournament_payload


class LeagueReviewTests(TestCase):
    def test_league_flag_survives_wrapped_api_and_firestore_fallback(self):
        payload = {"data": {"name": "League"}, "isLeague": True}
        self.assertIs(normalize_topdeck_tournament_payload(payload)["isLeague"], True)
        client = TopDeckClient("test")
        with (
            patch.object(client, "_request", return_value=payload),
            patch.object(client, "get_public_player_data", return_value=[]),
            patch.object(client, "get_firestore_tournament", return_value={"rounds": []}),
        ):
            self.assertIs(client.get_tournament("league")["isLeague"], True)

    def test_defaults_include_leagues_and_no_minimum_size(self):
        args = build_arg_parser().parse_args([])
        self.assertTrue(args.leagues)
        self.assertEqual(args.min_players, 0)
        self.assertEqual(args.days, 45)
        self.assertFalse(build_arg_parser().parse_args(["--no-leagues"]).leagues)

    def test_direct_writes_keep_rest_client_for_reads(self):
        reader, writer = MagicMock(), MagicMock()
        writer.upsert.return_value = [{"id": "p1", "topdeck_id": "td1"}]
        ingester = DataIngester(MagicMock(), reader, write_client=writer)
        self.assertIs(ingester.supabase, reader)
        self.assertEqual(ingester.batch_upsert_players({"td1": "Player"}), {"td1": "p1"})
        writer.upsert.assert_called_once()
        reader.table.assert_not_called()

    def test_direct_failure_rolls_back_before_the_next_write(self):
        client = DirectPostgresClient("unused")
        client._conn = MagicMock()
        client._conn.closed = False
        cursor = client._conn.cursor.return_value.__enter__.return_value
        cursor.description = [("id",), ("name",)]
        with patch(
            "supabase_client.psycopg2.extras.execute_values", side_effect=[RuntimeError("bad row"), [(1, "ok")]]
        ):
            with self.assertRaises(RuntimeError):
                client.upsert("players", {"id": 1, "name": "bad"}, "id")
            client._conn.rollback.assert_called_once()
            self.assertEqual(client.upsert("players", {"id": 1, "name": "ok"}, "id"), [{"id": 1, "name": "ok"}])
        client._conn.commit.assert_called_once()

    def test_direct_write_aligns_columns_and_collects_every_page(self):
        client = DirectPostgresClient("unused")
        client._conn = MagicMock()
        client._conn.closed = False
        cursor = client._conn.cursor.return_value.__enter__.return_value
        cursor.description = [("id",), ("name",)]
        with patch("supabase_client.psycopg2.extras.execute_values", return_value=[(1, "a"), (2, "b")]) as execute:
            result = client.upsert("players", [{"id": 1, "name": "a"}, {"name": "b", "id": 2}], "id")
        self.assertEqual(execute.call_args.args[2], [(1, "a"), (2, "b")])
        self.assertTrue(execute.call_args.kwargs["fetch"])
        self.assertEqual(len(result), 2)

    def test_forecast_exposes_blended_share_to_existing_consumers(self):
        rows = [
            {
                "player_id": "p",
                "topdeck_id": "td",
                "player_name": "Player",
                "commander_name": commander,
                "start_date": day,
            }
            for commander, day in [("A", "2026-09-01"), ("A", "2026-09-02"), ("B", "2026-09-03")]
        ]
        profile = build_profile_rows(rows, date(2026, 9, 4))[0]
        predictions = profile["commander_predictions"]
        self.assertAlmostEqual(sum(p["prediction_share"] for p in predictions), 1)
        for p in predictions:
            self.assertAlmostEqual(p["prediction_share"], p["model_share"])
            self.assertAlmostEqual(
                p["model_share"], 0.75 * p["weighted_share"] + (0.25 if p["commander"] == "B" else 0)
            )
        self.assertEqual(profile["active_commander_prediction_score"], predictions[0]["model_share"])
