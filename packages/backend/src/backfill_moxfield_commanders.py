#!/usr/bin/env python3
"""Backfill commanders for historical Moxfield decklist entries."""

from __future__ import annotations

import argparse
import collections
import csv
import html
import io
import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from ingest import (
    MTG_GAME,
    SupabaseClient,
    clean_commander_card_name,
    extract_commanders,
    normalize_commander_name,
    sanitize_commander_payload,
)

PLACEHOLDER_COMMANDERS = {"Unknown Commander", "Moxfield Deck"}
TRANSIENT_STATUSES = {
    "topdeck_timeout",
    "topdeck_connection_error",
    "supabase_update_failed",
}
PERMANENT_STATUSES = {
    "bad_moxfield_url",
    "missing_topdeck_ids",
    "moxfield_redirect",
    "topdeck_http_error",
    "no_commander_found",
}
DEFAULT_ATTEMPT_CACHE = Path("logs/backfill_moxfield_attempts.csv")


class RedirectedToMoxfieldError(RuntimeError):
    pass


class TopDeckHttpStatusError(RuntimeError):
    pass


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


def canonicalize_moxfield_url(decklist_url: str) -> str:
    decklist_url = decklist_url.strip()
    if not decklist_url:
        return decklist_url

    parsed = urlparse(decklist_url)
    path = parsed.path or ""
    if parsed.query:
        query = parse_qs(parsed.query)
        if "q" in query:
            return f"{parsed.scheme}://{parsed.netloc}{path}?q="
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def classify_bad_moxfield_url(decklist_url: str) -> str | None:
    if "~~Commanders~~" in decklist_url:
        return None
    canonical = canonicalize_moxfield_url(decklist_url).lower()
    if "moxfield.com" not in canonical:
        return "bad_moxfield_url"
    if canonical.endswith("/404"):
        return "bad_moxfield_url"
    if "/decks/undefined" in canonical:
        return "bad_moxfield_url"
    if any(segment in canonical for segment in ("/history", "/edit", "/settings", "/personal")):
        return "bad_moxfield_url"
    if "/search?q=" in canonical:
        return "bad_moxfield_url"

    parsed = urlparse(canonical)
    if not parsed.path.startswith("/decks/"):
        return "bad_moxfield_url"
    deck_id = parsed.path.removeprefix("/decks/").split("/", 1)[0]
    if not deck_id or deck_id in {"undefined", "404"}:
        return "bad_moxfield_url"
    return None


def load_attempt_cache(cache_path: Path) -> dict[str, dict[str, str]]:
    if not cache_path.exists():
        return {}

    raw_text = cache_path.read_text(errors="replace").replace("\x00", "")
    reader = csv.DictReader(io.StringIO(raw_text))
    return {row["entry_id"]: row for row in reader if row.get("entry_id")}


ENTRY_ID_LINE_RE = re.compile(r"(?m)^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}),")


def load_attempted_entry_ids(cache_path: Path) -> set[str]:
    if not cache_path.exists():
        return set()
    return set(ENTRY_ID_LINE_RE.findall(cache_path.read_text(errors="replace")))


def write_attempt_cache(cache_path: Path, attempt_cache: dict[str, dict[str, str]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "entry_id",
                "status",
                "detail",
                "decklist_url",
                "topdeck_tid",
                "player_topdeck_id",
                "last_attempted_at",
            ],
        )
        writer.writeheader()
        for entry_id in sorted(attempt_cache):
            writer.writerow(attempt_cache[entry_id])


def should_skip_cached_attempt(
    row: dict,
    attempt_cache: dict[str, dict[str, str]],
    retry_transient: bool,
    retry_statuses: set[str] | None,
) -> bool:
    cached = attempt_cache.get(row["id"])
    if retry_statuses is not None and not cached:
        return True
    if not cached:
        return False
    status = cached.get("status", "")
    if retry_statuses is not None:
        return status not in retry_statuses
    if status in PERMANENT_STATUSES or status == "resolved":
        return True
    if status in TRANSIENT_STATUSES and not retry_transient:
        return True
    return False


