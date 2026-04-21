#!/usr/bin/env python3
"""Repair unknown commander entries by re-parsing stored decklist_text."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

from ingest import (
    SUPABASE_REST_BASE,
    SupabaseClient,
    extract_commanders,
    load_local_env,
    normalize_commander_name,
)

logger = logging.getLogger("repair_unknown_commanders_from_decklists")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PAGE_SIZE = 1000
UPSERT_CHUNK_SIZE = 200


def chunked(values: list[Any], size: int) -> list[list[Any]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def fetch_unknown_entries(client: SupabaseClient) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    last_id: str | None = None
    while True:
        filters = {
            "select": "id,decklist_text,commander_id,commanders!inner(name)",
            "order": "id.asc",
            "limit": str(PAGE_SIZE),
            "commanders.name": "eq.Unknown Commander",
        }
        if last_id:
            filters["id"] = f"gt.{last_id}"
        page = client.select("tournament_entries", filters)
        if not page:
            break
        rows.extend(page)
        last_id = page[-1].get("id")
        if len(page) < PAGE_SIZE:
            break
    return rows


def fetch_commander_ids(client: SupabaseClient, commander_names: list[str]) -> dict[str, str]:
    wanted = set(commander_names)
    ids: dict[str, str] = {}
    last_id: str | None = None
    while True:
        filters = {
            "select": "id,name",
            "order": "id.asc",
            "limit": str(PAGE_SIZE),
        }
        if last_id:
            filters["id"] = f"gt.{last_id}"
        page = client.select("commanders", filters)
        if not page:
            break
        for row in page:
            if row.get("name") in wanted and row.get("id"):
                ids[row["name"]] = row["id"]
        last_id = page[-1].get("id")
        if len(page) < PAGE_SIZE:
            break
    return ids


def patch_tournament_entry_commander(
    client: SupabaseClient, entry_id: str, commander_id: str
) -> None:
    endpoint = f"{client.url}/rest/v1/tournament_entries"
    for attempt in range(3):
        try:
            response = requests.patch(
                endpoint,
                headers=client.headers,
                params={"id": f"eq.{entry_id}"},
                json={"commander_id": commander_id},
                timeout=30,
            )
            if response.status_code >= 400:
                logger.error("Supabase error: %s", response.text)
                response.raise_for_status()
            return
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ReadTimeout,
        ) as exc:
            if attempt == 2:
                raise
            wait_seconds = 2**attempt
            logger.warning(
                "Patch failed for %s, retrying in %ss... (%s/3) %s",
                entry_id,
                wait_seconds,
                attempt + 1,
                exc,
            )
            import time

            time.sleep(wait_seconds)


def main() -> None:
    load_local_env()
    supabase_url = os.environ.get("SUPABASE_URL", SUPABASE_REST_BASE)
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_key:
        raise SystemExit("SUPABASE_SERVICE_KEY is required")

    client = SupabaseClient(supabase_url, supabase_key)

    logger.info("Fetching tournament entries with Unknown Commander...")
    unknown_entries = fetch_unknown_entries(client)
    logger.info("Fetched %s Unknown Commander entries", len(unknown_entries))

    repairs: list[dict[str, str]] = []
    commander_names: set[str] = set()
    for row in unknown_entries:
        commander_name = normalize_commander_name(extract_commanders(row.get("decklist_text") or ""))
        if not commander_name or commander_name == "Unknown Commander":
            continue
        repairs.append({"id": row["id"], "commander_name": commander_name})
        commander_names.add(commander_name)

    logger.info("Parsed commander names for %s entries", len(repairs))
    if not repairs:
        logger.info("No repairs needed")
        return

    commander_id_by_name = fetch_commander_ids(client, sorted(commander_names))
    updates = [
        {"id": repair["id"], "commander_id": commander_id_by_name[repair["commander_name"]]}
        for repair in repairs
        if repair["commander_name"] in commander_id_by_name
    ]

    logger.info("Updating %s tournament entries", len(updates))
    updated = 0
    for row in updates:
        patch_tournament_entry_commander(client, row["id"], row["commander_id"])
        updated += 1
        if updated % 100 == 0 or updated == len(updates):
            logger.info("Updated %s/%s entries", updated, len(updates))

    logger.info("Unknown commander repair complete")


if __name__ == "__main__":
    main()
