#!/usr/bin/env python3
"""Compute the global Elo leaderboard and derived state activity.

Usage:
  python src/regional_elo.py
"""

from __future__ import annotations

import os
import time
import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

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
COMMANDER_RECENCY_HALF_LIFE_DAYS = 28
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


def update_elo(winner_rating: float, loser_rating: float) -> Tuple[float, float]:
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
) -> Dict[str, Any]:
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
    participant_records: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Process participant records into ratings updates."""
    player_ratings: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    game_events: List[Dict[str, Any]] = []

    standings: List[Tuple[float, int, Dict[str, Any]]] = []
    for p in participant_records:
        entry_id = p.get("entry_id") or ""
        standing: Dict[str, Any] = {
            "id": entry_id,
            "wins": p.get("wins", 0) or 0,
            "draws": p.get("draws", 0) or 0,
            "losses": p.get("losses", 0) or 0,
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
    player_ratings: Dict[Tuple[str, str, str], Dict[str, Any]],
    game_events: Iterable[Dict[str, Any]],
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
            new_player, new_opp = update_elo(
                player_row["rating"], opp_row["rating"]
            )
            player_row["wins"] += 1
            player_row["win_streak"] += 1
            player_row["loss_streak"] = 0
            opp_row["losses"] += 1
            opp_row["win_streak"] = 0
            opp_row["loss_streak"] += 1
        elif outcome == "loss":
            new_opp, new_player = update_elo(
                opp_row["rating"], player_row["rating"]
            )
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


QueryParams = Mapping[str, Any] | Sequence[Tuple[str, Any]]


def with_paging_params(params: QueryParams, limit: int, offset: int) -> QueryParams:
    page_params = {"limit": limit, "offset": offset}
    if isinstance(params, Mapping):
        return {**params, **page_params}
    return [*params, *page_params.items()]


def fetch_all(client: SupabaseClient, table: str, params: QueryParams, limit: int = 1000) -> List[Dict[str, Any]]:
    offset = 0
    rows: List[Dict[str, Any]] = []
    while True:
        page = client.select(table, with_paging_params(params, limit, offset))
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
    return rows


def fetch_participants_for_leaderboard(
    client: SupabaseClient, lookback_months: int = ACTIVE_PLAYER_LOOKBACK_MONTHS
) -> List[Dict[str, Any]]:
    cutoff = get_past_months_cutoff(lookback_months)
    return fetch_all(
        client,
        "game_participants",
        {
            "select": "entry_id,player_id,tournament_id,seat_position,wins,draws,losses",
            "tournament_id.start_date": f"gte.{cutoff}",
            "entries.tournament_id": "not.is.null",
            "entries.player_id": "not.is.null",
        },
    )


def fetch_commander_participants(
    client: SupabaseClient, lookback_months: int = COMMANDER_PRIMARY_LOOKBACK_MONTHS
) -> List[Dict[str, Any]]:
    cutoff = get_past_months_cutoff(lookback_months)
    return fetch_all(
        client,
        "game_participants",
        {
            "select": "entry_id,player_id,tournament_id,seat_position,wins,draws,losses",
            "tournament_id.start_date": "gte." + str(cutoff),
            "entries.tournament_id": "not.is.null",
            "entries.player_id": "not.is.null",
        },
    )


def fetch_distinct_entry_ids(
    client: SupabaseClient, lookback_months: int = ACTIVE_PLAYER_LOOKBACK_MONTHS
) -> set[str]:
    cutoff = get_past_months_cutoff(lookback_months)
    rows = fetch_all(
        client,
        "game_participants",
        {
            "select": "entry_id",
            "tournament_id.start_date": f"gte.{cutoff}",
            "entries.tournament_id": "not.is.null",
            "entries.player_id": "not.is.null",
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


def compute_leaderboard(
    player_rows: List[Dict[str, Any]]
) -> Dict[Tuple[str, str, str], List[Dict[str, Any]]]:
    """Build leaderboard grouped by region."""
    by_region: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in player_rows:
        region_type = row.get("region_type", GLOBAL_REGION_TYPE)
        region_key = row.get("region_key", GLOBAL_REGION_KEY)
        by_region[(region_type, region_key)].append(row)
    for key in by_region:
        by_region[key].sort(key=lambda x: x["rating"], reverse=True)
    return by_region


def build_player_profiles(
    player_rows: List[Dict[str, Any]],
    lookback_days: int = 30,
) -> List[Dict[str, Any]]:
    """Build profile summary with recent activity indicators."""
    recent_set = {r["player_id"] for r in player_rows if r.get("last_activity") and r["last_activity"] >= cutoff}
    return [r for r in player_rows if r.get("player_id") in recent_set]


def detect_active_players(
    client: SupabaseClient, lookback_months: int = ACTIVE_PLAYER_LOOKBACK_MONTHS
) -> List[Dict[str, Any]]:
    """Identify players with recent activity."""
    cutoff = get_past_months_cutoff(lookback_months)
    rows = fetch_all(
        client,
        "game_participants",
        {
            "select": "player_id",
            "tournament_id.start_date": f"gte.{cutoff}",
            "entries.tournament_id": "not.is.null",
            "entries.player_id": "not.is.null",
        },
    )
    seen: set[str] = set()
    active: List[Dict[str, Any]] = []
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


# === CLI Entry Point ===
import sys


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
        print(f"[DRY RUN] Participant fetch not executed in dry-run mode")
        if job_id:
            fail_job(client, job_id, "Dry-run mode")
        sys.exit(0)

    print("Fetching participants for leaderboard...")
    update_job_heartbeat(client, job_id)
    participant_rows = fetch_participants_for_leaderboard(
        client, lookback_months=ACTIVE_PLAYER_LOOKBACK_MONTHS
    )
    update_job_heartbeat(client, job_id)
    print(f"Found {len(participant_rows)} participant rows")

    print("Fetching distinct entries for global ratings...")
    entry_ids = fetch_distinct_entry_ids(
        client, lookback_months=ACTIVE_PLAYER_LOOKBACK_MONTHS
    )
    print(f"Found {len(entry_ids)} distinct entries")

    # Build ratings dict
    player_ratings: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for entry_id in entry_ids:
        key = (GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY, entry_id)
        player_ratings[key] = create_empty_ratings_row(
            entry_id, GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY
        )

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

    # Compute leaderboard
    print("Computing leaderboard...")
    leaderboard = compute_leaderboard(ratings_to_upsert)
    all_leaderboard_rows: List[Dict[str, Any]] = []
    for (region_type, region_key), rows in leaderboard.items():
        for rank, row in enumerate(rows, start=1):
            all_leaderboard_rows.append(
                {
                    "player_id": row["player_id"],
                    "region_type": region_type,
                    "region_key": region_key,
                    "rank": rank,
                    "rating": row["rating"],
                    "games_played": row["games_played"],
                    "wins": row["wins"],
                    "draws": row["draws"],
                    "losses": row["losses"],
                    "win_streak": row["win_streak"],
                    "loss_streak": row["loss_streak"],
                }
            )

    if all_leaderboard_rows:
        client.upsert(
            "global_elo_active_leaderboard",
            all_leaderboard_rows,
            on_conflict="player_id,region_type,region_key",
        )

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
    main()