def effective_start_date(row: dict) -> str:
    tournaments = relation_value(row, "tournaments")
    start_date = tournaments.get("start_date")
    return start_date if isinstance(start_date, str) else ""


def row_within_date_window(
    row: dict,
    *,
    start_date: str | None,
    end_date: str | None,
) -> bool:
    row_start_date = effective_start_date(row)
    if not row_start_date:
        return False
    if start_date and row_start_date < start_date:
        return False
    if end_date and row_start_date > end_date:
        return False
    return True


def find_resume_end_date(
    client: SupabaseClient,
    attempt_cache: dict[str, dict[str, str]],
    *,
    embedded_only: bool,
    include_known: bool,
    require_topdeck_ids: bool,
    player_topdeck_id: str | None,
    order_by: str,
    order_direction: str,
    start_date: str | None,
    end_date: str | None,
    retry_transient: bool,
    retry_statuses: set[str] | None,
    page_size: int,
) -> str | None:
    offset = 0
    while True:
        rows = fetch_moxfield_entries(
            client,
            limit=page_size,
            offset=offset,
            embedded_only=embedded_only,
            include_known=include_known,
            require_topdeck_ids=require_topdeck_ids,
            player_topdeck_id=player_topdeck_id,
            order_by=order_by,
            order_direction=order_direction,
            start_date=start_date,
            end_date=end_date,
        )
        if not rows:
            return None
        for row in rows:
            if not row_within_date_window(row, start_date=start_date, end_date=end_date):
                continue
            existing_name = commander_name_for_entry(row)
            if existing_name not in PLACEHOLDER_COMMANDERS and not include_known:
                continue
            if should_skip_cached_attempt(row, attempt_cache, retry_transient, retry_statuses):
                continue
            if classify_bad_moxfield_url(row.get("decklist_url") or ""):
                continue
            return effective_start_date(row) or end_date
        offset += len(rows)


def parse_retry_statuses(raw_value: str | None) -> set[str] | None:
    if not raw_value:
        return None
    return {value.strip() for value in raw_value.split(",") if value.strip()}


def summarize_attempt_statuses(attempt_cache: dict[str, dict[str, str]]) -> str:
    counts = collections.Counter(row.get("status", "unknown") for row in attempt_cache.values())
    if not counts:
        return "none"
    return ", ".join(f"{status}={counts[status]}" for status in sorted(counts))


def cached_ids_for_statuses(
    attempt_cache: dict[str, dict[str, str]],
    retry_statuses: set[str],
) -> list[str]:
    return sorted(entry_id for entry_id, row in attempt_cache.items() if row.get("status", "") in retry_statuses)


def load_entry_ids(entry_ids_path: Path) -> list[str]:
    if not entry_ids_path.exists():
        raise SystemExit(f"Error: entry IDs file not found: {entry_ids_path}")
    return [line.strip() for line in entry_ids_path.read_text().splitlines() if line.strip()]


def find_resume_index_for_entry_ids(
    entry_ids: list[str],
    attempt_cache: dict[str, dict[str, str]],
) -> int:
    for index, entry_id in enumerate(entry_ids):
        if entry_id not in attempt_cache:
            return index
    return len(entry_ids)


