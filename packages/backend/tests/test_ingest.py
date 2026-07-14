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
    extract_standing_rates,
    INGESTION_JOB_ALREADY_CLAIMED_EXIT_CODE,
    load_commander_oracle_aliases,
    normalize_commander_name,
    resolve_record_fields,
    sanitize_commander_payload,
    SupabaseClient,
    claim_ingestion_job,
    complete_ingestion_job,
    fail_ingestion_job,
    main,
)


class ResolveRecordFieldsTests(unittest.TestCase):
    def test_uses_explicit_wins_losses_draws_when_present(self) -> None:
        info = {"wins": 4, "losses": 1, "draws": 0, "points": 20}

        fields = resolve_record_fields(info)

        self.assertEqual(fields, {"wins": 4, "losses": 1, "draws": 0})

    def test_does_not_derive_wins_or_draws_from_points_when_missing(self) -> None:
        # Regression guard: merlion-anniversary-cedh reported points=1866 with no
        # explicit wins/losses/draws. The old fallback (points // 5, points % 5)
        # fabricated a 373-0-1 record, which is impossible for a 5-round event.
        # Point-scoring formulas vary per tournament/organizer and are not a
        # reliable stand-in for an explicit record.
        info = {"wins": None, "losses": None, "draws": None, "points": 1866}

        fields = resolve_record_fields(info)

        self.assertEqual(fields, {})

    def test_uses_only_the_fields_that_are_explicitly_present(self) -> None:
        info = {"wins": 3, "losses": None, "draws": None, "points": 15}

        fields = resolve_record_fields(info)

        self.assertEqual(fields, {"wins": 3})


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

    def test_clean_commander_card_name_falls_back_to_generated_oracle_alias_map(self) -> None:
        # A newly-released Universes Beyond alternate-name printing that hasn't
        # been hand-added to COMMANDER_NAME_ALIASES yet should still resolve
        # via the generated commander_oracle_aliases.json artifact, keyed off
        # the underlying Scryfall oracle_id (see generate_commander_oracle_aliases.py).
        load_commander_oracle_aliases.cache_clear()
        try:
            with patch(
                "ingest.load_commander_oracle_aliases",
                return_value={"Totally Radical Skater": "Nadier, Agent of the Duskenel"},
            ):
                self.assertEqual(
                    clean_commander_card_name("Totally Radical Skater"),
                    "Nadier, Agent of the Duskenel",
                )
        finally:
            load_commander_oracle_aliases.cache_clear()

    def test_hardcoded_alias_takes_precedence_over_generated_alias_map(self) -> None:
        load_commander_oracle_aliases.cache_clear()
        try:
            with patch(
                "ingest.load_commander_oracle_aliases",
                return_value={"Lucas, the Sharpshooter": "Some Other Card"},
            ):
                self.assertEqual(
                    clean_commander_card_name("Lucas, the Sharpshooter"),
                    "Bjorna, Nightfall Alchemist",
                )
        finally:
            load_commander_oracle_aliases.cache_clear()

    def test_load_commander_oracle_aliases_reads_generated_artifact(self) -> None:
        load_commander_oracle_aliases.cache_clear()
        try:
            aliases = load_commander_oracle_aliases()
        finally:
            load_commander_oracle_aliases.cache_clear()
        self.assertIsInstance(aliases, dict)
        self.assertEqual(aliases.get("Chief Jim Hopper"), "Sophina, Spearsage Deserter")

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
