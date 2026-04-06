#!/usr/bin/env python3
"""Deduplicate logical games and optionally recompute regional Elo.

Usage:
  python packages/backend/src/dedupe_games.py --dry-run
  python packages/backend/src/dedupe_games.py --apply
  python packages/backend/src/dedupe_games.py --apply --tournament-id <uuid>
  python packages/backend/src/dedupe_games.py --apply --recompute-regional-elo
"""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import requests


def load_credentials() -> tuple[str, str]:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" not in line or line.startswith("#"):
                    continue
                key, value = line.split("=", 1)
                if key == "SUPABASE_URL" and not supabase_url:
                    supabase_url = value
                elif key == "SUPABASE_SERVICE_KEY" and not supabase_key:
                    supabase_key = value

    if not supabase_url or not supabase_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")

    return supabase_url.rstrip("/"), supabase_key


class SupabaseAdminClient:
    def __init__(self, url: str, service_key: str):
        self.url = url
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def select_all(self, table: str, params: dict[str, str], page_size: int = 1000) -> list[dict]:
        rows: list[dict] = []
        offset = 0
        while True:
            headers = self.headers.copy()
            headers["Range"] = f"{offset}-{offset + page_size - 1}"
            response = requests.get(
                f"{self.url}/rest/v1/{table}",
                headers=headers,
                params=params,
                timeout=60,
            )
            response.raise_for_status()
            page = response.json()
            if not page:
                break
            rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return rows

    def patch_game_key(self, game_id: str, game_key: str) -> None:
        response = requests.patch(
            f"{self.url}/rest/v1/games",
            headers=self.headers,
            params={"id": f"eq.{game_id}"},
            json={"game_key": game_key},
            timeout=60,
        )
        response.raise_for_status()

    def delete_games(self, game_ids: Iterable[str]) -> int:
        game_ids = list(game_ids)
        if not game_ids:
            return 0
        response = requests.delete(
            f"{self.url}/rest/v1/games",
            headers=self.headers,
            params={"id": f"in.({','.join(game_ids)})"},
            timeout=60,
        )
        response.raise_for_status()
        deleted = response.json()
        return len(deleted) if isinstance(deleted, list) else len(game_ids)


@dataclass
class GameRow:
    id: str
    created_at: str
    tournament_id: str
    round_number: Optional[int]
    round_name: Optional[str]
    table_number: Optional[int]
    is_bracket: Optional[bool]
    game_key: Optional[str]

    def canonical_key(self) -> str:
        return "|".join([
            self.tournament_id,
            str(self.round_number) if self.round_number is not None else "RNULL",
            self.round_name or "RNNULL",
            str(self.table_number) if self.table_number is not None else "TNULL",
            str(bool(self.is_bracket)).lower(),
        ])


def fetch_games(client: SupabaseAdminClient, tournament_id: str | None) -> list[GameRow]:
    params = {
        "select": "id,created_at,tournament_id,round_number,round_name,table_number,is_bracket,game_key",
        "order": "created_at.asc",
    }
    if tournament_id:
        params["tournament_id"] = f"eq.{tournament_id}"
    rows = client.select_all("games", params)
    return [GameRow(**row) for row in rows]


def plan_dedupe(games: list[GameRow]) -> tuple[dict[str, str], list[str], dict[str, list[GameRow]]]:
    groups: dict[str, list[GameRow]] = defaultdict(list)
    for game in games:
        groups[game.canonical_key()].append(game)

    updates: dict[str, str] = {}
    deletions: list[str] = []
    duplicate_groups: dict[str, list[GameRow]] = {}

    for canonical_key, grouped_games in groups.items():
        grouped_games.sort(key=lambda row: (row.created_at, row.id))
        keeper = grouped_games[0]
        if keeper.game_key != canonical_key:
            updates[keeper.id] = canonical_key
        if len(grouped_games) > 1:
            duplicate_groups[canonical_key] = grouped_games
            deletions.extend(row.id for row in grouped_games[1:])

    return updates, deletions, duplicate_groups


def recompute_regional_elo() -> None:
    from regional_elo import compute_regional_elo, upsert_regional_elo

    regions = compute_regional_elo("state")
    upsert_regional_elo("state", regions)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicate logical games in Supabase")
    parser.add_argument("--tournament-id", help="Limit dedupe to one tournament UUID")
    parser.add_argument("--apply", action="store_true", help="Apply updates and deletions")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without mutating data")
    parser.add_argument(
        "--recompute-regional-elo",
        action="store_true",
        help="Recompute regional Elo after dedupe (only with --apply)",
    )
    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        parser.error("Choose --dry-run or --apply")
    if args.recompute_regional_elo and not args.apply:
        parser.error("--recompute-regional-elo requires --apply")

    url, key = load_credentials()
    client = SupabaseAdminClient(url, key)

    games = fetch_games(client, args.tournament_id)
    updates, deletions, duplicate_groups = plan_dedupe(games)

    print(f"games_scanned={len(games)}")
    print(f"games_to_update={len(updates)}")
    print(f"games_to_delete={len(deletions)}")
    print(f"duplicate_groups={len(duplicate_groups)}")

    for canonical_key, grouped_games in list(duplicate_groups.items())[:20]:
        print(f"\nGROUP {canonical_key}")
        for row in grouped_games:
            print(
                f"  id={row.id} created_at={row.created_at} "
                f"game_key={row.game_key}"
            )

    if not args.apply:
        return

    for game_id, game_key in updates.items():
        client.patch_game_key(game_id, game_key)
    if deletions:
        deleted = client.delete_games(deletions)
        print(f"deleted_games={deleted}")

    if args.recompute_regional_elo:
        recompute_regional_elo()
        print("regional_elo_recomputed=true")


if __name__ == "__main__":
    main()
