#!/usr/bin/env python3
"""Compute the global Elo leaderboard and derived state activity.

Usage:
  python src/regional_elo.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import requests
from postgrest.exceptions import APIError

from supabase import Client
from supabase_client import DirectPostgresClient, fetch_all, get_supabase_client, upsert_batched

K_FACTOR = 48
DEFAULT_RATING = 1500.0
ELO_BASE = 2
ELO_DIVISOR = 200
GLOBAL_REGION_TYPE = "global"
GLOBAL_REGION_KEY = "ALL"
STATE_REGION_TYPE = "state"
GLOBAL_ELO_RATINGS_TABLE_CANDIDATES = ("global_elo_ratings", "regional_elo_ratings")
GAME_RESULTS_TABLE_CANDIDATES = ("global_elo_game_results", "regional_elo_game_results")
COMMANDER_PRIMARY_LOOKBACK_MONTHS = 6
COMMANDER_FALLBACK_LOOKBACK_MONTHS = 12
COMMANDER_MIN_PRIMARY_ENTRIES = 2
COMMANDER_RECENCY_HALF_LIFE_DAYS = 24
ACTIVE_PLAYER_LOOKBACK_MONTHS = 6
# Business rule: players with no tournaments in the last 6 months are excluded
# from the public rankings (rank / topdeck_elo_rank), regardless of historical
# games played or rating. See docs/decisions/0016-rank-activity-window-and-topdeck-snapshot-pruning.md.
RANK_ACTIVITY_WINDOW_DAYS = 183
REGION_COUNTRY_BY_STATE = {
    "AGDER": "NORWAY",
    "ALABAMA": "UNITED STATES",
    "ALBERTA": "CANADA",
    "ANDALUCÍA": "SPAIN",
    "ANDALUSIA": "SPAIN",
    "ANDORRA LA VELLA": "ANDORRA",
    "ANTOFAGASTA": "CHILE",
    "ARAGÓN": "SPAIN",
    "ARAUCANÍA": "CHILE",
    "ARIZONA": "UNITED STATES",
    "ARKANSAS": "UNITED STATES",
    "AUCKLAND": "NEW ZEALAND",
    "BADEN-WURTTEMBERG": "GERMANY",
    "BADEN-WÜRTTEMBERG": "GERMANY",
    "BAJA CALIFORNIA": "MEXICO",
    "BANGKOK": "THAILAND",
    "BASQUE COUNTRY": "SPAIN",
    "BAVARIA": "GERMANY",
    "BAYERN": "GERMANY",
    "BERLIN": "GERMANY",
    "BERN": "SWITZERLAND",
    "BÍO BÍO": "CHILE",
    "BOGOTA": "COLOMBIA",
    "BOGOTÁ": "COLOMBIA",
    "BRAGA": "PORTUGAL",
    "BRITISH COLUMBIA": "CANADA",
    "BUENOS AIRES": "ARGENTINA",
    "BULACAN": "PHILIPPINES",
    "CALABRIA": "ITALY",
    "CALIFORNIA": "UNITED STATES",
    "CAMBRIDGE": "UNITED KINGDOM",
    "CATALONIA": "SPAIN",
    "CAYO": "BELIZE",
    "CENTRAL JAVA": "INDONESIA",
    "CHICAGO": "UNITED STATES",
    "COLORADO": "UNITED STATES",
    "CONNECTICUT": "UNITED STATES",
    "CÓRDOBA": "ARGENTINA",
    "COQUIMBO": "CHILE",
    "CUNDINAMARCA": "COLOMBIA",
    "D.C.": "UNITED STATES",
    "D.E.": "ARGENTINA",
    "DISTRICT OF COLUMBIA": "UNITED STATES",
    "ENGLAND": "UNITED KINGDOM",
    "FLORIDA": "UNITED STATES",
    "FRANCE": "FRANCE",
    "GALICIA": "SPAIN",
    "GEORGIA": "UNITED STATES",
    "GOLD COAST": "AUSTRALIA",
    "GUADELOUPE": "FRANCE",
    "GUANGDONG": "CHINA",
    "HAUTE GARONNE": "FRANCE",
    "HAUTE-GARONNE": "FRANCE",
    "HERZEGOVINA": "BOSNIA AND HERZEGOVINA",
    "IDAHO": "UNITED STATES",
    "ILLINOIS": "UNITED STATES",
    "INDIANA": "UNITED STATES",
    "IOWA": "UNITED STATES",
    "JOHOR": "MALAYSIA",
    "KANSAS": "UNITED STATES",
    "KENTUCKY": "UNITED STATES",
    "KERALA": "INDIA",
    "KRAKOW": "POLAND",
    "LIAONING": "CHINA",
    "LOMBARDY": "ITALY",
    "LOS ANGELES": "UNITED STATES",
    "LOUISIANA": "UNITED STATES",
    "MACAU": "CHINA",
    "MAGALLANES": "CHILE",
    "MAINE": "UNITED STATES",
    "MANCHESTER": "UNITED KINGDOM",
    "MARYLAND": "UNITED STATES",
    "MASSACHUSETTS": "UNITED STATES",
    "MÉXICO": "MEXICO",
    "MEXICO CITY": "MEXICO",
    "MICHIGAN": "UNITED STATES",
    "MINNESOTA": "UNITED STATES",
    "MISSOURI": "UNITED STATES",
    "MORELOS": "MEXICO",
    "NARAYANGANJ": "BANGLADESH",
    "NEBRASKA": "UNITED STATES",
    "NEVADA": "UNITED STATES",
    "NEW BRAUNSCHWEIG": "GERMANY",
    "NEW JERSEY": "UNITED STATES",
    "NEW SOUTH WALES": "AUSTRALIA",
    "NEW YORK": "UNITED STATES",
    "NEW Zealand": "NEW ZEALAND",
    "NEW ZEALAND": "NEW ZEALAND",
    "NORD-PAS-DE-CALAIS": "FRANCE",
    "NORTH CAROLINA": "UNITED STATES",
    "NORTH JAVA": "INDONESIA",
    "NORTH RHINE-WESTPHALIA": "GERMANY",
    "NORTH RHINE-WESTPHALIA, GERMANY": "GERMANY",
    "NORTHERN TERRITORY": "AUSTRALIA",
    "NORTHWEST TERRITORIES": "CANADA",
    "NOTTINGHAM": "UNITED KINGDOM",
    "NOVA SCOTIA": "CANADA",
    "OHIO": "UNITED STATES",
    "OKLAHOMA": "UNITED STATES",
    "ONTARIO": "CANADA",
    "OREGON": "UNITED STATES",
    "PENNSYLVANIA": "UNITED STATES",
    "PERRY": "UNITED STATES",
    "PUEBLA": "MEXICO",
    "PUERTO RICO": "UNITED STATES",
    "PUNJAB": "INDIA",
    "QUEBEC": "CANADA",
    "QUEENSLAND": "AUSTRALIA",
    "RÍO DE JANEIRO": "BRAZIL",
    "RIO DE JANEIRO": "BRAZIL",
    "SAN PATRICIO": "MEXICO",
    "SAO PAULO": "BRAZIL",
    "SASKATCHEWAN": "CANADA",
    "SCOTLAND": "UNITED KINGDOM",
    "SEOUL": "SOUTH KOREA",
    "SERBED": "SERBIA",
    "SHANGHAI": "CHINA",
    "SHEFFIELD": "UNITED KINGDOM",
    "SICILY": "ITALY",
    "SINGAPORE": "SINGAPORE",
    "SLOVENIJA": "SLOVENIA",
    "SOUTH AUSTRALIA": "AUSTRALIA",
    "SOUTH CAROLINA": "UNITED STATES",
    "SYDNEY": "AUSTRALIA",
    "TAIPEI": "TAIWAN",
    "TAIWAN": "TAIWAN",
    "TARRAGONA": "SPAIN",
    "TENNESSEE": "UNITED STATES",
    "TEXAS": "UNITED STATES",
    "THESSALONIKI": "GREECE",
    "TOKYO": "JAPAN",
    "TORONTO": "CANADA",
    "TRENTO": "ITALY",
    "TUSCANY": "ITALY",
    "UTAH": "UNITED STATES",
    "UTRECHT": "NETHERLANDS",
    "UTRECHT, NETHERLANDS": "NETHERLANDS",
    "VALLÈS": "SPAIN",
    "VERACRUZ": "MEXICO",
    "VICTORIA": "AUSTRALIA",
    "VIRGINIA": "UNITED STATES",
    "WASHINGTON": "UNITED STATES",
    "WEST AUSTRALIA": "AUSTRALIA",
    "WISCONSIN": "UNITED STATES",
    "WYOMING": "UNITED STATES",
    "YUCATÁN": "MEXICO",
    "YUKON": "CANADA",
}

MAINTENANCE_JOBS_TABLE = "elo_maintenance_jobs"


@dataclass
class JobMetrics:
    ratings_count: int
    state_activity_count: int
    game_events_count: int
    leaderboard_count: int
    profile_count: int
    commander_profile_count: int
    duration_seconds: float


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


def elo_probability(rating_a: float, rating_b: float) -> float:
    """Calculate expected probability of A winning."""
    return 1 / (1 + pow(ELO_BASE, (rating_b - rating_a) / ELO_DIVISOR))


def update_elo(winner_rating: float, loser_rating: float) -> tuple[float, float]:
    """Calculate new Elo ratings after a game."""
    expected_winner = elo_probability(winner_rating, loser_rating)
    expected_loser = elo_probability(loser_rating, winner_rating)
    new_winner = winner_rating + K_FACTOR * (1 - expected_winner)
    new_loser = loser_rating + K_FACTOR * (0 - expected_loser)
    return new_winner, new_loser


def get_past_months_cutoff(months: int) -> date:
    """Return date threshold for historical lookback."""
    return (utc_now() - timedelta(days=30 * months)).date()


def get_past_days_cutoff(days: int) -> date:
    """Return date threshold for recent lookback."""
    return (utc_now() - timedelta(days=days)).date()


def normalize_state_for_region(state: str) -> str:
    """Normalize state abbreviation or name for regional grouping."""
    if not state:
        return ""
    return state.upper().strip()


def get_country_for_state(state: str) -> str:
    """Look up country associated with a state."""
    normalized = normalize_state_for_region(state)
    return REGION_COUNTRY_BY_STATE.get(normalized, "")


def create_empty_ratings_row(
    player_id: str, region_type: str, region_key: str, rating: float = DEFAULT_RATING
) -> dict[str, Any]:
    """Create a new ratings row with default values."""
    return {
        "player_id": player_id,
        "region_type": region_type,
        "region_key": region_key,
        "rating": rating,
        "games_played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "win_streak": 0,
        "loss_streak": 0,
    }


def _process_one_game(
    standings: list[tuple[float, int, dict[str, Any]]],
    game_id: str = "",
    tournament_id: str = "",
    game_date: str | None = None,
) -> list[dict[str, Any]]:
    """Produce pairwise Elo events for the players in one game."""
    if len(standings) < 2:
        return []

    # Sort by rating descending, seat ascending to break ties
    standings.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    opponent_count = len(standings) - 1
    events: list[dict[str, Any]] = []
    for rating, seat, standing in standings:
        player_id = standing["id"]
        entry_id = standing.get("entry_id", player_id)
        is_winner = standing["wins"] >= 1
        is_draw = standing["draws"] >= 1

        for opp_rating, opp_seat, opp_standing in standings:
            if opp_rating > rating or (opp_rating == rating and opp_seat < seat):
                opp_player_id = opp_standing["id"]
                opp_entry_id = opp_standing.get("entry_id", opp_player_id)

                if is_winner and not opp_standing["wins"] >= 1:
                    outcome = "win"
                elif opp_standing["wins"] >= 1 and not is_winner:
                    outcome = "loss"
                elif is_draw:
                    outcome = "draw"
                else:
                    outcome = "unknown"

                if outcome in ("win", "loss", "draw"):
                    events.append(
                        {
                            "player_id": player_id,
                            "opp_player_id": opp_player_id,
                            "entry_id": entry_id,
                            "opp_entry_id": opp_entry_id,
                            "outcome": outcome,
                            "is_draw": is_draw,
                            "game_id": game_id,
                            "tournament_id": tournament_id,
                            "game_date": game_date,
                            "opponent_count": opponent_count,
                        }
                    )
    return events


def process_results(
    participant_records: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Process participant records into pairwise Elo events, grouped by game."""
    # Group rows by game_id so we only compare players who actually played together.
    # Without grouping, process_results would produce O(n²) pairs across all 300k+
    # rows — ~57 billion comparisons instead of ~500k.
    games: dict[str, list[tuple[float, int, dict[str, Any]]]] = {}
    game_meta: dict[str, dict[str, Any]] = {}
    ungrouped: list[tuple[float, int, dict[str, Any]]] = []

    for p in participant_records:
        player_id = p.get("player_id") or p.get("entry_id") or ""
        entry_id = p.get("entry_id") or player_id
        standing: dict[str, Any] = {
            "id": player_id,
            "entry_id": entry_id,
            "wins": 1 if p.get("result") == "win" else 0,
            "draws": 1 if p.get("result") == "draw" else 0,
            "losses": 1 if p.get("result") == "loss" else 0,
        }
        rating = p.get("rating", DEFAULT_RATING) or DEFAULT_RATING
        seat = p.get("seat_position") or 0
        game_id = p.get("game_id") or ""

        if game_id:
            games.setdefault(game_id, []).append((rating, seat, standing))
            if game_id not in game_meta:
                game_meta[game_id] = {
                    "tournament_id": p.get("tournament_id") or "",
                    "game_date": p.get("start_date"),
                }
        else:
            ungrouped.append((rating, seat, standing))

    game_events: list[dict[str, Any]] = []
    for gid, standings in games.items():
        meta = game_meta.get(gid, {})
        game_events.extend(_process_one_game(standings, game_id=gid, **meta))

    # Fallback: rows without game_id get processed as one group (legacy behaviour).
    if ungrouped:
        game_events.extend(_process_one_game(ungrouped))

    return game_events


