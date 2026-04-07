#!/usr/bin/env python3
"""Compute a global cEDH Elo and derive state assignments from recency + volume.

Usage:
  python src/regional_elo.py

The resulting data model is:
  - `regional_elo_ratings`: one global row per player (`global` / `ALL`)
  - `regional_elo_state_activity`: per-player state activity snapshots
  - `regional_elo_leaderboard` view: state leaderboards ranked by global Elo
    after assigning each player to a primary state
"""

from __future__ import annotations

import argparse
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List

from ingest import SupabaseClient

K_FACTOR = 30
DEFAULT_RATING = 1500.0
ELO_BASE = 2
ELO_DIVISOR = 200
GLOBAL_REGION_TYPE = "global"
GLOBAL_REGION_KEY = "ALL"
STATE_REGION_TYPE = "state"


@dataclass
class PlayerRating:
    rating: float = DEFAULT_RATING
    games: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    last_game_date: str | None = None


@dataclass
class StateActivity:
    games_30d: int = 0
    games_90d: int = 0
    games_365d: int = 0
    games_lifetime: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    last_game_date: str | None = None
    activity_score: float = 0.0
    is_primary_state: bool = False


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


def fetch_game_results(client: SupabaseClient) -> List[Dict[str, Any]]:
    tournaments = fetch_all(
        client,
        "tournaments",
        {
            "select": "id,start_date,state,country,city,name",
            "state": "not.is.null",
            "order": "start_date.asc,id.asc",
        },
    )
    tournament_map = {
        row["id"]: row
        for row in tournaments
        if (row.get("state") or "").strip()
    }
    if not tournament_map:
        return []

    games = fetch_all(
        client,
        "games",
        {
            "select": "id,tournament_id,is_draw,round_number,round_name,table_number",
            "order": "tournament_id.asc,id.asc",
        },
    )
    filtered_games = [row for row in games if row.get("tournament_id") in tournament_map]
    game_map = {row["id"]: row for row in filtered_games}
    if not game_map:
        return []

    entries = fetch_all(
        client,
        "tournament_entries",
        {
            "select": "id,player_id",
            "order": "id.asc",
        },
    )
    entry_map = {row["id"]: row for row in entries if row.get("player_id")}
    if not entry_map:
        return []

    participants = fetch_all(
        client,
        "game_participants",
        {
            "select": "game_id,entry_id,result",
            "order": "game_id.asc,entry_id.asc",
        },
    )

    rows: List[Dict[str, Any]] = []
    for participant in participants:
        game = game_map.get(participant.get("game_id"))
        entry = entry_map.get(participant.get("entry_id"))
        if not game or not entry:
            continue
        tournament = tournament_map.get(game["tournament_id"])
        if not tournament:
            continue
        rows.append(
            {
                "game_id": game["id"],
                "tournament_id": game["tournament_id"],
                "start_date": tournament.get("start_date"),
                "state": tournament.get("state"),
                "country": tournament.get("country"),
                "city": tournament.get("city"),
                "tournament_name": tournament.get("name"),
                "entry_id": participant.get("entry_id"),
                "player_id": entry.get("player_id"),
                "result": participant.get("result"),
                "is_draw": game.get("is_draw"),
                "round_number": game.get("round_number"),
                "round_name": game.get("round_name"),
                "table_number": game.get("table_number"),
            }
        )

    rows.sort(
        key=lambda row: (
            row.get("start_date") or "",
            row.get("game_id") or "",
            row.get("table_number") if row.get("table_number") is not None else -1,
            row.get("entry_id") or "",
        )
    )
    return rows


def parse_game_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def normalized_state(row: Dict[str, Any]) -> str | None:
    state = (row.get("state") or "").strip()
    return state.upper() if state else None


def included_game(rows: List[Dict[str, Any]]) -> bool:
    if not rows:
        return False
    players = [row["player_id"] for row in rows if row.get("player_id")]
    if len(players) < 2:
        return False
    if any((row.get("result") or "") == "bye" for row in rows):
        return False
    return True


def compute_expected_scores(players: List[str], ratings: Dict[str, PlayerRating]) -> dict[str, float]:
    equities: dict[str, float] = {}
    total_equity = 0.0
    for player_id in players:
        equity = ELO_BASE ** (ratings[player_id].rating / ELO_DIVISOR)
        equities[player_id] = equity
        total_equity += equity

    if total_equity == 0:
        return {player_id: 0.0 for player_id in players}
    return {player_id: equity / total_equity for player_id, equity in equities.items()}


def bucketed_activity_score(activity: StateActivity) -> float:
    games_31_90 = max(activity.games_90d - activity.games_30d, 0)
    games_91_365 = max(activity.games_365d - activity.games_90d, 0)
    return round(
        (1.0 * activity.games_30d)
        + (0.35 * games_31_90)
        + (0.10 * games_91_365)
        + (0.02 * activity.games_lifetime),
        6,
    )


