#!/usr/bin/env python3
"""Scrub recent TopDeck search results against Supabase and emit missing-TID candidates.

This is intentionally a heuristic scrub, not authoritative discovery.
TopDeck search is incomplete, so the output should be reviewed before promotion
into the supplemental manifest.
"""

from __future__ import annotations

import argparse
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from ingest import (
    SupabaseClient,
    TopDeckClient,
    dedupe_preserve_order,
    extract_name_and_tid,
    parse_tournament_start_date,
    write_tids,
)


TEST_NAME_RE = re.compile(r"(test|temp|copy)", re.IGNORECASE)


def load_credentials() -> tuple[str, str, str]:
    from export_all_time_tids import load_credentials

    supabase_url, supabase_key = load_credentials()

    topdeck_key = None
    for env_key in ("TOPDECK_API_KEY", "TOPDECK_GG_API_KEY"):
        topdeck_key = topdeck_key or __import__("os").getenv(env_key)

    if not topdeck_key:
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" not in line:
                    continue
                key, value = line.strip().split("=", 1)
                if key in ("TOPDECK_API_KEY", "TOPDECK_GG_API_KEY"):
                    topdeck_key = value
                    break

    if not topdeck_key:
        raise SystemExit("Error: TOPDECK_API_KEY must be set")

    return topdeck_key, supabase_url, supabase_key


def fetch_topdeck_search_tids(topdeck: TopDeckClient, *, days: int) -> list[dict]:
    start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
    rows = topdeck.search_tournaments(start_date=start_date)
    now_ts = int(time.time())
    candidates: list[dict] = []
    for row in rows:
        name, tid = extract_name_and_tid(row)
        if not tid or not name:
            continue
        start_dt = parse_tournament_start_date(row)
        start_ts = int(start_dt.timestamp()) if start_dt else 0

        if TEST_NAME_RE.search(name):
            continue
        if start_ts and start_ts > now_ts:
            continue

        candidates.append(
            {
                "tid": tid,
                "name": name,
                "start_date": start_ts,
            }
        )
    return candidates


def fetch_existing_tids(client: SupabaseClient) -> set[str]:
    rows: list[dict] = []
    offset = 0
    limit = 1000
    while True:
        page = client.select(
            "tournaments",
            {
                "select": "topdeck_tid",
                "topdeck_tid": "not.is.null",
                "order": "start_date.desc,topdeck_tid.asc",
                "limit": limit,
                "offset": offset,
            },
        )
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
    return {row["topdeck_tid"] for row in rows if row.get("topdeck_tid")}


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrub TopDeck search results for missing tournaments")
    parser.add_argument("--days", type=int, default=45, help="Search window for TopDeck search_tournaments")
    parser.add_argument(
        "--out",
        default="data/missing_tids_candidates.txt",
        help="Output file for candidate TIDs",
    )
    args = parser.parse_args()

    topdeck_key, supabase_url, supabase_key = load_credentials()
    topdeck = TopDeckClient(topdeck_key)
    supabase = SupabaseClient(supabase_url, supabase_key)

    topdeck_rows = fetch_topdeck_search_tids(topdeck, days=args.days)
    existing_tids = fetch_existing_tids(supabase)

    missing_rows = [row for row in topdeck_rows if row["tid"] not in existing_tids]
    missing_tids = dedupe_preserve_order([row["tid"] for row in missing_rows])

    header_lines = [
        "# Candidate missing tournament IDs from a TopDeck search scrub",
        "# Review before promotion to all_time_tids.supplemental.txt",
        f"# Search window: last {args.days} days",
        f"# Candidate count: {len(missing_tids)}",
    ]
    write_tids(Path(args.out), missing_tids, header_lines=header_lines)
    print(f"Wrote {len(missing_tids)} candidate tids to {args.out}")

    preview = missing_rows[:20]
    for row in preview:
        print(
            f"{row['tid']}\tstart={row['start_date']}\t{row['name']}"
        )


if __name__ == "__main__":
    main()
