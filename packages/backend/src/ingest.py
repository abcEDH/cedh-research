#!/usr/bin/env python3
"""
cEDH Analytics Data Ingestion Pipeline

Fetches tournament data from TopDeck.gg API and loads into Supabase.
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime
from typing import Any

import requests
from dateutil import parser as date_parser

# Optional: psycopg2 for direct connection
try:
    import psycopg2
    import psycopg2.extras

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


# TopDeck API constants
TOPDECK_API_BASE = "https://api.topdeck.gg/v2"
TOPDECK_STANDING_RATE_FIELDS = [
    ("primaryWinRate", "opponentWinRate"),
    ("primaryWinRateElo", "opponentWinRateElo"),
    ("primaryWinRateO", "opponentWinRateO"),
    ("winRate", "opponentWinRate"),
    ("successRate", "opponentSuccessRate"),
]


# Supabase constants
SUPABASE_REST_BASE = "https://msjjihqbxtgjdtapywrj.supabase.co"


from pathlib import Path

# Ensure logs directory exists
_log_dir = Path(__file__).parent.parent.parent / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_log_dir / "ingest.log"),
    ],
)
logger = logging.getLogger(__name__)


def normalize_rate_value(value: Any) -> float | None:
    """Normalize TopDeck rate fields to a 0-1 float."""
    if value is None or value == "":
        return None

    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return None

    if normalized < 0:
        return None
    if normalized > 1:
        normalized = normalized / 100
    if normalized > 1:
        return None

    return normalized


def extract_standing_rates(standing: dict[str, Any]) -> tuple[float | None, float | None]:
    """Extract normalized win rates from a standing record.

    Scans TOPDECK_STANDING_RATE_FIELDS for non-empty primary and opponent rates,
    returning them as floats in [0, 1]. If no rate is found for a category, returns
    None for that slot.
    """
    primary_rate: float | None = None
    for primary_rate_key, _ in TOPDECK_STANDING_RATE_FIELDS:
        primary_rate = normalize_rate_value(standing.get(primary_rate_key))
        if primary_rate is not None:
            break

    opponent_rate: float | None = None
    for _, opponent_rate_key in TOPDECK_STANDING_RATE_FIELDS:
        opponent_rate = normalize_rate_value(standing.get(opponent_rate_key))
        if opponent_rate is not None:
            break

    return primary_rate, opponent_rate


def clean_commander_card_name(name: str) -> str:
    """Strip set indicator suffix and normalize commander card names."""
    if not name:
        return ""
    return name.split("[")[0].strip()


def normalize_region_name(
    state: str | None,
    city: str | None = None,
    country: str | None = None,
    venue: str | None = None,
) -> str | None:
    """Normalize state/region name for consistent regional Elo grouping.

    Args:
        state: Raw state/province name from TopDeck
        city: City name
        country: Country name
        venue: Venue name

    Returns:
        Normalized state name or None
    """
    if not state:
        return None

    normalized = state.upper().strip()

    # Known state abbreviations and alternate spellings
    state_normalizations = {
        "ALBERTA": "AB",
        "ANDALUCÍA": "ANDALUSIA",
        "ANDALUCIA": "ANDALUSIA",
        "ARAGÓN": "ARAGON",
        "ARAGON": "ARAGON",
        "AUCKLAND": "AUCKLAND",
        "BADA WURTTEMBERG": "BADEN-WURTTEMBERG",
        "BADA-WURTTEMBERG": "BADEN-WURTTEMBERG",
        "BADEN-WURTTEMBERG": "BADEN-WURTTEMBERG",
        "BADEN-WÜRTTEMBERG": "BADEN-WURTTEMBERG",
        "BAVARIA": "BAYERN",
        "BAYERN": "BAYERN",
        "BERLIN": "BERLIN",
        "BOGOTA": "BOGOTA",
        "BOGOTÁ": "BOGOTA",
        "BRITISH COLUMBIA": "BC",
        "BRITISH COLUMBIA, CANADA": "BC",
        "CITY OF": "",
        "CONNECTICUT": "CT",
        "D.C.": "DC",
        "D.C": "DC",
        "D.C., US": "DC",
        "DISTRICT OF COLUMBIA": "DC",
        "ENGLAND": "ENGLAND",
        "FLEVOLAND": "FLEVOLAND",
        "FLORIDA": "FL",
        "GELDERLAND": "GELDERLAND",
        "GEORGIA": "GA",
        "GIRALTAR": "GIBRALTAR",
        "GÜELL": "GIRONA",
        "HAUTE GARONNE": "HAUTE-GARONNE",
        "HAUTE-GARONNE": "HAUTE-GARONNE",
        "ILLINOIS": "IL",
        "INDIANA": "IN",
        "KANSAS": "KS",
        "KENTUCKY": "KY",
        "LIMBURG": "LIMBURG",
        "LOUISIANA": "LA",
        "MARYLAND": "MD",
        "MASSACHUSETTS": "MA",
        "MICHIGAN": "MI",
        "MINNESOTA": "MN",
        "MISSOURI": "MO",
        "MORAVIAN-SILESIAN REGION": "MORAVIAN-SILESIAN",
        "NEBRASKA": "NE",
        "NEVADA": "NV",
        "NEW BRUNSWICK": "NB",
        "NEW JERSEY": "NJ",
        "NEW SOUTH WALES": "NSW",
        "NEW YORK": "NY",
        "NEW ZEALAND": "NZ",
        "NORTH CAROLINA": "NC",
        "NORTH RHINE-WESTPHALIA": "NORTH RHINE-WESTPHALIA",
        "NORTH RHINE-WESTPHALIA, GERMANY": "NORTH RHINE-WESTPHALIA",
        "NORTHERN TERRITORY": "NT",
        "NORTHWEST TERRITORIES": "NT",
        "NOTthing": "NOTTINGHAM",
        "NOTTINGHAMSHIRE": "NOTTINGHAM",
        "NOTTM": "NOTTINGHAM",
        "NOUVEAU BRUNSWICK": "NB",
        "ONTARIO": "ON",
        "OREGON": "OR",
        "PENNSYLVANIA": "PA",
        "PÉRDUES": "PORDIMON",
        "PRAGUE": "PRAGUE",
        "PRAGUE CITY": "PRAGUE",
        "PROVINCE OF": "",
        "QUEBEC": "QC",
        "QUEENSLAND": "QLD",
        "RÉPUBLIQUE TCHÈQUE": "CZ",
        "REGION OF": "",
        "RHONE": "RHONE",
        "SAARLAND": "SAARLAND",
        "SASKATCHEWAN": "SK",
        "SCOTLAND": "SCT",
        "SHIKOKU": "SHIKOKU",
        "SICILY": "SICILY",
        "SICH": "SICILY",
        "SINGAPORE": "SG",
        "SOUTH AUSTRALIA": "SA",
        "SOUTH CAROLINA": "SC",
        "SOUTH ENGLAND": "SOUTH ENGLAND",
        "SPAIN": "SPAIN",
        "STATE OF": "",
        "SWEDEN": "SWEDEN",
        "TERritory OF": "",
        "TEXAS": "TX",
        "THE NETHERLANDS": "NETHERLANDS",
        "THE NETHERLANDS, NL": "NETHERLANDS",
        "THURINGIA": "THURINGIA",
        "TOkyo": "TOKYO",
        "Tasmania": "TAS",
        "UNDEFINED": None,
        "UNIFIED TERRITORIES": "NT",
        "UNITED KINGDOM": "UK",
        "UTRECHT": "UTRECHT",
        "UTRECHT, NETHERLANDS": "UTRECHT",
        "UTTAR PRADESH": "UP",
        "VALENCIANA": "VALENCIA",
        "VICTORIA": "VIC",
        "VIRGINIA": "VA",
        "WASHINGTON": "WA",
        "WEST AUSTRALIA": "WA",
        "WEST MIDLANDS": "WEST MIDLANDS",
        "WEST VIRGINIA": "WV",
        "WISCONSIN": "WI",
        "WYOMING": "WY",
        "YUKON": "YT",
    }

    # Direct match
    if normalized in state_normalizations:
        result = state_normalizations[normalized]
        if result is None or result == "":
            return None
        return result

    # Partial match for composite names
    for key, value in state_normalizations.items():
        if key in normalized or normalized in key:
            if value is None or value == "":
                return None
            return value

    # Return as-is if no normalization needed
    return normalized


class TopDeckClient:
    """Client for TopDeck.gg API v2."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = TOPDECK_API_BASE

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_payload: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Make an authenticated request to the TopDeck API."""
        if max_retries <= 0:
            return None
        headers = {"Authorization": f"Bearer {self.api_key}"}

        for attempt in range(max_retries):
            try:
                if method == "GET":
                    response = requests.get(url, headers=headers, timeout=30)
                elif method == "POST":
                    response = requests.post(
                        url, json=json_payload, headers=headers, timeout=30
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if response.status_code >= 400:
                    logger.error(f"TopDeck API error: {response.text}")
                    response.raise_for_status()

                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Request failed, retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} retries: {e}")
                    raise

        return None

    def search_tournaments(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        min_players: int = 16,
    ) -> list[dict[str, Any]]:
        """Search for tournaments within a date range."""
        params = {"pageSize": 100}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        url = f"{self.base_url}/tournaments"
        response = self._request("POST", url, json_payload=params)

        tournaments = response.get("tournaments", [])
        logger.info(
            f"Found {len(tournaments)} tournaments in search (min {min_players} players)"
        )

        return [
            t
            for t in tournaments
            if t.get("playerCount", 0) >= min_players
            or t.get("players", []) is not None
            and len(t.get("players", [])) >= min_players
        ]

    def get_tournament(self, tid: str) -> dict[str, Any]:
        """Get detailed tournament data including standings."""
        url = f"{self.base_url}/tournaments/{tid}"
        return self._request("GET", url)


class SupabaseClient:
    """Client for Supabase REST API."""

    def __init__(self, url: str, service_key: str):
        self.url = url
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any] | None:
        """Upsert data into a table with retry logic."""
        endpoint = f"{self.url}/rest/v1/{table}"

        headers = self.headers.copy()
        if on_conflict:
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        params: dict[str, str] = {}
        if on_conflict:
            params["on_conflict"] = on_conflict

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    endpoint, json=data, headers=headers, params=params, timeout=30
                )
                if response.status_code >= 400:
                    logger.error(f"Supabase error: {response.text}")
                    response.raise_for_status()
                return response.json()
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout,
            ) as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Connection error, retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} retries: {e}")
                    raise

        return None

    def select(
        self, table: str, filters: dict[str, str] | None = None, max_retries: int = 8
    ) -> list[dict[str, Any]]:
        """Select data from a table with retry logic."""
        endpoint = f"{self.url}/rest/v1/{table}"
        params = filters or {}

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    endpoint, headers=self.headers, params=params, timeout=60
                )
                if response.status_code >= 500:
                    raise requests.exceptions.HTTPError(
                        f"{response.status_code} Server Error", response=response
                    )
                response.raise_for_status()
                return response.json()
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.HTTPError,
            ) as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Query failed, retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Query failed after {max_retries} retries: {e}")
                    raise


class DirectPostgresClient:
    """Client for direct Postgres connection using psycopg2 (faster for large batches)."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self._conn = None

    def connect(self):
        """Establish database connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.db_url)

    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()

    def upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str | None = None,
    ) -> list[dict[str, Any]]:
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

        self.connect()
        with self._conn.cursor() as cursor:
            psycopg2.extras.execute_values(
                cursor, sql, [(tuple(d.values()) for d in data)], page_size=1000
            )
            self._conn.commit()
            results = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            return [dict(zip(col_names, row)) for row in results]

    def select(
        self, table: str, filters: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """Select data from a table."""
        self.connect()

        where_clauses: list[str] = []
        params: list[Any] = []

        if filters:
            for col, val in filters.items():
                if val.startswith("eq."):
                    where_clauses.append(f"{col} = %s")
                    params.append(val[3:])
                elif val.startswith("ilike."):
                    where_clauses.append(f"{col} ILIKE %s")
                    params.append(val[6:])

        sql = f"SELECT * FROM {table}"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
            if not results:
                return []
            col_names = [desc[0] for desc in cursor.description]
            return [dict(zip(col_names, row)) for row in results]


def extract_commanders(decklist: str) -> list[str]:
    """Extract commander names from a decklist.

    Parses the ~Commanders~~ section to extract partner commanders.
    Returns a list of commander names (usually 1, or 2 for partner pairs).
    """
    if not decklist:
        return []

    commanders: list[str] = []
    in_commanders = False

    for line in decklist.split("\n"):
        line = line.strip()

        # Detect commander section
        if "~~Commanders~~" in line or "~~COMMANDERS~~" in line or "Commanders" in line:
            in_commanders = True
            continue

        # Stop at next section
        if in_commanders and line.startswith("~"):
            break

        if in_commanders and line:
            # Remove quantity prefix (e.g., "1 Commander Name" -> "Commander Name")
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[0].isdigit():
                commanders.append(parts[1].strip())
            elif len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                # Partner pair like "1 Tymna the Weaver"
                commanders.append(parts[1] + " " + parts[2])
            else:
                commanders.append(line)

    return [clean_commander_card_name(c) for c in commanders if c]


def normalize_commander_name(commanders: list[str]) -> str:
    """Normalize commander pair name for consistent matching.

    Sorts partner commander names alphabetically to ensure consistent ordering.
    Single commanders are returned as-is.
    """
    if not commanders:
        return ""
    return " / ".join(sorted(commanders))


class DataIngester:
    """Main ingestion orchestrator."""

    def __init__(
        self,
        topdeck: TopDeckClient,
        supabase: SupabaseClient,
        min_players: int = 16,
    ):
        self.topdeck = topdeck
        self.supabase = supabase
        self.min_players = min_players
        self.commander_cache: dict[str, str] = {}  # name -> id
        self.player_cache: dict[str, str] = {}  # topdeck_id -> id

    def get_or_create_commander(
        self, name: str, commander_names: list[str]
    ) -> str | None:
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
            "commander_names": [
                clean_commander_card_name(value) for value in (commander_names or [name])
            ],
        }
        result = self.supabase.upsert("commanders", data, on_conflict="name")
        if result:
            self.commander_cache[name] = result[0]["id"]
            return result[0]["id"]
        return None

    def get_or_create_player(self, topdeck_id: str, name: str) -> str | None:
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

    def batch_upsert_commanders(
        self, commander_data: dict[str, list[str]]
    ) -> dict[str, str]:
        """Batch upsert commanders and return name -> id mapping."""
        if not commander_data:
            return {}

        data = [
            {"name": name, "commander_names": names}
            for name, names in commander_data.items()
        ]

        result = self.supabase.upsert("commanders", data, on_conflict="name")
        if not result:
            logger.error("Failed to batch upsert commanders")
            return {}

        return {r["name"]: r["id"] for r in result}

    def batch_upsert_players(self, player_data: dict[str, str]) -> dict[str, str]:
        """Batch upsert players and return topdeck_id -> id mapping."""
        if not player_data:
            return {}

        data = [{"topdeck_id": tid, "name": name} for tid, name in player_data.items()]

        result = self.supabase.upsert("players", data, on_conflict="topdeck_id")
        if not result:
            logger.error("Failed to batch upsert players")
            return {}

        return {r["topdeck_id"]: r["id"] for r in result}

    def batch_upsert_entries(
        self, entries: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Batch upsert tournament entries and return topdeck entry id -> db id mapping."""
        if not entries:
            return {}

        result = self.supabase.upsert(
            "tournament_entries", entries, on_conflict="topdeck_entry_id"
        )
        if not result:
            logger.error("Failed to batch upsert tournament entries")
            return {}

        return {r["topdeck_entry_id"]: r["id"] for r in result}

    def process_tournament(self, tournament: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single tournament and ingest all data.

        Args:
            tournament: Tournament data from TopDeck API

        Returns:
            Result summary or None on failure
        """
        tid = tournament.get("id")
        name = tournament.get("name", "Unknown Tournament")
        rounds = tournament.get("rounds", [])
        standings = tournament.get("standings", [])
        start_date = tournament.get("startDate")
        player_count = len(standings)
        swiss_rounds = tournament.get("swissNum", 0)
        reported_top_cut = tournament.get("topCut", 0)
        effective_top_cut = reported_top_cut
        if player_count <= 34:
            effective_top_cut = 4

        # Skip if too few players
        if player_count < self.min_players:
            logger.info(
                f"Skipping {name}: only {player_count} players (min: {self.min_players})"
            )
            return None

        logger.info(
            f"Processing: {name} ({player_count} players, {len(rounds)} rounds)"
        )

        # Convert timestamp to ISO format
        if isinstance(start_date, (int, float)):
            start_date = datetime.fromtimestamp(start_date).isoformat()

        # Get location data
        event_data = tournament.get("eventData", {})

        # Upsert tournament
        tournament_data: dict[str, Any] = {
            "topdeck_tid": tid,
            "name": name,
            "start_date": start_date,
            "player_count": player_count,
            "swiss_rounds": swiss_rounds,
            "top_cut": effective_top_cut,
            "average_elo": (
                int(tournament.get("averageElo"))
                if tournament.get("averageElo")
                else None
            ),
            "median_elo": (
                int(tournament.get("medianElo"))
                if tournament.get("medianElo")
                else None
            ),
            "top_elo": (
                int(tournament.get("topElo")) if tournament.get("topElo") else None
            ),
            "city": event_data.get("city"),
            "state": normalize_region_name(
                event_data.get("state"),
                city=event_data.get("city"),
                country=event_data.get("country"),
                venue=event_data.get("location"),
            ),
            "venue": event_data.get("location"),
            "latitude": event_data.get("lat"),
            "longitude": event_data.get("lng"),
            "header_image_url": event_data.get("headerImage"),
        }

        result = self.supabase.upsert(
            "tournaments", tournament_data, on_conflict="topdeck_tid"
        )
        if not result:
            logger.error(f"Failed to upsert tournament: {tid}")
            return None

        tournament_id = result[0]["id"]
        logger.info(f"Tournament ID: {tournament_id}")

        # === BATCH PROCESSING: Pre-process all data first ===
        total_players = len(standings)
        logger.info(f"Pre-processing {total_players} players...")

        # Step 1: Extract all unique commanders and players (local processing)
        commander_data: dict[str, list[str]] = {}  # name -> [individual_commander_names]
        player_data: dict[str, str] = {}  # topdeck_id -> name
        standing_info: list[dict[str, Any]] = (
            []
        )  # [{idx, topdeck_id, commander_name, decklist, ...}]

        for idx, standing in enumerate(standings):
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
            standing_info.append(
                {
                    "idx": idx,
                    "topdeck_id": player_topdeck_id,
                    "name": player_name,
                    "commander_name": commander_name,
                    "decklist": decklist,
                    "rank": standing.get("rank"),
                    "points": standing.get("points"),
                    "omw": standing.get("omw"),
                    "gw": standing.get("gw"),
                    "pgw": standing.get("pgw"),
                }
            )

        # Step 2: Batch upsert commanders
        logger.info(f"Upserting {len(commander_data)} unique commanders...")
        commander_id_map = self.batch_upsert_commanders(commander_data)
        self.commander_cache.update(commander_id_map)

        # Step 3: Batch upsert players
        logger.info(f"Upserting {len(player_data)} unique players...")
        player_id_map = self.batch_upsert_players(player_data)
        self.player_cache.update(player_id_map)

        # Step 4: Build entry records
        entries: list[dict[str, Any]] = []
        for info in standing_info:
            commander_id = commander_id_map.get(info["commander_name"])
            player_id = player_id_map.get(info["topdeck_id"])

            if not commander_id or not player_id:
                logger.warning(
                    f"Missing commander or player for standing {info['idx']}: "
                    f"commander={commander_id}, player={player_id}"
                )
                continue

            primary_rate, opponent_rate = extract_standing_rates(info)

            entry = {
                "tournament_id": tournament_id,
                "player_id": player_id,
                "commander_id": commander_id,
                "rank": info["rank"],
                "points": info["points"],
                "omw": info["omw"],
                "gw": info["gw"],
                "pgw": info["pgw"],
                "primary_win_rate": primary_rate,
                "opponent_win_rate": opponent_rate,
                "decklist_text": info["decklist"],
                "topdeck_entry_id": f"{tid}_{info['topdeck_id']}",
            }
            entries.append(entry)

        # Step 5: Batch upsert entries
        logger.info(f"Upserting {len(entries)} tournament entries...")
        entry_id_map = self.batch_upsert_entries(entries)

        # Step 6: Process game results
        games_processed = 0
        entries_by_rank = sorted(
            [
                (
                    e,
                    entry_id_map.get(e.get("topdeck_entry_id")),
                    e.get("rank", 999),
                )
                for e in entries
            ],
            key=lambda x: x[2],
        )

        # Process each round
        for round_data in rounds:
            round_num = round_data.get("round", 0)
            tables = round_data.get("tables", [])

            for table in tables:
                table_num = table.get("table", 0)
                game_id = f"{tid}_R{round_num}_T{table_num}"
                seats = table.get("seats", [])

                # Build game participants map
                participant_map: dict[int, dict[str, Any]] = {}
                for seat in seats:
                    seat_num = seat.get("seat", 0)
                    entry_id = seat.get("entryId")
                    # Find the entry by topdeck_entry_id
                    for e, db_id, _ in entries_by_rank:
                        if e.get("topdeck_entry_id") == entry_id:
                            participant_map[seat_num] = {
                                "entry_id": db_id,
                                "standing": e,
                            }
                            break

                # Process results
                results = table.get("results", [])
                for result in results:
                    winner_seats = result.get("winners", [])
                    draws = result.get("draws", [])

                    # Get winner/loser IDs
                    winner_ids = [
                        participant_map[s]["entry_id"]
                        for s in winner_seats
                        if s in participant_map and participant_map[s].get("entry_id")
                    ]
                    loser_seats = [
                        s for s in participant_map.keys() if s not in winner_seats and s not in draws
                    ]

                    if not winner_ids:
                        continue

                    # Create game record
                    game_record = {
                        "tournament_id": tournament_id,
                        "game_id": game_id,
                        "round": round_num,
                        "table_number": table_num,
                        "winners": winner_ids,
                    }

                    # Upsert game
                    try:
                        game_result = self.supabase.upsert(
                            "games", game_record, on_conflict="game_id"
                        )
                        if game_result:
                            games_processed += 1

                            # Create participant records
                            for seat_num, participant in participant_map.items():
                                entry_id = participant.get("entry_id")
                                if not entry_id:
                                    continue

                                is_winner = seat_num in winner_seats
                                is_draw = seat_num in draws

                                standing = participant.get("standing", {})
                                primary_rate, opponent_rate = extract_standing_rates(standing)

                                participant_record = {
                                    "game_id": game_result[0]["id"],
                                    "entry_id": entry_id,
                                    "seat_position": seat_num,
                                    "won": is_winner,
                                    "draw": is_draw,
                                    "primary_win_rate": primary_rate,
                                    "opponent_win_rate": opponent_rate,
                                }
                                self.supabase.upsert(
                                    "game_participants", participant_record
                                )
                    except Exception as e:
                        logger.warning(f"Failed to upsert game {game_id}: {e}")

        logger.info(
            f"Completed {name}: {len(entries)} entries, {games_processed} games"
        )
        return {
            "tournament_id": tournament_id,
            "entries": len(entries),
            "games": games_processed,
        }


def parse_tournament_start_date(tournament: dict[str, Any]) -> datetime | None:
    """Parse tournament start date from various formats."""
    start_date = tournament.get("startDate")
    if not start_date:
        return None

    try:
        if isinstance(start_date, (int, float)):
            return datetime.fromtimestamp(start_date)
        return date_parser.parse(str(start_date))
    except Exception:
        return None


def normalize_tournament_name(name: str) -> str:
    """Normalize tournament name for matching."""
    return name.lower().strip()


def build_game_key(
    tournament_id: str,
    round_num: int,
    table_num: int,
    seat_num: int,
) -> str:
    """Build a unique key for a game."""
    return f"{tournament_id}_R{round_num}_T{table_num}_S{seat_num}"


def extract_name_and_tid(tournament: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract normalized name and tid from a tournament dict."""
    name = tournament.get("name")
    tid = tournament.get("id")
    return (normalize_tournament_name(name) if name else None, tid)


def main():
    """Main entry point for ingestion."""
    parser = argparse.ArgumentParser(description="cEDH Analytics Data Ingestion")
    parser.add_argument(
        "--tournament-id",
        type=str,
        help="TopDeck tournament ID (slug) to ingest",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of recent days to search for tournaments",
    )
    parser.add_argument(
        "--min-players",
        type=int,
        default=16,
        help="Minimum player count for tournaments to include",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct Postgres connection for faster ingestion",
    )

    args = parser.parse_args()

    # Load environment variables
    topdeck_api_key = (
        "dev"  # TODO: Replace with actual key loading from env
    )
    supabase_url = SUPABASE_REST_BASE
    supabase_key = (
        "dev"  # TODO: Replace with actual key loading from env
    )

    # Initialize clients
    topdeck = TopDeckClient(topdeck_api_key)
    supabase = SupabaseClient(supabase_url, supabase_key)

    # Initialize ingester
    ingester = DataIngester(topdeck, supabase, min_players=args.min_players)

    if args.tournament_id:
        # Ingest single tournament
        logger.info(f"Fetching tournament: {args.tournament_id}")
        tournament = topdeck.get_tournament(args.tournament_id)
        ingester.process_tournament(tournament)
    else:
        # Search and ingest recent tournaments
        logger.info(f"Searching for tournaments in the last {args.days} days")
        tournaments = topdeck.search_tournaments(
            start_date=f"{args.days} days ago", min_players=args.min_players
        )
        logger.info(f"Found {len(tournaments)} tournaments to process")

        for tournament in tournaments:
            try:
                ingester.process_tournament(tournament)
            except Exception as e:
                logger.error(f"Failed to process tournament: {e}")


if __name__ == "__main__":
    main()
