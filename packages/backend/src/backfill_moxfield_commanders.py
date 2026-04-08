#!/usr/bin/env python3
"""Backfill commanders for historical Moxfield decklist entries."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import requests

from ingest import (
    SupabaseClient,
    extract_commanders,
    normalize_commander_name,
)

PLACEHOLDER_COMMANDERS = {"Unknown Commander", "Moxfield Deck"}


def load_credentials() -> tuple[str, str]:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    for env_path in (Path(".env"), Path("packages/backend/.env")):
        if supabase_url and supabase_key:
            break
        if not env_path.exists():
            continue

        for line in env_path.read_text().splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            key, value = line.strip().split("=", 1)
            value = value.strip().strip("'\"")
            if key == "SUPABASE_URL" and not supabase_url:
                supabase_url = value
            elif key == "SUPABASE_SERVICE_KEY" and not supabase_key:
                supabase_key = value

    if not supabase_url or not supabase_key:
        raise SystemExit("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

    return supabase_url, supabase_key


def fetch_moxfield_entries(
    client: SupabaseClient,
    *,
    limit: int,
    offset: int,
    embedded_only: bool,
    include_known: bool,
) -> list[dict]:
    decklist_filter = "ilike.*moxfield.com*"
    if embedded_only:
        decklist_filter = "ilike.*~~Commanders~~*moxfield.com*"

    select = "id,decklist_url,commanders(name)"
    filters = {}
    if not include_known:
        select = "id,decklist_url,commanders!inner(name)"
        filters["commanders.name"] = 'in.("Unknown Commander","Moxfield Deck")'

    return client.select(
        "tournament_entries",
        {
            "select": select,
            "decklist_url": decklist_filter,
            "order": "created_at.asc",
            "limit": limit,
            "offset": offset,
            **filters,
        },
    )


def commander_name_for_entry(entry: dict) -> str | None:
    commander = entry.get("commanders")
    if isinstance(commander, list):
        commander = commander[0] if commander else None
    if not isinstance(commander, dict):
        return None
    name = commander.get("name")
    return name if isinstance(name, str) else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill commanders for Moxfield decklist entries")
    parser.add_argument("--limit", type=int, help="Maximum rows to update")
    parser.add_argument("--page-size", type=int, default=250, help="Supabase page size")
    parser.add_argument("--offset", type=int, default=0, help="Initial row offset")
    parser.add_argument("--include-known", action="store_true", help="Update rows that already have non-placeholder commanders")
    parser.add_argument("--embedded-only", action="store_true", help="Only process imported deck text with embedded commander sections")
    parser.add_argument("--resolve-moxfield-api", action="store_true", help="Fetch pure Moxfield URLs from the Moxfield API")
    parser.add_argument("--resolve-moxfield-page", action="store_true", help="Scrape pure Moxfield URLs from public deck pages")
    parser.add_argument("--max-moxfield-requests", type=int, help="Stop after this many Moxfield URL requests")
    parser.add_argument("--max-api-requests", type=int, help="Deprecated alias for --max-moxfield-requests")
    parser.add_argument("--sleep", type=float, default=0.2, help="Seconds to sleep between Moxfield URL requests")
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes")
    args = parser.parse_args()
    max_moxfield_requests = args.max_moxfield_requests
    if max_moxfield_requests is None:
        max_moxfield_requests = args.max_api_requests
    moxfield_source = "api"
    if args.resolve_moxfield_api and args.resolve_moxfield_page:
        moxfield_source = "auto"
    elif args.resolve_moxfield_page:
        moxfield_source = "page"

    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)
    http = requests.Session()

    scanned = 0
    updated = 0
    skipped_known = 0
    unresolved = 0
    moxfield_requests = 0
    offset = args.offset

    while True:
        rows = fetch_moxfield_entries(
            client,
            limit=args.page_size,
            offset=offset,
            embedded_only=args.embedded_only,
            include_known=args.include_known,
        )
        if not rows:
            break

        commander_data: dict[str, list[str]] = {}
        pending_updates: list[tuple[str, str]] = []

        for row in rows:
            scanned += 1
            existing_name = commander_name_for_entry(row)
            if existing_name not in PLACEHOLDER_COMMANDERS and not args.include_known:
                skipped_known += 1
                continue

            decklist = row.get("decklist_url") or ""
            if (
                max_moxfield_requests is not None
                and moxfield_requests >= max_moxfield_requests
                and "~~Commanders~~" not in decklist
            ):
                break

            should_resolve_moxfield = args.resolve_moxfield_api or args.resolve_moxfield_page
            if max_moxfield_requests is not None and moxfield_requests >= max_moxfield_requests:
                should_resolve_moxfield = False

            commanders = extract_commanders(
                decklist,
                resolve_moxfield=should_resolve_moxfield,
                moxfield_session=http,
                moxfield_source=moxfield_source,
            )
            if should_resolve_moxfield and "~~Commanders~~" not in decklist:
                moxfield_requests += 1
                time.sleep(args.sleep)

            commander_name = normalize_commander_name(commanders)
            if commander_name in PLACEHOLDER_COMMANDERS:
                unresolved += 1
                continue

            commander_data[commander_name] = commanders
            pending_updates.append((row["id"], commander_name))

            if args.limit and updated + len(pending_updates) >= args.limit:
                break

        if commander_data and not args.dry_run:
            result = client.upsert(
                "commanders",
                [
                    {"name": name, "commander_names": names or [name]}
                    for name, names in commander_data.items()
                ],
                on_conflict="name",
            )
            commander_ids = {row["name"]: row["id"] for row in result}
            for entry_id, commander_name in pending_updates:
                commander_id = commander_ids.get(commander_name)
                if not commander_id:
                    continue
                client.update("tournament_entries", {"commander_id": commander_id}, {"id": f"eq.{entry_id}"})
                updated += 1
        else:
            updated += len(pending_updates)

        print(
            f"scanned={scanned} updated={updated} unresolved={unresolved} "
            f"skipped_known={skipped_known} moxfield_requests={moxfield_requests}"
        )

        if args.limit and updated >= args.limit:
            break
        if max_moxfield_requests is not None and moxfield_requests >= max_moxfield_requests and not args.embedded_only:
            break

        if args.dry_run or args.include_known or not pending_updates:
            offset += len(rows)

    print(
        f"Done. scanned={scanned} updated={updated} unresolved={unresolved} "
        f"skipped_known={skipped_known} moxfield_requests={moxfield_requests} dry_run={args.dry_run}"
    )


if __name__ == "__main__":
    main()
