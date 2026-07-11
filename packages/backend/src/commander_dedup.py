#!/usr/bin/env python3
"""Commander deduplication helpers for partner pairs and oracle_id variants."""

from __future__ import annotations

import requests

from ingest import (
    SupabaseClient,
    clean_commander_card_name,
)


def canonical_pair_key(names: list[str]) -> tuple[str, ...]:
    """Return sorted pair key for deduplication matching."""
    cleaned = [clean_commander_card_name(name) for name in names if name and name.strip()]
    return tuple(sorted(cleaned))


def repoint_tournament_entries(
    client: SupabaseClient,
    source_commander_id: str,
    target_commander_id: str,
) -> None:
    """Repoint all tournament entries from source commander to target commander."""
    endpoint = f"{client.url}/rest/v1/tournament_entries"
    response = requests.patch(
        endpoint,
        headers=client.headers,
        params={"commander_id": f"eq.{source_commander_id}"},
        json={"commander_id": target_commander_id},
        timeout=60,
    )
    response.raise_for_status()


def repoint_commander_matchups(
    client: SupabaseClient,
    source_commander_id: str,
    target_commander_id: str,
) -> None:
    """Repoint commander_matchups rows from source commander to target commander.

    commander_matchups.commander_id and .opponent_commander_id both have
    non-cascading foreign keys to commanders(id). Deleting a commander row that
    still has matchup rows pointing at it (via either column) fails the DELETE
    with a foreign-key violation - after any tournament_entries repoint has
    already committed, leaving a half-merged duplicate. Must be called before
    delete_commander_row() for any merge that could touch matchup data.
    """
    endpoint = f"{client.url}/rest/v1/commander_matchups"
    for column in ("commander_id", "opponent_commander_id"):
        response = requests.patch(
            endpoint,
            headers=client.headers,
            params={column: f"eq.{source_commander_id}"},
            json={column: target_commander_id},
            timeout=60,
        )
        response.raise_for_status()


def update_commander_row(
    client: SupabaseClient,
    commander_id: str,
    target_name: str,
    target_order: tuple[str, str] | None = None,
    oracle_ids: list[str] | None = None,
) -> None:
    """Update a commander row with new name and/or oracle_ids."""
    endpoint = f"{client.url}/rest/v1/commanders"
    update_data = {"name": target_name}
    if target_order:
        update_data["commander_names"] = list(target_order)
    if oracle_ids is not None:
        update_data["oracle_ids"] = oracle_ids

    response = requests.patch(
        endpoint,
        headers=client.headers,
        params={"id": f"eq.{commander_id}"},
        json=update_data,
        timeout=60,
    )
    response.raise_for_status()


def delete_commander_row(client: SupabaseClient, commander_id: str) -> None:
    """Delete a commander row."""
    endpoint = f"{client.url}/rest/v1/commanders"
    response = requests.delete(
        endpoint,
        headers=client.headers,
        params={"id": f"eq.{commander_id}"},
        timeout=60,
    )
    response.raise_for_status()


__all__ = [
    "canonical_pair_key",
    "repoint_tournament_entries",
    "repoint_commander_matchups",
    "update_commander_row",
    "delete_commander_row",
]
