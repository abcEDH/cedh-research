#!/usr/bin/env python3
"""Consume the partner-commander sweep "pending" flag ahead of a maintenance run.

See issue #314. ``sweep_partner_commander_order.py`` marks a durable
``partner_commander_sweep_pending`` flag (via
``mark_partner_commander_sweep_pending()``) whenever it performs a live
commander merge. The ``chain-elo`` job in ``ci-backend-ingestion.yml`` can
skip dispatching a maintenance refresh when an Elo job is already in flight
-- and if that in-flight job has already passed its own commander-view
rebuild step, the sweep's merges land after it. The materialized commander
trend views (``commander_weekly_trends``, ``commander_monthly_trends``) and
``player_commander_profiles`` then keep referencing merged-away commander
IDs until some later, unrelated refresh happens to notice.

Every ``ci-backend-maintenance.yml`` run calls this script first, before its
own Elo recompute step. If a sweep was pending, this script forces a
commander materialized-view refresh and a ``player_commander_profiles``
rebuild right here -- even when this maintenance run would otherwise be a
lightweight smoke check -- and clears the flag via
``consume_partner_commander_sweep_pending()``, an atomic read-and-clear RPC.
That guarantees the merge's follow-up refresh eventually happens rather than
being silently dropped. If nothing was pending, this is a fast no-op.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

import requests

from backfill_moxfield_commanders import load_credentials
from supabase_client import SupabaseClient

CONSUME_RPC_NAME = "consume_partner_commander_sweep_pending"
RPC_TIMEOUT_SECONDS = 30


def consume_sweep_pending_flag(client: SupabaseClient) -> bool:
    """Atomically read-and-clear the pending flag. Returns whether it was set.

    Uses the DB-side RPC (backed by a ``FOR UPDATE`` row lock -- see the
    ``20260815020000_partner_commander_sweep_pending.sql`` migration) rather
    than a plain SELECT-then-UPDATE from here, so two concurrent maintenance
    runs can never both observe ``pending=true`` and both force a rebuild
    while leaving the flag cleared only once.
    """
    endpoint = f"{client.url}/rest/v1/rpc/{CONSUME_RPC_NAME}"
    response = requests.post(endpoint, headers=client.headers, json={}, timeout=RPC_TIMEOUT_SECONDS)
    response.raise_for_status()
    return bool(response.json())


def force_commander_view_rebuild(
    client: SupabaseClient,
    *,
    refresh_materialized_views: Callable[[SupabaseClient], int],
    rebuild_player_commander_profiles: Callable[[], None],
) -> None:
    """Force the two commander-derived refreshes the pending flag guarantees.

    Both calls are the same ones a normal ``refresh_mode: full`` maintenance
    dispatch already makes (see ``regional_elo.py``'s
    ``refresh_materialized_views()`` and ``rebuild_player_commander_profiles.py``),
    so running them here on a run that was already going to do so anyway is a
    harmless, idempotent extra pass -- not a second, divergent code path.
    """
    print("Forcing commander materialized-view refresh (pending sweep merge)...")
    refresh_materialized_views(client)
    print("Forcing player_commander_profiles rebuild (pending sweep merge)...")
    rebuild_player_commander_profiles()


def build_arg_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="Consume the partner-commander sweep pending flag ahead of a maintenance run."
    )


def main() -> None:
    build_arg_parser().parse_args()

    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)

    pending = consume_sweep_pending_flag(client)
    print(f"sweep_pending_consumed={pending}")

    if not pending:
        return

    # Imported lazily so a run that finds nothing pending (the common case)
    # never pays for regional_elo.py's heavier import chain, and so tests of
    # the "nothing pending" path don't need those modules importable at all.
    from rebuild_player_commander_profiles import main as rebuild_profiles_main
    from regional_elo import refresh_materialized_views as refresh_mvs

    force_commander_view_rebuild(
        client,
        refresh_materialized_views=refresh_mvs,
        rebuild_player_commander_profiles=rebuild_profiles_main,
    )


if __name__ == "__main__":
    main()