def record_attempt(
    attempt_cache: dict[str, dict[str, str]],
    *,
    row: dict,
    status: str,
    detail: str = "",
) -> None:
    player_topdeck_id = relation_value(row, "players").get("topdeck_id") or ""
    tournament_topdeck_id = relation_value(row, "tournaments").get("topdeck_tid") or ""
    attempt_cache[row["id"]] = {
        "entry_id": row["id"],
        "status": status,
        "detail": detail[:500],
        "decklist_url": row.get("decklist_url") or "",
        "topdeck_tid": tournament_topdeck_id,
        "player_topdeck_id": player_topdeck_id,
        "last_attempted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def fetch_moxfield_entries(
    client: SupabaseClient,
    *,
    limit: int,
    offset: int,
    embedded_only: bool,
    include_known: bool,
    require_topdeck_ids: bool = False,
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
        relations = "commanders!inner(name),players!inner(topdeck_id),tournaments!inner(topdeck_tid,start_date)"
        select = f"id,decklist_url,{relations}"
        filters["commanders.name"] = 'in.("Unknown Commander","Moxfield Deck")'
    if require_topdeck_ids:
        filters["players.topdeck_id"] = "not.is.null"
        filters["tournaments.topdeck_tid"] = "not.is.null"
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


def fetch_entries_by_ids(
    client: SupabaseClient,
    *,
    entry_ids: list[str],
    include_known: bool,
    require_topdeck_ids: bool = False,
) -> list[dict]:
    if not entry_ids:
        return []
    select = "id,decklist_url,commanders(name),players(topdeck_id),tournaments(topdeck_tid,start_date)"
    if not include_known:
        relations = "commanders!left(name),players!left(topdeck_id),tournaments!left(topdeck_tid,start_date)"
        select = f"id,decklist_url,{relations}"
    ids = ",".join(entry_ids)
    return client.select(
        "tournament_entries",
        {
            "select": select,
            "id": f"in.({ids})",
            **(
                {
                    "players.topdeck_id": "not.is.null",
                    "tournaments.topdeck_tid": "not.is.null",
                }
                if require_topdeck_ids
                else {}
            ),
            "limit": len(entry_ids),
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
                **dict(zip(("name", "commander_names"), sanitize_commander_payload(name, names), strict=True)),
                "game": MTG_GAME,
                "identity_kind": "commander",
            }
            for name, names in commander_data.items()
        ],
        on_conflict="game,name",
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
                writer.writerow(
                    {
                        "entry_id": row["id"],
                        "decklist_url": row.get("decklist_url") or "",
                        "commander_names": "",
                    }
                )
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


def build_topdeck_deck_page_url(tournament_id: str, player_identifier: str) -> str:
    return f"https://topdeck.gg/deck/{tournament_id}/{player_identifier}"


def fetch_topdeck_deck_page_details(
    tournament_id: str,
    player_identifier: str,
    session: requests.Session,
    timeout: float,
) -> tuple[list[str], str]:
    url = build_topdeck_deck_page_url(tournament_id, player_identifier)
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "cedh-research/1.0",
    }
    for _ in range(4):
        response = session.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=False,
        )
        if 300 <= response.status_code < 400:
            location = response.headers.get("location", "")
            if "moxfield.com" in location:
                raise RedirectedToMoxfieldError(location)
            if not location:
                raise TopDeckHttpStatusError(f"redirect-without-location:{response.status_code}")
            if location.startswith("/"):
                url = f"https://topdeck.gg{location}"
            elif location.startswith("http"):
                url = location
            else:
                url = f"https://topdeck.gg/{location.lstrip('/')}"
            continue
        if response.status_code >= 400:
            raise TopDeckHttpStatusError(str(response.status_code))
        return extract_topdeck_deck_page_commanders(response.text), url
    raise TopDeckHttpStatusError("too-many-redirects")


