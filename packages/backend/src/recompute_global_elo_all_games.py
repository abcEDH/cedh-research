#!/usr/bin/env python3
"""Recompute global Elo from every game currently exposed by Supabase."""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from ingest import SupabaseClient, load_local_env

K_FACTOR = 48
DEFAULT_RATING = 1500.0
ELO_BASE = 2
ELO_DIVISOR = 200
GLOBAL_REGION_TYPE = "global"
GLOBAL_REGION_KEY = "ALL"


def elo_probability(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + pow(ELO_BASE, (rating_b - rating_a) / ELO_DIVISOR))


def fetch_all(client: SupabaseClient, table: str, params: dict[str, str], limit: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = client.select(table, {**params, "limit": str(limit), "offset": str(offset)})
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
        if offset % 25000 == 0:
            print(f"Fetched {offset} rows from {table}...")
    return rows


def expected_delta(rating: float, opponent_rating: float, score: float) -> float:
    return K_FACTOR * (score - elo_probability(rating, opponent_rating))


def parse_game_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def create_rating(player_id: str) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "region_type": GLOBAL_REGION_TYPE,
        "region_key": GLOBAL_REGION_KEY,
        "rating": DEFAULT_RATING,
        "games_played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "last_game_date": None,
    }


def game_score(result: str) -> float | None:
    if result == "win":
        return 1.0
    if result == "draw":
        return 0.5
    if result == "loss":
        return 0.0
    return None


def apply_game(ratings: dict[str, dict[str, Any]], participants: list[dict[str, Any]]) -> None:
    valid = [
        row
        for row in participants
        if row.get("player_id") and game_score(str(row.get("result") or "")) is not None
    ]
    if len(valid) < 2:
        return

    game_date = parse_game_date(valid[0].get("start_date"))
    deltas: dict[str, float] = defaultdict(float)
    increments: dict[str, dict[str, int]] = defaultdict(lambda: {"games_played": 0, "wins": 0, "draws": 0, "losses": 0})

    for row in valid:
        player_id = row["player_id"]
        ratings.setdefault(player_id, create_rating(player_id))
        result = str(row.get("result") or "")
        increments[player_id]["games_played"] = 1
        if result == "win":
            increments[player_id]["wins"] = 1
        elif result == "draw":
            increments[player_id]["draws"] = 1
        elif result == "loss":
            increments[player_id]["losses"] = 1

    for index, row in enumerate(valid):
        player_id = row["player_id"]
        score = game_score(str(row.get("result") or ""))
        if score is None:
            continue
        player_rating = float(ratings[player_id]["rating"])
        opponents = valid[:index] + valid[index + 1 :]
        for opponent in opponents:
            opponent_id = opponent["player_id"]
            opponent_score = game_score(str(opponent.get("result") or ""))
            if opponent_score is None:
                continue
            deltas[player_id] += expected_delta(
                player_rating,
                float(ratings[opponent_id]["rating"]),
                score,
            ) / max(len(opponents), 1)

    for player_id, delta in deltas.items():
        row = ratings[player_id]
        row["rating"] = round(float(row["rating"]) + delta, 3)
        for key, value in increments[player_id].items():
            row[key] += value
        if game_date and (row["last_game_date"] is None or game_date > row["last_game_date"]):
            row["last_game_date"] = game_date


