#!/usr/bin/env python3
"""
cEDH Analytics Data Ingestion Pipeline

Fetches tournament data from TopDeck.gg API and loads into Supabase.
Designed to run weekly via GitHub Actions or manually.

Usage:
    python src/ingest.py --days 7 --min-players 32
    python src/ingest.py --tournament-id PqmLzgBpDBUM57JZ1OYB
    python src/ingest.py --tournament-id TID --direct  # Use direct Postgres (faster)
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests
from dateutil import parser as date_parser

# Optional: psycopg2 for direct Postgres connection (10x faster for large batches)
try:
    import psycopg2
    from psycopg2.extras import execute_values
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

BACKFILL_RUN_STATUSES = {"pending", "running", "completed", "completed_with_errors", "failed"}
BACKFILL_BATCH_STATUSES = {"pending", "running", "completed", "failed"}
US_STATE_BY_ABBREV = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonicalize_state_value(value: Any) -> str | None:
    if value is None:
        return None
    state = str(value).strip()
    if not state:
        return None
    upper_state = state.upper()
    if upper_state in US_STATE_BY_ABBREV:
        return US_STATE_BY_ABBREV[upper_state]
    if state == upper_state:
        return state.title()
    return state


class TopDeckClient:
    """Client for TopDeck.gg API V2."""

    BASE_URL = "https://topdeck.gg/api"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"Authorization": api_key})
        self.min_request_interval_seconds = float(os.getenv("TOPDECK_MIN_REQUEST_INTERVAL_SECONDS", "0.75"))
        self._last_request_monotonic = 0.0

    def _request(self, method: str, url: str, *, json_payload: dict | None = None, max_retries: int = 3):
        """HTTP request with basic retry for transient upstream errors."""
        for attempt in range(max_retries):
            try:
                if self.min_request_interval_seconds > 0 and self._last_request_monotonic:
                    elapsed = time.monotonic() - self._last_request_monotonic
                    if elapsed < self.min_request_interval_seconds:
                        time.sleep(self.min_request_interval_seconds - elapsed)
                response = self.session.request(method, url, json=json_payload, timeout=60)
                self._last_request_monotonic = time.monotonic()
                if response.status_code in (429, 502, 503, 504):
                    raise requests.exceptions.HTTPError(f"{response.status_code} Server Error", response=response)
                response.raise_for_status()
                return response
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
                if attempt < max_retries - 1:
                    response = getattr(e, "response", None)
                    status_code = response.status_code if response is not None else None
                    if status_code == 429:
                        retry_after = response.headers.get("Retry-After") if response is not None else None
                        try:
                            wait_time = max(float(retry_after), 5.0) if retry_after else float(5 * (2 ** attempt))
                        except ValueError:
                            wait_time = float(5 * (2 ** attempt))
                    else:
                        wait_time = float(2 ** attempt)
                    logger.warning(f"TopDeck request error, retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"TopDeck request failed after {max_retries} retries: {e}")
                    raise

    def search_tournaments(
        self,
        days: int = 7,
        min_players: int = 32,
        game: str = "Magic: The Gathering",
        format_: str = "EDH",
        light: bool = False,
    ) -> list[dict]:
        """Search for recent tournaments meeting criteria."""
        if light:
            payload = {
                "game": game,
                "format": format_,
                "last": days,
                "participantMin": min_players,
                "columns": ["name", "id"],
                "rounds": False,
                "tables": [],
                "players": [],
            }
        else:
            payload = {
                "game": game,
                "format": format_,
                "last": days,
                "participantMin": min_players,
                "columns": [
                    "name",
                    "decklist",
                    "wins",
                    "draws",
                    "losses",
                    "id",
                    "winRate",
                ],
                "rounds": True,
                "tables": ["table", "players", "winner", "status"],
                "players": ["name", "id", "decklist"],
            }

        logger.info(f"Searching tournaments: last {days} days, min {min_players} players")
        response = self._request("POST", f"{self.BASE_URL}/v2/tournaments", json_payload=payload)
        tournaments = response.json()
        logger.info(f"Found {len(tournaments)} tournaments")
        return tournaments

    def get_tournament(self, tid: str) -> dict:
        """Get full tournament details by ID."""
        logger.info(f"Fetching tournament: {tid}")
        response = self._request("GET", f"{self.BASE_URL}/v2/tournaments/{tid}")
        return response.json()


class SupabaseClient:
    """Lightweight Supabase client for data insertion."""

    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip("/")
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def upsert(self, table: str, data: dict | list, on_conflict: str = None, max_retries: int = 3) -> dict:
        """Upsert data into a table with retry logic."""
        endpoint = f"{self.url}/rest/v1/{table}"

        headers = self.headers.copy()
        if on_conflict:
            headers["Prefer"] = f"resolution=merge-duplicates,return=representation"

        params = {}
        if on_conflict:
            params["on_conflict"] = on_conflict

        for attempt in range(max_retries):
            try:
                response = requests.post(endpoint, json=data, headers=headers, params=params, timeout=30)
                if response.status_code >= 400:
                    logger.error(f"Supabase error: {response.text}")
                    response.raise_for_status()
                return response.json()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Connection error, retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} retries: {e}")
                    raise

    def select(self, table: str, filters: dict = None, max_retries: int = 3) -> list:
        """Select data from a table with retry logic."""
        endpoint = f"{self.url}/rest/v1/{table}"
        params = filters or {}

        for attempt in range(max_retries):
            try:
                response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Select error, retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Select failed after {max_retries} retries: {e}")
                    raise


class DirectPostgresClient:
    """Direct PostgreSQL client using psycopg2 for high-performance batch operations.

    This is ~10x faster than the REST API for large batches (1000+ rows).
    Requires psycopg2 and SUPABASE_DB_URL environment variable.

    See: docs/supabase-batch-ingestion-patterns.md
    """

    def __init__(self, db_url: str):
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 is required for direct Postgres connection. Install with: pip install psycopg2-binary")
        self.db_url = db_url
        self._conn = None

    def connect(self):
        """Establish database connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.db_url)
        return self._conn

    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()

    def upsert(self, table: str, data: dict | list, on_conflict: str = None) -> list:
        """Upsert data using execute_values for high performance.

        Args:
            table: Target table name
            data: Dict or list of dicts to upsert
            on_conflict: Comma-separated column names for ON CONFLICT clause

        Returns:
            List of inserted/updated records with IDs
        """
        if not data:
            return []

        if isinstance(data, dict):
            data = [data]

        if not data:
            return []

        # Get columns from first record
        columns = list(data[0].keys())
        cols_str = ", ".join(columns)

        # Build ON CONFLICT clause
        if on_conflict:
            conflict_cols = on_conflict.replace(" ", "").split(",")
            update_cols = [c for c in columns if c not in conflict_cols]
            update_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
            conflict_clause = f"ON CONFLICT ({on_conflict}) DO UPDATE SET {update_str}"
        else:
            conflict_clause = ""

        sql = f"""
            INSERT INTO {table} ({cols_str})
            VALUES %s
            {conflict_clause}
            RETURNING *
        """

        # Convert dicts to tuples
        values = [tuple(d.get(c) for c in columns) for d in data]

        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                execute_values(cursor, sql, values, page_size=2000)
                results = cursor.fetchall()
                col_names = [desc[0] for desc in cursor.description]
                conn.commit()
                return [dict(zip(col_names, row)) for row in results]
        except Exception as e:
            conn.rollback()
            logger.error(f"Direct Postgres upsert failed: {e}")
            raise

    def select(self, table: str, filters: dict = None) -> list:
        """Select data from a table.

        Args:
            table: Table name
            filters: Dict of filters in Supabase format (e.g., {"name": "eq.value"})

        Returns:
            List of records as dicts
        """
        where_clauses = []
        params = []

        if filters:
            for col, val in filters.items():
                if isinstance(val, str) and val.startswith("eq."):
                    where_clauses.append(f"{col} = %s")
                    params.append(val[3:])  # Remove "eq." prefix
                elif isinstance(val, str) and val.startswith("in."):
                    # Handle IN clause
                    in_values = val[3:].strip("()").split(",")
                    placeholders = ",".join(["%s"] * len(in_values))
                    where_clauses.append(f"{col} IN ({placeholders})")
                    params.extend(in_values)

        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
        sql = f"SELECT * FROM {table} WHERE {where_str}"

        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                if not results:
                    return []
                col_names = [desc[0] for desc in cursor.description]
                return [dict(zip(col_names, row)) for row in results]
        except Exception as e:
            logger.error(f"Direct Postgres select failed: {e}")
            raise


