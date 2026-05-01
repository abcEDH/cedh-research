#!/usr/bin/env python3
"""Rebuild derived global Elo tables from global_elo_game_results."""

from __future__ import annotations

import argparse
import ast
import math
import os
import re
import time
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from ingest import SupabaseClient, load_local_env

K_FACTOR = 48
DEFAULT_RATING = 1500.0
ELO_BASE = 2
ELO_DIVISOR = 200
GLOBAL_REGION_TYPE = "global"
GLOBAL_REGION_KEY = "ALL"
ACTIVE_LOOKBACK_DAYS = 180


def load_region_country_map() -> dict[str, str]:
    """Load the checked-in state/country mapping without importing regional_elo.py."""
    source = Path(__file__).with_name("regional_elo.py").read_text()
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "REGION_COUNTRY_BY_STATE" for target in node.targets):
                value = ast.literal_eval(node.value)
                return dict(value)
    return {}


REGION_COUNTRY_BY_STATE = load_region_country_map()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_date(value: str | None) -> date | None:
    parsed = parse_datetime(value)
    return parsed.date() if parsed else None


def normalize_key(value: str | None) -> str:
    return (value or "").strip().upper()


def infer_country(state: str | None, country: str | None) -> str:
    normalized_country = normalize_key(country)
    if normalized_country:
        return normalized_country
    return REGION_COUNTRY_BY_STATE.get(normalize_key(state), "")


def score_for_result(result: str | None) -> float | None:
    if result == "win":
        return 1.0
    if result == "draw":
        return 0.5
    if result == "loss":
        return 0.0
    return None


def rating_equity(rating: float) -> float:
    return pow(ELO_BASE, rating / ELO_DIVISOR)


def empty_rating(player_id: str) -> dict[str, Any]:
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


def with_page_params(
    params: dict[str, str] | list[tuple[str, str]], limit: int, offset: int
) -> dict[str, str] | list[tuple[str, str]]:
    if isinstance(params, list):
        return [*params, ("limit", str(limit)), ("offset", str(offset))]
    return {**params, "limit": str(limit), "offset": str(offset)}


