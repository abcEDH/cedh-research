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

Also covers the token-based ack (post-review hardening of the original
read-and-clear RPC): the flag is only cleared after this run's rebuild
succeeds, and only if the token it read is still the one on file -- so a
failed rebuild leaves the flag pending for the next run to retry, and a
newer merge marking the flag again mid-rebuild isn't clobbered by a stale
ack.
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
    acknowledge_sweep_pending,
    force_commander_view_rebuild,
    main,
    read_sweep_pending_state,
)

TOKEN = "11111111-1111-1111-1111-111111111111"


class ReadSweepPendingStateTests(unittest.TestCase):
    def _client(self) -> Mock:
        client = Mock()
        client.url = "https://example.supabase.co"
        client.headers = {"apikey": "test"}
        return client

    def test_reads_pending_and_token_via_plain_select(self) -> None:
        client = self._client()
        with patch.object(consume_module, "requests") as mock_requests:
            mock_requests.get.return_value = Mock(
                raise_for_status=Mock(), json=Mock(return_value=[{"pending": True, "token": TOKEN}])
            )

            pending, token = read_sweep_pending_state(client)

        self.assertTrue(pending)
        self.assertEqual(token, TOKEN)
        mock_requests.get.assert_called_once()
        call_args = mock_requests.get.call_args
        self.assertIn("partner_commander_sweep_state", call_args.args[0])
        self.assertEqual(call_args.kwargs["params"]["select"], "pending,token")

    def test_returns_false_and_no_token_when_nothing_was_pending(self) -> None:
        client = self._client()
        with patch.object(consume_module, "requests") as mock_requests:
            mock_requests.get.return_value = Mock(
                raise_for_status=Mock(), json=Mock(return_value=[{"pending": False, "token": None}])
            )

            pending, token = read_sweep_pending_state(client)

        self.assertFalse(pending)
        self.assertIsNone(token)

    def test_returns_false_when_row_is_missing(self) -> None:
        client = self._client()
        with patch.object(consume_module, "requests") as mock_requests:
            mock_requests.get.return_value = Mock(raise_for_status=Mock(), json=Mock(return_value=[]))

            pending, token = read_sweep_pending_state(client)

        self.assertFalse(pending)
        self.assertIsNone(token)


class AcknowledgeSweepPendingTests(unittest.TestCase):
    def _client(self) -> Mock:
        client = Mock()
        client.url = "https://example.supabase.co"
        client.headers = {"apikey": "test"}
        return client

    def test_posts_the_token_to_the_consume_rpc(self) -> None:
        client = self._client()
        with patch.object(consume_module, "requests") as mock_requests:
            mock_requests.post.return_value = Mock(raise_for_status=Mock(), json=Mock(return_value=True))

            result = acknowledge_sweep_pending(client, TOKEN)

        self.assertTrue(result)
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        self.assertIn("consume_partner_commander_sweep_pending", call_args.args[0])
        self.assertEqual(call_args.kwargs["json"], {"p_token": TOKEN})

    def test_returns_false_when_token_is_stale(self) -> None:
        """A newer mark_pending happened since this run read the token (e.g.
        a fresh live merge landed while this run's rebuild was in flight).
        The RPC's compare-and-clear then matches nothing and reports false --
        this run must not treat that as having consumed anything.
        """
        client = self._client()
        with patch.object(consume_module, "requests") as mock_requests:
            mock_requests.post.return_value = Mock(raise_for_status=Mock(), json=Mock(return_value=False))

            result = acknowledge_sweep_pending(client, TOKEN)

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
    refresh anyway. Also covers the token-based ack: no ack on a failed
    rebuild, and a stale-token ack is tolerated rather than raising.
    """

    def _run_main_with(
        self,
        *,
        pending: bool,
        token: str | None = TOKEN,
        refresh_mvs: Mock,
        rebuild_profiles_main: Mock,
        ack_result: bool = True,
    ) -> Mock:
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
            mock_requests.get.return_value = Mock(
                raise_for_status=Mock(), json=Mock(return_value=[{"pending": pending, "token": token}])
            )
            mock_requests.post.return_value = Mock(raise_for_status=Mock(), json=Mock(return_value=ack_result))
            main()

        return mock_requests

    def test_forces_rebuild_and_acks_with_the_read_token_when_a_sweep_merge_was_pending(self) -> None:
        """The scenario #314 exists for: chain-elo's enqueue_elo_refresh
        returned null (an Elo job was already in flight and may have already
        passed its commander-view rebuild), so no maintenance workflow was
        dispatched off that ingestion run. The *next* maintenance run --
        whatever triggers it -- must still see the flag, force the rebuild,
        and ack with the token it read.
        """
        refresh_mvs = Mock(return_value=4)
        rebuild_profiles_main = Mock()

        mock_requests = self._run_main_with(
            pending=True, refresh_mvs=refresh_mvs, rebuild_profiles_main=rebuild_profiles_main
        )

        mock_requests.get.assert_called_once()
        refresh_mvs.assert_called_once()
        rebuild_profiles_main.assert_called_once_with()
        mock_requests.post.assert_called_once()
        self.assertEqual(mock_requests.post.call_args.kwargs["json"], {"p_token": TOKEN})

    def test_no_rebuild_or_ack_when_nothing_was_pending(self) -> None:
        """The common case: no sweep merge happened, so reading the flag is a
        fast no-op and the heavier commander-view/profile rebuild imports are
        never touched, nor is the ack RPC called.
        """
        refresh_mvs = Mock(return_value=0)
        rebuild_profiles_main = Mock()

        mock_requests = self._run_main_with(
            pending=False, token=None, refresh_mvs=refresh_mvs, rebuild_profiles_main=rebuild_profiles_main
        )

        refresh_mvs.assert_not_called()
        rebuild_profiles_main.assert_not_called()
        mock_requests.post.assert_not_called()

    def test_ack_is_never_sent_when_the_forced_rebuild_fails(self) -> None:
        """If the forced rebuild raises, the flag must stay pending so the
        next maintenance run retries it -- acking here would silently lose
        the refresh request the pending flag exists to guarantee.
        """
        refresh_mvs = Mock(side_effect=RuntimeError("materialized view refresh failed"))
        rebuild_profiles_main = Mock()

        with self.assertRaises(RuntimeError):
            self._run_main_with(pending=True, refresh_mvs=refresh_mvs, rebuild_profiles_main=rebuild_profiles_main)

        rebuild_profiles_main.assert_not_called()

    def test_stale_token_ack_does_not_raise(self) -> None:
        """A newer merge marked the flag again while this run's rebuild was
        in flight. The compare-and-clear ack reports false; main() must
        treat that as a benign, expected outcome (log and continue) rather
        than raising or retrying the clear itself.
        """
        refresh_mvs = Mock(return_value=1)
        rebuild_profiles_main = Mock()

        mock_requests = self._run_main_with(
            pending=True,
            refresh_mvs=refresh_mvs,
            rebuild_profiles_main=rebuild_profiles_main,
            ack_result=False,
        )

        refresh_mvs.assert_called_once()
        rebuild_profiles_main.assert_called_once_with()
        mock_requests.post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
