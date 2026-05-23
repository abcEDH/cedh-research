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
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
UTC = timezone.utc
from typing import Any

import requests

from ingest import SupabaseClient

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


def process_results(
    participant_records: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Process participant records into ratings updates."""
    game_events: list[dict[str, Any]] = []

    standings: list[tuple[float, int, dict[str, Any]]] = []
    for p in participant_records:
        entry_id = p.get("entry_id") or ""
        standing: dict[str, Any] = {
            "id": entry_id,
            "wins": 1 if p.get("result") == "win" else 0,
            "draws": 1 if p.get("result") == "draw" else 0,
            "losses": 1 if p.get("result") == "loss" else 0,
        }
        rating = p.get("rating", DEFAULT_RATING) or DEFAULT_RATING
        seat = p.get("seat_position") or 0
        standings.append((rating, seat, standing))

    if len(standings) < 2:
        return []

    # Sort by rating descending, then seat ascending to break ties
    standings.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    # Process each seat vs higher-rated seats (players who should be favored)
    for rating, seat, standing in standings:
        entry_id = standing["id"]
        is_winner = standing["wins"] >= 1
        is_draw = standing["draws"] >= 1

        # Find higher/equal rated opponents
        for opp_rating, opp_seat, opp_standing in standings:
            if opp_rating > rating or (opp_rating == rating and opp_seat < seat):
                opp_entry_id = opp_standing["id"]
                opp_is_winner = opp_standing["wins"] >= 1

                # Determine game outcome from perspective of current player
                if is_winner and not opp_is_winner:
                    outcome = "win"
                elif opp_is_winner and not is_winner:
                    outcome = "loss"
                elif is_draw:
                    outcome = "draw"
                else:
                    outcome = "unknown"

                if outcome in ("win", "loss", "draw"):
                    game_events.append(
                        {
                            "entry_id": entry_id,
                            "opp_entry_id": opp_entry_id,
                            "outcome": outcome,
                        }
                    )

    return game_events


def update_ratings_with_games(
    player_ratings: dict[tuple[str, str, str], dict[str, Any]],
    game_events: Iterable[dict[str, Any]],
) -> None:
    """Update ratings based on game results."""
    for event in game_events:
        entry_id = event["entry_id"]
        opp_entry_id = event["opp_entry_id"]
        outcome = event["outcome"]

        if outcome == "unknown":
            continue

        key = None
        opp_key = None
        for k, v in player_ratings.items():
            if v["player_id"] == entry_id:
                key = k
            if v["player_id"] == opp_entry_id:
                opp_key = k
            if key and opp_key:
                break

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
            player_row["draws"] += 1
            opp_row["draws"] += 1

        player_row["rating"] = new_player
        opp_row["rating"] = new_opp
        player_row["games_played"] += 1
        opp_row["games_played"] += 1


def claim_job(client: SupabaseClient, job_id: str, github_run_id: int) -> bool:
    """Atomically claim a job by transitioning it to 'running'."""
    try:
        updated = client.update(
            MAINTENANCE_JOBS_TABLE,
            {
                "status": "running",
                "github_run_id": github_run_id,
                "started_at": utc_now().isoformat(),
                "heartbeat_at": utc_now().isoformat(),
            },
            {"id": f"eq.{job_id}", "status": "in.(pending,dispatched)"},
        )
        return bool(updated)
    except Exception as exc:
        print(f"Failed to claim job {job_id}: {exc}", flush=True)
        return False


def update_job_heartbeat(client: SupabaseClient, job_id: str) -> None:
    """Best-effort heartbeat so stale-job detection knows we are alive."""
    try:
        client.update(
            MAINTENANCE_JOBS_TABLE,
            {"heartbeat_at": utc_now().isoformat()},
            {"id": f"eq.{job_id}", "status": "eq.running"},
        )
    except Exception as exc:
        # Best-effort: heartbeat failures should not fail the job
        print(f"Heartbeat failed for job {job_id} (safe to continue): {exc}", flush=True)


def complete_job(client: SupabaseClient, job_id: str, metrics: dict) -> None:
    """Mark job as completed with output metrics."""
    now = utc_now().isoformat()
    client.update(
        MAINTENANCE_JOBS_TABLE,
        {"status": "completed", "completed_at": now, "heartbeat_at": now, **metrics},
        {"id": f"eq.{job_id}", "status": "eq.running"},
    )


def fail_job(client: SupabaseClient, job_id: str, error: str) -> None:
    """Mark job as failed with error message."""
    try:
        client.update(
            MAINTENANCE_JOBS_TABLE,
            {
                "status": "failed",
                "completed_at": utc_now().isoformat(),
                "error_text": error[:2000],
            },
            {"id": f"eq.{job_id}", "status": "in.(pending,dispatched,running)"},
        )
    except Exception as exc:
        # Best-effort: failure logging should not crash the process
        print(f"Failed to record job failure for {job_id}: {exc}", flush=True)


QueryParams = Mapping[str, Any] | Sequence[tuple[str, Any]]


def with_paging_params(params: QueryParams, limit: int, offset: int) -> QueryParams:
    page_params = {"limit": limit, "offset": offset}
    if isinstance(params, Mapping):
        return {**params, **page_params}
    return [*params, *page_params.items()]


def fetch_all(
    client: SupabaseClient,
    table: str,
    params: QueryParams,
    limit: int = 1000,
    max_retries: int = 8,
) -> list[dict[str, Any]]:
    offset = 0
    rows: list[dict[str, Any]] = []
    while True:
        page = client.select(table, with_paging_params(params, limit, offset), max_retries=max_retries)
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
    return rows


def fetch_participants_for_leaderboard(
    client: SupabaseClient, lookback_months: int = ACTIVE_PLAYER_LOOKBACK_MONTHS
) -> list[dict[str, Any]]:
    cutoff = get_past_months_cutoff(lookback_months)
    return fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": "entry_id,player_id,tournament_id,seat_position,result",
            "start_date": f"gte.{cutoff}",
            "result": "neq.bye",
        },
    )


def fetch_commander_participants(
    client: SupabaseClient, lookback_months: int = COMMANDER_PRIMARY_LOOKBACK_MONTHS
) -> list[dict[str, Any]]:
    cutoff = get_past_months_cutoff(lookback_months)
    return fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": "entry_id,player_id,tournament_id,seat_position,result",
            "start_date": "gte." + str(cutoff),
            "result": "neq.bye",
        },
    )


def fetch_distinct_entry_ids(client: SupabaseClient, lookback_months: int = ACTIVE_PLAYER_LOOKBACK_MONTHS) -> set[str]:
    cutoff = get_past_months_cutoff(lookback_months)
    rows = fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": "entry_id",
            "start_date": f"gte.{cutoff}",
        },
    )
    return {r["entry_id"] for r in rows}


def fetch_distinct_commander_ids(
    client: SupabaseClient, lookback_months: int = COMMANDER_PRIMARY_LOOKBACK_MONTHS
) -> set[str]:
    cutoff = get_past_months_cutoff(lookback_months)
    rows = fetch_all(
        client,
        "tournament_entries",
        {
            "select": "commander_id",
            "tournament_id.start_date": f"gte.{cutoff}",
        },
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


def detect_active_players(
    client: SupabaseClient, lookback_months: int = ACTIVE_PLAYER_LOOKBACK_MONTHS
) -> list[dict[str, Any]]:
    """Identify players with recent activity."""
    cutoff = get_past_months_cutoff(lookback_months)
    rows = fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": "player_id",
            "start_date": f"gte.{cutoff}",
            "result": "neq.bye",
        },
    )
    seen: set[str] = set()
    active: list[dict[str, Any]] = []
    for r in rows:
        pid = r["player_id"]
        if pid and pid not in seen:
            seen.add(pid)
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
]

ACTIVE_LEADERBOARD_TABLE = "global_elo_active_leaderboard"
ACTIVE_LEADERBOARD_BATCH_SIZE = 1000


def assign_topdeck_elo_ranks(
    rows: list[dict[str, Any]],
) -> None:
    """Assign topdeck_elo_rank within each (region_type, region_key) partition.

    Rows are sorted by topdeck_elo DESC with NULLs last; rows whose
    topdeck_elo is None receive rank = None. Ties are broken stably by
    rating DESC, then player_name ASC for deterministic ordering. Mutates
    rows in place by setting the ``topdeck_elo_rank`` field.
    """
    partitions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        partitions[(row.get("region_type", ""), row.get("region_key", ""))].append(row)

    for partition_rows in partitions.values():
        ranked = [r for r in partition_rows if r.get("topdeck_elo") is not None]
        unranked = [r for r in partition_rows if r.get("topdeck_elo") is None]
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
                continue
            raise

    raise RuntimeError("topdeck_player_elos is missing both topdeck_id and uid columns") from last_schema_error


def build_active_leaderboard_rows(
    ratings_rows: Iterable[Mapping[str, Any]],
    player_index: Mapping[str, Mapping[str, Any]],
    topdeck_elo_by_topdeck_id: Mapping[str, float],
    state_stats_by_player: Mapping[str, Mapping[str, Any]],
    updated_at: str,
) -> list[dict[str, Any]]:
    """Materialise active leaderboard rows for global, country, and state slices.

    Mirrors the shape produced by the regional_elo_leaderboard view but is
    persisted to the leaderboard table so PostgREST can serve the data
    without joining to topdeck_player_elos at request time.
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

        rating = _coerce_float(rating_row.get("rating")) or DEFAULT_RATING
        games_played = int(rating_row.get("games_played") or 0)
        wins = int(rating_row.get("wins") or 0)
        draws = int(rating_row.get("draws") or 0)
        losses = int(rating_row.get("losses") or 0)
        topdeck_id = player.get("topdeck_id")
        topdeck_elo = topdeck_elo_by_topdeck_id.get(str(topdeck_id)) if topdeck_id else None

        state_stats = state_stats_by_player.get(player_id) or {}
        primary_country_key = state_stats.get("country_key") or ""
        primary_region_key = state_stats.get("region_key") or ""
        activity_score = _coerce_float(state_stats.get("activity_score"))
        last_game_date = state_stats.get("last_game_date")

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
        partition_rows.sort(
            key=lambda r: (
                -float(r.get("rating") or 0),
                -float(r.get("activity_score") or 0),
                -int(r.get("games_played") or 0),
                str(r.get("player_name") or ""),
            )
        )
        for index, row in enumerate(partition_rows, start=1):
            row["rank"] = index

    assign_topdeck_elo_ranks(leaderboard_rows)
    return leaderboard_rows


def fetch_player_index(client: SupabaseClient) -> dict[str, dict[str, Any]]:
    """Fetch the player directory keyed by id for leaderboard enrichment."""
    rows = fetch_all(
        client,
        "players",
        {"select": "id,name,topdeck_id"},
    )
    return {row["id"]: row for row in rows if row.get("id")}


def fetch_topdeck_elo_by_topdeck_id(client: SupabaseClient) -> dict[str, float]:
    """Load the TopDeck Elo snapshot keyed by the external TopDeck player id."""
    selected_id_column = detect_topdeck_elo_id_column(client)
    rows = fetch_all(
        client,
        "topdeck_player_elos",
        {"select": f"{selected_id_column},elo"},
    )
    elo_by_topdeck_id: dict[str, float] = {}
    for row in rows:
        topdeck_id = row.get(selected_id_column)
        elo = _coerce_float(row.get("elo"))
        if topdeck_id and elo is not None:
            elo_by_topdeck_id[str(topdeck_id)] = elo
    return elo_by_topdeck_id


def fetch_primary_state_stats(client: SupabaseClient) -> dict[str, dict[str, Any]]:
    """Load primary-state activity per player for country/state slice enrichment."""
    rows = fetch_all(
        client,
        "regional_elo_primary_state_assignments",
        {
            "select": ("player_id,region_type,region_key,country_key,activity_score,last_game_date"),
        },
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


def delete_stale_active_leaderboard_rows(client: SupabaseClient, run_marker: str) -> None:
    """Delete leaderboard rows that the current run did not refresh."""
    try:
        endpoint = f"{client.url}/rest/v1/{ACTIVE_LEADERBOARD_TABLE}"
        params = {"updated_at": f"lt.{run_marker}"}
        headers = {**client.headers, "Prefer": "return=minimal"}
        response = requests.delete(endpoint, headers=headers, params=params, timeout=60)
        if response.status_code >= 400:
            print(
                f"Stale leaderboard cleanup failed (non-fatal): {response.status_code} {response.text[:200]}",
                flush=True,
            )
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        print(f"Stale leaderboard cleanup raised (non-fatal): {exc}", flush=True)


def upsert_active_leaderboard_rows(
    client: SupabaseClient,
    rows: list[dict[str, Any]],
    batch_size: int = ACTIVE_LEADERBOARD_BATCH_SIZE,
) -> None:
    """Upsert leaderboard rows in batches keyed on (region_type, region_key, player_id)."""
    if not rows:
        return
    for start_index in range(0, len(rows), batch_size):
        batch = rows[start_index : start_index + batch_size]
        client.upsert(
            ACTIVE_LEADERBOARD_TABLE,
            batch,
            on_conflict="region_type,region_key,player_id",
        )


def refresh_materialized_views(client: SupabaseClient) -> int:
    """Refresh downstream materialized views. Returns count of successful refreshes."""
    success_count = 0
    for fn_name in MATERIALIZED_VIEW_REFRESH_FUNCTIONS:
        try:
            print(f"Refreshing materialized views via {fn_name}()...")
            client.rpc(fn_name)
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

    client = SupabaseClient(supabase_url, supabase_key)
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

    print("Fetching participants for leaderboard...")
    update_job_heartbeat(client, job_id)
    participant_rows = fetch_participants_for_leaderboard(client, lookback_months=ACTIVE_PLAYER_LOOKBACK_MONTHS)
    update_job_heartbeat(client, job_id)
    print(f"Found {len(participant_rows)} participant rows")

    print("Fetching distinct entries for global ratings...")
    entry_ids = fetch_distinct_entry_ids(client, lookback_months=ACTIVE_PLAYER_LOOKBACK_MONTHS)
    print(f"Found {len(entry_ids)} distinct entries")

    # Build ratings dict
    player_ratings: dict[tuple[str, str, str], dict[str, Any]] = {}
    for entry_id in entry_ids:
        key = (GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY, entry_id)
        player_ratings[key] = create_empty_ratings_row(entry_id, GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY)

    update_job_heartbeat(client, job_id)

    # Process results and update ratings
    print("Processing results for global ratings...")
    game_events = process_results(participant_rows)
    update_ratings_with_games(player_ratings, game_events)

    update_job_heartbeat(client, job_id)

    # Apply to database
    print("Upserting global Elo ratings...")
    ratings_to_upsert = list(player_ratings.values())
    if ratings_to_upsert:
        client.upsert(
            "global_elo_ratings",
            ratings_to_upsert,
            on_conflict="player_id,region_type,region_key",
        )

    update_job_heartbeat(client, job_id)

    # Compute leaderboard - persist global, country, and state slices so
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

    leaderboard_run_marker = utc_now().isoformat()
    all_leaderboard_rows = build_active_leaderboard_rows(
        ratings_to_upsert,
        player_index,
        topdeck_elo_by_topdeck_id,
        state_stats_by_player,
        leaderboard_run_marker,
    )

    if all_leaderboard_rows:
        print(f"Upserting {len(all_leaderboard_rows)} active leaderboard rows (global + country + state)...")
        upsert_active_leaderboard_rows(client, all_leaderboard_rows)
    delete_stale_active_leaderboard_rows(client, leaderboard_run_marker)

    update_job_heartbeat(client, job_id)

    # Build player profiles
    print("Building player profiles...")
    profiles = build_player_profiles(ratings_to_upsert)
    if profiles:
        client.upsert(
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

    if active:
        client.upsert(
            "global_elo_state_activity",
            active,
            on_conflict="player_id",
        )

    update_job_heartbeat(client, job_id)

    # Record game events
    print("Recording game events...")
    event_rows = [
        {
            "entry_id": e["entry_id"],
            "opp_entry_id": e["opp_entry_id"],
            "outcome": e["outcome"],
        }
        for e in game_events
    ]
    if event_rows:
        client.upsert(
            "global_elo_game_events",
            event_rows,
            on_conflict="",
        )

    update_job_heartbeat(client, job_id)

    # Refresh downstream materialized views
    print("Refreshing materialized views...")
    mv_count = refresh_materialized_views(client)
    print(f"Refreshed {mv_count}/{len(MATERIALIZED_VIEW_REFRESH_FUNCTIONS)} materialized views.")

    update_job_heartbeat(client, job_id)

    duration = time.time() - start

    metrics = JobMetrics(
        ratings_count=len(ratings_to_upsert),
        state_activity_count=len(active),
        game_events_count=len(event_rows),
        leaderboard_count=len(all_leaderboard_rows),
        profile_count=len(profiles),
        commander_profile_count=0,
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
        import traceback
        traceback.print_exc()
        # Best-effort: mark the job as failed in the DB so the queue doesn't
        # leave it stuck in 'running' until the stale-cleanup cron fires.
        _job_id = None
        try:
            import sys as _sys
            for _i, _arg in enumerate(_sys.argv):
                if _arg == "--job-id" and _i + 1 < len(_sys.argv):
                    _job_id = _sys.argv[_i + 1]
                    break
            if _job_id:
                _url = os.environ.get("SUPABASE_URL", "")
                _key = os.environ.get("SUPABASE_SERVICE_KEY", "")
                if _url and _key:
                    _client = SupabaseClient(_url, _key)
                    fail_job(_client, _job_id, str(exc))
        except Exception:
            pass
        _sys.exit(1)