def fetch_all(
    client: SupabaseClient,
    table: str,
    params: dict[str, str] | list[tuple[str, str]],
    limit: int = 1000,
    label: str | None = None,
    max_retries: int = 8,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    started = time.time()
    while True:
        page = client.select(table, with_page_params(params, limit, offset), max_retries=max_retries)
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
        if offset % 25000 == 0:
            elapsed = time.time() - started
            source = label or table
            print(f"Fetched {offset:,} rows from {source} in {elapsed:.1f}s", flush=True)
    return rows


def _http_error_is_missing_topdeck_column(exc: requests.exceptions.HTTPError, column_name: str) -> bool:
    response = exc.response
    status_code = getattr(response, "status_code", None)
    response_text = str(getattr(response, "text", "") or "").lower()
    normalized_column = column_name.lower()

    if status_code not in {400, 404} or normalized_column not in response_text:
        return False

    missing_column_markers = (
        "42703",
        "pgrst204",
        "could not find",
        "does not exist",
        "unknown column",
    )
    return any(marker in response_text for marker in missing_column_markers)


def detect_topdeck_elo_id_column(client: SupabaseClient) -> str:
    """Detect the TopDeck Elo id column without weakening full snapshot retries."""
    last_schema_error: requests.exceptions.HTTPError | None = None
    for id_column in ("topdeck_id", "uid"):
        try:
            client.select(
                "topdeck_player_elos",
                {"select": id_column, "limit": "1"},
                max_retries=1,
            )
            return id_column
        except requests.exceptions.HTTPError as exc:
            if _http_error_is_missing_topdeck_column(exc, id_column):
                last_schema_error = exc
                if id_column == "topdeck_id":
                    print(
                        "topdeck_player_elos.topdeck_id not available; falling back to uid",
                        flush=True,
                    )
                continue
            raise

    raise RuntimeError("topdeck_player_elos is missing both topdeck_id and uid columns") from last_schema_error


def fetch_topdeck_elos(client: SupabaseClient) -> dict[str, float]:
    """Read TopDeck Elo rows from either the normalized or legacy live schema."""
    id_column = detect_topdeck_elo_id_column(client)
    rows = fetch_all(
        client,
        "topdeck_player_elos",
        {"select": f"{id_column},elo"},
    )
    return {str(row[id_column]): float(row["elo"]) for row in rows if row.get(id_column) and row.get("elo") is not None}


def month_starts(start: date, end: date) -> list[date]:
    current = date(start.year, start.month, 1)
    months: list[date] = []
    while current <= end:
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def bracket_round_sort_value(round_name: str | None) -> int:
    """Order bracket rounds as Top 64, Top 32, ..., Top 4, Finals."""
    normalized = (round_name or "").strip().lower()
    match = re.search(r"top\s*(\d+)", normalized)
    if match:
        return 10_000 - int(match.group(1))
    if normalized in {"final", "finals", "championship"}:
        return 10_000
    if "semi" in normalized:
        return 9_996
    if "quarter" in normalized:
        return 9_992
    return 9_900


def game_sort_key(item: tuple[str, list[dict[str, Any]]]) -> tuple[Any, ...]:
    game_id, rows = item
    first = rows[0]
    round_number = first.get("round_number")
    round_name = first.get("round_name")
    is_swiss = isinstance(round_number, int)
    return (
        first.get("start_date") or "",
        first.get("tournament_id") or "",
        0 if is_swiss else 1,
        round_number if is_swiss else bracket_round_sort_value(round_name),
        first.get("table_number") if first.get("table_number") is not None else 999_999,
        game_id,
    )


def fetch_results_by_month(client: SupabaseClient) -> list[dict[str, Any]]:
    select = (
        "game_id,tournament_id,start_date,state,country,entry_id,player_id,topdeck_id,"
        "player_name,result,is_draw,round_number,round_name,table_number"
    )
    all_rows: list[dict[str, Any]] = []
    windows = month_starts(date(2022, 8, 1), datetime.now(UTC).date())
    for window_start in windows:
        window_end = next_month(window_start)
        rows = fetch_all(
            client,
            "global_elo_game_results",
            [
                ("select", select),
                ("start_date", f"gte.{window_start.isoformat()}"),
                ("start_date", f"lt.{window_end.isoformat()}"),
            ],
            label=f"global_elo_game_results {window_start:%Y-%m}",
        )
        all_rows.extend(rows)
        print(
            f"Fetched {len(rows):,} rows for {window_start:%Y-%m}; total {len(all_rows):,}",
            flush=True,
        )
    return all_rows


def rest_delete(client: SupabaseClient, table: str, params: dict[str, str]) -> None:
    response = requests.delete(
        f"{client.url}/rest/v1/{table}",
        headers={**client.headers, "Prefer": "return=minimal"},
        params=params,
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"DELETE {table} failed: {response.status_code} {response.text}")


def chunked_upsert(
    client: SupabaseClient,
    table: str,
    rows: list[dict[str, Any]],
    on_conflict: str,
    chunk_size: int = 1000,
) -> None:
    for start in range(0, len(rows), chunk_size):
        client.upsert(table, rows[start : start + chunk_size], on_conflict=on_conflict)
        if start and start % 25000 == 0:
            print(f"Upserted {start:,}/{len(rows):,} rows into {table}", flush=True)


def apply_game(
    game_rows: list[dict[str, Any]],
    ratings: dict[str, dict[str, Any]],
    state_activity: dict[tuple[str, str], dict[str, Any]],
    player_meta: dict[str, dict[str, str | None]],
    now: date,
) -> list[dict[str, Any]]:
    participants: list[dict[str, Any]] = []
    seen_players: set[str] = set()
    for row in game_rows:
        player_id = row.get("player_id")
        if not player_id or player_id in seen_players:
            continue
        if score_for_result(row.get("result")) is None:
            continue
        participants.append(row)
        seen_players.add(player_id)
    if len(participants) < 2:
        return []
    if not any((score_for_result(row.get("result")) or 0) > 0 for row in participants):
        return []

    game_date = parse_date(participants[0].get("start_date"))
    game_datetime = participants[0].get("start_date")
    deltas: dict[str, float] = defaultdict(float)
    expected_scores: dict[str, float] = {}
    before_ratings: dict[str, float] = {}

    for row in participants:
        player_id = row["player_id"]
        ratings.setdefault(player_id, empty_rating(player_id))
        player_meta.setdefault(
            player_id,
            {
                "player_name": row.get("player_name"),
                "topdeck_id": row.get("topdeck_id"),
            },
        )
        before_ratings[player_id] = float(ratings[player_id]["rating"])

    total_equity = sum(rating_equity(before_ratings[row["player_id"]]) for row in participants)
    draw_count = sum(1 for row in participants if row.get("result") == "draw")

    for row in participants:
        player_id = row["player_id"]
        score = score_for_result(row.get("result"))
        if score is None:
            continue
        actual = 1 / draw_count if row.get("result") == "draw" and draw_count else score
        expected = rating_equity(before_ratings[player_id]) / total_equity
        expected_scores[player_id] = expected
        deltas[player_id] = K_FACTOR * (actual - expected)

    events: list[dict[str, Any]] = []
    for row in participants:
        player_id = row["player_id"]
        result = row.get("result")
        score = score_for_result(result)
        if score is None:
            continue

        rating_row = ratings[player_id]
        rating_row["rating"] = round(float(rating_row["rating"]) + deltas[player_id], 6)
        rating_row["games_played"] += 1
        if result == "win":
            rating_row["wins"] += 1
        elif result == "draw":
            rating_row["draws"] += 1
        elif result == "loss":
            rating_row["losses"] += 1
        if game_date and (rating_row["last_game_date"] is None or game_date > rating_row["last_game_date"]):
            rating_row["last_game_date"] = game_date

        state_key = normalize_key(row.get("state"))
        if state_key:
            country_key = infer_country(row.get("state"), row.get("country"))
            activity_key = (player_id, state_key)
            activity = state_activity.setdefault(
                activity_key,
                {
                    "region_type": "state",
                    "region_key": state_key,
                    "country_key": country_key or None,
                    "player_id": player_id,
                    "games_30d": 0,
                    "games_90d": 0,
                    "games_365d": 0,
                    "games_lifetime": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "last_game_date": None,
                    "activity_score": 0.0,
                    "is_primary_state": False,
                },
            )
            if country_key and not activity.get("country_key"):
                activity["country_key"] = country_key
            activity["games_lifetime"] += 1
            if result == "win":
                activity["wins"] += 1
            elif result == "draw":
                activity["draws"] += 1
            elif result == "loss":
                activity["losses"] += 1
            if game_date:
                age_days = (now - game_date).days
                if age_days <= 30:
                    activity["games_30d"] += 1
                if age_days <= 90:
                    activity["games_90d"] += 1
                if age_days <= 365:
                    activity["games_365d"] += 1
                activity["activity_score"] += math.pow(0.5, max(age_days, 0) / 180)
                if activity["last_game_date"] is None or game_date > activity["last_game_date"]:
                    activity["last_game_date"] = game_date

        events.append(
            {
                "region_type": GLOBAL_REGION_TYPE,
                "region_key": GLOBAL_REGION_KEY,
                "game_id": row["game_id"],
                "tournament_id": row["tournament_id"],
                "player_id": player_id,
                "entry_id": row["entry_id"],
                "game_date": game_datetime,
                "game_result": result,
                "is_draw": bool(row.get("is_draw")) or result == "draw",
                "opponent_count": len(participants) - 1,
                "expected_score": round(expected_scores[player_id], 6),
                "actual_score": 1 / draw_count if result == "draw" and draw_count else score,
                "rating_before": round(before_ratings[player_id], 6),
                "rating_delta": round(deltas[player_id], 6),
                "rating_after": round(float(rating_row["rating"]), 6),
            }
        )
    return events


def build_rows(
    client: SupabaseClient,
    results: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]
]:
    ratings: dict[str, dict[str, Any]] = {}
    state_activity: dict[tuple[str, str], dict[str, Any]] = {}
    player_meta: dict[str, dict[str, str | None]] = {}
    events: list[dict[str, Any]] = []
    today = datetime.now(UTC).date()

    print("Fetching TopDeck Elos for enrichment...", flush=True)
    topdeck_elos = fetch_topdeck_elos(client)

    games: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        games[row["game_id"]].append(row)

    for index, (_, rows) in enumerate(sorted(games.items(), key=game_sort_key), start=1):
        events.extend(apply_game(rows, ratings, state_activity, player_meta, today))
        if index % 25000 == 0:
            print(f"Processed {index:,}/{len(games):,} games", flush=True)

    for activity in state_activity.values():
        activity["activity_score"] = round(float(activity["activity_score"]), 6)

    activity_by_player: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for activity in state_activity.values():
        activity_by_player[activity["player_id"]].append(activity)
    for rows in activity_by_player.values():
        rows.sort(
            key=lambda row: (
                float(row["activity_score"]),
                int(row["games_lifetime"]),
                row["last_game_date"] or date.min,
                row["region_key"],
            ),
            reverse=True,
        )
        rows[0]["is_primary_state"] = True

    rating_rows = []
    for row in ratings.values():
        rating_rows.append(
            {
                **row,
                "rating": round(float(row["rating"]), 3),
                "last_game_date": str(row["last_game_date"]) if row.get("last_game_date") else None,
            }
        )

    state_rows = []
    for row in state_activity.values():
        state_rows.append(
            {
                **row,
                "last_game_date": str(row["last_game_date"]) if row.get("last_game_date") else None,
            }
        )

    primary_by_player = {row["player_id"]: row for row in state_rows if row.get("is_primary_state")}
    active_cutoff = today - timedelta(days=ACTIVE_LOOKBACK_DAYS)
    active_rating_rows = [
        row
        for row in rating_rows
        if row.get("last_game_date") and date.fromisoformat(row["last_game_date"]) >= active_cutoff
    ]
    active_rating_rows.sort(
        key=lambda row: (
            -float(row["rating"]),
            -int(row["games_played"]),
            player_meta[row["player_id"]].get("player_name") or "",
        )
    )

    leaderboard_rows: list[dict[str, Any]] = []

    def append_ranked(region_type: str, region_key: str, country_key: str | None, rows: list[dict[str, Any]]) -> None:
        # We now offer two primary sort paths. The "rank" column remains tied to
        # our internal Elo rating. The "topdeck_elo_rank" is calculated separately.

        # 1. Internal Rank (by rating)
        rows.sort(
            key=lambda row: (
                -float(row["rating"]),
                -float(primary_by_player.get(row["player_id"], {}).get("activity_score", 0)),
                -int(row["games_played"]),
                player_meta[row["player_id"]].get("player_name") or "",
            )
        )
        internal_ranks = {row["player_id"]: rank for rank, row in enumerate(rows, start=1)}

        # 2. TopDeck Rank (by topdeck_elo)
        rows.sort(
            key=lambda row: (
                -(topdeck_elos.get(player_meta[row["player_id"]].get("topdeck_id") or "") or 0),
                -float(row["rating"]),
                player_meta[row["player_id"]].get("player_name") or "",
            )
        )
        topdeck_ranks = {}
        for rank, row in enumerate(rows, start=1):
            tid = player_meta[row["player_id"]].get("topdeck_id")
            if tid and tid in topdeck_elos:
                topdeck_ranks[row["player_id"]] = rank

        for row in rows:
            player_id = row["player_id"]
            meta = player_meta[player_id]
            primary = primary_by_player.get(player_id, {})
            tid = meta.get("topdeck_id")
            t_elo = topdeck_elos.get(tid) if tid else None

            leaderboard_rows.append(
                {
                    "region_type": region_type,
                    "region_key": region_key,
                    "country_key": country_key,
                    "player_id": player_id,
                    "player_name": meta.get("player_name") or "Unknown",
                    "topdeck_id": tid,
                    "rank": internal_ranks[player_id],
                    "topdeck_elo": t_elo,
                    "topdeck_elo_rank": topdeck_ranks.get(player_id),
                    "rating": row["rating"],
                    "games_played": row["games_played"],
                    "wins": row["wins"],
                    "draws": row["draws"],
                    "losses": row["losses"],
                    "last_game_date": row["last_game_date"],
                    "primary_country_key": primary.get("country_key"),
                    "primary_region_key": primary.get("region_key"),
                    "activity_score": primary.get("activity_score"),
                }
            )

    append_ranked(GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY, None, active_rating_rows.copy())
    by_country: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_state: dict[tuple[str | None, str], list[dict[str, Any]]] = defaultdict(list)
    active_by_id = {row["player_id"]: row for row in active_rating_rows}
    for player_id, primary in primary_by_player.items():
        rating = active_by_id.get(player_id)
        if not rating:
            continue
        country_key = primary.get("country_key")
        state_key = primary.get("region_key")
        if country_key:
            by_country[country_key].append(rating)
        if state_key:
            by_state[(country_key, state_key)].append(rating)
    for country_key, rows in by_country.items():
        append_ranked("country", country_key, country_key, rows)
    for (country_key, state_key), rows in by_state.items():
        append_ranked("state", state_key, country_key, rows)

    profile_rows: list[dict[str, Any]] = []
    for row in rating_rows:
        meta = player_meta[row["player_id"]]
        assignments = sorted(
            activity_by_player.get(row["player_id"], []),
            key=lambda activity: (
                -float(activity["activity_score"]),
                -int(activity["games_lifetime"]),
                activity["region_key"],
            ),
        )
        primary = primary_by_player.get(row["player_id"], {})
        profile_rows.append(
            {
                "player_id": row["player_id"],
                "topdeck_id": meta.get("topdeck_id"),
                "player_name": meta.get("player_name") or "Unknown",
                "games_played": row["games_played"],
                "wins": row["wins"],
                "draws": row["draws"],
                "losses": row["losses"],
                "last_game_date": row["last_game_date"],
                "home_country_key": primary.get("country_key"),
                "home_region_key": primary.get("region_key"),
                "state_assignments": [
                    {
                        "country_key": activity.get("country_key"),
                        "region_key": activity.get("region_key"),
                        "games_played": activity.get("games_lifetime"),
                        "wins": activity.get("wins"),
                        "draws": activity.get("draws"),
                        "losses": activity.get("losses"),
                    }
                    for activity in assignments
                ],
            }
        )

    return rating_rows, state_rows, events, leaderboard_rows, profile_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--preview-topdeck-id", default="")
    args = parser.parse_args()

    load_local_env()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
    client = SupabaseClient(url, key)

    results = fetch_results_by_month(client)
    print(f"Fetched {len(results):,} participant result rows", flush=True)
    rating_rows, state_rows, event_rows, leaderboard_rows, profile_rows = build_rows(client, results)
    print(
        "Built "
        f"{len(rating_rows):,} ratings, "
        f"{len(state_rows):,} state activity rows, "
        f"{len(event_rows):,} game events, "
        f"{len(leaderboard_rows):,} active leaderboard rows, "
        f"{len(profile_rows):,} profiles",
        flush=True,
    )
    if args.preview_topdeck_id:
        preview_profiles = [row for row in profile_rows if row.get("topdeck_id") == args.preview_topdeck_id]
        if preview_profiles:
            profile = preview_profiles[0]
            rating = next(row for row in rating_rows if row["player_id"] == profile["player_id"])
            print(
                "Preview "
                f"{profile['player_name']} ({args.preview_topdeck_id}): "
                f"rating={rating['rating']} "
                f"games={rating['games_played']} "
                f"record={rating['wins']}/{rating['draws']}/{rating['losses']} "
                f"last={rating['last_game_date']} "
                f"home={profile['home_country_key']}/{profile['home_region_key']}",
                flush=True,
            )
        else:
            print(f"Preview player not found: {args.preview_topdeck_id}", flush=True)
    if not args.apply:
        print("Dry run complete. Pass --apply to write changes.", flush=True)
        return

    print("Writing derived Elo tables", flush=True)
    # We use UPSERT for almost everything, so explicit DELETE is only for tables
    # where we want to ensure no stale data remains (like state activity).
    # For global_elo_game_events, we'll just upsert and let it overwrite.

    print("Upserting ratings", flush=True)
    chunked_upsert(client, "global_elo_ratings", rating_rows, "player_id,region_type,region_key")

    print("Upserting state activity", flush=True)
    # Clear state activity before re-upserting to ensure old primary states are removed
    rest_delete(client, "global_elo_state_activity", {"region_type": "eq.state"})
    chunked_upsert(client, "global_elo_state_activity", state_rows, "region_type,region_key,player_id")

    print("Upserting game events", flush=True)
    chunked_upsert(client, "global_elo_game_events", event_rows, "region_type,region_key,game_id,player_id")

    print("Upserting active leaderboard", flush=True)
    # We clear the leaderboard because rank order changes and we don't want trailing rows
    rest_delete(client, "global_elo_active_leaderboard", {"region_type": "not.is.null"})
    chunked_upsert(client, "global_elo_active_leaderboard", leaderboard_rows, "region_type,region_key,player_id")

    print("Upserting profile summaries", flush=True)
    chunked_upsert(client, "global_elo_player_profile_summaries", profile_rows, "player_id")
    print("Done", flush=True)


if __name__ == "__main__":
    main()
