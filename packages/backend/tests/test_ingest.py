import json
import unittest
import os
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch


try:
    import requests as requests_module
except ModuleNotFoundError:
    requests_module = types.ModuleType("requests")
    requests_module.get = Mock()
    requests_module.post = Mock()
    requests_module.patch = Mock()
    requests_module.exceptions = types.SimpleNamespace(
        ConnectionError=ConnectionError,
        Timeout=TimeoutError,
        ReadTimeout=TimeoutError,
        JSONDecodeError=ValueError,
        HTTPError=RuntimeError,
        RequestException=Exception,
    )
    sys.modules["requests"] = requests_module

dateutil_module = types.ModuleType("dateutil")
dateutil_parser_module = types.ModuleType("dateutil.parser")
dateutil_parser_module.parse = lambda value: value
dateutil_module.parser = dateutil_parser_module
sys.modules.setdefault("dateutil", dateutil_module)
sys.modules.setdefault("dateutil.parser", dateutil_parser_module)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import (  # noqa: E402
    _describe_request_failure,
    clean_commander_card_name,
    deduplicate_commanders_in_batch,
    extract_standing_rates,
    INGESTION_JOB_ALREADY_CLAIMED_EXIT_CODE,
    normalize_commander_name,
    sanitize_commander_payload,
    SupabaseClient,
    claim_ingestion_job,
    complete_ingestion_job,
    fail_ingestion_job,
    main,
)


class ExtractStandingRatesTests(unittest.TestCase):
    def test_uses_primary_and_opponent_fallbacks_independently(self) -> None:
        standing = {
            "successRate": 0.72,
            "opponentWinRate": 0.41,
        }

        win_rate, opponent_win_rate = extract_standing_rates(standing)

        self.assertEqual(win_rate, 0.72)
        self.assertEqual(opponent_win_rate, 0.41)

    def test_accepts_percent_values_for_both_fields(self) -> None:
        standing = {
            "winRate": 71,
            "opponentSuccessRate": 48,
        }

        win_rate, opponent_win_rate = extract_standing_rates(standing)

        self.assertEqual(win_rate, 0.71)
        self.assertEqual(opponent_win_rate, 0.48)