def fetch_topdeck_deck_page_commanders(
    tournament_id: str,
    player_identifier: str,
    session: requests.Session,
    timeout: float,
) -> list[str]:
    commanders, _final_url = fetch_topdeck_deck_page_details(
        tournament_id,
        player_identifier,
        session,
        timeout,
    )
    return commanders


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill commanders for Moxfield decklist entries")
    parser.add_argument("--limit", type=int, help="Maximum rows to update")
    parser.add_argument("--page-size", type=int, default=250, help="Supabase page size")
    parser.add_argument("--offset", type=int, default=0, help="Initial row offset")
    parser.add_argument("--entry-ids-file", type=Path, help="Process only the listed tournament_entry IDs")
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
    parser.add_argument(
        "--include-known",
        action="store_true",
        help="Update rows that already have non-placeholder commanders",
    )
    parser.add_argument(
        "--embedded-only",
        action="store_true",
        help="Only process imported deck text with embedded commander sections",
    )
    parser.add_argument(
        "--resolve-moxfield-api",
        action="store_true",
        help="Fetch pure Moxfield URLs from the Moxfield API",
    )
    parser.add_argument(
        "--resolve-moxfield-page",
        action="store_true",
        help="Scrape pure Moxfield URLs from public deck pages",
    )
    parser.add_argument(
        "--resolve-topdeck-deck-page",
        action="store_true",
        help="Scrape TopDeck's /deck/{tournament}/{player} page",
    )
    parser.add_argument(
        "--process-all-moxfield-rows",
        action="store_true",
        help="Process all Moxfield rows for TopDeck deck URL rewrites; only update commanders when missing/unknown",
    )
    parser.add_argument("--player-topdeck-id", help="Only process entries for one TopDeck player id")
    parser.add_argument("--max-moxfield-requests", type=int, help="Stop after this many Moxfield URL requests")
    parser.add_argument("--max-topdeck-requests", type=int, help="Stop after this many TopDeck deck page requests")
    parser.add_argument(
        "--topdeck-timeout",
        type=float,
        default=10,
        help="Seconds before a TopDeck deck page request times out",
    )
    parser.add_argument("--max-api-requests", type=int, help="Deprecated alias for --max-moxfield-requests")
    parser.add_argument("--sleep", type=float, default=0.2, help="Seconds to sleep between Moxfield URL requests")
    parser.add_argument("--export-unresolved-csv", type=Path, help="Write unresolved Moxfield entries to CSV")
    parser.add_argument("--import-resolved-csv", type=Path, help="Read resolved commander mappings from CSV")
    parser.add_argument("--commander-delimiter", default="|", help="Delimiter for commander_names in import CSV")
    parser.add_argument(
        "--attempt-cache",
        type=Path,
        default=DEFAULT_ATTEMPT_CACHE,
        help="CSV file storing per-entry attempt status for resume/skip behavior",
    )
    parser.add_argument(
        "--retry-transient",
        action="store_true",
        help="Retry entries previously marked with transient network or Supabase failures",
    )
    parser.add_argument(
        "--retry-status",
        help="Comma-separated cached statuses to retry, e.g. topdeck_timeout,topdeck_connection_error",
    )
    parser.add_argument(
        "--full-date-window",
        action="store_true",
        help="Do not shrink the requested date window based on cached attempted work",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes")
    args = parser.parse_args()
    max_moxfield_requests = args.max_moxfield_requests
    if max_moxfield_requests is None:
        max_moxfield_requests = args.max_api_requests
    retry_statuses = parse_retry_statuses(args.retry_status)
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
    attempt_cache = load_attempt_cache(args.attempt_cache)

    effective_start = args.start_date
    effective_end = args.end_date
    process_all_moxfield_rows = args.process_all_moxfield_rows
    if (
        not process_all_moxfield_rows
        and not args.full_date_window
        and args.resolve_topdeck_deck_page
        and not args.retry_transient
        and retry_statuses is None
    ):
        resume_end = find_resume_end_date(
            client,
            attempt_cache,
            embedded_only=args.embedded_only,
            include_known=args.include_known,
            require_topdeck_ids=False,
            player_topdeck_id=args.player_topdeck_id,
            order_by=args.order_by,
            order_direction=args.order_direction,
            start_date=args.start_date,
            end_date=args.end_date,
            retry_transient=args.retry_transient,
            retry_statuses=retry_statuses,
            page_size=max(args.page_size, 500),
        )
        if resume_end:
            effective_end = resume_end
            print(
                f"Adjusted date window from start={args.start_date or ''} end={args.end_date or ''} "
                f"to start={effective_start or ''} end={effective_end or ''}",
                flush=True,
            )

    scanned = 0
    updated = 0
    decklist_updated = 0
    skipped_known = 0
    unresolved = 0
    repeated_unresolved = 0
    cached_skipped = 0
    bad_url_skipped = 0
    moxfield_requests = 0
    topdeck_requests = 0
    offset = args.offset
    attempted_unresolved_ids: set[str] = set()
    attempted_entry_ids = set(attempt_cache)
    attempted_entry_ids.update(load_attempted_entry_ids(args.attempt_cache))
    retry_entry_ids = (
        cached_ids_for_statuses(attempt_cache, retry_statuses)
        if retry_statuses
        else load_entry_ids(args.entry_ids_file)
        if args.entry_ids_file
        else []
    )
    retry_index = 0
    if args.entry_ids_file and retry_statuses is None:
        total_targets = len(retry_entry_ids)
        retry_entry_ids = [entry_id for entry_id in retry_entry_ids if entry_id not in attempted_entry_ids]
        print(
            f"Resuming entry ID list with {len(retry_entry_ids)} remaining of {total_targets}",
            flush=True,
        )

    while True:
        if args.entry_ids_file:
            batch_ids = retry_entry_ids[retry_index : retry_index + args.page_size]
            rows = fetch_entries_by_ids(
                client,
                entry_ids=batch_ids,
                include_known=args.include_known or process_all_moxfield_rows,
                require_topdeck_ids=False,
            )
            retry_index += len(batch_ids)
        elif retry_statuses:
            batch_ids = retry_entry_ids[retry_index : retry_index + args.page_size]
            rows = fetch_entries_by_ids(
                client,
                entry_ids=batch_ids,
                include_known=args.include_known or process_all_moxfield_rows,
                require_topdeck_ids=False,
            )
            retry_index += len(batch_ids)
        else:
            rows = fetch_moxfield_entries(
                client,
                limit=args.page_size,
                offset=offset,
                embedded_only=args.embedded_only,
                include_known=args.include_known or process_all_moxfield_rows,
                require_topdeck_ids=process_all_moxfield_rows,
                player_topdeck_id=args.player_topdeck_id,
                order_by=args.order_by,
                order_direction=args.order_direction,
                start_date=effective_start,
                end_date=effective_end,
            )
        if not rows:
            break

        rows = [row for row in rows if row_within_date_window(row, start_date=effective_start, end_date=effective_end)]
        if not rows:
            if retry_statuses or args.entry_ids_file:
                continue
            offset += args.page_size
            continue

        commander_data: dict[str, list[str]] = {}
        pending_updates: list[tuple[str, str]] = []
        pending_decklist_updates: list[tuple[str, str]] = []
        row_effects: dict[str, dict[str, bool]] = {}
        page_skipped = 0
        page_unresolved = 0
        page_processed = 0

        for row in rows:
            scanned += 1
            page_processed += 1
            existing_name = commander_name_for_entry(row)
            needs_commander_update = existing_name in PLACEHOLDER_COMMANDERS or args.include_known
            if not process_all_moxfield_rows and existing_name not in PLACEHOLDER_COMMANDERS and not args.include_known:
                skipped_known += 1
                page_skipped += 1
                continue
            if should_skip_cached_attempt(row, attempt_cache, args.retry_transient, retry_statuses):
                cached_skipped += 1
                page_skipped += 1
                continue
            if row["id"] in attempted_unresolved_ids:
                repeated_unresolved += 1
                page_skipped += 1
                continue

            decklist = row.get("decklist_url") or ""
            bad_url_reason = classify_bad_moxfield_url(decklist)
            if bad_url_reason:
                bad_url_skipped += 1
                unresolved += 1
                page_unresolved += 1
                attempted_unresolved_ids.add(row["id"])
                record_attempt(
                    attempt_cache,
                    row=row,
                    status=bad_url_reason,
                    detail=canonicalize_moxfield_url(decklist),
                )
                continue
            if (
                max_moxfield_requests is not None
                and moxfield_requests >= max_moxfield_requests
                and "~~Commanders~~" not in decklist
            ):
                break

            should_resolve_moxfield = args.resolve_moxfield_api or args.resolve_moxfield_page
            if max_moxfield_requests is not None and moxfield_requests >= max_moxfield_requests:
                should_resolve_moxfield = False

            commanders = []
            commander_name = existing_name or ""
            if needs_commander_update:
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

            topdeck_deck_url = ""
            should_fetch_topdeck = args.resolve_topdeck_deck_page and (
                process_all_moxfield_rows or commander_name in PLACEHOLDER_COMMANDERS
            )
            if should_fetch_topdeck:
                if args.max_topdeck_requests is not None and topdeck_requests >= args.max_topdeck_requests:
                    break
                player_topdeck_id = relation_value(row, "players").get("topdeck_id")
                tournament_topdeck_id = relation_value(row, "tournaments").get("topdeck_tid")
                if player_topdeck_id and tournament_topdeck_id:
                    try:
                        topdeck_commanders, topdeck_deck_url = fetch_topdeck_deck_page_details(
                            tournament_topdeck_id,
                            player_topdeck_id,
                            http,
                            args.topdeck_timeout,
                        )
                    except RedirectedToMoxfieldError as exc:
                        record_attempt(
                            attempt_cache,
                            row=row,
                            status="moxfield_redirect",
                            detail=str(exc),
                        )
                        attempted_unresolved_ids.add(row["id"])
                        unresolved += 1
                        page_unresolved += 1
                        topdeck_requests += 1
                        continue
                    except requests.Timeout as exc:
                        print(f"TopDeck deck page fetch failed for entry {row['id']}: {exc}")
                        record_attempt(
                            attempt_cache,
                            row=row,
                            status="topdeck_timeout",
                            detail=str(exc),
                        )
                        attempted_unresolved_ids.add(row["id"])
                        unresolved += 1
                        page_unresolved += 1
                        topdeck_requests += 1
                        continue
                    except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError) as exc:
                        print(f"TopDeck deck page fetch failed for entry {row['id']}: {exc}")
                        record_attempt(
                            attempt_cache,
                            row=row,
                            status="topdeck_connection_error",
                            detail=str(exc),
                        )
                        attempted_unresolved_ids.add(row["id"])
                        unresolved += 1
                        page_unresolved += 1
                        topdeck_requests += 1
                        continue
                    except TopDeckHttpStatusError as exc:
                        print(f"TopDeck deck page fetch failed for entry {row['id']}: {exc}")
                        record_attempt(
                            attempt_cache,
                            row=row,
                            status="topdeck_http_error",
                            detail=str(exc),
                        )
                        attempted_unresolved_ids.add(row["id"])
                        unresolved += 1
                        page_unresolved += 1
                        topdeck_requests += 1
                        continue
                    except requests.RequestException as exc:
                        print(f"TopDeck deck page fetch failed for entry {row['id']}: {exc}")
                        record_attempt(
                            attempt_cache,
                            row=row,
                            status="topdeck_connection_error",
                            detail=str(exc),
                        )
                        attempted_unresolved_ids.add(row["id"])
                        unresolved += 1
                        page_unresolved += 1
                        topdeck_requests += 1
                        continue
                    topdeck_requests += 1
                    if topdeck_commanders:
                        commanders = topdeck_commanders
                        if needs_commander_update:
                            commander_name = normalize_commander_name(commanders)
                    if topdeck_deck_url and decklist != topdeck_deck_url:
                        pending_decklist_updates.append((row["id"], topdeck_deck_url))
                else:
                    record_attempt(
                        attempt_cache,
                        row=row,
                        status="missing_topdeck_ids",
                        detail=f"player={player_topdeck_id or ''} tournament={tournament_topdeck_id or ''}",
                    )
                    attempted_unresolved_ids.add(row["id"])
                    unresolved += 1
                    page_unresolved += 1
                    continue

            if needs_commander_update and commander_name in PLACEHOLDER_COMMANDERS:
                attempted_unresolved_ids.add(row["id"])
                unresolved += 1
                page_unresolved += 1
                record_attempt(
                    attempt_cache,
                    row=row,
                    status="no_commander_found",
                    detail=canonicalize_moxfield_url(decklist),
                )
                continue

            if needs_commander_update:
                commander_data[commander_name] = commanders
                pending_updates.append((row["id"], commander_name))
            row_effects[row["id"]] = {
                "commander_update": needs_commander_update,
                "decklist_update": bool(topdeck_deck_url and decklist != topdeck_deck_url),
            }
            record_attempt(
                attempt_cache,
                row=row,
                status="resolved",
                detail=topdeck_deck_url or commander_name,
            )

            if args.limit and updated + len(pending_updates) >= args.limit:
                break

        write_attempt_cache(args.attempt_cache, attempt_cache)

        if commander_data and not args.dry_run:
            try:
                commander_ids = upsert_commanders(client, commander_data)
            except requests.RequestException as exc:
                print(f"Supabase commander upsert failed: {exc}")
                for entry_id, _commander_name in pending_updates:
                    attempted_unresolved_ids.add(entry_id)
                    unresolved += 1
                    row = {
                        "id": entry_id,
                        "decklist_url": attempt_cache.get(entry_id, {}).get("decklist_url", ""),
                        "players": {"topdeck_id": attempt_cache.get(entry_id, {}).get("player_topdeck_id", "")},
                        "tournaments": {"topdeck_tid": attempt_cache.get(entry_id, {}).get("topdeck_tid", "")},
                    }
                    record_attempt(
                        attempt_cache,
                        row=row,
                        status="supabase_update_failed",
                        detail=str(exc),
                    )
                write_attempt_cache(args.attempt_cache, attempt_cache)
            else:
                for entry_id, commander_name in pending_updates:
                    commander_id = commander_ids.get(commander_name)
                    if not commander_id:
                        continue
                    try:
                        client.update("tournament_entries", {"commander_id": commander_id}, {"id": f"eq.{entry_id}"})
                        updated += 1
                    except requests.RequestException as exc:
                        print(f"Supabase update failed for entry {entry_id}: {exc}")
                        attempted_unresolved_ids.add(entry_id)
                        unresolved += 1
                        row = {
                            "id": entry_id,
                            "decklist_url": attempt_cache.get(entry_id, {}).get("decklist_url", ""),
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

        successful_decklist_update_ids: set[str] = set()
        if pending_decklist_updates and not args.dry_run:
            for entry_id, topdeck_deck_url in pending_decklist_updates:
                try:
                    client.update("tournament_entries", {"decklist_url": topdeck_deck_url}, {"id": f"eq.{entry_id}"})
                    decklist_updated += 1
                    successful_decklist_update_ids.add(entry_id)
                except requests.RequestException as exc:
                    print(f"Supabase decklist update failed for entry {entry_id}: {exc}")
                    attempted_unresolved_ids.add(entry_id)
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
            decklist_updated += len(pending_decklist_updates)
            successful_decklist_update_ids = {entry_id for entry_id, _ in pending_decklist_updates}

        write_attempt_cache(args.attempt_cache, attempt_cache)

        print(
            f"scanned={scanned} updated={updated} unresolved={unresolved} "
            f"repeated_unresolved={repeated_unresolved} skipped_known={skipped_known} "
            f"cached_skipped={cached_skipped} bad_url_skipped={bad_url_skipped} "
            f"decklist_updated={decklist_updated} moxfield_requests={moxfield_requests} "
            f"topdeck_requests={topdeck_requests}",
            flush=True,
        )

        if args.limit and updated >= args.limit:
            break
        if max_moxfield_requests is not None and moxfield_requests >= max_moxfield_requests and not args.embedded_only:
            break
        if args.max_topdeck_requests is not None and topdeck_requests >= args.max_topdeck_requests:
            break

        if retry_statuses or args.entry_ids_file:
            continue
        page_retained_successes = sum(
            1
            for entry_id, effects in row_effects.items()
            if not effects["decklist_update"] or entry_id not in successful_decklist_update_ids
        )
        if args.dry_run or args.include_known:
            offset += page_processed
        else:
            offset += page_unresolved + page_skipped + page_retained_successes

    print(
        f"Done. scanned={scanned} updated={updated} unresolved={unresolved} "
        f"repeated_unresolved={repeated_unresolved} skipped_known={skipped_known} "
        f"cached_skipped={cached_skipped} bad_url_skipped={bad_url_skipped} "
        f"decklist_updated={decklist_updated} moxfield_requests={moxfield_requests} "
        f"topdeck_requests={topdeck_requests} dry_run={args.dry_run}",
        flush=True,
    )
    print(f"Attempt status summary: {summarize_attempt_statuses(attempt_cache)}", flush=True)


if __name__ == "__main__":
    main()