def update_ratings_with_games(
    player_ratings: dict[tuple[str, str, str], dict[str, Any]],
    game_events: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Update ratings based on game results and return game event rows for DB write.

    Groups events by game_id to capture per-game rating_before / rating_after so the
    returned rows can be upserted into global_elo_game_events (one row per player per game).
    """
    # Build a reverse lookup once so each event is O(1) instead of O(n).
    pid_to_key: dict[str, tuple[str, str, str]] = {v["player_id"]: k for k, v in player_ratings.items()}

    # Group all events by game_id to process one game at a time.
    events_by_game: dict[str, list[dict[str, Any]]] = defaultdict(list)
    no_game_id: list[dict[str, Any]] = []
    for event in game_events:
        gid = event.get("game_id") or ""
        if gid:
            events_by_game[gid].append(event)
        else:
            no_game_id.append(event)

    db_event_rows: list[dict[str, Any]] = []

    def _apply_game(events: list[dict[str, Any]], emit_db_rows: bool) -> None:
        # All players whose rating_before we need to snapshot.
        players_in_game: set[str] = set()
        for e in events:
            if e["outcome"] != "unknown":
                players_in_game.add(e["player_id"])
                players_in_game.add(e["opp_player_id"])

        # Capture pre-game ratings.
        rating_before: dict[str, float] = {}
        for pid in players_in_game:
            key = pid_to_key.get(pid)
            if key:
                rating_before[pid] = float(player_ratings[key]["rating"])

        # Apply pairwise events sequentially.
        for event in events:
            player_id = event["player_id"]
            opp_player_id = event["opp_player_id"]
            outcome = event["outcome"]

            if outcome == "unknown":
                continue

            key = pid_to_key.get(player_id)
            opp_key = pid_to_key.get(opp_player_id)
            if not key or not opp_key:
                continue

            player_row = player_ratings[key]
            opp_row = player_ratings[opp_key]

            if outcome == "win":
                new_player, new_opp = update_elo(player_row["rating"], opp_row["rating"])
                player_row["wins"] += 1
                player_row["win_streak"] += 1
                player_row["loss_streak"] = 0
                opp_row["losses"] += 1
                opp_row["win_streak"] = 0
                opp_row["loss_streak"] += 1
            elif outcome == "loss":
                new_opp, new_player = update_elo(opp_row["rating"], player_row["rating"])
                player_row["losses"] += 1
                player_row["loss_streak"] += 1
                player_row["win_streak"] = 0
                opp_row["wins"] += 1
                opp_row["win_streak"] += 1
                opp_row["loss_streak"] = 0
            else:  # draw
                new_player = player_row["rating"]
                new_opp = opp_row["rating"]
                player_row["draws"] += 1
                opp_row["draws"] += 1

            player_row["rating"] = new_player
            opp_row["rating"] = new_opp
            player_row["games_played"] += 1
            opp_row["games_played"] += 1

        if not emit_db_rows:
            return

        # Emit one DB row per player per game.
        # Use first event for game-level metadata; per-player outcome from their events.
        first = events[0] if events else None
        if not first:
            return
        game_id = first["game_id"]
        tournament_id = first.get("tournament_id") or ""
        game_date = first.get("game_date")
        opponent_count = first.get("opponent_count") or (len(players_in_game) - 1)

        # Collect per-player outcome from the events (win > draw > loss).
        player_outcomes: dict[str, str] = {}
        for e in events:
            pid = e["player_id"]
            if e["outcome"] in ("win",):
                player_outcomes[pid] = "win"
            elif e["outcome"] == "draw" and player_outcomes.get(pid) != "win":
                player_outcomes[pid] = "draw"
            elif e["outcome"] == "loss" and pid not in player_outcomes:
                player_outcomes[pid] = "loss"

        # Collect entry_id per player (first occurrence wins).
        # Both player_id and opp_player_id need entry_ids — the top-rated player in a
        # game only ever appears as opp_player_id and would otherwise fall back to pid.
        player_entry_ids: dict[str, str] = {}
        for e in events:
            pid = e["player_id"]
            if pid not in player_entry_ids:
                player_entry_ids[pid] = e.get("entry_id") or pid
            opp_pid = e["opp_player_id"]
            if opp_pid not in player_entry_ids:
                player_entry_ids[opp_pid] = e.get("opp_entry_id") or opp_pid

        # region_type/region_key from the first matched key.
        sample_key = next((pid_to_key[p] for p in players_in_game if p in pid_to_key), None)
        region_type = sample_key[0] if sample_key else GLOBAL_REGION_TYPE
        region_key = sample_key[1] if sample_key else GLOBAL_REGION_KEY

        for pid in players_in_game:
            key = pid_to_key.get(pid)
            if not key or pid not in rating_before:
                continue
            before = rating_before[pid]
            after = float(player_ratings[key]["rating"])
            result = player_outcomes.get(pid, "loss")
            actual = 1.0 if result == "win" else (0.5 if result == "draw" else 0.0)
            # Expected score = sum of pairwise win probabilities vs each opponent
            expected = sum(
                elo_probability(before, rating_before[opp])
                for opp in players_in_game
                if opp != pid and opp in rating_before
            )
            db_event_rows.append(
                {
                    "region_type": region_type,
                    "region_key": region_key,
                    "game_id": game_id,
                    "tournament_id": tournament_id,
                    "player_id": pid,
                    "entry_id": player_entry_ids.get(pid, pid),
                    "game_date": game_date,
                    "game_result": result,
                    "is_draw": result == "draw",
                    "opponent_count": opponent_count,
                    "expected_score": round(expected, 6),
                    "actual_score": round(actual, 6),
                    "rating_before": round(before, 6),
                    "rating_delta": round(after - before, 6),
                    "rating_after": round(after, 6),
                }
            )

    for gid, events in events_by_game.items():
        _apply_game(events, emit_db_rows=bool(gid))

    # Legacy/fallback: rows without game_id — apply but don't emit DB rows (missing required columns).
    if no_game_id:
        _apply_game(no_game_id, emit_db_rows=False)

    return db_event_rows


def claim_job(client: Client, job_id: str, github_run_id: int) -> bool:
    """Atomically claim a job by transitioning it to 'running'."""
    try:
        result = (
            client.table(MAINTENANCE_JOBS_TABLE)
            .update(
                {
                    "status": "running",
                    "github_run_id": github_run_id,
                    "started_at": utc_now().isoformat(),
                    "heartbeat_at": utc_now().isoformat(),
                }
            )
            .eq("id", job_id)
            .in_("status", ["pending", "dispatched"])
            .execute()
        )
        return bool(result.data)
    except Exception as exc:
        print(f"Failed to claim job {job_id}: {exc}", flush=True)
        return False


def update_job_heartbeat(client: Client, job_id: str) -> None:
    """Best-effort heartbeat so stale-job detection knows we are alive."""
    if not job_id:
        return
    try:
        client.table(MAINTENANCE_JOBS_TABLE).update({"heartbeat_at": utc_now().isoformat()}).eq("id", job_id).eq(
            "status", "running"
        ).execute()
    except Exception as exc:
        # Best-effort: heartbeat failures should not fail the job
        print(f"Heartbeat failed for job {job_id} (safe to continue): {exc}", flush=True)


def complete_job(client: Client, job_id: str, metrics: dict) -> None:
    """Mark job as completed with output metrics."""
    now = utc_now().isoformat()
    client.table(MAINTENANCE_JOBS_TABLE).update(
        {"status": "completed", "completed_at": now, "heartbeat_at": now, **metrics}
    ).eq("id", job_id).eq("status", "running").execute()


def fail_job(client: Client, job_id: str, error: str) -> None:
    """Mark job as failed with error message."""
    try:
        client.table(MAINTENANCE_JOBS_TABLE).update(
            {
                "status": "failed",
                "completed_at": utc_now().isoformat(),
                "error_text": error[:2000],
            }
        ).eq("id", job_id).in_("status", ["pending", "dispatched", "running"]).execute()
    except Exception as exc:
        # Best-effort: failure logging should not crash the process
        print(f"Failed to record job failure for {job_id}: {exc}", flush=True)


def fetch_participants_for_leaderboard(
    client: Client,
    lookback_months: int = ACTIVE_PLAYER_LOOKBACK_MONTHS,
    direct: DirectPostgresClient | None = None,
) -> list[dict[str, Any]]:
    cutoff = get_past_months_cutoff(lookback_months)
    if direct is not None:
        return direct.select(
            "global_elo_game_results",
            {
                "start_date": f"gte.{cutoff}",
                "result": "neq.bye",
            },
        )
    return fetch_all(
        client,
        "global_elo_game_results",
        columns="game_id,entry_id,player_id,tournament_id,seat_position,result",
        filters=[("start_date", "gte", cutoff), ("result", "neq", "bye")],
    )


def fetch_commander_participants(
    client: Client, lookback_months: int = COMMANDER_PRIMARY_LOOKBACK_MONTHS
) -> list[dict[str, Any]]:
    cutoff = get_past_months_cutoff(lookback_months)
    return fetch_all(
        client,
        "global_elo_game_results",
        columns="game_id,entry_id,player_id,tournament_id,seat_position,result",
        filters=[("start_date", "gte", str(cutoff)), ("result", "neq", "bye")],
    )


def fetch_distinct_entry_ids(
    client: Client,
    lookback_months: int = ACTIVE_PLAYER_LOOKBACK_MONTHS,
    direct: DirectPostgresClient | None = None,
) -> set[str]:
    cutoff = get_past_months_cutoff(lookback_months)
    if direct is not None:
        rows = direct.select(
            "global_elo_game_results",
            {"start_date": f"gte.{cutoff}"},
        )
        return {r["player_id"] for r in rows}
    rows = fetch_all(
        client,
        "global_elo_game_results",
        columns="player_id",
        filters=[("start_date", "gte", cutoff)],
    )
    return {r["player_id"] for r in rows}


def _rpc_fetch_all(
    client: Client,
    function_name: str,
    payload: dict[str, Any] | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Paginate through a PostgREST RPC that accepts p_limit / p_offset.

    Uses a raw POST (not `client.rpc()`) so a long, explicit timeout can be
    set -- the underlying postgrest-py session's default timeout is much
    shorter and would cut off a slow aggregate RPC.
    """
    rows: list[dict[str, Any]] = []
    offset = 0
    endpoint = f"{client.postgrest.base_url}/rpc/{function_name}"
    headers = dict(client.postgrest.headers)
    while True:
        page_payload = {**(payload or {}), "p_limit": limit, "p_offset": offset}
        response = requests.post(endpoint, json=page_payload, headers=headers, timeout=600)
        if response.status_code >= 400:
            raise RuntimeError(f"RPC {function_name} failed: {response.status_code} {response.text}")
        page = response.json()
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
        print(f"Fetched {len(rows):,} rows from {function_name}", flush=True)
    return rows


def fetch_elo_watermark(client: Client) -> str | None:
    """Return the max game_date in global_elo_game_events, or None if the table is empty."""
    rows = (
        client.table("global_elo_game_events")
        .select("game_date")
        .eq("region_type", "global")
        .order("game_date", desc=True)
        .limit(1)
        .execute()
        .data
    )
    return rows[0]["game_date"] if rows else None


def load_ratings_from_snapshot(
    client: Client,
    watermark: str,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Load per-player Elo ratings as they stood just before *watermark* using the snapshot RPC."""
    rows = _rpc_fetch_all(
        client,
        "get_global_elo_snapshot_before",
        {"cutoff": watermark},
    )
    ratings: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        player_id = row.get("player_id")
        if not player_id:
            continue
        key: tuple[str, str, str] = (GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY, str(player_id))
        ratings[key] = {
            "player_id": str(player_id),
            "region_type": GLOBAL_REGION_TYPE,
            "region_key": GLOBAL_REGION_KEY,
            "rating": float(row.get("rating") or DEFAULT_RATING),
            "games_played": int(row.get("games_played") or 0),
            "wins": int(row.get("wins") or 0),
            "draws": int(row.get("draws") or 0),
            "losses": int(row.get("losses") or 0),
            "win_streak": 0,
            "loss_streak": 0,
        }
    return ratings


def fetch_participants_since(
    client: Client,
    since: str,
    direct: DirectPostgresClient | None = None,
) -> list[dict[str, Any]]:
    """Fetch game participants for games played on or after *since* (ISO date/datetime string)."""
    if direct is not None:
        return direct.select(
            "global_elo_game_results",
            {
                "start_date": f"gte.{since}",
                "result": "neq.bye",
            },
        )
    return fetch_all(
        client,
        "global_elo_game_results",
        columns="game_id,entry_id,player_id,tournament_id,start_date,seat_position,result,is_draw",
        filters=[("start_date", "gte", since), ("result", "neq", "bye")],
    )


def fetch_distinct_commander_ids(client: Client, lookback_months: int = COMMANDER_PRIMARY_LOOKBACK_MONTHS) -> set[str]:
    cutoff = get_past_months_cutoff(lookback_months)
    # Uses PostgREST FK dot-filter: tournament_id is a FK to tournaments.start_date.
    # Tracked in issue #193 for verification before this function is activated.
    rows = fetch_all(
        client,
        "tournament_entries",
        columns="commander_id",
        filters=[("tournament_id.start_date", "gte", cutoff)],
    )
    return {r["commander_id"] for r in rows if r.get("commander_id")}


def compute_leaderboard(player_rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    """Build leaderboard grouped by region."""
    by_region: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in player_rows:
        region_type = row.get("region_type", GLOBAL_REGION_TYPE)
        region_key = row.get("region_key", GLOBAL_REGION_KEY)
        by_region[(region_type, region_key)].append(row)
    for key in by_region:
        by_region[key].sort(key=lambda x: x["rating"], reverse=True)
    return by_region


def build_player_profiles(
    player_rows: list[dict[str, Any]],
    lookback_days: int = 30,
) -> list[dict[str, Any]]:
    """Build profile summary with recent activity indicators."""
    cutoff = get_past_days_cutoff(lookback_days)
    recent_set = {r["player_id"] for r in player_rows if r.get("last_activity") and r["last_activity"] >= cutoff}
    return [r for r in player_rows if r.get("player_id") in recent_set]


UNKNOWN_COMMANDER_NAME = "Unknown Commander"


def build_primary_commanders(client: Client) -> dict[str, tuple[str, float]]:
    """Return {player_id: (commander_name, known_pct)} for players where known_pct >= 0.5.

    Queries tournament_entries joined to commanders, groups by player_id +
    commander_name, picks the most-played known commander per player, and
    computes known_pct = known_entries / total_entries.  Players whose
    known_pct falls below 0.5 are omitted from the result.
    """
    # Fetch all entries with their joined commander name
    rows = fetch_all(
        client,
        "tournament_entries",
        columns="player_id,commander_id,commanders(name)",
    )

    # Tally per-player counts
    total_by_player: dict[str, int] = defaultdict(int)
    known_by_player: dict[str, int] = defaultdict(int)
    commander_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in rows:
        pid = row.get("player_id")
        if not pid:
            continue
        total_by_player[pid] += 1
        commander_data = row.get("commanders") or {}
        name = commander_data.get("name") if isinstance(commander_data, dict) else None
        if name and name != UNKNOWN_COMMANDER_NAME:
            known_by_player[pid] += 1
            commander_counts[pid][name] += 1

    result: dict[str, tuple[str, float]] = {}
    for pid, known_count in known_by_player.items():
        total = total_by_player[pid]
        known_pct = known_count / total if total > 0 else 0.0
        if known_pct < 0.5:
            continue
        # Pick the most-played known commander; break ties alphabetically
        primary = max(commander_counts[pid].items(), key=lambda kv: (kv[1], kv[0]))[0]
        result[pid] = (primary, round(known_pct, 4))

    return result


def detect_active_players(client: Client, lookback_months: int = ACTIVE_PLAYER_LOOKBACK_MONTHS) -> list[dict[str, Any]]:
    """Identify players with recent activity.

    Dedup happens in Postgres via the get_active_global_elo_player_ids RPC
    (SELECT DISTINCT) rather than paging every matching game-result row through
    PostgREST — the latter used deep OFFSET scans that tripped statement_timeout.
    """
    cutoff = get_past_months_cutoff(lookback_months)
    # The RPC's DISTINCT join is computed per request, so use a large page size
    # to fetch the (small, ~tens-of-thousands) active set in one call instead of
    # re-running the join per page. _rpc_fetch_all still pages if it ever grows
    # past the limit; PostgREST applies no max-rows cap on this project.
    rows = _rpc_fetch_all(
        client,
        "get_active_global_elo_player_ids",
        {"cutoff": str(cutoff)},
        limit=50000,
    )
    active: list[dict[str, Any]] = []
    for r in rows:
        pid = r.get("player_id")
        if pid:
            active.append({"player_id": pid})
    return active


def compute_commander_recency_weight(
    first_appearance_date: date,
) -> float:
    """Weight based on recency: 1.0 at cutoff, tapering to 0.5 at 2x cutoff."""
    days_since = (utc_now().date() - first_appearance_date).days
    half_life = COMMANDER_RECENCY_HALF_LIFE_DAYS
    weight = pow(0.5, days_since / half_life)
    return min(1.0, max(0.5, weight))


MATERIALIZED_VIEW_REFRESH_FUNCTIONS = [
    "refresh_commander_trends",
    "refresh_card_frequencies",
    "refresh_card_performance",
    "refresh_regional_elo_data_validity",
]

# Read timeout for MV refresh RPCs. Slightly above the 30min server-side
# statement_timeout those functions set, so the server's own limit (a clean
# 57014) fires before the client read timeout.
REFRESH_RPC_TIMEOUT_SECONDS = 1860

ACTIVE_LEADERBOARD_TABLE = "global_elo_active_leaderboard"
ACTIVE_LEADERBOARD_BATCH_SIZE = 1000


def assign_topdeck_elo_ranks(
    rows: list[dict[str, Any]],
    reference_date: date | None = None,
) -> None:
    """Assign topdeck_elo_rank within each (region_type, region_key) partition.

    Eligible rows -- those with a non-null topdeck_elo AND at least one
    games-backed record in this app AND recent activity within
    ``RANK_ACTIVITY_WINDOW_DAYS`` (see ``_is_topdeck_rank_eligible``) -- are
    sorted by topdeck_elo DESC, ties broken stably by rating DESC, then player_name
    ASC for deterministic ordering. All other rows receive rank = None,
    including rows with a non-null topdeck_elo but zero recorded games, and
    rows whose most recent recorded game is older than the activity window.

    topdeck_elo is imported independently from TopDeck.gg's own published
    Elo snapshot (see ``import_topdeck_player_elos.py``) and is keyed only by
    a player's external topdeck_id, so it can be populated for a player who
    has never actually recorded a game in this app's data. Without the
    games-played gate, that external rating -- which reflects no real
    competitive standing here -- could rank a zero-game player ahead of (or
    at rank 1 above) players with real, games-backed rankings, which is the
    same class of bug fixed for the ``rank`` field in
    ``build_active_leaderboard_rows`` (#252). Mutates rows in place by
    setting the ``topdeck_elo_rank`` field.

    ``reference_date`` is the date the activity window is measured against;
    it defaults to today (UTC) and is only overridden in tests.
    """
    partitions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        partitions[(row.get("region_type", ""), row.get("region_key", ""))].append(row)

    for partition_rows in partitions.values():
        ranked = []
        unranked = []
        for r in partition_rows:
            if _is_topdeck_rank_eligible(r, reference_date):
                ranked.append(r)
            else:
                unranked.append(r)
        ranked.sort(
            key=lambda r: (
                -float(r.get("topdeck_elo") or 0),
                -float(r.get("rating") or 0),
                str(r.get("player_name") or ""),
            )
        )
        for index, row in enumerate(ranked, start=1):
            row["topdeck_elo_rank"] = index
        for row in unranked:
            row["topdeck_elo_rank"] = None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _api_error_is_missing_topdeck_column(exc: APIError, column_name: str) -> bool:
    haystack = " ".join(str(part).lower() for part in (exc.code, exc.message, exc.details) if part)
    normalized_column = column_name.lower()

    if normalized_column not in haystack:
        return False

    missing_column_markers = (
        "42703",
        "pgrst204",
        "could not find",
        "does not exist",
        "unknown column",
    )
    return any(marker in haystack for marker in missing_column_markers)


def detect_topdeck_elo_id_column(client: Client) -> str:
    """Detect the TopDeck Elo id column without weakening full snapshot retries."""
    last_schema_error: APIError | None = None
    for id_column in ("topdeck_id", "uid"):
        try:
            client.table("topdeck_player_elos").select(id_column).limit(1).execute()
            return id_column
        except APIError as exc:
            if _api_error_is_missing_topdeck_column(exc, id_column):
                last_schema_error = exc
                continue
            raise

    raise RuntimeError("topdeck_player_elos is missing both topdeck_id and uid columns") from last_schema_error


def build_active_leaderboard_rows(
    ratings_rows: Iterable[Mapping[str, Any]],
    player_index: Mapping[str, Mapping[str, Any]],
    topdeck_elo_by_topdeck_id: Mapping[str, float],
    state_stats_by_player: Mapping[str, Mapping[str, Any]],
    updated_at: str,
    canonical_counts_by_player: Mapping[str, Mapping[str, Any]] | None = None,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    """Materialise active leaderboard rows for global, country, and state slices.

    Mirrors the shape produced by the regional_elo_leaderboard view but is
    persisted to the leaderboard table so PostgREST can serve the data
    without joining to topdeck_player_elos at request time.

    ``reference_date`` anchors the "no tournaments in the last 6 months"
    activity gate (``RANK_ACTIVITY_WINDOW_DAYS``, see ``_is_rank_eligible``);
    it defaults to today (UTC) and is only overridden in tests.
    """
    leaderboard_rows: list[dict[str, Any]] = []
    for rating_row in ratings_rows:
        if rating_row.get("region_type") != GLOBAL_REGION_TYPE:
            continue
        if rating_row.get("region_key") != GLOBAL_REGION_KEY:
            continue

        player_id = rating_row.get("player_id")
        if not player_id:
            continue
        player = player_index.get(player_id)
        if not player:
            continue

        rating = _coerce_float(rating_row.get("rating"))
        if rating is None:
            rating = DEFAULT_RATING
        canonical = (canonical_counts_by_player or {}).get(player_id)
        state_stats = state_stats_by_player.get(player_id) or {}
        if canonical is not None:
            games_played = int(canonical.get("games_played") or 0)
            wins = int(canonical.get("wins") or 0)
            draws = int(canonical.get("draws") or 0)
            losses = int(canonical.get("losses") or 0)
            # Prefer the canonical global last_game_date over the primary-state
            # one below: a player's most recent game is often played while
            # traveling outside their primary state, so gating eligibility on
            # the primary-state-only date would wrongly mark active players as
            # inactive. Falls back to the primary-state date only when no
            # canonical row exists at all (see the `else` branch).
            last_game_date = canonical.get("last_game_date") or state_stats.get("last_game_date")
        else:
            games_played = int(rating_row.get("games_played") or 0)
            wins = int(rating_row.get("wins") or 0)
            draws = int(rating_row.get("draws") or 0)
            losses = int(rating_row.get("losses") or 0)
            last_game_date = state_stats.get("last_game_date")
        topdeck_id = player.get("topdeck_id")
        topdeck_elo = topdeck_elo_by_topdeck_id.get(str(topdeck_id)) if topdeck_id else None

        primary_country_key = state_stats.get("country_key") or ""
        primary_region_key = state_stats.get("region_key") or ""
        activity_score = _coerce_float(state_stats.get("activity_score"))

        base_row: dict[str, Any] = {
            "player_id": player_id,
            "player_name": player.get("name") or "",
            "topdeck_id": topdeck_id,
            "rating": rating,
            "games_played": games_played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "last_game_date": last_game_date,
            "primary_country_key": primary_country_key or None,
            "primary_region_key": primary_region_key or None,
            "activity_score": activity_score,
            "topdeck_elo": topdeck_elo,
            "updated_at": updated_at,
        }

        # Global slice - one row per player.
        leaderboard_rows.append(
            {
                **base_row,
                "region_type": GLOBAL_REGION_TYPE,
                "region_key": GLOBAL_REGION_KEY,
                "country_key": None,
            }
        )

        # Country slice - first-class row per country, no longer inferred at read time.
        if primary_country_key:
            leaderboard_rows.append(
                {
                    **base_row,
                    "region_type": "country",
                    "region_key": primary_country_key,
                    "country_key": primary_country_key,
                }
            )

        # State slice - keyed on the state region key under its country.
        if primary_region_key:
            leaderboard_rows.append(
                {
                    **base_row,
                    "region_type": STATE_REGION_TYPE,
                    "region_key": primary_region_key,
                    "country_key": primary_country_key or None,
                }
            )

    # Assign rating rank within each partition.
    partitions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in leaderboard_rows:
        partitions[(row["region_type"], row["region_key"])].append(row)

    for partition_rows in partitions.values():
        # Players with zero games sit at DEFAULT_RATING (an anchor/mean value,
        # not a real competitive signal) because create_empty_ratings_row seeds
        # every tracked player at that value before any games are processed.
        # Real ratings can legitimately drift below that anchor (or below zero)
        # for players who have actually played, so ranking purely on the numeric
        # rating value lets a zero-game player's sentinel rating outrank -- and
        # even land at rank 1 ahead of -- players with real, hard-earned
        # ratings. Only players with at least one recorded game AND recent
        # activity (within RANK_ACTIVITY_WINDOW_DAYS of reference_date) are
        # eligible for a rating-based rank at all; everyone else gets
        # rank = None rather than a fallback ordinal. Several apps/web read
        # paths fall back to `rank` whenever `topdeck_elo_rank` is null, so a
        # non-null fallback rank would let an inactive/zero-game player show
        # up with what looks like a real rank badge again (Codex P2 review
        # finding on PR #263).
        eligible_rows = [r for r in partition_rows if _is_rank_eligible(r, reference_date)]
        ineligible_rows = [r for r in partition_rows if not _is_rank_eligible(r, reference_date)]

        eligible_rows.sort(key=_leaderboard_rank_sort_key)

        for index, row in enumerate(eligible_rows, start=1):
            row["rank"] = index
        for row in ineligible_rows:
            row["rank"] = None

    assign_topdeck_elo_ranks(leaderboard_rows, reference_date)
    return leaderboard_rows


def _parse_last_game_date(value: Any) -> date | None:
    """Parse a `last_game_date` value that may arrive as a `date`, a
    `datetime`, an ISO date/datetime string, or `None` -- the exact shape
    depends on whether the row was built in Python or round-tripped through a
    PostgREST JSON response. Returns None if the value is missing, empty, or
    unparseable so callers can treat it as "no known activity" rather than
    raising.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _is_recently_active(last_game_date: Any, reference_date: date | None = None) -> bool:
    """Return True if `last_game_date` is within RANK_ACTIVITY_WINDOW_DAYS
    (183 days) of `reference_date` (defaults to today, UTC).

    Implements the "players with no tournaments in the last 6 months are
    excluded from the rankings" business rule. A missing or unparseable
    `last_game_date` is treated as ineligible rather than defaulting to
    active, since we have no evidence of recent play.
    """
    parsed = _parse_last_game_date(last_game_date)
    if parsed is None:
        return False
    if reference_date is None:
        reference_date = utc_now().date()
    return (reference_date - parsed).days <= RANK_ACTIVITY_WINDOW_DAYS


def _is_rank_eligible(row: Mapping[str, Any], reference_date: date | None = None) -> bool:
    """Return True if *row* has a real, games-backed rating AND recent activity.

    Zero-game players are seeded with the DEFAULT_RATING anchor rather than a
    genuine computed rating, so they must never be eligible to outrank (or, in
    the worst case, become rank 1 ahead of) a player with a real rating -
    including a legitimately negative one.

    Additionally, a player whose most recent recorded game (`last_game_date`)
    is older than RANK_ACTIVITY_WINDOW_DAYS (183 days, ~6 months) relative to
    `reference_date` is excluded from ranking regardless of games played or
    rating -- the "no tournaments in the last 6 months" business rule.
    """
    games_played = row.get("games_played")
    try:
        if int(games_played or 0) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    return _is_recently_active(row.get("last_game_date"), reference_date)


def _is_topdeck_rank_eligible(row: Mapping[str, Any], reference_date: date | None = None) -> bool:
    """Return True if *row* is eligible for a topdeck_elo_rank.

    Composes the shared games-backed + recent-activity gate
    (``_is_rank_eligible``) with the topdeck_elo-specific requirement that
    the row actually has an imported topdeck_elo value. Kept separate from
    ``_is_rank_eligible`` itself because that helper is also used for the
    unrelated, purely rating-based ``rank`` field in
    ``build_active_leaderboard_rows``, which must stay eligible for players
    who have no topdeck_elo at all.
    """
    return row.get("topdeck_elo") is not None and _is_rank_eligible(row, reference_date)


def _leaderboard_rank_sort_key(r: Mapping[str, Any]) -> tuple[float, float, int, str]:
    """Sort key for rating rank: highest rating first, ties broken by activity,
    then games played, then name. A missing rating sorts last rather than
    being coerced to 0 (which could beat a real negative rating); missing
    activity_score/games_played fall back to 0, the correct "no activity"
    floor for those fields."""
    rating = r.get("rating")
    activity_score = r.get("activity_score")
    games_played = r.get("games_played")
    return (
        -float(rating) if rating is not None else float("inf"),
        -float(activity_score) if activity_score is not None else 0.0,
        -int(games_played) if games_played is not None else 0,
        str(r.get("player_name") or ""),
    )


def fetch_player_index(client: Client) -> dict[str, dict[str, Any]]:
    """Fetch the player directory keyed by id for leaderboard enrichment."""
    rows = fetch_all(
        client,
        "players",
        columns="id,name,topdeck_id",
    )
    return {row["id"]: row for row in rows if row.get("id")}


def fetch_topdeck_elo_by_topdeck_id(client: Client) -> dict[str, float]:
    """Load the TopDeck Elo snapshot keyed by the external TopDeck player id."""
    selected_id_column = detect_topdeck_elo_id_column(client)
    rows = fetch_all(
        client,
        "topdeck_player_elos",
        columns=f"{selected_id_column},elo",
    )
    elo_by_topdeck_id: dict[str, float] = {}
    for row in rows:
        topdeck_id = row.get(selected_id_column)
        elo = _coerce_float(row.get("elo"))
        if topdeck_id and elo is not None:
            elo_by_topdeck_id[str(topdeck_id)] = elo
    return elo_by_topdeck_id


def fetch_primary_state_stats(client: Client) -> dict[str, dict[str, Any]]:
    """Load primary-state activity per player for country/state slice enrichment."""
    rows = fetch_all(
        client,
        "regional_elo_primary_state_assignments",
        columns="player_id,region_type,region_key,country_key,activity_score,last_game_date",
    )
    by_player: dict[str, dict[str, Any]] = {}
    for row in rows:
        player_id = row.get("player_id")
        if not player_id:
            continue
        # Backfill country_key from the state lookup when the source view does
        # not expose it directly (older view definitions only carry region_key).
        if not row.get("country_key"):
            inferred_country = get_country_for_state(row.get("region_key") or "")
            if inferred_country:
                row["country_key"] = inferred_country
        by_player[player_id] = row
    return by_player


def fetch_canonical_event_counts(client: Client) -> dict[str, dict[str, Any]]:
    """Return per-player canonical game counts and last_game_date from the
    leaderboard view.

    The view aggregates from global_elo_game_events, which is the ground-truth
    source. Bypasses the stale accumulator columns in global_elo_ratings that
    drift when full recomputes run multiple times.

    ``last_game_date`` here is the player's true global last game date, unlike
    the primary-state-only date from ``fetch_primary_state_stats`` -- it must
    be used for activity-eligibility checks so a player who last played while
    traveling outside their primary state isn't wrongly marked inactive.

    Must be called after game events for the current run have been upserted.
    """
    rows = fetch_all(
        client,
        "regional_elo_leaderboard",
        columns="player_id,games_played,wins,losses,draws,last_game_date",
        filters=[("region_type", "eq", GLOBAL_REGION_TYPE), ("region_key", "eq", GLOBAL_REGION_KEY)],
    )
    return {
        row["player_id"]: {
            "games_played": int(row.get("games_played") or 0),
            "wins": int(row.get("wins") or 0),
            "losses": int(row.get("losses") or 0),
            "draws": int(row.get("draws") or 0),
            "last_game_date": row.get("last_game_date"),
        }
        for row in rows
        if row.get("player_id")
    }


def delete_stale_active_leaderboard_rows(client: Client, run_marker: str) -> None:
    """Delete leaderboard rows that the current run did not refresh."""
    try:
        endpoint = f"{client.postgrest.base_url}/{ACTIVE_LEADERBOARD_TABLE}"
        params = {"updated_at": f"lt.{run_marker}"}
        headers = {**dict(client.postgrest.headers), "Prefer": "return=minimal"}
        response = requests.delete(endpoint, headers=headers, params=params, timeout=60)
        if response.status_code >= 400:
            print(
                f"Stale leaderboard cleanup failed (non-fatal): {response.status_code} {response.text[:200]}",
                flush=True,
            )
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        print(f"Stale leaderboard cleanup raised (non-fatal): {exc}", flush=True)


def upsert_active_leaderboard_rows(
    client: Client,
    rows: list[dict[str, Any]],
    batch_size: int = ACTIVE_LEADERBOARD_BATCH_SIZE,
) -> None:
    """Upsert leaderboard rows in batches keyed on (region_type, region_key, player_id)."""
    upsert_batched(
        client,
        ACTIVE_LEADERBOARD_TABLE,
        rows,
        on_conflict="region_type,region_key,player_id",
        batch_size=batch_size,
    )


def refresh_materialized_views(client: Client, direct: DirectPostgresClient | None = None) -> int:
    """Refresh downstream materialized views. Returns count of successful refreshes.

    The heaviest refreshes (card_frequencies, card_performance) run for minutes
    and the Supabase REST gateway returns a 504 before they finish, regardless of
    the client read timeout. When a direct Postgres connection is available, call
    the refresh functions through it to bypass the gateway entirely; the
    functions' own statement_timeout (30min) still bounds them. Fall back to a
    long-timeout REST POST when no direct connection is configured -- not
    client.rpc(), whose underlying session timeout is much shorter.
    """
    success_count = 0
    for fn_name in MATERIALIZED_VIEW_REFRESH_FUNCTIONS:
        try:
            print(f"Refreshing materialized views via {fn_name}()...")
            if direct is not None:
                direct.call_function(fn_name)
            else:
                endpoint = f"{client.postgrest.base_url}/rpc/{fn_name}"
                response = requests.post(
                    endpoint, json={}, headers=dict(client.postgrest.headers), timeout=REFRESH_RPC_TIMEOUT_SECONDS
                )
                if response.status_code >= 400:
                    raise RuntimeError(f"{response.status_code} {response.text}")
            success_count += 1
            print(f"  {fn_name}() completed.")
        except Exception as exc:
            print(f"  {fn_name}() failed (non-fatal): {exc}", flush=True)
    return success_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Elo ratings and leaderboards.")
    parser.add_argument("--job-id", type=str, default="", help="EloMaintenanceJobs UUID")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes (dry-run by default)",
    )
    parser.add_argument(
        "--smoke-days",
        type=int,
        default=30,
        help="Days of history to include in smoke test",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not apply changes (default when --apply is not set)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full refresh even when job_id is specified",
    )
    args = parser.parse_args()

    apply = args.apply
    dry_run = not apply

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    client = get_supabase_client(supabase_url, supabase_key)
    db_url = os.environ.get("SUPABASE_DB_URL")
    direct: DirectPostgresClient | None = None
    if db_url:
        try:
            candidate = DirectPostgresClient(db_url)
            candidate.connect()
            direct = candidate
            print("DirectPostgres connection established")
        except Exception as e:
            print(f"DirectPostgres unavailable ({e}); falling back to REST")
    job_id = args.job_id
    github_run_id = int(os.environ.get("GITHUB_RUN_ID", 0))

    if job_id:
        if not apply:
            sys.stderr.write("--job-id requires --apply because queued jobs represent live refreshes.\n")
            sys.exit(1)
        if not claim_job(client, job_id, github_run_id):
            print(f"No active job found for ID {job_id} - may already be claimed")
            sys.exit(0)
        update_job_heartbeat(client, job_id)
    else:
        if not apply:
            print("--apply not specified; using dry-run mode")
            print("Use --apply to write changes, --job-id to track as maintenance job")

    start = time.time()

    if dry_run:
        smoke_days = args.smoke_days
        cutoff = get_past_days_cutoff(smoke_days)
        print(f"[DRY RUN] Would compute Elo for games since {cutoff}")
        print("[DRY RUN] Participant fetch not executed in dry-run mode")
        if job_id:
            fail_job(client, job_id, "Dry-run mode")
        sys.exit(0)

    # Incremental or cold-start: choose participant fetch strategy based on watermark.
    print("Checking event-log watermark for incremental mode...")
    watermark = fetch_elo_watermark(client)
    update_job_heartbeat(client, job_id)

    if watermark:
        print(f"Watermark found: {watermark} — loading snapshot and fetching new games only")
        player_ratings = load_ratings_from_snapshot(client, watermark)
        print(f"Loaded {len(player_ratings):,} player ratings from snapshot")
        update_job_heartbeat(client, job_id)
        print(f"Fetching new participants since {watermark}...")
        participant_rows = fetch_participants_since(client, watermark, direct=direct)
    else:
        print("No watermark — cold start: building ratings from full game history")
        participant_rows = fetch_participants_for_leaderboard(
            client, lookback_months=ACTIVE_PLAYER_LOOKBACK_MONTHS, direct=direct
        )
        update_job_heartbeat(client, job_id)
        player_ids = fetch_distinct_entry_ids(client, lookback_months=ACTIVE_PLAYER_LOOKBACK_MONTHS, direct=direct)
        player_ratings = {}
        for pid in player_ids:
            key = (GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY, pid)
            player_ratings[key] = create_empty_ratings_row(pid, GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY)

    print(f"Found {len(participant_rows):,} participant rows to process")
    update_job_heartbeat(client, job_id)

    # Process results and update ratings; collect game event rows for upsert.
    print("Processing results for global ratings...")
    game_events = process_results(participant_rows)
    db_event_rows = update_ratings_with_games(player_ratings, game_events)

    update_job_heartbeat(client, job_id)

    # Apply to database
    print("Upserting global Elo ratings...")
    ratings_to_upsert = list(player_ratings.values())
    if ratings_to_upsert:
        upsert_batched(
            client,
            "global_elo_ratings",
            ratings_to_upsert,
            on_conflict="player_id,region_type,region_key",
        )

    update_job_heartbeat(client, job_id)

    # Build player profiles
    print("Building player profiles...")
    profiles = build_player_profiles(ratings_to_upsert)

    # Enrich profiles with primary commander data
    print("Building primary commanders...")
    primary_commanders = build_primary_commanders(client)
    commander_profile_count = 0
    for profile in profiles:
        pid = profile.get("player_id")
        if pid and pid in primary_commanders:
            name, known_pct = primary_commanders[pid]
            profile["primary_commander_name"] = name
            profile["primary_commander_known_pct"] = known_pct
            commander_profile_count += 1
        else:
            profile["primary_commander_name"] = None
            profile["primary_commander_known_pct"] = None

    if profiles:
        upsert_batched(
            client,
            "global_elo_player_profile_summaries",
            profiles,
            on_conflict="player_id",
        )

    update_job_heartbeat(client, job_id)

    # Detect active players
    print("Detecting active players...")
    active = detect_active_players(client)
    for a in active:
        a["last_active"] = str(utc_now().date())
        a["region_type"] = GLOBAL_REGION_TYPE
        a["region_key"] = GLOBAL_REGION_KEY

    if active:
        upsert_batched(
            client,
            "global_elo_state_activity",
            active,
            on_conflict="region_type,region_key,player_id",
        )

    update_job_heartbeat(client, job_id)

    # Upsert game events — always written; uses DirectPostgres bulk path when available.
    print(f"Recording {len(db_event_rows):,} game events...")
    if db_event_rows:
        if direct is not None:
            direct.upsert(
                "global_elo_game_events",
                db_event_rows,
                on_conflict="region_type,region_key,game_id,player_id",
            )
        else:
            upsert_batched(
                client,
                "global_elo_game_events",
                db_event_rows,
                on_conflict="region_type,region_key,game_id,player_id",
            )

    update_job_heartbeat(client, job_id)

    # Refresh downstream materialized views
    print("Refreshing materialized views...")
    mv_count = refresh_materialized_views(client, direct=direct)
    print(f"Refreshed {mv_count}/{len(MATERIALIZED_VIEW_REFRESH_FUNCTIONS)} materialized views.")

    update_job_heartbeat(client, job_id)

    # Compute leaderboard after game events are committed so the view's canonical
    # counts include the current run. Persist global, country, and state slices so
    # /regional-elo can serve sorted reads (including TopDeck Elo) without a
    # second query against topdeck_player_elos.
    print("Computing leaderboard...")
    print("Loading player directory...")
    player_index = fetch_player_index(client)
    print(f"Loaded {len(player_index)} player rows")

    print("Loading TopDeck Elo snapshot...")
    topdeck_elo_by_topdeck_id = fetch_topdeck_elo_by_topdeck_id(client)
    print(f"Loaded {len(topdeck_elo_by_topdeck_id)} TopDeck Elo entries")

    print("Loading primary-state activity stats...")
    state_stats_by_player = fetch_primary_state_stats(client)
    print(f"Loaded {len(state_stats_by_player)} primary-state stat rows")

    print("Loading canonical game event counts...")
    canonical_counts = fetch_canonical_event_counts(client)
    print(f"Loaded canonical counts for {len(canonical_counts)} players")

    leaderboard_run_marker = utc_now().isoformat()
    all_leaderboard_rows = build_active_leaderboard_rows(
        ratings_to_upsert,
        player_index,
        topdeck_elo_by_topdeck_id,
        state_stats_by_player,
        leaderboard_run_marker,
        canonical_counts,
    )

    if all_leaderboard_rows:
        print(f"Upserting {len(all_leaderboard_rows)} active leaderboard rows (global + country + state)...")
        upsert_active_leaderboard_rows(client, all_leaderboard_rows)
    delete_stale_active_leaderboard_rows(client, leaderboard_run_marker)

    update_job_heartbeat(client, job_id)

    duration = time.time() - start

    metrics = JobMetrics(
        ratings_count=len(ratings_to_upsert),
        state_activity_count=len(active),
        game_events_count=len(db_event_rows),
        leaderboard_count=len(all_leaderboard_rows),
        profile_count=len(profiles),
        commander_profile_count=commander_profile_count,
        duration_seconds=duration,
    )

    print(f"Done in {duration:.1f}s. Ratings: {metrics.ratings_count}")
    if job_id:
        complete_job(
            client,
            job_id,
            {
                "ratings_count": metrics.ratings_count,
                "state_activity_count": metrics.state_activity_count,
                "game_events_count": metrics.game_events_count,
                "leaderboard_count": metrics.leaderboard_count,
                "profile_count": metrics.profile_count,
                "commander_profile_count": metrics.commander_profile_count,
                "duration_seconds": metrics.duration_seconds,
            },
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        traceback.print_exc()
        # Best-effort: mark the job as failed in the DB so the queue doesn't
        # leave it stuck in 'running' until the stale-cleanup cron fires.
        job_id_arg = None
        try:
            for _i, _arg in enumerate(sys.argv):
                if _arg == "--job-id" and _i + 1 < len(sys.argv):
                    job_id_arg = sys.argv[_i + 1]
                    break
            if job_id_arg:
                _url = os.environ.get("SUPABASE_URL", "")
                _key = os.environ.get("SUPABASE_SERVICE_KEY", "")
                if _url and _key:
                    _client = get_supabase_client(_url, _key)
                    fail_job(_client, job_id_arg, str(exc))
        except Exception as report_exc:
            # Best-effort reporting failed; don't mask the original traceback.
            sys.stderr.write(f"[warn] fail_job reporting failed: {report_exc}\n")
        sys.exit(1)
