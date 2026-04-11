#!/usr/bin/env python3
"""Replace stored Moxfield decklist URLs with TopDeck deck URLs when resolvable."""

from __future__ import annotations

import argparse
from pathlib import Path

import requests

from backfill_moxfield_commanders import (
    RedirectedToMoxfieldError,
    TopDeckHttpStatusError,
    classify_bad_moxfield_url,
    fetch_topdeck_deck_page_details,
    load_attempt_cache,
    load_credentials,
    parse_retry_statuses,
    record_attempt,
    relation_value,
    should_skip_cached_attempt,
    summarize_attempt_statuses,
    write_attempt_cache,
)
from ingest import SupabaseClient

DEFAULT_URL_ATTEMPT_CACHE = Path("logs/backfill_topdeck_decklist_urls_attempts.csv")


def fetch_topdeck_url_candidates(
    client: SupabaseClient,
    *,
    limit: int,
    offset: int,
    player_topdeck_id: str | None = None,
    order_by: str = "tournament-date",
    order_direction: str = "desc",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    select = "id,decklist_url,players!inner(topdeck_id),tournaments!inner(topdeck_tid,start_date)"
    filters: dict[str, str | list[str]] = {
        "decklist_url": "ilike.*moxfield.com*",
        "players.topdeck_id": "not.is.null",
        "tournaments.topdeck_tid": "not.is.null",
    }
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
            "order": order,
            "limit": limit,
            "offset": offset,
            **filters,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill TopDeck deck URLs onto tournament entry decklist_url rows")
    parser.add_argument("--limit", type=int, help="Maximum rows to update")
    parser.add_argument("--page-size", type=int, default=250, help="Supabase page size")
    parser.add_argument("--offset", type=int, default=0, help="Initial row offset")
    parser.add_argument("--start-date", help="Only process tournaments on or after this date")
    parser.add_argument("--end-date", help="Only process tournaments on or before this date")
    parser.add_argument(
        "--order-by",
        choices=["tournament-date", "created-at"],
        default="tournament-date",
        help="Order Moxfield rows for processing",
    )
    parser.add_argument(
        "--order-direction",
        choices=["asc", "desc"],
        default="desc",
        help="Sort direction for candidate rows",
    )
    parser.add_argument("--player-topdeck-id", help="Only process entries for one TopDeck player id")
    parser.add_argument("--topdeck-timeout", type=float, default=10, help="Seconds before a TopDeck deck page request times out")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without writing updates")
    parser.add_argument(
        "--attempt-cache",
        type=Path,
        default=DEFAULT_URL_ATTEMPT_CACHE,
        help=f"CSV cache of attempted entry ids (default: {DEFAULT_URL_ATTEMPT_CACHE})",
    )
    parser.add_argument("--retry-transient", action="store_true", help="Retry transient statuses from the attempt cache")
    parser.add_argument(
        "--retry-statuses",
        help="Comma-separated cached statuses to retry exclusively (implies retry_transient)",
    )
    args = parser.parse_args()

    retry_statuses = parse_retry_statuses(args.retry_statuses)
    if retry_statuses is not None:
        args.retry_transient = True

    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)
    attempt_cache = load_attempt_cache(args.attempt_cache)

    http = requests.Session()

    scanned = 0
    updated = 0
    unresolved = 0
    cached_skipped = 0
    bad_url_skipped = 0
    topdeck_requests = 0
    offset = args.offset

    while True:
        rows = fetch_topdeck_url_candidates(
            client,
            limit=args.page_size,
            offset=offset,
            player_topdeck_id=args.player_topdeck_id,
            order_by=args.order_by,
            order_direction=args.order_direction,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        if not rows:
            break

        page_processed = 0
        page_cached_skipped = 0
        page_bad_url_skipped = 0
        page_unresolved = 0
        pending_updates: list[tuple[str, str]] = []

        for row in rows:
            scanned += 1
            page_processed += 1

            if should_skip_cached_attempt(row, attempt_cache, args.retry_transient, retry_statuses):
                cached_skipped += 1
                page_cached_skipped += 1
                continue

            decklist = row.get("decklist_url") or ""
            bad_url_reason = classify_bad_moxfield_url(decklist)
            if bad_url_reason:
                bad_url_skipped += 1
                page_bad_url_skipped += 1
                record_attempt(
                    attempt_cache,
                    row=row,
                    status=bad_url_reason,
                    detail=decklist,
                )
                continue

            player_topdeck_id = relation_value(row, "players").get("topdeck_id")
            tournament_topdeck_id = relation_value(row, "tournaments").get("topdeck_tid")
            if not player_topdeck_id or not tournament_topdeck_id:
                unresolved += 1
                page_unresolved += 1
                record_attempt(
                    attempt_cache,
                    row=row,
                    status="missing_topdeck_ids",
                    detail=f"player={player_topdeck_id or ''} tournament={tournament_topdeck_id or ''}",
                )
                continue

            try:
                _commanders, topdeck_deck_url = fetch_topdeck_deck_page_details(
                    tournament_topdeck_id,
                    player_topdeck_id,
                    http,
                    args.topdeck_timeout,
                )
            except RedirectedToMoxfieldError as exc:
                unresolved += 1
                page_unresolved += 1
                topdeck_requests += 1
                record_attempt(
                    attempt_cache,
                    row=row,
                    status="moxfield_redirect",
                    detail=str(exc),
                )
                continue
            except requests.Timeout as exc:
                unresolved += 1
                page_unresolved += 1
                topdeck_requests += 1
                record_attempt(
                    attempt_cache,
                    row=row,
                    status="topdeck_timeout",
                    detail=str(exc),
                )
                continue
            except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError) as exc:
                unresolved += 1
                page_unresolved += 1
                topdeck_requests += 1
                record_attempt(
                    attempt_cache,
                    row=row,
                    status="topdeck_connection_error",
                    detail=str(exc),
                )
                continue
            except TopDeckHttpStatusError as exc:
                unresolved += 1
                page_unresolved += 1
                topdeck_requests += 1
                record_attempt(
                    attempt_cache,
                    row=row,
                    status="topdeck_http_error",
                    detail=str(exc),
                )
                continue
            except requests.RequestException as exc:
                unresolved += 1
                page_unresolved += 1
                topdeck_requests += 1
                record_attempt(
                    attempt_cache,
                    row=row,
                    status="topdeck_connection_error",
                    detail=str(exc),
                )
                continue

            topdeck_requests += 1
            pending_updates.append((row["id"], topdeck_deck_url))
            record_attempt(
                attempt_cache,
                row=row,
                status="resolved",
                detail=topdeck_deck_url,
            )

            if args.limit and updated + len(pending_updates) >= args.limit:
                break

        write_attempt_cache(args.attempt_cache, attempt_cache)

        if pending_updates and not args.dry_run:
            for entry_id, topdeck_deck_url in pending_updates:
                try:
                    client.update("tournament_entries", {"decklist_url": topdeck_deck_url}, {"id": f"eq.{entry_id}"})
                    updated += 1
                except requests.RequestException as exc:
                    unresolved += 1
                    page_unresolved += 1
                    row = {
                        "id": entry_id,
                        "decklist_url": topdeck_deck_url,
                        "players": {"topdeck_id": attempt_cache.get(entry_id, {}).get("player_topdeck_id", "")},
                        "tournaments": {"topdeck_tid": attempt_cache.get(entry_id, {}).get("topdeck_tid", "")},
                    }
                    record_attempt(
                        attempt_cache,
                        row=row,
                        status="supabase_update_failed",
                        detail=str(exc),
                    )
        else:
            updated += len(pending_updates)

        write_attempt_cache(args.attempt_cache, attempt_cache)

        print(
            f"scanned={scanned} updated={updated} unresolved={unresolved} "
            f"cached_skipped={cached_skipped} bad_url_skipped={bad_url_skipped} "
            f"topdeck_requests={topdeck_requests}",
            flush=True,
        )

        if args.limit and updated >= args.limit:
            break
        if args.dry_run:
            offset += page_processed
        else:
            offset += page_cached_skipped + page_bad_url_skipped + page_unresolved

    print(
        f"Done. scanned={scanned} updated={updated} unresolved={unresolved} "
        f"cached_skipped={cached_skipped} bad_url_skipped={bad_url_skipped} "
        f"topdeck_requests={topdeck_requests} dry_run={args.dry_run}",
        flush=True,
    )
    print(f"Attempt status summary: {summarize_attempt_statuses(attempt_cache)}", flush=True)


if __name__ == "__main__":
    main()