class CommanderNormalizationTests(unittest.TestCase):
    def test_clean_commander_card_name_maps_stranger_things_to_in_universe(self) -> None:
        self.assertEqual(clean_commander_card_name("Lucas, the Sharpshooter"), "Bjorna, Nightfall Alchemist")

    def test_clean_commander_card_name_unescapes_quotes(self) -> None:
        self.assertEqual(clean_commander_card_name("K\\'rrik, Son of Yawgmoth"), "K'rrik, Son of Yawgmoth")

    def test_clean_commander_card_name_strips_double_faced_backside(self) -> None:
        self.assertEqual(
            clean_commander_card_name("Etali, Primal Conqueror // Etali, Primal Sickness"),
            "Etali, Primal Conqueror",
        )

    def test_normalize_commander_name_strips_back_faces_from_partner_pair(self) -> None:
        self.assertEqual(
            normalize_commander_name(
                [
                    "Etali, Primal Conqueror // Etali, Primal Sickness",
                    "Vivi Ornitier",
                ]
            ),
            "Etali, Primal Conqueror / Vivi Ornitier",
        )

    def test_sanitize_commander_payload_canonicalizes_name_and_components(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Kraum, Ludevic\\'s Opus / Tymna the Weaver",
                ["Kraum, Ludevic\\'s Opus", "Tymna the Weaver"],
            ),
            (
                "Tymna the Weaver / Kraum, Ludevic's Opus",
                ["Tymna the Weaver", "Kraum, Ludevic's Opus"],
            ),
        )

    def test_sanitize_commander_payload_maps_stranger_things_pair(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Lucas, the Sharpshooter / Will the Wise",
                ["Lucas, the Sharpshooter", "Will the Wise"],
            ),
            (
                "Bjorna, Nightfall Alchemist / Wernog, Rider's Chaplain",
                ["Bjorna, Nightfall Alchemist", "Wernog, Rider's Chaplain"],
            ),
        )

    def test_sanitize_commander_payload_rejects_illegal_pair(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Etali, Primal Conqueror / Kinnan, Bonder Prodigy",
                ["Etali, Primal Conqueror", "Kinnan, Bonder Prodigy"],
            ),
            ("Unknown Commander", ["Unknown Commander"]),
        )

    def test_normalize_commander_name_uses_canonical_legal_pair_order(self) -> None:
        self.assertEqual(
            normalize_commander_name(["Haldan, Avid Arcanist", "Pako, Arcane Retriever"]),
            "Pako, Arcane Retriever / Haldan, Avid Arcanist",
        )

    def test_deduplicate_commanders_keeps_single_partner_pair(self) -> None:
        commander_data = {
            "Tymna the Weaver / Kraum, Ludevic's Opus": [
                "Tymna the Weaver",
                "Kraum, Ludevic's Opus",
            ]
        }
        result = deduplicate_commanders_in_batch(commander_data)
        self.assertEqual(len(result), 1)
        self.assertIn("Tymna the Weaver / Kraum, Ludevic's Opus", result)

    def test_deduplicate_commanders_merges_reversed_partner_pairs(self) -> None:
        # When both orders of a partner pair are in the batch, keep only one
        commander_data = {
            "Tymna the Weaver / Kraum, Ludevic's Opus": [
                "Tymna the Weaver",
                "Kraum, Ludevic's Opus",
            ],
            "Kraum, Ludevic's Opus / Tymna the Weaver": [
                "Kraum, Ludevic's Opus",
                "Tymna the Weaver",
            ],
        }
        result = deduplicate_commanders_in_batch(commander_data)
        # Should keep only one entry for this pair
        self.assertEqual(len(result), 1)
        # The first occurrence should be kept
        self.assertIn("Tymna the Weaver / Kraum, Ludevic's Opus", result)

    def test_deduplicate_commanders_keeps_single_commanders(self) -> None:
        commander_data = {
            "Urza, Lord Artificer": ["Urza, Lord Artificer"],
            "Rhystic Study": ["Rhystic Study"],
        }
        result = deduplicate_commanders_in_batch(commander_data)
        self.assertEqual(len(result), 2)
        self.assertIn("Urza, Lord Artificer", result)
        self.assertIn("Rhystic Study", result)


class OracleIdDeduplicationTests(unittest.TestCase):
    """Tests for oracle_id-based deduplication of Universes Beyond variants.

    When the same card appears in Scryfall with different names (e.g., alternate
    art, alternate universe printings), they share the same oracle_id. The
    sweep_oracle_id_duplicates.py script groups commanders by oracle_id and
    merges those with the same oracle_id into a canonical entry.

    Example: "Esika, God of the Tree" and "The Prismatic Bridge" are alternate
    names for the same card (same oracle_id). Without deduplication, they would
    create two separate commander entries. After sweep_oracle_id_duplicates.py,
    only one canonical entry exists.
    """

    def test_oracle_id_dedup_requires_scryfall_data(self) -> None:
        """Oracle ID deduplication depends on legal_commander_pairings.json from Scryfall."""
        # This test documents the dependency on the legal_commander_pairings.json
        # which is generated by generate_legal_commander_pairings.py from Scryfall
        data_path = Path(__file__).resolve().parents[1] / "data" / "legal_commander_pairings.json"
        if not data_path.exists():
            self.skipTest("legal_commander_pairings.json not available")

        # If the file exists, verify it has the expected structure
        payload = json.loads(data_path.read_text())
        self.assertIn("legal_pairs", payload)
        pairs = payload.get("legal_pairs") or []
        self.assertGreater(len(pairs), 0)


