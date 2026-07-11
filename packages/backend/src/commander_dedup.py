#!/usr/bin/env python3
"""Commander deduplication helpers for partner pairs and oracle_id variants."""

from __future__ import annotations

import requests

from ingest import (
    clean_commander_card_name,
    SupabaseClient,
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
    "update_commander_row",
    "delete_commander_row",
]
