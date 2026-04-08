#!/usr/bin/env python3
"""Backfill commanders for historical Moxfield decklist entries."""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
import time
from pathlib import Path

import requests

from ingest import (
    SupabaseClient,
    clean_commander_card_name,
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
    player_topdeck_id: str | None = None,
    order_by: str = "tournament-date",
    order_direction: str = "desc",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    decklist_filter = "ilike.*moxfield.com*"
    if embedded_only:
        decklist_filter = "ilike.*~~Commanders~~*moxfield.com*"

    select = "id,decklist_url,commanders(name),players(topdeck_id),tournaments(topdeck_tid,start_date)"
    filters = {}
    if not include_known:
        select = "id,decklist_url,commanders!inner(name),players!inner(topdeck_id),tournaments!inner(topdeck_tid,start_date)"
        filters["commanders.name"] = 'in.("Unknown Commander","Moxfield Deck")'
    if player_topdeck_id:
        filters["players.topdeck_id"] = f"eq.{player_topdeck_id}"
    date_filters = []
    if start_date:
        date_filters.append(f"gte.{start_date}")
    if end_date:
        date_filters.append(f"lte.{end_date}")
    if date_filters:
        filters["tournaments.start_date"] = date_filters

    if order_by == "tournament-date":
        order = f"tournaments(start_date).{order_direction}"
    else:
        order = f"created_at.{order_direction}"

    return client.select(
        "tournament_entries",
        {
            "select": select,
            "decklist_url": decklist_filter,
            "order": order,
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


def upsert_commanders(client: SupabaseClient, commander_data: dict[str, list[str]]) -> dict[str, str]:
    if not commander_data:
        return {}

    result = client.upsert(
        "commanders",
        [
            {
                "name": name,
                "commander_names": [clean_commander_card_name(value) for value in (names or [name])],
            }
            for name, names in commander_data.items()
        ],
        on_conflict="name",
    )
    return {row["name"]: row["id"] for row in result}


def export_unresolved_csv(
    client: SupabaseClient,
    *,
    output_path: Path,
    page_size: int,
    limit: int | None,
) -> None:
    written = 0
    offset = 0
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["entry_id", "decklist_url", "commander_names"])
        writer.writeheader()
        while True:
            rows = fetch_moxfield_entries(
                client,
                limit=page_size,
                offset=offset,
                embedded_only=False,
                include_known=False,
                player_topdeck_id=None,
                order_by="tournament-date",
                order_direction="desc",
                start_date=None,
                end_date=None,
            )
            if not rows:
                break

            for row in rows:
                writer.writerow({
                    "entry_id": row["id"],
                    "decklist_url": row.get("decklist_url") or "",
                    "commander_names": "",
                })
                written += 1
                if limit and written >= limit:
                    print(f"Exported {written} unresolved Moxfield rows to {output_path}")
                    return

            offset += len(rows)

    print(f"Exported {written} unresolved Moxfield rows to {output_path}")


def import_resolved_csv(
    client: SupabaseClient,
    *,
    input_path: Path,
    commander_delimiter: str,
    dry_run: bool,
) -> None:
    rows_to_update: list[tuple[str, str]] = []
    commander_data: dict[str, list[str]] = {}
    skipped = 0

    with input_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            entry_id = (row.get("entry_id") or "").strip()
            raw_commander_names = (row.get("commander_names") or "").strip()
            if not entry_id or not raw_commander_names:
                skipped += 1
                continue

            commanders = [
                clean_commander_card_name(commander)
                for commander in raw_commander_names.split(commander_delimiter)
                if commander.strip()
            ]
            commander_name = normalize_commander_name(commanders)
            if commander_name in PLACEHOLDER_COMMANDERS:
                skipped += 1
                continue

            commander_data[commander_name] = commanders
            rows_to_update.append((entry_id, commander_name))

    commander_ids = {} if dry_run else upsert_commanders(client, commander_data)
    updated = 0
    for entry_id, commander_name in rows_to_update:
        if dry_run:
            updated += 1
            continue

        commander_id = commander_ids.get(commander_name)
        if not commander_id:
            skipped += 1
            continue
        client.update("tournament_entries", {"commander_id": commander_id}, {"id": f"eq.{entry_id}"})
        updated += 1

    print(f"Imported {updated} resolved rows from {input_path}; skipped={skipped} dry_run={dry_run}")


def relation_value(row: dict, key: str) -> dict:
    value = row.get(key)
    if isinstance(value, list):
        return value[0] if value else {}
    return value if isinstance(value, dict) else {}


def extract_topdeck_deck_page_commanders(page_html: str) -> list[str]:
    names = []
    for tag in re.findall(r"<[^>]*commander-card[^>]*>", page_html):
        match = re.search(r"""data-name=(["'])((?:\\.|(?!\1).)*?)\1""", tag)
        if not match:
            continue
        name = match.group(2)
        decoded = html.unescape(name).strip()
        if decoded and decoded not in names:
            names.append(decoded)
    return names


def fetch_topdeck_deck_page_commanders(
    tournament_id: str,
    player_identifier: str,
    session: requests.Session,
    timeout: float,
) -> list[str]:
    response = session.get(
        f"https://topdeck.gg/deck/{tournament_id}/{player_identifier}",
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "cedh-research/1.0",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return extract_topdeck_deck_page_commanders(response.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill commanders for Moxfield decklist entries")
    parser.add_argument("--limit", type=int, help="Maximum rows to update")
    parser.add_argument("--page-size", type=int, default=250, help="Supabase page size")
    parser.add_argument("--offset", type=int, default=0, help="Initial row offset")
    parser.add_argument("--start-date", help="Only process tournaments on or after this date")
    parser.add_argument("--end-date", help="Only process tournaments on or before this date")
    parser.add_argument(
        "--order-by",
        choices=["tournament-date", "created-at"],
        default="tournament-date",
        help="Order unresolved rows for processing",
    )
    parser.add_argument(
        "--order-direction",
        choices=["asc", "desc"],
        default="desc",
        help="Sort direction for unresolved rows",
    )
    parser.add_argument("--include-known", action="store_true", help="Update rows that already have non-placeholder commanders")
    parser.add_argument("--embedded-only", action="store_true", help="Only process imported deck text with embedded commander sections")
    parser.add_argument("--resolve-moxfield-api", action="store_true", help="Fetch pure Moxfield URLs from the Moxfield API")
    parser.add_argument("--resolve-moxfield-page", action="store_true", help="Scrape pure Moxfield URLs from public deck pages")
    parser.add_argument("--resolve-topdeck-deck-page", action="store_true", help="Scrape TopDeck's /deck/{tournament}/{player} page")
    parser.add_argument("--player-topdeck-id", help="Only process entries for one TopDeck player id")
    parser.add_argument("--max-moxfield-requests", type=int, help="Stop after this many Moxfield URL requests")
    parser.add_argument("--max-topdeck-requests", type=int, help="Stop after this many TopDeck deck page requests")
    parser.add_argument("--topdeck-timeout", type=float, default=10, help="Seconds before a TopDeck deck page request times out")
    parser.add_argument("--max-api-requests", type=int, help="Deprecated alias for --max-moxfield-requests")
    parser.add_argument("--sleep", type=float, default=0.2, help="Seconds to sleep between Moxfield URL requests")
    parser.add_argument("--export-unresolved-csv", type=Path, help="Write unresolved Moxfield entries to CSV")
    parser.add_argument("--import-resolved-csv", type=Path, help="Read resolved commander mappings from CSV")
    parser.add_argument("--commander-delimiter", default="|", help="Delimiter for commander_names in import CSV")
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

    if args.export_unresolved_csv:
        export_unresolved_csv(
            client,
            output_path=args.export_unresolved_csv,
            page_size=args.page_size,
            limit=args.limit,
        )
        return

    if args.import_resolved_csv:
        import_resolved_csv(
            client,
            input_path=args.import_resolved_csv,
            commander_delimiter=args.commander_delimiter,
            dry_run=args.dry_run,
        )
        return

    http = requests.Session()

    scanned = 0
    updated = 0
    skipped_known = 0
    unresolved = 0
    repeated_unresolved = 0
    moxfield_requests = 0
    topdeck_requests = 0
    offset = args.offset
    attempted_unresolved_ids: set[str] = set()

    while True:
        rows = fetch_moxfield_entries(
            client,
            limit=args.page_size,
            offset=offset,
            embedded_only=args.embedded_only,
            include_known=args.include_known,
            player_topdeck_id=args.player_topdeck_id,
            order_by=args.order_by,
            order_direction=args.order_direction,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        if not rows:
            break

        commander_data: dict[str, list[str]] = {}
        pending_updates: list[tuple[str, str]] = []
        page_skipped = 0
        page_unresolved = 0
        page_processed = 0

        for row in rows:
            scanned += 1
            page_processed += 1
            existing_name = commander_name_for_entry(row)
            if existing_name not in PLACEHOLDER_COMMANDERS and not args.include_known:
                skipped_known += 1
                page_skipped += 1
                continue
            if row["id"] in attempted_unresolved_ids:
                repeated_unresolved += 1
                page_skipped += 1
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
            if commander_name in PLACEHOLDER_COMMANDERS and args.resolve_topdeck_deck_page:
                if args.max_topdeck_requests is not None and topdeck_requests >= args.max_topdeck_requests:
                    break
                player_topdeck_id = relation_value(row, "players").get("topdeck_id")
                tournament_topdeck_id = relation_value(row, "tournaments").get("topdeck_tid")
                if player_topdeck_id and tournament_topdeck_id:
                    try:
                        commanders = fetch_topdeck_deck_page_commanders(
                            tournament_topdeck_id,
                            player_topdeck_id,
                            http,
                            args.topdeck_timeout,
                        )
                    except requests.RequestException as exc:
                        print(f"TopDeck deck page fetch failed for entry {row['id']}: {exc}")
                    topdeck_requests += 1
                    commander_name = normalize_commander_name(commanders)

            if commander_name in PLACEHOLDER_COMMANDERS:
                attempted_unresolved_ids.add(row["id"])
                unresolved += 1
                page_unresolved += 1
                continue

            commander_data[commander_name] = commanders
            pending_updates.append((row["id"], commander_name))

            if args.limit and updated + len(pending_updates) >= args.limit:
                break

        if commander_data and not args.dry_run:
            commander_ids = upsert_commanders(client, commander_data)
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
            f"repeated_unresolved={repeated_unresolved} skipped_known={skipped_known} "
            f"moxfield_requests={moxfield_requests} topdeck_requests={topdeck_requests}",
            flush=True,
        )

        if args.limit and updated >= args.limit:
            break
        if max_moxfield_requests is not None and moxfield_requests >= max_moxfield_requests and not args.embedded_only:
            break
        if args.max_topdeck_requests is not None and topdeck_requests >= args.max_topdeck_requests:
            break

        if args.dry_run or args.include_known:
            offset += page_processed
        else:
            offset += page_unresolved + page_skipped

    print(
        f"Done. scanned={scanned} updated={updated} unresolved={unresolved} "
        f"repeated_unresolved={repeated_unresolved} skipped_known={skipped_known} moxfield_requests={moxfield_requests} "
        f"topdeck_requests={topdeck_requests} dry_run={args.dry_run}",
        flush=True,
    )


if __name__ == "__main__":
    main()
