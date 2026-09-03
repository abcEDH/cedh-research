#!/usr/bin/env python3
"""Repair games that were ingested without a winner or draw outcome."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

from ingest import DataIngester, TopDeckClient
from supabase import Client
from supabase_client import get_supabase_client


def load_env() -> None:
    for env_path in (Path("packages/backend/.env"), Path(".env"), Path(__file__).resolve().parents[1] / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def delete_tournament_games(client: Client, tournament_id: str) -> int:
    """Delete every `games` row for one tournament, returning the count removed.

    Uses the fluent builder's `.delete()` (composition over the raw `Client`)
    rather than the old `SupabaseRepairClient(SupabaseClient)` subclass --
    `DataIngester` now expects a plain `Client`, and subclassing the removed
    wrapper is no longer possible.
    """
    result = client.table("games").delete().eq("tournament_id", tournament_id).select("id").execute()
    deleted = result.data
    return len(deleted) if isinstance(deleted, list) else 0


def fetch_affected_tournaments(
    supabase_url: str,
    supabase_key: str,
    *,
    only_tid: str | None,
    page_size: int = 1000,
) -> list[dict[str, str]]:
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
    }
    seen: dict[str, dict[str, str]] = {}
    offset = 0

    while True:
        page_headers = headers.copy()
        page_headers["Range"] = f"{offset}-{offset + page_size - 1}"
        response = requests.get(
            f"{supabase_url}/rest/v1/games",
            headers=page_headers,
            params={
                "select": "tournament_id,tournaments(topdeck_tid,name)",
                "is_draw": "eq.false",
                "winner_id": "is.null",
                "order": "tournament_id.asc",
            },
            timeout=60,
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            break

        for row in rows:
            tournament = row.get("tournaments") or {}
            topdeck_tid = tournament.get("topdeck_tid")
            if not topdeck_tid:
                continue
            if only_tid and topdeck_tid != only_tid:
                continue
            seen[topdeck_tid] = {
                "topdeck_tid": topdeck_tid,
                "tournament_id": row["tournament_id"],
                "name": tournament.get("name") or "",
            }

        if len(rows) < page_size:
            break
        offset += page_size

    return sorted(seen.values(), key=lambda row: row["topdeck_tid"])


def count_bad_games_for_tournament(
    supabase_url: str,
    supabase_key: str,
    tournament_id: str,
) -> int:
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Prefer": "count=exact",
        "Range": "0-0",
    }
    response = requests.get(
        f"{supabase_url}/rest/v1/games",
        headers=headers,
        params={
            "select": "id",
            "tournament_id": f"eq.{tournament_id}",
            "is_draw": "eq.false",
            "winner_id": "is.null",
        },
        timeout=60,
    )
    response.raise_for_status()
    content_range = response.headers.get("content-range", "")
    total = content_range.rsplit("/", 1)[-1]
    return int(total) if total.isdigit() else 0


def normalize_tournament_payload(tournament: dict[str, Any], topdeck_tid: str) -> dict[str, Any]:
    metadata = tournament.get("data")
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            tournament.setdefault(key, value)

    tournament.setdefault("id", topdeck_tid)
    tournament.setdefault("TID", topdeck_tid)

    for standing in tournament.get("standings") or []:
        if "rank" not in standing and "standing" in standing:
            standing["rank"] = standing["standing"]

    return tournament


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only-tid", help="Repair one TopDeck tournament ID")
    parser.add_argument("--limit", type=int, default=0, help="Maximum tournaments to process")
    parser.add_argument("--sleep", type=float, default=0.25, help="Seconds to sleep between tournaments")
    parser.add_argument(
        "--delete-first",
        action="store_true",
        help="Delete existing games for each tournament before reingesting",
    )
    parser.add_argument("--dry-run", action="store_true", help="List targets without mutating Supabase")
    args = parser.parse_args()

    load_env()
    supabase_url = require_env("SUPABASE_URL").rstrip("/")
    supabase_key = require_env("SUPABASE_SERVICE_KEY")
    topdeck_key = require_env("TOPDECK_API_KEY")

    targets = fetch_affected_tournaments(
        supabase_url,
        supabase_key,
        only_tid=args.only_tid,
    )
    if args.limit > 0:
        targets = targets[: args.limit]

    print(f"affected_tournaments={len(targets)}")
    if args.dry_run:
        for target in targets[:50]:
            print(f"{target['topdeck_tid']}\t{target['name']}")
        if len(targets) > 50:
            print(f"... {len(targets) - 50} more")
        return 0

    topdeck = TopDeckClient(topdeck_key)
    supabase = get_supabase_client(supabase_url, supabase_key)
    ingester = DataIngester(topdeck, supabase)

    repaired = 0
    failed = 0
    skipped = 0

    for index, target in enumerate(targets, start=1):
        tid = target["topdeck_tid"]
        tournament_id = target["tournament_id"]
        before = count_bad_games_for_tournament(supabase_url, supabase_key, tournament_id)
        print(f"[{index}/{len(targets)}] tid={tid} bad_before={before} name={target['name']}")
        if before == 0:
            skipped += 1
            continue

        try:
            tournament = topdeck.get_tournament(tid)
            if not tournament:
                raise RuntimeError("TopDeck returned an empty payload")
            normalize_tournament_payload(tournament, tid)

            if not tournament.get("startDate") or not tournament.get("rounds"):
                skipped += 1
                print("  skipped=true reason=topdeck_payload_missing_start_date_or_rounds")
                continue

            if args.delete_first:
                deleted = delete_tournament_games(supabase, tournament_id)
                print(f"  deleted_games={deleted}")

            result = ingester.process_tournament(tournament)
            if not result:
                skipped += 1
                print("  skipped=true")
                continue

            after = count_bad_games_for_tournament(supabase_url, supabase_key, tournament_id)
            print(f"  games_processed={result.get('games')} bad_after={after}")
            repaired += 1
        except Exception as exc:
            failed += 1
            print(f"  failed={type(exc).__name__}: {exc}", file=sys.stderr)

        if args.sleep > 0:
            time.sleep(args.sleep)

    print(f"repaired={repaired} skipped={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
