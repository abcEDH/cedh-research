#!/usr/bin/env python3
"""Admin debug helper for regional Elo discrepancies.

Usage:
  python packages/backend/src/regional_elo_debug.py --topdeck-id <TOPDECK_PROFILE_ID>
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

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


class SupabaseDebugClient:
    def __init__(self, url: str, service_key: str):
        self.url = url
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        }

    def select(self, table: str, params: dict[str, str]) -> list[dict]:
        response = requests.get(
            f"{self.url}/rest/v1/{table}",
            headers=self.headers,
            params=params,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()


def print_json(label: str, payload: object) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Debug regional Elo data for one TopDeck profile")
    parser.add_argument("--topdeck-id", required=True, help="TopDeck profile UID")
    args = parser.parse_args()

    url, key = load_credentials()
    client = SupabaseDebugClient(url, key)

    player_rows = client.select(
        "players",
        {
            "select": "id,name,topdeck_id",
            "topdeck_id": f"eq.{args.topdeck_id}",
        },
    )
    if not player_rows:
        raise SystemExit(f"No player found for topdeck_id={args.topdeck_id}")

    player = player_rows[0]
    print_json("PLAYER", player)

    regional_rows = client.select(
        "regional_elo_leaderboard",
        {
            "select": "region_key,rank,rating,games_played,wins,draws,losses,last_game_date",
            "topdeck_id": f"eq.{args.topdeck_id}",
            "order": "games_played.desc",
        },
    )
    print_json("REGIONAL LEADERBOARD ROWS", regional_rows)

    raw_game_rows = client.select(
        "regional_elo_game_results",
        {
            "select": "game_id,start_date,state,tournament_name,round_number,table_number,result",
            "topdeck_id": f"eq.{args.topdeck_id}",
            "order": "start_date.desc",
            "limit": "500",
        },
    )
    print_json("REGIONAL RAW GAME ROWS (LATEST 500)", raw_game_rows[:50])

    entry_rows = client.select(
        "player_commander_entries",
        {
            "select": "start_date,state,commander_name,topdeck_id",
            "topdeck_id": f"eq.{args.topdeck_id}",
            "order": "start_date.desc",
            "limit": "500",
        },
    )
    print_json("PLAYER COMMANDER ENTRIES (LATEST 500)", entry_rows[:50])

    state_counter = Counter((row.get("state") or "").strip().upper() or "<missing>" for row in raw_game_rows)
    tournaments_by_state: dict[str, set[str]] = defaultdict(set)
    results_by_state = defaultdict(Counter)
    duplicate_counter = Counter(
        (
            row.get("tournament_name"),
            row.get("round_number"),
            row.get("table_number"),
            row.get("result"),
        )
        for row in raw_game_rows
    )
    for row in raw_game_rows:
        state = (row.get("state") or "").strip().upper() or "<missing>"
        tournaments_by_state[state].add(row.get("tournament_name") or "<unknown>")
        results_by_state[state][row.get("result") or "<missing>"] += 1

    duplicate_groups = [
        {
            "tournament_name": key[0],
            "round_number": key[1],
            "table_number": key[2],
            "result": key[3],
            "copies": copies,
        }
        for key, copies in duplicate_counter.items()
        if copies > 1
    ]

    summary = {
        "regional_raw_game_count": len(raw_game_rows),
        "regional_distinct_tournaments": len({row.get("tournament_name") for row in raw_game_rows}),
        "regional_inferred_unique_game_count": len(duplicate_counter),
        "entry_row_count": len(entry_rows),
        "entry_distinct_tournaments_by_date_and_commander": len(
            {
                (
                    row.get("start_date"),
                    row.get("state"),
                    row.get("commander_name"),
                )
                for row in entry_rows
            }
        ),
        "games_by_state": dict(state_counter),
        "tournaments_by_state": {state: sorted(names) for state, names in tournaments_by_state.items()},
        "results_by_state": {state: dict(counter) for state, counter in results_by_state.items()},
        "duplicate_game_groups": duplicate_groups,
    }
    print_json("SUMMARY", summary)

    if regional_rows:
        top_region = regional_rows[0]
        expected_games = top_region.get("games_played")
        if isinstance(expected_games, int):
            print("\n=== QUICK READ ===")
            print(
                f"Top counted region: {top_region.get('region_key')} with {expected_games} games "
                f"({top_region.get('wins')}-{top_region.get('draws')}-{top_region.get('losses')})."
            )
            print(
                f"Raw regional rows found: {len(raw_game_rows)}. "
                f"Player commander entry rows found: {len(entry_rows)}."
            )
            if duplicate_groups:
                inferred_unique_games = len(duplicate_counter)
                print(
                    f"Duplicate game signatures detected: {len(duplicate_groups)} groups. "
                    f"Inferred unique games: {inferred_unique_games}."
                )


if __name__ == "__main__":
    main()