def build_leaderboard_rows(
    client: SupabaseClient,
    ratings: list[dict[str, Any]],
    player_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    print("Fetching TopDeck Elos for enrichment...", flush=True)
    topdeck_elos = {
        row["topdeck_id"]: float(row["elo"])
        for row in fetch_all(client, "topdeck_player_elos", {"select": "topdeck_id,elo"})
    }

    ranked = sorted(ratings, key=lambda row: (-float(row["rating"]), -int(row["games_played"]), player_lookup.get(row["player_id"], {}).get("name") or ""))
    
    # Pre-calculate TopDeck ranks within the active set
    active_players_with_tid = [
        (row["player_id"], player_lookup.get(row["player_id"], {}).get("topdeck_id"))
        for row in ratings
    ]
    topdeck_ranked = sorted(
        active_players_with_tid,
        key=lambda item: (-(topdeck_elos.get(item[1] or "") or 0), -float(next(r["rating"] for r in ratings if r["player_id"] == item[0]))),
    )
    topdeck_ranks = {}
    for rank, (player_id, tid) in enumerate(topdeck_ranked, start=1):
        if tid and tid in topdeck_elos:
            topdeck_ranks[player_id] = rank

    rows: list[dict[str, Any]] = []
    for rank, row in enumerate(ranked, start=1):
        player = player_lookup.get(row["player_id"], {})
        tid = player.get("topdeck_id")
        t_elo = topdeck_elos.get(tid) if tid else None
        
        rows.append(
            {
                "region_type": GLOBAL_REGION_TYPE,
                "region_key": GLOBAL_REGION_KEY,
                "country_key": None,
                "player_id": row["player_id"],
                "player_name": player.get("name") or "Unknown",
                "topdeck_id": tid,
                "rank": rank,
                "topdeck_elo": t_elo,
                "topdeck_elo_rank": topdeck_ranks.get(row["player_id"]),
                "rating": row["rating"],
                "games_played": row["games_played"],
                "wins": row["wins"],
                "draws": row["draws"],
                "losses": row["losses"],
                "last_game_date": str(row["last_game_date"]) if row.get("last_game_date") else None,
                "primary_country_key": None,
                "primary_region_key": None,
                "activity_score": None,
            }
        )
    return rows


def fetch_players(client: SupabaseClient, player_ids: list[str]) -> dict[str, dict[str, Any]]:
    players: dict[str, dict[str, Any]] = {}
    for start in range(0, len(player_ids), 100):
        chunk = player_ids[start : start + 100]
        rows = client.select(
            "players",
            {
                "id": f"in.({','.join(chunk)})",
                "select": "id,name,topdeck_id",
            },
        )
        for row in rows:
            players[row["id"]] = row
    return players


def main() -> None:
    load_local_env()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")

    client = SupabaseClient(supabase_url, supabase_key)
    rows = fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": "game_id,start_date,player_id,result",
            "result": "neq.bye",
            "order": "start_date.asc,game_id.asc",
        },
    )
    print(f"Fetched {len(rows)} participant result rows")

    games: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("game_id"):
            games[row["game_id"]].append(row)
    print(f"Processing {len(games)} games")

    ratings: dict[str, dict[str, Any]] = {}
    for _, participants in sorted(
        games.items(),
        key=lambda item: ((item[1][0].get("start_date") or ""), item[0]),
    ):
        apply_game(ratings, participants)

    rating_rows = list(ratings.values())
    player_lookup = fetch_players(client, list(ratings))
    leaderboard_rows = build_leaderboard_rows(client, rating_rows, player_lookup)
    profile_rows = [
        {
            "player_id": row["player_id"],
            "topdeck_id": player_lookup.get(row["player_id"], {}).get("topdeck_id"),
            "player_name": player_lookup.get(row["player_id"], {}).get("name") or "Unknown",
            "games_played": row["games_played"],
            "wins": row["wins"],
            "draws": row["draws"],
            "losses": row["losses"],
            "last_game_date": str(row["last_game_date"]) if row.get("last_game_date") else None,
            "home_country_key": None,
            "home_region_key": None,
            "state_assignments": [],
        }
        for row in rating_rows
    ]

    print(f"Upserting {len(rating_rows)} global_elo_ratings rows")
    for start in range(0, len(rating_rows), 1000):
        payload = [
            {
                **row,
                "last_game_date": str(row["last_game_date"]) if row.get("last_game_date") else None,
            }
            for row in rating_rows[start : start + 1000]
        ]
        client.upsert("global_elo_ratings", payload, on_conflict="player_id,region_type,region_key")

    print(f"Upserting {len(leaderboard_rows)} global_elo_active_leaderboard rows")
    for start in range(0, len(leaderboard_rows), 1000):
        client.upsert(
            "global_elo_active_leaderboard",
            leaderboard_rows[start : start + 1000],
            on_conflict="region_type,region_key,player_id",
        )

    print(f"Upserting {len(profile_rows)} global_elo_player_profile_summaries rows")
    for start in range(0, len(profile_rows), 1000):
        client.upsert(
            "global_elo_player_profile_summaries",
            profile_rows[start : start + 1000],
            on_conflict="player_id",
        )

    print(
        f"Done. Games={len(games)} players={len(rating_rows)} "
        f"top_rating={leaderboard_rows[0]['rating'] if leaderboard_rows else 'n/a'}"
    )


if __name__ == "__main__":
    main()