def process_games(
    rows: List[Dict[str, Any]],
) -> tuple[Dict[str, PlayerRating], Dict[str, Dict[str, StateActivity]], List[Dict[str, Any]]]:
    global_ratings: Dict[str, PlayerRating] = defaultdict(PlayerRating)
    state_activity: Dict[str, Dict[str, StateActivity]] = defaultdict(lambda: defaultdict(StateActivity))
    event_rows: List[Dict[str, Any]] = []

    current_game_id: str | None = None
    buffer: List[Dict[str, Any]] = []

    def flush_game(game_rows: List[Dict[str, Any]]) -> None:
        if not included_game(game_rows):
            return

        game_date_raw = game_rows[0].get("start_date")
        game_date = parse_game_date(game_date_raw)
        today = datetime.utcnow().date()
        age_days = (today - game_date).days if game_date else None
        players = [row["player_id"] for row in game_rows if row.get("player_id")]
        expected_scores = compute_expected_scores(players, global_ratings)
        is_draw = any((row.get("result") or "") == "draw" for row in game_rows) or bool(game_rows[0].get("is_draw"))
        draw_value = 1.0 / len(players) if is_draw and players else 0.0
        state_key = normalized_state(game_rows[0])

        for row in game_rows:
            player_id = row["player_id"]
            rating_stats = global_ratings[player_id]
            expected = expected_scores[player_id]

            if is_draw:
                actual = draw_value
                rating_stats.draws += 1
            else:
                actual = 1.0 if row.get("result") == "win" else 0.0
                if actual == 1.0:
                    rating_stats.wins += 1
                else:
                    rating_stats.losses += 1

            before = rating_stats.rating
            delta = K_FACTOR * (actual - expected)
            rating_stats.rating += delta
            rating_stats.games += 1
            rating_stats.last_game_date = game_date_raw or rating_stats.last_game_date

            event_rows.append(
                {
                    "region_type": GLOBAL_REGION_TYPE,
                    "region_key": GLOBAL_REGION_KEY,
                    "game_id": row["game_id"],
                    "tournament_id": row["tournament_id"],
                    "player_id": player_id,
                    "entry_id": row["entry_id"],
                    "game_date": game_date_raw,
                    "game_result": row.get("result") or ("draw" if is_draw else "loss"),
                    "is_draw": is_draw,
                    "opponent_count": max(len(players) - 1, 0),
                    "expected_score": round(expected, 6),
                    "actual_score": round(actual, 6),
                    "rating_before": round(before, 6),
                    "rating_delta": round(delta, 6),
                    "rating_after": round(rating_stats.rating, 6),
                }
            )

            if not state_key:
                continue

            activity = state_activity[player_id][state_key]
            activity.games_lifetime += 1
            activity.last_game_date = game_date_raw or activity.last_game_date
            if is_draw:
                activity.draws += 1
            elif actual == 1.0:
                activity.wins += 1
            else:
                activity.losses += 1

            if age_days is None:
                continue
            if age_days <= 365:
                activity.games_365d += 1
            if age_days <= 90:
                activity.games_90d += 1
            if age_days <= 30:
                activity.games_30d += 1

    for row in rows:
        game_id = row["game_id"]
        if current_game_id is None:
            current_game_id = game_id
        if game_id != current_game_id:
            flush_game(buffer)
            buffer = []
            current_game_id = game_id
        buffer.append(row)

    if buffer:
        flush_game(buffer)

    for player_states in state_activity.values():
        primary_state: str | None = None
        primary_sort_key: tuple[float, str, int, int, str] | None = None
        for region_key, activity in player_states.items():
            activity.activity_score = bucketed_activity_score(activity)
            sort_key = (
                activity.activity_score,
                activity.last_game_date or "",
                activity.games_30d,
                activity.games_lifetime,
                region_key,
            )
            if primary_sort_key is None or sort_key > primary_sort_key:
                primary_sort_key = sort_key
                primary_state = region_key
        if primary_state:
            player_states[primary_state].is_primary_state = True

    return global_ratings, state_activity, event_rows


def build_global_rating_rows(global_ratings: Dict[str, PlayerRating]) -> List[Dict[str, Any]]:
    updated_at = datetime.utcnow().isoformat()
    rows: List[Dict[str, Any]] = []
    for player_id, stats in global_ratings.items():
        rows.append(
            {
                "region_type": GLOBAL_REGION_TYPE,
                "region_key": GLOBAL_REGION_KEY,
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


def build_state_activity_rows(state_activity: Dict[str, Dict[str, StateActivity]]) -> List[Dict[str, Any]]:
    updated_at = datetime.utcnow().isoformat()
    rows: List[Dict[str, Any]] = []
    for player_id, state_rows in state_activity.items():
        for region_key, activity in state_rows.items():
            rows.append(
                {
                    "region_type": STATE_REGION_TYPE,
                    "region_key": region_key,
                    "player_id": player_id,
                    "games_30d": activity.games_30d,
                    "games_90d": activity.games_90d,
                    "games_365d": activity.games_365d,
                    "games_lifetime": activity.games_lifetime,
                    "wins": activity.wins,
                    "draws": activity.draws,
                    "losses": activity.losses,
                    "last_game_date": activity.last_game_date,
                    "activity_score": activity.activity_score,
                    "is_primary_state": activity.is_primary_state,
                    "updated_at": updated_at,
                }
            )
    return rows


def upsert_rows(client: SupabaseClient, table: str, rows: List[Dict[str, Any]], on_conflict: str) -> None:
    if not rows:
        print(f"No rows to upsert for {table}.")
        return

    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        client.upsert(table, batch, on_conflict=on_conflict)
        print(f"Upserted {len(batch)} rows into {table}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute global Elo and derived state activity leaderboards")
    parser.parse_args()

    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)

    rows = fetch_game_results(client)

    global_ratings, state_activity, event_rows = process_games(rows)

    upsert_rows(
        client,
        "regional_elo_ratings",
        build_global_rating_rows(global_ratings),
        on_conflict="region_type,region_key,player_id",
    )
    upsert_rows(
        client,
        "regional_elo_state_activity",
        build_state_activity_rows(state_activity),
        on_conflict="region_type,region_key,player_id",
    )
    upsert_rows(
        client,
        "regional_elo_game_events",
        event_rows,
        on_conflict="region_type,region_key,game_id,player_id",
    )


if __name__ == "__main__":
    main()