def extract_commanders(decklist: str) -> list[str]:
    """Extract commander names from a decklist string."""
    if not decklist:
        return []

    # Handle Moxfield URLs - can't extract without API call
    if "moxfield.com" in decklist:
        return []

    # Parse TopDeck format: ~~Commanders~~\n1 Commander Name\n...
    if "~~Commanders~~" in decklist:
        try:
            cmd_section = decklist.split("~~Commanders~~")[1].split("~~")[0]
            commanders = []
            for line in cmd_section.split("\\n"):
                line = line.strip()
                if line and line[0].isdigit():
                    # Remove leading "1 " or similar
                    name = re.sub(r"^\d+\s+", "", line)
                    if name:
                        commanders.append(name)
            return commanders
        except Exception as e:
            logger.warning(f"Failed to parse decklist: {e}")
            return []

    return []


def normalize_commander_name(commanders: list[str]) -> str:
    """Create a normalized commander name (sorted for partners)."""
    if not commanders:
        return "Unknown Commander"

    # Sort for consistency (e.g., "Kraum / Tymna" = "Tymna / Kraum")
    sorted_cmds = sorted(commanders)
    return " / ".join(sorted_cmds)


def normalize_rate_value(value: Any) -> Optional[float]:
    """Normalize TopDeck rate fields into 0-1 decimal form for NUMERIC(5,4)."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric > 1:
        numeric = numeric / 100.0
    if numeric < 0 or numeric > 1:
        return None
    return numeric


class DataIngester:
    """Main ingestion orchestrator."""

    def __init__(self, topdeck: TopDeckClient, supabase: SupabaseClient, min_players: int = 16):
        self.topdeck = topdeck
        self.supabase = supabase
        self.min_players = min_players
        self.commander_cache = {}  # name -> id
        self.player_cache = {}  # topdeck_id -> id

    def fetch_existing_tournament(self, tid: str) -> dict | None:
        existing = self.supabase.select(
            "tournaments",
            {
                "select": "id,city,state,country,venue,latitude,longitude,header_image_url",
                "topdeck_tid": f"eq.{tid}",
                "limit": 1,
            },
        )
        return existing[0] if existing else None

    @staticmethod
    def extract_event_data(tournament: dict, info: dict | None = None) -> dict:
        info = info or {}
        event_data = tournament.get("eventData") or info.get("eventData") or {}
        if not isinstance(event_data, dict):
            event_data = {}

        return {
            "city": event_data.get("city") or event_data.get("town") or event_data.get("municipality"),
            "state": canonicalize_state_value(
                event_data.get("state") or event_data.get("province") or event_data.get("region")
            ),
            "country": event_data.get("country"),
            "venue": event_data.get("location") or event_data.get("venue") or event_data.get("address"),
            "latitude": event_data.get("lat") if event_data.get("lat") is not None else event_data.get("latitude"),
            "longitude": event_data.get("lng") if event_data.get("lng") is not None else event_data.get("longitude"),
            "header_image_url": event_data.get("headerImage") or event_data.get("header_image_url"),
        }

    def get_or_create_commander(self, name: str, commander_names: list[str]) -> str:
        """Get or create a commander entry, return UUID. (Legacy - use batch method)"""
        if name in self.commander_cache:
            return self.commander_cache[name]

        # Try to find existing
        existing = self.supabase.select("commanders", {"name": f"eq.{name}"})
        if existing:
            self.commander_cache[name] = existing[0]["id"]
            return existing[0]["id"]

        # Create new
        data = {
            "name": name,
            "commander_names": commander_names or [name],
        }
        result = self.supabase.upsert("commanders", data, on_conflict="name")
        if result:
            self.commander_cache[name] = result[0]["id"]
            return result[0]["id"]
        return None

    def get_or_create_player(self, topdeck_id: str, name: str) -> str:
        """Get or create a player entry, return UUID. (Legacy - use batch method)"""
        if not topdeck_id:
            return None

        if topdeck_id in self.player_cache:
            return self.player_cache[topdeck_id]

        # Try to find existing
        existing = self.supabase.select("players", {"topdeck_id": f"eq.{topdeck_id}"})
        if existing:
            self.player_cache[topdeck_id] = existing[0]["id"]
            return existing[0]["id"]

        # Create new
        data = {"topdeck_id": topdeck_id, "name": name}
        result = self.supabase.upsert("players", data, on_conflict="topdeck_id")
        if result:
            self.player_cache[topdeck_id] = result[0]["id"]
            return result[0]["id"]
        return None

    def batch_upsert_commanders(self, commander_data: dict[str, list[str]]) -> dict[str, str]:
        """Batch upsert commanders and return name -> id mapping."""
        if not commander_data:
            return {}

        # Build batch data
        batch = [
            {"name": name, "commander_names": names or [name]}
            for name, names in commander_data.items()
            if name not in self.commander_cache
        ]

        if batch:
            logger.info(f"Batch upserting {len(batch)} commanders...")
            result = self.supabase.upsert("commanders", batch, on_conflict="name")
            if result:
                for cmd in result:
                    self.commander_cache[cmd["name"]] = cmd["id"]

        return self.commander_cache.copy()

    def batch_upsert_players(self, player_data: dict[str, str]) -> dict[str, str]:
        """Batch upsert players and return topdeck_id -> id mapping."""
        if not player_data:
            return {}

        # Build batch data (only new players)
        batch = [
            {"topdeck_id": tid, "name": name}
            for tid, name in player_data.items()
            if tid and tid not in self.player_cache
        ]

        if batch:
            logger.info(f"Batch upserting {len(batch)} players...")
            result = self.supabase.upsert("players", batch, on_conflict="topdeck_id")
            if result:
                for player in result:
                    self.player_cache[player["topdeck_id"]] = player["id"]

        return self.player_cache.copy()

    def batch_upsert_entries(self, entries: list[dict]) -> dict[str, str]:
        """Batch upsert tournament entries and return topdeck_player_id -> entry_id mapping."""
        if not entries:
            return {}

        deduped_entries: list[dict] = []
        seen_entry_keys: set[tuple[str, str]] = set()
        duplicate_count = 0
        for entry in entries:
            entry_key = (entry["tournament_id"], entry["player_id"])
            if entry_key in seen_entry_keys:
                duplicate_count += 1
                continue
            seen_entry_keys.add(entry_key)
            deduped_entries.append(entry)

        if duplicate_count:
            logger.warning(
                f"Skipped {duplicate_count} duplicate tournament entry rows before upsert"
            )

        logger.info(f"Batch upserting {len(deduped_entries)} tournament entries...")
        result = self.supabase.upsert(
            "tournament_entries", deduped_entries, on_conflict="tournament_id,player_id"
        )

        entry_map = {}
        if result:
            for entry in result:
                # Find the topdeck_id for this player_id
                for tid, pid in self.player_cache.items():
                    if pid == entry["player_id"]:
                        entry_map[tid] = entry["id"]
                        break
        return entry_map

    def process_tournament(self, tournament: dict) -> dict:
        """Process a single tournament and load into database."""
        # Handle both search results and direct fetch formats
        if "data" in tournament:
            info = tournament["data"]
            standings = tournament.get("standings", [])
            rounds = tournament.get("rounds", [])
            tid = tournament.get("TID", "unknown")
        else:
            info = tournament
            standings = tournament.get("standings", [])
            rounds = tournament.get("rounds", [])
            tid = tournament.get("TID", "unknown")

        name = info.get("name") or tournament.get("tournamentName", "Unknown")
        start_date = info.get("startDate") or tournament.get("startDate")
        standings = standings or []
        rounds = rounds or []
        player_count = len(standings)
        swiss_rounds = tournament.get("swissNum", 0)
        reported_top_cut = tournament.get("topCut", 0)
        effective_top_cut = reported_top_cut
        if player_count <= 34:
            effective_top_cut = 4

        # Skip if too few players
        if player_count < self.min_players:
            logger.info(f"Skipping {name}: only {player_count} players (min: {self.min_players})")
            return None

        logger.info(f"Processing: {name} ({player_count} players, {len(rounds)} rounds)")

        # Convert timestamp to ISO format
        if isinstance(start_date, (int, float)):
            start_date = datetime.fromtimestamp(start_date).isoformat()

        existing_tournament = self.fetch_existing_tournament(tid)
        location_data = self.extract_event_data(tournament, info)

        # Upsert tournament
        tournament_data = {
            "topdeck_tid": tid,
            "name": name,
            "start_date": start_date,
            "player_count": player_count,
            "swiss_rounds": swiss_rounds,
            "top_cut": effective_top_cut,
            "average_elo": int(tournament.get("averageElo")) if tournament.get("averageElo") else None,
            "median_elo": int(tournament.get("medianElo")) if tournament.get("medianElo") else None,
            "top_elo": int(tournament.get("topElo")) if tournament.get("topElo") else None,
            "city": location_data["city"] or (existing_tournament or {}).get("city"),
            "state": location_data["state"] or (existing_tournament or {}).get("state"),
            "country": location_data["country"] or (existing_tournament or {}).get("country"),
            "venue": location_data["venue"] or (existing_tournament or {}).get("venue"),
            "latitude": (
                location_data["latitude"]
                if location_data["latitude"] is not None
                else (existing_tournament or {}).get("latitude")
            ),
            "longitude": (
                location_data["longitude"]
                if location_data["longitude"] is not None
                else (existing_tournament or {}).get("longitude")
            ),
            "header_image_url": location_data["header_image_url"] or (existing_tournament or {}).get("header_image_url"),
        }

        result = self.supabase.upsert("tournaments", tournament_data, on_conflict="topdeck_tid")
        if not result:
            logger.error(f"Failed to upsert tournament: {tid}")
            return None

        tournament_id = result[0]["id"]
        logger.info(f"Tournament ID: {tournament_id}")

        # === BATCH PROCESSING: Pre-process all data first ===
        total_players = len(standings)
        logger.info(f"Pre-processing {total_players} players...")

        # Step 1: Extract all unique commanders and players (local processing)
        commander_data = {}  # name -> [individual_commander_names]
        player_data = {}  # topdeck_id -> name
        standing_info = []  # [{idx, topdeck_id, commander_name, decklist, ...}]

        for idx, standing in enumerate(standings):
            if not isinstance(standing, dict):
                continue
            player_topdeck_id = standing.get("id")
            player_name = standing.get("name", "Unknown")
            decklist = standing.get("decklist") or ""

            # Extract and normalize commander
            commanders = extract_commanders(decklist)
            commander_name = normalize_commander_name(commanders)

            # Collect unique commanders
            if commander_name not in commander_data:
                commander_data[commander_name] = commanders

            # Collect unique players
            if player_topdeck_id and player_topdeck_id not in player_data:
                player_data[player_topdeck_id] = player_name

            # Store for later entry creation
            standing_info.append({
                "idx": idx,
                "topdeck_id": player_topdeck_id,
                "commander_name": commander_name,
                "decklist": decklist,
                "standing": standing,
            })

        # Step 2: Batch upsert commanders (1 API call)
        self.batch_upsert_commanders(commander_data)

        # Step 3: Batch upsert players (1 API call)
        self.batch_upsert_players(player_data)

        # Step 4: Build all entry records with resolved IDs
        entries = []
        for info in standing_info:
            commander_id = self.commander_cache.get(info["commander_name"])
            player_id = self.player_cache.get(info["topdeck_id"])

            if not commander_id or not player_id:
                continue

            standing = info["standing"]
            final_standing = info["idx"] + 1
            decklist = info["decklist"]

            top_16_cutoff = 4 if player_count <= 34 else 16
            entries.append({
                "tournament_id": tournament_id,
                "player_id": player_id,
                "commander_id": commander_id,
                "final_standing": final_standing,
                "points": int(standing.get("points") or 0),
                "wins": int(standing.get("wins") or 0),
                "losses": int(standing.get("losses") or 0),
                "draws": int(standing.get("draws") or 0),
                "win_rate": normalize_rate_value(standing.get("winRate")),
                "opponent_win_rate": normalize_rate_value(standing.get("opponentWinRate")),
                "decklist_url": decklist if decklist and "http" in decklist else None,
                "decklist_text": decklist if decklist and "http" not in decklist else None,
                "made_top_cut": final_standing <= effective_top_cut if effective_top_cut > 0 else False,
                "made_top_16": final_standing <= top_16_cutoff,
            })

        # Step 5: Batch upsert all entries (1 API call)
        entry_map = self.batch_upsert_entries(entries)
        logger.info(f"Created {len(entry_map)} tournament entries")

        # === BATCH PROCESSING FOR GAMES ===
        if not rounds:
            logger.warning(f"No rounds data for {name}")
            return {
                "tournament_id": tournament_id,
                "name": name,
                "players": player_count,
                "entries_created": len(entry_map),
                "games_created": 0,
            }

        # Step 1: Pre-process all rounds/tables to build game data
        logger.info(f"Pre-processing {len(rounds)} rounds for games...")
        games_data = []  # List of (game_data, participants_info)

        for round_data in rounds:
            round_num = round_data.get("round")
            is_bracket = isinstance(round_num, str) and not round_num.isdigit()

            for table in round_data.get("tables", []):
                if not isinstance(table, dict):
                    continue
                table_num = table.get("table")
                if table_num == "Byes":
                    continue

                players = table.get("players", [])
                winner_name = table.get("winner")
                winner_id_raw = table.get("winner_id")
                status = table.get("status", "Unknown")

                if len(players) < 2:
                    continue

                # Determine winner player_id
                winner_player_id = None
                is_draw = winner_id_raw == "Draw" or winner_name is None

                if not is_draw:
                    for p in players:
                        if not isinstance(p, dict):
                            continue
                        if p.get("id") == winner_id_raw or p.get("name") == winner_name:
                            winner_player_id = self.player_cache.get(p.get("id"))
                            break

                game_data = {
                    "tournament_id": tournament_id,
                    "round_number": int(round_num) if isinstance(round_num, int) or (isinstance(round_num, str) and round_num.isdigit()) else None,
                    "round_name": str(round_num) if is_bracket else None,
                    "is_bracket": is_bracket,
                    "table_number": table_num if isinstance(table_num, int) else None,
                    "status": status,
                    "is_draw": is_draw,
                    "winner_id": winner_player_id,
                }
                game_data["game_key"] = build_game_key(
                    tournament_id,
                    game_data["round_number"],
                    game_data["round_name"],
                    game_data["table_number"],
                    game_data["is_bracket"],
                )

                # Build participants info for this game
                participants_info = []
                for seat, player in enumerate(players):
                    if not isinstance(player, dict):
                        continue
                    player_topdeck_id = player.get("id")
                    if not player_topdeck_id or player_topdeck_id not in entry_map:
                        continue

                    entry_id = entry_map[player_topdeck_id]
                    is_winner = player_topdeck_id == winner_id_raw

                    if is_draw:
                        result_str = "draw"
                        points = 1
                    elif is_winner:
                        result_str = "win"
                        points = 5
                    else:
                        result_str = "loss"
                        points = 0

                    participants_info.append({
                        "entry_id": entry_id,
                        "seat_position": seat,
                        "result": result_str,
                        "points_earned": points,
                    })

                games_data.append((game_data, participants_info))

        # Step 2: Batch upsert all games
        if games_data:
            game_records = [g[0] for g in games_data]
            logger.info(f"Batch upserting {len(game_records)} games...")

            try:
                game_results = self.supabase.upsert("games", game_records, on_conflict="game_key")

                # Step 3: Build and batch upsert all participants
                if game_results:
                    all_participants = []
                    for i, game_result in enumerate(game_results):
                        game_id = game_result["id"]
                        _, participants_info = games_data[i]

                        for p in participants_info:
                            all_participants.append({
                                "game_id": game_id,
                                "entry_id": p["entry_id"],
                                "seat_position": p["seat_position"],
                                "result": p["result"],
                                "points_earned": p["points_earned"],
                            })

                    if all_participants:
                        logger.info(f"Batch upserting {len(all_participants)} game participants...")
                        self.supabase.upsert("game_participants", all_participants, on_conflict="game_id,entry_id")

            except Exception as e:
                logger.error(f"Failed to batch create games: {e}")
                return {
                    "tournament_id": tournament_id,
                    "name": name,
                    "players": player_count,
                    "entries_created": len(entry_map),
                    "games_created": 0,
                }

        games_created = len(games_data)
        logger.info(f"Created {games_created} games for {name}")

        return {
            "tournament_id": tournament_id,
            "name": name,
            "players": player_count,
            "entries_created": len(entry_map),
            "games_created": games_created,
        }


def parse_tournament_start_date(tournament: dict) -> Optional[datetime]:
    """Extract and parse tournament start date from search or detail payloads."""
    info = tournament.get("data", tournament)
    start_date = info.get("startDate") or tournament.get("startDate")
    if start_date is None:
        return None
    try:
        if isinstance(start_date, (int, float)):
            return datetime.fromtimestamp(start_date)
        if isinstance(start_date, str):
            return date_parser.parse(start_date)
    except Exception:
        return None
    return None


def normalize_tournament_name(name: str) -> str:
    """Normalize tournament name for fuzzy matching."""
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def build_game_key(
    tournament_id: str,
    round_number: Optional[int],
    round_name: Optional[str],
    table_number: Optional[int],
    is_bracket: bool,
) -> str:
    """Build deterministic game key for idempotent upserts."""
    return "|".join([
        str(tournament_id),
        str(round_number) if round_number is not None else "RNULL",
        round_name or "RNNULL",
        str(table_number) if table_number is not None else "TNULL",
        str(is_bracket).lower() if is_bracket is not None else "BNULL",
    ])


def extract_name_and_tid(tournament: dict) -> tuple[Optional[str], Optional[str]]:
    """Extract a display name and tournament id/slug from a search payload."""
    name = (
        tournament.get("tournamentName")
        or tournament.get("name")
        or tournament.get("data", {}).get("name")
    )
    tid = (
        tournament.get("TID")
        or tournament.get("id")
        or tournament.get("data", {}).get("id")
        or tournament.get("tournamentId")
    )
    return name, tid


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def load_tids(path: Path) -> list[str]:
    return dedupe_preserve_order([
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ])


def write_tids(path: Path, tids: list[str], *, header_lines: Optional[list[str]] = None) -> None:
    lines = [*(header_lines or []), "", *tids, ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def chunk_items(items: list[str], batch_size: int) -> list[list[str]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def fetch_existing_tids(client: Any, tids: list[str]) -> set[str]:
    existing: set[str] = set()
    if not tids:
        return existing

    chunk_size = 200
    for i in range(0, len(tids), chunk_size):
        chunk = tids[i : i + chunk_size]
        quoted = ",".join(f'"{tid}"' for tid in chunk)
        rows = client.select(
            "tournaments",
            {
                "select": "topdeck_tid",
                "topdeck_tid": f"in.({quoted})",
            },
        )
        existing.update(
            row["topdeck_tid"]
            for row in rows
            if row.get("topdeck_tid")
        )
    return existing


def fetch_failed_tids_for_run(client: Any, run_key: str) -> list[str]:
    run_rows = client.select(
        "ingestion_backfill_runs",
        {
            "select": "id",
            "run_key": f"eq.{run_key}",
            "limit": 1,
        },
    )
    if not run_rows:
        raise SystemExit(f"No backfill run found for run_key={run_key}")

    run_id = run_rows[0]["id"]
    event_rows = client.select(
        "ingestion_backfill_events",
        {
            "select": "tid,created_at",
            "run_id": f"eq.{run_id}",
            "event_type": "eq.process_failed",
            "order": "created_at.asc",
            "limit": 10000,
        },
    )
    return dedupe_preserve_order([
        row["tid"]
        for row in event_rows
        if row.get("tid")
    ])


def compute_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_backfill_run_key(tids_path: Path, batch_size: int) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{tids_path.stem}-{batch_size}-{timestamp}"


def ensure_backfill_run_status(status: str) -> str:
    if status not in BACKFILL_RUN_STATUSES:
        raise ValueError(f"invalid backfill run status: {status}")
    return status


def ensure_backfill_batch_status(status: str) -> str:
    if status not in BACKFILL_BATCH_STATUSES:
        raise ValueError(f"invalid backfill batch status: {status}")
    return status


def upsert_backfill_run(
    client: Any,
    *,
    run_key: str,
    tids_path: Path,
    batch_size: int,
    total_tournaments: int,
    total_batches: int,
    start_date: Optional[str],
    end_date: Optional[str],
    status: str,
) -> Optional[dict]:
    status = ensure_backfill_run_status(status)
    payload = {
        "run_key": run_key,
        "manifest_path": str(tids_path),
        "manifest_sha256": compute_file_sha256(tids_path),
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "batch_size": batch_size,
        "discovered_tournament_count": total_tournaments,
        "total_batches": total_batches,
        "status": status,
        "heartbeat_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    result = client.upsert("ingestion_backfill_runs", payload, on_conflict="run_key")
    return result[0] if result else None


def upsert_backfill_batch(
    client: Any,
    *,
    run_id: str,
    batch_index: int,
    batch_start: int,
    batch_end: int,
    tournament_count: int,
    status: str,
    error_text: Optional[str] = None,
) -> None:
    status = ensure_backfill_batch_status(status)
    now = utc_now_iso()
    payload = {
        "run_id": run_id,
        "batch_index": batch_index,
        "batch_start": batch_start,
        "batch_end": batch_end,
        "tournament_count": tournament_count,
        "status": status,
        "error_text": error_text,
        "updated_at": now,
        "started_at": now if status == "running" else None,
        "finished_at": now if status in {"completed", "failed"} else None,
    }
    client.upsert("ingestion_backfill_batches", payload, on_conflict="run_id,batch_index")


def update_backfill_run_progress(
    client: Any,
    *,
    run_row: dict,
    processed_count: int,
    succeeded_count: int,
    failed_count: int,
    status: str,
    current_batch_index: Optional[int] = None,
    current_tid: Optional[str] = None,
    last_completed_tid: Optional[str] = None,
    current_batch_processed_count: Optional[int] = None,
    current_batch_succeeded_count: Optional[int] = None,
    current_batch_failed_count: Optional[int] = None,
    last_success_at: Optional[str] = None,
    heartbeat_at: Optional[str] = None,
) -> Optional[dict]:
    status = ensure_backfill_run_status(status)
    payload = {
        "run_key": run_row["run_key"],
        "manifest_path": run_row["manifest_path"],
        "manifest_sha256": run_row["manifest_sha256"],
        "requested_start_date": run_row.get("requested_start_date"),
        "requested_end_date": run_row.get("requested_end_date"),
        "batch_size": run_row["batch_size"],
        "discovered_tournament_count": run_row["discovered_tournament_count"],
        "total_batches": run_row["total_batches"],
        "processed_tournament_count": processed_count,
        "succeeded_tournament_count": succeeded_count,
        "failed_tournament_count": failed_count,
        "current_batch_index": current_batch_index,
        "current_tid": current_tid,
        "last_completed_tid": last_completed_tid,
        "current_batch_processed_count": current_batch_processed_count or 0,
        "current_batch_succeeded_count": current_batch_succeeded_count or 0,
        "current_batch_failed_count": current_batch_failed_count or 0,
        "last_success_at": last_success_at,
        "heartbeat_at": heartbeat_at or utc_now_iso(),
        "status": status,
        "updated_at": utc_now_iso(),
    }
    result = client.upsert("ingestion_backfill_runs", payload, on_conflict="run_key")
    return result[0] if result else None


def append_backfill_event(
    client: Any,
    *,
    run_id: str,
    batch_index: int,
    event_type: str,
    tid: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    client.upsert(
        "ingestion_backfill_events",
        {
            "run_id": run_id,
            "batch_index": batch_index,
            "tid": tid,
            "event_type": event_type,
            "payload": payload or {},
            "created_at": utc_now_iso(),
        },
    )


def main():
    parser = argparse.ArgumentParser(description="cEDH Analytics Data Ingestion")
    parser.add_argument("--days", type=int, default=7, help="Days back to search")
    parser.add_argument("--start-date", type=str, help="Backfill start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Backfill end date (YYYY-MM-DD, inclusive)")
    parser.add_argument("--min-players", type=int, default=16, help="Minimum players")
    parser.add_argument("--tournament-id", type=str, help="Process specific tournament")
    parser.add_argument("--tids-file", type=str, help="Path to file with one tournament ID per line")
    parser.add_argument("--batch-size", type=int, default=50, help="Tournament batch size when processing --tids-file")
    parser.add_argument("--batch-index", type=int, help="0-based batch index to process from --tids-file")
    parser.add_argument("--run-key", type=str, help="Stable identifier for recording a historical backfill run")
    parser.add_argument(
        "--skip-existing-tids",
        action="store_true",
        help="When using --tids-file, skip TIDs already present in tournaments.topdeck_tid before batching",
    )
    parser.add_argument(
        "--only-failed-from-run-key",
        type=str,
        help="When using --tids-file, keep only TIDs that previously emitted process_failed in the specified run",
    )
    parser.add_argument(
        "--selected-tids-out",
        type=str,
        help="Write the final post-filter TID list to this path before processing",
    )
    parser.add_argument(
        "--record-backfill",
        action="store_true",
        help="Persist backfill run and batch status to ingestion_backfill_runs/_batches",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Fail fast instead of continuing to later tournaments after an error in --tids-file mode",
    )
    parser.add_argument("--names-file", type=str, help="Path to file with one tournament name per line")
    parser.add_argument("--resolve-days", type=int, default=120, help="Days back to search when resolving names to IDs")
    parser.add_argument("--resolve-min-players", type=int, default=0, help="Min players for name resolution search")
    parser.add_argument("--tids-out", type=str, help="Write resolved tournament IDs to this file")
    parser.add_argument(
        "--resolve-include-ambiguous",
        action="store_true",
        help="Include all candidate IDs for ambiguous name matches",
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct Postgres connection (10x faster for large batches). Requires SUPABASE_DB_URL env var and psycopg2.",
    )
    args = parser.parse_args()

    # Load credentials from environment
    topdeck_key = os.getenv("TOPDECK_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    supabase_db_url = os.getenv("SUPABASE_DB_URL")

    # Fallback to .env file
    if not topdeck_key:
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        if key in ("TOPDECK_API_KEY", "TOPDECK_GG_API_KEY"):
                            topdeck_key = value
                        elif key == "SUPABASE_URL":
                            supabase_url = value
                        elif key == "SUPABASE_SERVICE_KEY":
                            supabase_key = value
                        elif key == "SUPABASE_DB_URL":
                            supabase_db_url = value

    if not topdeck_key:
        logger.error("TOPDECK_API_KEY not set")
        sys.exit(1)

    topdeck = TopDeckClient(topdeck_key)

    if args.dry_run:
        logger.info("DRY RUN - not writing to database")
        if (
            args.only_failed_from_run_key
            or args.skip_existing_tids
            or args.record_backfill
        ):
            if not supabase_url or not supabase_key:
                logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
                sys.exit(1)
            db_client = SupabaseClient(supabase_url, supabase_key)
        else:
            db_client = None
    elif args.direct:
        # Use direct Postgres connection for ~10x faster batch operations
        if not supabase_db_url:
            logger.error("SUPABASE_DB_URL not set. Required for --direct mode.")
            logger.error("Get it from Supabase Dashboard: Project Settings > Database > Connection string > URI")
            sys.exit(1)
        if not PSYCOPG2_AVAILABLE:
            logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
            sys.exit(1)
        logger.info("Using direct Postgres connection (--direct mode)")
        db_client = DirectPostgresClient(supabase_db_url)
    else:
        if not supabase_url or not supabase_key:
            logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
            sys.exit(1)
        db_client = SupabaseClient(supabase_url, supabase_key)

    ingester = DataIngester(topdeck, db_client, min_players=args.min_players) if db_client else None

    # Process tournaments
    if args.names_file:
        names_path = Path(args.names_file)
        if not names_path.exists():
            logger.error(f"Names file not found: {names_path}")
            sys.exit(1)
        names = [
            line.strip()
            for line in names_path.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        logger.info(f"Loaded {len(names)} tournament names from {names_path}")

        logger.info(
            f"Resolving names using last {args.resolve_days} days, min_players={args.resolve_min_players}"
        )
        tournaments = topdeck.search_tournaments(
            days=args.resolve_days, min_players=args.resolve_min_players, light=True
        )

        # Build lookup map from normalized name -> list of (name, tid)
        name_map: dict[str, list[tuple[str, str]]] = {}
        for t in tournaments:
            t_name, t_tid = extract_name_and_tid(t)
            if not t_name or not t_tid:
                continue
            key = normalize_tournament_name(t_name)
            name_map.setdefault(key, []).append((t_name, t_tid))

        resolved: dict[str, str] = {}
        resolved_extra: set[str] = set()
        unresolved: list[str] = []

        for raw_name in names:
            key = normalize_tournament_name(raw_name)
            matches = name_map.get(key, [])
            if len(matches) == 1:
                resolved[raw_name] = matches[0][1]
                continue

            # Fallback: contains match (unique)
            contains_matches = [
                (t_name, t_tid)
                for k, vals in name_map.items()
                if key and key in k
                for (t_name, t_tid) in vals
            ]
            if len(contains_matches) == 1:
                resolved[raw_name] = contains_matches[0][1]
                continue

            if args.resolve_include_ambiguous and (matches or contains_matches):
                for _, t_tid in (matches or contains_matches):
                    resolved_extra.add(t_tid)
            else:
                unresolved.append(raw_name)
            if matches or contains_matches:
                logger.warning(
                    f"Ambiguous match for '{raw_name}': {[m[0] for m in (matches or contains_matches)]}"
                )

        if args.tids_out:
            out_path = Path(args.tids_out)
            all_tids = set(resolved.values()) | resolved_extra
            out_path.write_text("\n".join(sorted(all_tids)) + "\n")
            logger.info(f"Wrote {len(all_tids)} TIDs to {out_path}")
        else:
            for name, tid in resolved.items():
                logger.info(f"Resolved: {name} -> {tid}")

        if unresolved:
            logger.warning(f"Unresolved ({len(unresolved)}): {unresolved}")

        logger.info("Name resolution complete")
        return

    if args.tournament_id:
        tournament = topdeck.get_tournament(args.tournament_id)
        tournament["TID"] = args.tournament_id
        if ingester:
            result = ingester.process_tournament(tournament)
            logger.info(f"Result: {result}")
    elif args.tids_file:
        tids_path = Path(args.tids_file)
        if not tids_path.exists():
            logger.error(f"TIDs file not found: {tids_path}")
            sys.exit(1)
        tids = load_tids(tids_path)
        logger.info(f"Loaded {len(tids)} unique tournament IDs from {tids_path}")

        if args.only_failed_from_run_key:
            if not ingester:
                logger.error("--only-failed-from-run-key requires a readable database client")
                sys.exit(1)
            failed_tids = set(fetch_failed_tids_for_run(ingester.supabase, args.only_failed_from_run_key))
            original_count = len(tids)
            tids = [tid for tid in tids if tid in failed_tids]
            logger.info(
                f"Filtered manifest to {len(tids)} failed tids from run_key={args.only_failed_from_run_key} "
                f"(from {original_count})"
            )

        if args.skip_existing_tids:
            if not ingester:
                logger.error("--skip-existing-tids requires a readable database client")
                sys.exit(1)
            existing_tids = fetch_existing_tids(ingester.supabase, tids)
            original_count = len(tids)
            tids = [tid for tid in tids if tid not in existing_tids]
            logger.info(
                f"Skipped {original_count - len(tids)} tids already present in tournaments.topdeck_tid; "
                f"{len(tids)} remaining"
            )

        if args.selected_tids_out:
            selected_path = Path(args.selected_tids_out)
            header_lines = [
                "# Selected tournament IDs after ingest.py pre-batch filtering",
                f"# Source manifest: {tids_path}",
                f"# only_failed_from_run_key: {args.only_failed_from_run_key or ''}",
                f"# skip_existing_tids: {args.skip_existing_tids}",
            ]
            write_tids(selected_path, tids, header_lines=header_lines)
            logger.info(f"Wrote {len(tids)} selected tids to {selected_path}")

        if args.batch_size <= 0:
            logger.error("--batch-size must be positive")
            sys.exit(1)

        start_dt = date_parser.parse(args.start_date) if args.start_date else None
        end_dt = date_parser.parse(args.end_date) if args.end_date else None
        if start_dt and end_dt and end_dt < start_dt:
            logger.error("--end-date must be on or after --start-date")
            sys.exit(1)

        batches = chunk_items(tids, args.batch_size)
        logger.info(f"Prepared {len(batches)} batches from {len(tids)} tournaments (batch_size={args.batch_size})")

        if args.batch_index is not None and (args.batch_index < 0 or args.batch_index >= len(batches)):
            logger.error(f"--batch-index must be between 0 and {max(len(batches) - 1, 0)}")
            sys.exit(1)

        selected_batches = (
            [(args.batch_index, batches[args.batch_index])]
            if args.batch_index is not None
            else list(enumerate(batches))
        )

        run_key = args.run_key or default_backfill_run_key(tids_path, args.batch_size)
        processed_count = 0
        succeeded_count = 0
        failed_count = 0
        run_row = None
        if args.record_backfill:
            if not ingester:
                logger.error("--record-backfill requires a writable database client")
                sys.exit(1)
            run_row = upsert_backfill_run(
                ingester.supabase,
                run_key=run_key,
                tids_path=tids_path,
                batch_size=args.batch_size,
                total_tournaments=len(tids),
                total_batches=len(batches),
                start_date=start_dt.date().isoformat() if start_dt else None,
                end_date=end_dt.date().isoformat() if end_dt else None,
                status="running",
            )
            if not run_row:
                logger.error("Failed to initialize ingestion_backfill_runs row")
                sys.exit(1)

        for batch_index, batch_tids in selected_batches:
            batch_start = batch_index * args.batch_size
            batch_end = batch_start + len(batch_tids) - 1
            logger.info(
                f"Processing batch {batch_index + 1}/{len(batches)} "
                f"(batch_index={batch_index}, tids={batch_start}-{batch_end})"
            )
            if args.record_backfill and run_row:
                upsert_backfill_batch(
                    ingester.supabase,
                    run_id=run_row["id"],
                    batch_index=batch_index,
                    batch_start=batch_start,
                    batch_end=batch_end,
                    tournament_count=len(batch_tids),
                    status="running",
                )
                append_backfill_event(
                    ingester.supabase,
                    run_id=run_row["id"],
                    batch_index=batch_index,
                    event_type="batch_started",
                    payload={
                        "batch_start": batch_start,
                        "batch_end": batch_end,
                        "tournament_count": len(batch_tids),
                    },
                )
                update_backfill_run_progress(
                    ingester.supabase,
                    run_row=run_row,
                    processed_count=processed_count,
                    succeeded_count=succeeded_count,
                    failed_count=failed_count,
                    status="running",
                    current_batch_index=batch_index,
                    current_batch_processed_count=0,
                    current_batch_succeeded_count=0,
                    current_batch_failed_count=0,
                )

            batch_failed = False
            batch_error_text = None
            batch_processed_count = 0
            batch_succeeded_count = 0
            batch_failed_count = 0
            for tid in batch_tids:
                processed_count += 1
                batch_processed_count += 1
                if args.record_backfill and run_row:
                    append_backfill_event(
                        ingester.supabase,
                        run_id=run_row["id"],
                        batch_index=batch_index,
                        tid=tid,
                        event_type="fetch_started",
                    )
                    update_backfill_run_progress(
                        ingester.supabase,
                        run_row=run_row,
                        processed_count=processed_count,
                        succeeded_count=succeeded_count,
                        failed_count=failed_count,
                        status="running",
                        current_batch_index=batch_index,
                        current_tid=tid,
                        current_batch_processed_count=batch_processed_count,
                        current_batch_succeeded_count=batch_succeeded_count,
                        current_batch_failed_count=batch_failed_count,
                    )
                try:
                    tournament = topdeck.get_tournament(tid)
                except Exception as e:
                    failed_count += 1
                    batch_failed_count += 1
                    batch_failed = True
                    batch_error_text = f"fetch {tid}: {e}"
                    logger.error(f"Failed to fetch {tid}: {e}")
                    if args.record_backfill and run_row:
                        append_backfill_event(
                            ingester.supabase,
                            run_id=run_row["id"],
                            batch_index=batch_index,
                            tid=tid,
                            event_type="fetch_failed",
                            payload={"error": str(e)},
                        )
                        update_backfill_run_progress(
                            ingester.supabase,
                            run_row=run_row,
                            processed_count=processed_count,
                            succeeded_count=succeeded_count,
                            failed_count=failed_count,
                            status="running",
                            current_batch_index=batch_index,
                            current_tid=tid,
                            last_completed_tid=tid,
                            current_batch_processed_count=batch_processed_count,
                            current_batch_succeeded_count=batch_succeeded_count,
                            current_batch_failed_count=batch_failed_count,
                        )
                    if args.stop_on_error:
                        break
                    continue

                tournament["TID"] = tid
                ts = parse_tournament_start_date(tournament)
                if ts is None:
                    logger.warning(f"Skipping {tid}: missing start date")
                    if args.record_backfill and run_row:
                        append_backfill_event(
                            ingester.supabase,
                            run_id=run_row["id"],
                            batch_index=batch_index,
                            tid=tid,
                            event_type="tournament_skipped",
                            payload={"reason": "missing start date"},
                        )
                        update_backfill_run_progress(
                            ingester.supabase,
                            run_row=run_row,
                            processed_count=processed_count,
                            succeeded_count=succeeded_count,
                            failed_count=failed_count,
                            status="running",
                            current_batch_index=batch_index,
                            current_tid=tid,
                            last_completed_tid=tid,
                            current_batch_processed_count=batch_processed_count,
                            current_batch_succeeded_count=batch_succeeded_count,
                            current_batch_failed_count=batch_failed_count,
                        )
                    continue

                if start_dt and ts.date() < start_dt.date():
                    logger.info(f"Skipping {tid}: before start-date filter")
                    if args.record_backfill and run_row:
                        append_backfill_event(
                            ingester.supabase,
                            run_id=run_row["id"],
                            batch_index=batch_index,
                            tid=tid,
                            event_type="tournament_skipped",
                            payload={"reason": "before start-date filter"},
                        )
                        update_backfill_run_progress(
                            ingester.supabase,
                            run_row=run_row,
                            processed_count=processed_count,
                            succeeded_count=succeeded_count,
                            failed_count=failed_count,
                            status="running",
                            current_batch_index=batch_index,
                            current_tid=tid,
                            last_completed_tid=tid,
                            current_batch_processed_count=batch_processed_count,
                            current_batch_succeeded_count=batch_succeeded_count,
                            current_batch_failed_count=batch_failed_count,
                        )
                    continue
                if end_dt and ts.date() > end_dt.date():
                    logger.info(f"Skipping {tid}: after end-date filter")
                    if args.record_backfill and run_row:
                        append_backfill_event(
                            ingester.supabase,
                            run_id=run_row["id"],
                            batch_index=batch_index,
                            tid=tid,
                            event_type="tournament_skipped",
                            payload={"reason": "after end-date filter"},
                        )
                        update_backfill_run_progress(
                            ingester.supabase,
                            run_row=run_row,
                            processed_count=processed_count,
                            succeeded_count=succeeded_count,
                            failed_count=failed_count,
                            status="running",
                            current_batch_index=batch_index,
                            current_tid=tid,
                            last_completed_tid=tid,
                            current_batch_processed_count=batch_processed_count,
                            current_batch_succeeded_count=batch_succeeded_count,
                            current_batch_failed_count=batch_failed_count,
                        )
                    continue

                if ingester:
                    try:
                        if args.record_backfill and run_row:
                            append_backfill_event(
                                ingester.supabase,
                                run_id=run_row["id"],
                                batch_index=batch_index,
                                tid=tid,
                                event_type="process_started",
                            )
                        result = ingester.process_tournament(tournament)
                        if result:
                            succeeded_count += 1
                            batch_succeeded_count += 1
                            logger.info(f"Processed: {result['name']}")
                            if args.record_backfill and run_row:
                                last_success_at = utc_now_iso()
                                append_backfill_event(
                                    ingester.supabase,
                                    run_id=run_row["id"],
                                    batch_index=batch_index,
                                    tid=tid,
                                    event_type="process_succeeded",
                                    payload=result,
                                )
                                update_backfill_run_progress(
                                    ingester.supabase,
                                    run_row=run_row,
                                    processed_count=processed_count,
                                    succeeded_count=succeeded_count,
                                    failed_count=failed_count,
                                    status="running",
                                    current_batch_index=batch_index,
                                    current_tid=tid,
                                    last_completed_tid=tid,
                                    current_batch_processed_count=batch_processed_count,
                                    current_batch_succeeded_count=batch_succeeded_count,
                                    current_batch_failed_count=batch_failed_count,
                                    last_success_at=last_success_at,
                                    heartbeat_at=last_success_at,
                                )
                    except Exception as e:
                        failed_count += 1
                        batch_failed_count += 1
                        batch_failed = True
                        batch_error_text = f"process {tid}: {e}"
                        logger.error(f"Failed to process {tid}: {e}")
                        if args.record_backfill and run_row:
                            append_backfill_event(
                                ingester.supabase,
                                run_id=run_row["id"],
                                batch_index=batch_index,
                                tid=tid,
                                event_type="process_failed",
                                payload={"error": str(e)},
                            )
                            update_backfill_run_progress(
                                ingester.supabase,
                                run_row=run_row,
                                processed_count=processed_count,
                                succeeded_count=succeeded_count,
                                failed_count=failed_count,
                                status="running",
                                current_batch_index=batch_index,
                                current_tid=tid,
                                last_completed_tid=tid,
                                current_batch_processed_count=batch_processed_count,
                                current_batch_succeeded_count=batch_succeeded_count,
                                current_batch_failed_count=batch_failed_count,
                            )
                        if args.stop_on_error:
                            break
                else:
                    logger.info(f"Would process: {tournament.get('tournamentName')} ({len(tournament.get('standings', []))} players)")

            if args.record_backfill and run_row:
                append_backfill_event(
                    ingester.supabase,
                    run_id=run_row["id"],
                    batch_index=batch_index,
                    event_type="batch_failed" if batch_failed else "batch_completed",
                    payload={
                        "processed_count": batch_processed_count,
                        "succeeded_count": batch_succeeded_count,
                        "failed_count": batch_failed_count,
                        "error_text": batch_error_text,
                    },
                )
                upsert_backfill_batch(
                    ingester.supabase,
                    run_id=run_row["id"],
                    batch_index=batch_index,
                    batch_start=batch_start,
                    batch_end=batch_end,
                    tournament_count=len(batch_tids),
                    status="failed" if batch_failed else "completed",
                    error_text=batch_error_text,
                )
                update_backfill_run_progress(
                    ingester.supabase,
                    run_row=run_row,
                    processed_count=processed_count,
                    succeeded_count=succeeded_count,
                    failed_count=failed_count,
                    status="running",
                    current_batch_index=batch_index,
                    current_tid=None,
                    current_batch_processed_count=batch_processed_count,
                    current_batch_succeeded_count=batch_succeeded_count,
                    current_batch_failed_count=batch_failed_count,
                )

            if batch_failed and args.stop_on_error:
                break

        if args.record_backfill and run_row:
            final_status = "completed_with_errors" if failed_count else "completed"
            update_backfill_run_progress(
                ingester.supabase,
                run_row=run_row,
                processed_count=processed_count,
                succeeded_count=succeeded_count,
                failed_count=failed_count,
                status=final_status,
                current_batch_index=None,
                current_tid=None,
                current_batch_processed_count=0,
                current_batch_succeeded_count=0,
                current_batch_failed_count=0,
            )
    else:
        if args.start_date:
            start_dt = date_parser.parse(args.start_date)
            end_dt = date_parser.parse(args.end_date) if args.end_date else datetime.utcnow()
            if end_dt < start_dt:
                logger.error("--end-date must be on or after --start-date")
                sys.exit(1)
            days_back = (datetime.utcnow() - start_dt).days + 1
            logger.info(
                f"Backfill range: {start_dt.date()} to {end_dt.date()} ({days_back} days lookback)"
            )
            tournaments = topdeck.search_tournaments(
                days=days_back, min_players=args.min_players
            )
            tournaments = [
                t
                for t in tournaments
                if (ts := parse_tournament_start_date(t)) is not None
                and ts.date() >= start_dt.date()
                and ts.date() <= end_dt.date()
            ]
            logger.info(f"{len(tournaments)} tournaments after date filtering")
        else:
            tournaments = topdeck.search_tournaments(
                days=args.days, min_players=args.min_players
            )

        for t in tournaments:
            if ingester:
                try:
                    result = ingester.process_tournament(t)
                    if result:
                        logger.info(f"Processed: {result['name']}")
                except Exception as e:
                    logger.error(f"Failed to process {t.get('tournamentName')}: {e}")
            else:
                logger.info(f"Would process: {t.get('tournamentName')} ({len(t.get('standings', []))} players)")

    # Cleanup direct Postgres connection
    if args.direct and db_client:
        db_client.close()
        logger.info("Closed direct Postgres connection")

    logger.info("Ingestion complete")


if __name__ == "__main__":
    main()
