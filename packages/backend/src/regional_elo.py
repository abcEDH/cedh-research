#!/usr/bin/env python3
"""Compute regional Elo leaderboards and store them in Supabase.

Usage:
  python src/regional_elo.py --region-type state
"""

from __future__ import annotations

import argparse
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

from ingest import SupabaseClient

K_FACTOR = 30
DEFAULT_RATING = 1500.0
ELO_BASE = 2
ELO_DIVISOR = 200


@dataclass
class PlayerStats:
    rating: float = DEFAULT_RATING
    games: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    last_game_date: str | None = None


def load_credentials() -> tuple[str, str]:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        raise SystemExit("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

    return supabase_url, supabase_key


def fetch_all(client: SupabaseClient, table: str, params: Dict[str, Any], limit: int = 1000) -> List[Dict[str, Any]]:
    offset = 0
    rows: List[Dict[str, Any]] = []
    while True:
        page_params = {**params, "limit": limit, "offset": offset}
        page = client.select(table, page_params)
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
        time.sleep(0.05)
    return rows


def region_key_from_row(row: Dict[str, Any], region_type: str) -> str | None:
    if region_type == "state":
        state = (row.get("state") or "").strip()
        return state.upper() if state else None
    return None


def process_game(
    rows: List[Dict[str, Any]],
    region_stats: Dict[str, PlayerStats],
    game_date: str | None,
) -> None:
    if not rows:
        return

    players = [row["player_id"] for row in rows if row.get("player_id")]
    if len(players) < 2:
        return

    if any((row.get("result") or "") == "bye" for row in rows):
        return

    is_draw = any((row.get("result") or "") == "draw" for row in rows) or bool(rows[0].get("is_draw"))
    result_value = 1.0 / len(players) if is_draw else None

    equities = {}
    total_equity = 0.0
    for player_id in players:
        rating = region_stats[player_id].rating
        equity = ELO_BASE ** (rating / ELO_DIVISOR)
        equities[player_id] = equity
        total_equity += equity

    if total_equity == 0:
        return

    for row in rows:
        player_id = row["player_id"]
        stats = region_stats[player_id]
        expected = equities[player_id] / total_equity
        if is_draw:
            result = result_value
            stats.draws += 1
        else:
            result = 1.0 if row.get("result") == "win" else 0.0
            if result == 1.0:
                stats.wins += 1
            else:
                stats.losses += 1

        stats.rating += K_FACTOR * (result - expected)
        stats.games += 1
        stats.last_game_date = game_date or stats.last_game_date


def build_upsert_rows(
    region_type: str,
    region_key: str,
    region_stats: Dict[str, PlayerStats],
) -> List[Dict[str, Any]]:
    updated_at = datetime.utcnow().isoformat()
    rows = []
    for player_id, stats in region_stats.items():
        rows.append(
            {
                "region_type": region_type,
                "region_key": region_key,
                "player_id": player_id,
                "rating": round(stats.rating, 3),
                "games_played": stats.games,
                "wins": stats.wins,
                "draws": stats.draws,
                "losses": stats.losses,
                "last_game_date": stats.last_game_date,
                "updated_at": updated_at,
            }
        )
    return rows


def compute_regional_elo(region_type: str) -> Dict[str, Dict[str, PlayerStats]]:
    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)

    rows = fetch_all(
        client,
        "regional_elo_game_results",
        {
            "order": "start_date.asc,game_id.asc,table_number.asc",
        },
    )

    regions: Dict[str, Dict[str, PlayerStats]] = defaultdict(lambda: defaultdict(PlayerStats))
    current_game_id: str | None = None
    current_region_key: str | None = None
    buffer: List[Dict[str, Any]] = []
    current_game_date: str | None = None

    for row in rows:
        region_key = region_key_from_row(row, region_type)
        if not region_key:
            continue
        game_id = row["game_id"]
        if current_game_id is None:
            current_game_id = game_id
            current_region_key = region_key
            current_game_date = row.get("start_date")

        if game_id != current_game_id or region_key != current_region_key:
            process_game(buffer, regions[current_region_key], current_game_date)
            buffer = []
            current_game_id = game_id
            current_region_key = region_key
            current_game_date = row.get("start_date")

        buffer.append(row)

    if buffer and current_region_key:
        process_game(buffer, regions[current_region_key], current_game_date)

    return regions


def upsert_regional_elo(region_type: str, regions: Dict[str, Dict[str, PlayerStats]]) -> None:
    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)

    all_rows: List[Dict[str, Any]] = []
    for region_key, stats in regions.items():
        all_rows.extend(build_upsert_rows(region_type, region_key, stats))

    if not all_rows:
        print("No regional elo rows to upsert.")
        return

    batch_size = 500
    for i in range(0, len(all_rows), batch_size):
        batch = all_rows[i : i + batch_size]
        client.upsert("regional_elo_ratings", batch, on_conflict="region_type,region_key,player_id")
        print(f"Upserted {len(batch)} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute regional Elo leaderboards")
    parser.add_argument("--region-type", default="state", choices=["state"], help="Region grouping")
    args = parser.parse_args()

    regions = compute_regional_elo(args.region_type)
    upsert_regional_elo(args.region_type, regions)


if __name__ == "__main__":
    main()
