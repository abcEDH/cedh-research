"""Tests for issue #314: guaranteeing a maintenance refresh after a live
partner-commander sweep via a durable "pending" flag.

``sweep_partner_commander_order.py`` marks the flag when it merges a
duplicate commander live (see ``test_sweep_partner_commander_order.py``'s
``MarkSweepPendingTests``). This module covers the consuming side:
``consume_partner_commander_sweep_pending.py``, which
``ci-backend-maintenance.yml`` runs at the start of every maintenance job so
that even a run chain-elo would otherwise have skipped (the
already-in-flight-Elo-job path) still guarantees a commander-view /
``player_commander_profiles`` rebuild.
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    import requests as requests_module
except ModuleNotFoundError:
    requests_module = types.ModuleType("requests")
    requests_module.get = Mock()
    requests_module.post = Mock()
    requests_module.patch = Mock()
    requests_module.delete = Mock()
    requests_module.exceptions = types.SimpleNamespace(
        ConnectionError=ConnectionError,
        Timeout=TimeoutError,
        ReadTimeout=TimeoutError,
        JSONDecodeError=ValueError,
        HTTPError=RuntimeError,
        RequestException=Exception,
    )
    sys.modules["requests"] = requests_module

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import consume_partner_commander_sweep_pending as consume_module  # noqa: E402
from consume_partner_commander_sweep_pending import (  # noqa: E402
    consume_sweep_pending_flag,
    force_commander_view_rebuild,
    main,
)


class ConsumeSweepPendingFlagTests(unittest.TestCase):
    def _client(self) -> Mock:
        client = Mock()
        client.url = "https://example.supabase.co"
        client.headers = {"apikey": "test"}
        return client

    def test_posts_to_the_consume_rpc_and_returns_true_when_pending(self) -> None:
        client = self._client()
        with patch.object(consume_module, "requests") as mock_requests:
            mock_requests.post.return_value = Mock(raise_for_status=Mock(), json=Mock(return_value=True))

            result = consume_sweep_pending_flag(client)

        self.assertTrue(result)
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        self.assertIn("consume_partner_commander_sweep_pending", call_args.args[0])
        self.assertEqual(call_args.kwargs["headers"], client.headers)

    def test_returns_false_when_nothing_was_pending(self) -> None:
        client = self._client()
        with patch.object(consume_module, "requests") as mock_requests:
            mock_requests.post.return_value = Mock(raise_for_status=Mock(), json=Mock(return_value=False))

            result = consume_sweep_pending_flag(client)

        self.assertFalse(result)


class ForceCommanderViewRebuildTests(unittest.TestCase):
    def test_calls_both_refreshes(self) -> None:
        client = Mock()
        refresh_mvs = Mock(return_value=4)
        rebuild_profiles = Mock()

        force_commander_view_rebuild(
            client,
            refresh_materialized_views=refresh_mvs,
            rebuild_player_commander_profiles=rebuild_profiles,
        )

        refresh_mvs.assert_called_once_with(client)
        rebuild_profiles.assert_called_once_with()


class MainAlreadyInFlightEloJobTests(unittest.TestCase):
    """Covers the acceptance criterion: exercise the already-in-flight-Elo-job
    path -- chain-elo exited 0 without dispatching, but the pending flag
    causes the *next* maintenance run to pick up the merge's follow-up
    refresh anyway.
    """

    def _run_main_with(self, *, consumed: bool, refresh_mvs: Mock, rebuild_profiles_main: Mock) -> Mock:
        client = Mock()
        client.url = "https://example.supabase.co"
        client.headers = {"apikey": "test"}

        fake_regional_elo = types.ModuleType("regional_elo")
        fake_regional_elo.refresh_materialized_views = refresh_mvs
        fake_rebuild_profiles = types.ModuleType("rebuild_player_commander_profiles")
        fake_rebuild_profiles.main = rebuild_profiles_main

        with (
            patch.object(consume_module, "load_credentials", return_value=("url", "key")),
            patch.object(consume_module, "SupabaseClient", return_value=client),
            patch.object(consume_module, "requests") as mock_requests,
            patch.dict(
                sys.modules,
                {"regional_elo": fake_regional_elo, "rebuild_player_commander_profiles": fake_rebuild_profiles},
            ),
            patch.object(sys, "argv", ["consume_partner_commander_sweep_pending.py"]),
        ):
            mock_requests.post.return_value = Mock(raise_for_status=Mock(), json=Mock(return_value=consumed))
            main()

        return mock_requests

    def test_forces_rebuild_when_a_sweep_merge_was_pending(self) -> None:
        """The scenario #314 exists for: chain-elo's enqueue_elo_refresh
        returned null (an Elo job was already in flight and may have already
        passed its commander-view rebuild), so no maintenance workflow was
        dispatched off that ingestion run. The *next* maintenance run --
        whatever triggers it -- must still see the flag and force the
        rebuild rather than silently reflecting merged-away commander IDs.
        """
        refresh_mvs = Mock(return_value=4)
        rebuild_profiles_main = Mock()

        mock_requests = self._run_main_with(
            consumed=True, refresh_mvs=refresh_mvs, rebuild_profiles_main=rebuild_profiles_main
        )

        mock_requests.post.assert_called_once()
        refresh_mvs.assert_called_once()
        rebuild_profiles_main.assert_called_once_with()

    def test_no_rebuild_forced_when_nothing_was_pending(self) -> None:
        """The common case: no sweep merge happened, so consuming the flag is
        a fast no-op and the heavier commander-view/profile rebuild imports
        are never touched.
        """
        refresh_mvs = Mock(return_value=0)
        rebuild_profiles_main = Mock()

        self._run_main_with(consumed=False, refresh_mvs=refresh_mvs, rebuild_profiles_main=rebuild_profiles_main)

        refresh_mvs.assert_not_called()
        rebuild_profiles_main.assert_not_called()


if __name__ == "__main__":
    unittest.main()