class IngestionJobLifecycleTests(unittest.TestCase):
    def test_claim_ingestion_job_sends_update(self) -> None:
        client = Mock()
        client.update.return_value = [{"id": "job-1"}]
        result = claim_ingestion_job(client, "job-1", github_run_id=99)
        self.assertTrue(result)
        client.update.assert_called_once()
        call_args = client.update.call_args
        self.assertEqual(call_args.args[0], "ingestion_jobs")
        self.assertEqual(call_args.args[1]["status"], "running")
        self.assertEqual(call_args.args[1]["github_run_id"], 99)

    def test_claim_ingestion_job_returns_false_on_empty(self) -> None:
        client = Mock()
        client.update.return_value = []
        result = claim_ingestion_job(client, "job-1", github_run_id=0)
        self.assertFalse(result)

    def test_claim_ingestion_job_raises_on_operational_error(self) -> None:
        client = Mock()
        client.update.side_effect = ConnectionError("Supabase unreachable")
        with self.assertRaises(ConnectionError):
            claim_ingestion_job(client, "job-1", github_run_id=0)

    @patch.dict(
        os.environ,
        {
            "TOPDECK_API_KEY": "topdeck-key",
            "SUPABASE_SERVICE_KEY": "supabase-key",
            "SUPABASE_URL": "https://test.supabase.co",
        },
        clear=False,
    )
    @patch("ingest._run_ingestion")
    @patch("ingest.update_ingestion_heartbeat")
    @patch("ingest.claim_ingestion_job")
    @patch("ingest.DataIngester")
    @patch("ingest.SupabaseClient")
    @patch("ingest.TopDeckClient")
    @patch("ingest.load_local_env")
    def test_main_exits_with_distinct_code_when_job_already_claimed(
        self,
        mock_load_local_env: Mock,
        mock_topdeck_client: Mock,
        mock_supabase_client: Mock,
        mock_data_ingester: Mock,
        mock_claim_ingestion_job: Mock,
        mock_update_ingestion_heartbeat: Mock,
        mock_run_ingestion: Mock,
    ) -> None:
        mock_claim_ingestion_job.return_value = False

        with patch.object(sys, "argv", ["ingest.py", "--job-id", "job-1"]):
            with self.assertRaises(SystemExit) as exc:
                main()

        self.assertEqual(exc.exception.code, INGESTION_JOB_ALREADY_CLAIMED_EXIT_CODE)
        mock_update_ingestion_heartbeat.assert_not_called()
        mock_run_ingestion.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "TOPDECK_API_KEY": "topdeck-key",
            "SUPABASE_SERVICE_KEY": "supabase-key",
            "SUPABASE_URL": "https://test.supabase.co",
        },
        clear=False,
    )
    @patch("ingest._run_ingestion")
    @patch("ingest.update_ingestion_heartbeat")
    @patch("ingest.claim_ingestion_job")
    @patch("ingest.DataIngester")
    @patch("ingest.SupabaseClient")
    @patch("ingest.TopDeckClient")
    @patch("ingest.load_local_env")
    def test_main_exits_when_claim_ingestion_job_errors(
        self,
        mock_load_local_env: Mock,
        mock_topdeck_client: Mock,
        mock_supabase_client: Mock,
        mock_data_ingester: Mock,
        mock_claim_ingestion_job: Mock,
        mock_update_ingestion_heartbeat: Mock,
        mock_run_ingestion: Mock,
    ) -> None:
        mock_claim_ingestion_job.side_effect = ConnectionError("Supabase unreachable")

        with patch.object(sys, "argv", ["ingest.py", "--job-id", "job-1"]):
            with self.assertRaises(SystemExit) as exc:
                main()

        self.assertEqual(exc.exception.code, 1)
        mock_claim_ingestion_job.assert_called_once()
        mock_update_ingestion_heartbeat.assert_not_called()
        mock_run_ingestion.assert_not_called()

    def test_fail_ingestion_job_truncates_error(self) -> None:
        client = Mock()
        fail_ingestion_job(client, "job-1", "x" * 3000)
        call_args = client.update.call_args
        self.assertLessEqual(len(call_args.args[1]["error_text"]), 2000)

    def test_complete_ingestion_job_sets_completed_status(self) -> None:
        client = Mock()
        complete_ingestion_job(client, "job-1", {"duration_seconds": 42.5})
        call_args = client.update.call_args
        self.assertEqual(call_args.args[1]["status"], "completed")
        self.assertEqual(call_args.args[1]["duration_seconds"], 42.5)


if __name__ == "__main__":
    unittest.main()
