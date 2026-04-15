#!/usr/bin/env python3
"""
cEDH Analytics Data Ingestion Pipeline

Fetches tournament data from TopDeck.gg API and loads into Supabase.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
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
TOPDECK_API_BASE = "https://topdeck.gg/api/v2"
TOPDECK_FIRESTORE_PROJECT = "eminence-1b40b"
TOPDECK_FIRESTORE_API_KEY = "AIzaSyBISF4HIfUsepAAqqYHte2NE_L8eaT6iwI"
TOPDECK_STANDING_RATE_FIELDS = [
    ("primaryWinRate", "opponentWinRate"),
    ("primaryWinRateElo", "opponentWinRateElo"),
    ("primaryWinRateO", "opponentWinRateO"),
    ("winRate", "opponentWinRate"),
    ("successRate", "opponentSuccessRate"),
]


def normalize_topdeck_tournament_payload(
    tournament: dict[str, Any],
    tid: str | None = None,
) -> dict[str, Any]:
    """Flatten current TopDeck v2 tournament payloads into the ingester shape."""
    if not isinstance(tournament, dict):
        return tournament

    if isinstance(tournament.get("data"), dict):
        normalized = dict(tournament["data"])
        for key in ("standings", "rounds", "eventData"):
            if key in tournament and key not in normalized:
                normalized[key] = tournament[key]
    else:
        normalized = dict(tournament)

    topdeck_tid = tid or normalized.get("id") or normalized.get("TID")
    if topdeck_tid:
        normalized["id"] = topdeck_tid
        normalized["TID"] = topdeck_tid

    if "name" not in normalized and normalized.get("tournamentName"):
        normalized["name"] = normalized["tournamentName"]

    normalized.setdefault("standings", [])
    normalized.setdefault("rounds", [])
    normalized.setdefault("eventData", {})
    return normalized


# Supabase constants
SUPABASE_REST_BASE = "https://msjjihqbxtgjdtapywrj.supabase.co"

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


def load_local_env() -> None:
    """Load local env files without overriding already-exported variables."""
    for env_path in (Path("packages/backend/.env"), Path(".env"), Path(__file__).resolve().parents[1] / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


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


def should_use_firestore_tournament_fallback(tournament: Any) -> bool:
    """Return true for legacy TopDeck events where v2 returns an empty shell."""
    if not isinstance(tournament, dict):
        return False

    rounds = tournament.get("rounds")
    standings = tournament.get("standings")
    if rounds or standings:
        return False

    data = tournament.get("data")
    if isinstance(data, dict):
        name = data.get("name")
        start_date = data.get("startDate")
        return not start_date or name in (None, "", "Unknown Name")

    return not tournament.get("startDate")


def decode_firestore_value(value: dict[str, Any]) -> Any:
    """Decode Firestore REST typed values into plain Python values."""
    if "stringValue" in value:
        return value["stringValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "booleanValue" in value:
        return value["booleanValue"]
    if "nullValue" in value:
        return None
    if "timestampValue" in value:
        return value["timestampValue"]
    if "arrayValue" in value:
        return [
            decode_firestore_value(item)
            for item in value.get("arrayValue", {}).get("values", [])
        ]
    if "mapValue" in value:
        return {
            key: decode_firestore_value(item)
            for key, item in value.get("mapValue", {}).get("fields", {}).items()
        }
    return None


def firestore_bracket_name(round_data: dict[str, Any]) -> str | None:
    """Map TopDeck's legacy bracket codes to stable round labels."""
    bracket = round_data.get("Bracket")
    if not bracket:
        return None

    bracket_name_map = {
        "Quart": "Quarterfinals",
        "Semi": "Semifinals",
        "Fin": "Finals",
    }
    if bracket in bracket_name_map:
        return bracket_name_map[bracket]
    return f"Top {bracket}" if isinstance(bracket, str) else str(bracket)


def firestore_status(round_data: dict[str, Any], pod: dict[str, Any]) -> str:
    """Normalize legacy round/pod state to the games.status values we store."""
    state = str(round_data.get("State") or "").lower()
    if pod.get("Locked") or state == "complete":
        return "Completed"
    if state == "active":
        return "Active"
    return "Pending"


def firestore_tournament_to_topdeck_payload(
    tid: str, data: dict[str, Any]
) -> dict[str, Any] | None:
    """Convert a legacy TopDeck Firestore tournament document to v2-like data."""
    players = data.get("Players") or {}
    rounds = data.get("Rounds") or []
    config = data.get("Config") or {}
    metadata = data.get("Metadata") or {}

    if not isinstance(players, dict) or not isinstance(rounds, list):
        return None
    if not players and not rounds:
        return None

    standings: list[dict[str, Any]] = []
    for player_id, player in players.items():
        if not isinstance(player, dict):
            continue
        standings.append(
            {
                "id": player_id,
                "name": player.get("name") or player.get("discord") or "Unknown",
                "decklist": player.get("decklist") or "",
                "rank": player.get("standing"),
                "points": player.get("points"),
                "wins": player.get("gamesWon"),
                "draws": player.get("gamesDrawn"),
                "losses": player.get("gamesLost"),
            }
        )
    standings.sort(key=lambda row: row.get("rank") or 999999)

    table_start = config.get("TableStart") or 1
    converted_rounds: list[dict[str, Any]] = []
    swiss_round_count = 0
    for round_index, round_data in enumerate(rounds, start=1):
        if not isinstance(round_data, dict):
            continue

        round_name = firestore_bracket_name(round_data)
        round_value: int | str
        if round_name:
            round_value = round_name
        else:
            swiss_round_count += 1
            round_value = swiss_round_count

        tables: list[dict[str, Any]] = []
        pods = round_data.get("Pods") or []
        if not isinstance(pods, list):
            pods = []
        for pod_index, pod in enumerate(pods):
            if not isinstance(pod, dict):
                continue

            winner = pod.get("Winner")
            winner_id = "Draw" if winner == "_DRAW_" else winner
            pod_players = []
            for player_topdeck_id in pod.get("Players") or []:
                player = players.get(player_topdeck_id) or {}
                pod_players.append(
                    {
                        "id": player_topdeck_id,
                        "name": player.get("name") or player.get("discord") or "Unknown",
                        "decklist": player.get("decklist"),
                    }
                )

            tables.append(
                {
                    "table": table_start + pod_index,
                    "players": pod_players,
                    "winner_id": winner_id,
                    "winner": (
                        None
                        if winner_id in (None, "Draw")
                        else (players.get(winner_id) or {}).get("name")
                    ),
                    "status": firestore_status(round_data, pod),
                }
            )

        converted_rounds.append({"round": round_value, "tables": tables})

    start_date = None
    for round_data in rounds:
        if isinstance(round_data, dict) and round_data.get("StartTime"):
            start_date = int(round_data["StartTime"]) / 1000
            break
    if not start_date:
        start_date = config.get("DateCreated")

    return {
        "id": tid,
        "TID": tid,
        "name": config.get("Name") or metadata.get("Name") or tid,
        "game": metadata.get("Game"),
        "startDate": start_date,
        "swissNum": swiss_round_count,
        "topCut": len(rounds) - swiss_round_count,
        "standings": standings,
        "rounds": converted_rounds,
        "eventData": {},
        "_source": "topdeck_firestore",
    }


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
        headers = {"Authorization": self.api_key}

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

                if response.status_code == 429:
                    retry_after = 60
                    try:
                        retry_after = int(response.json().get("retryAfterSeconds", retry_after))
                    except (TypeError, ValueError, requests.exceptions.JSONDecodeError):
                        pass
                    if attempt < max_retries - 1:
                        wait_time = max(retry_after, 1)
                        logger.warning(
                            f"TopDeck rate limited, retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue

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
    ) -> list[dict[str, Any]]:
        """Search for tournaments within a date range."""
        params: dict[str, Any] = {
            "game": "Magic: The Gathering",
            "format": "EDH",
        }
        if start_date:
            params["start"] = int(date_parser.parse(start_date).timestamp())
        if end_date:
            params["end"] = int(date_parser.parse(end_date).timestamp())

        url = f"{self.base_url}/tournaments"
        response = self._request("POST", url, json_payload=params)

        tournaments = response if isinstance(response, list) else response.get("tournaments", [])
        logger.info(f"Found {len(tournaments)} tournaments in search")

        return [
            normalize_topdeck_tournament_payload(t)
            for t in tournaments
        ]

    def get_tournament(self, tid: str) -> dict[str, Any]:
        """Get detailed tournament data including standings."""
        url = f"{self.base_url}/tournaments/{tid}"
        tournament = normalize_topdeck_tournament_payload(self._request("GET", url), tid=tid)
        if should_use_firestore_tournament_fallback(tournament):
            firestore_tournament = self.get_firestore_tournament(tid)
            if firestore_tournament:
                return firestore_tournament
        return tournament

    def get_firestore_tournament(self, tid: str) -> dict[str, Any] | None:
        """Fetch a legacy bracket tournament from TopDeck's Firestore document."""
        url = (
            "https://firestore.googleapis.com/v1/projects/"
            f"{TOPDECK_FIRESTORE_PROJECT}/databases/(default)/documents/"
            f"tournaments/{tid}?key={TOPDECK_FIRESTORE_API_KEY}"
        )
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            logger.warning(
                f"TopDeck Firestore fallback failed for {tid}: {response.text}"
            )
            response.raise_for_status()

        document = response.json()
        fields = document.get("fields")
        if not isinstance(fields, dict):
            return None

        data = {key: decode_firestore_value(value) for key, value in fields.items()}
        return firestore_tournament_to_topdeck_payload(tid, data)


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
        if max_retries <= 0:
            return None
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
        if max_retries <= 0:
            return []
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
        # This is a safety net; the loop above either returns or raises
        return []


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
    ):
        self.topdeck = topdeck
        self.supabase = supabase
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

        entry_keys_by_player_id = {
            entry["player_id"]: entry.get("topdeck_entry_id")
            for entry in entries
            if entry.get("player_id") and entry.get("topdeck_entry_id")
        }
        db_entries = [
            {k: v for k, v in entry.items() if k != "topdeck_entry_id"}
            for entry in entries
        ]

        result = self.supabase.upsert(
            "tournament_entries", db_entries, on_conflict="tournament_id,player_id"
        )
        if not result:
            logger.error("Failed to batch upsert tournament entries")
            return {}

        entry_id_map: dict[str, str] = {}
        for row in result:
            topdeck_entry_id = entry_keys_by_player_id.get(row.get("player_id"))
            if topdeck_entry_id:
                entry_id_map[topdeck_entry_id] = row["id"]
        return entry_id_map

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
        seen_entry_player_ids: set[str] = set()
        for info in standing_info:
            commander_id = commander_id_map.get(info["commander_name"])
            player_id = player_id_map.get(info["topdeck_id"])

            if not commander_id or not player_id:
                logger.warning(
                    f"Missing commander or player for standing {info['idx']}: "
                    f"commander={commander_id}, player={player_id}"
                )
                continue

            if player_id in seen_entry_player_ids:
                logger.warning(
                    f"Skipping duplicate standing for player {info['topdeck_id']} "
                    f"in tournament {tid}"
                )
                continue
            seen_entry_player_ids.add(player_id)

            primary_rate, opponent_rate = extract_standing_rates(info)

            entry = {
                "tournament_id": tournament_id,
                "player_id": player_id,
                "commander_id": commander_id,
                "final_standing": info["rank"],
                "points": info["points"],
                "win_rate": primary_rate,
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
        entries_by_topdeck_id = {
            e.get("topdeck_entry_id", "").removeprefix(f"{tid}_"): (e, db_id)
            for e, db_id in (
                (entry, entry_id_map.get(entry.get("topdeck_entry_id")))
                for entry in entries
            )
            if e.get("topdeck_entry_id") and db_id
        }
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
            round_value = round_data.get("round")
            round_num = round_value if isinstance(round_value, int) else None
            round_name = None if isinstance(round_value, int) else str(round_value) if round_value else None
            is_bracket = round_num is None
            tables = round_data.get("tables", [])

            for table in tables:
                table_num = table.get("table") or table.get("table_number") or table.get("tableNumber")
                seats = table.get("seats", [])
                players = table.get("players", [])

                # Build game participants map
                participant_map: dict[int, dict[str, Any]] = {}
                if players:
                    for seat_num, player in enumerate(players):
                        player_topdeck_id = player.get("id")
                        entry_pair = entries_by_topdeck_id.get(player_topdeck_id)
                        if entry_pair:
                            standing, db_id = entry_pair
                            participant_map[seat_num] = {
                                "entry_id": db_id,
                                "standing": standing,
                                "topdeck_id": player_topdeck_id,
                            }
                else:
                    for seat in seats:
                        seat_num = seat.get("seat", 0)
                        entry_id = seat.get("entryId")
                        # Find the entry by topdeck_entry_id
                        for e, db_id, _ in entries_by_rank:
                            if e.get("topdeck_entry_id") == entry_id:
                                participant_map[seat_num] = {
                                    "entry_id": db_id,
                                    "standing": e,
                                    "topdeck_id": e.get("topdeck_id"),
                                }
                                break

                if not participant_map:
                    continue

                game_key = build_game_key(tournament_id, round_num, round_name, table_num, is_bracket)
                winner_topdeck_id = table.get("winner_id") or table.get("winnerId")
                uses_topdeck_winner_id = players and (
                    "winner_id" in table or "winnerId" in table
                )

                # Process current TopDeck v2 results.
                if uses_topdeck_winner_id:
                    is_draw = is_draw_winner_id(winner_topdeck_id)
                    winner_player_id = None if is_draw else player_id_map.get(str(winner_topdeck_id))

                    game_record = {
                        "tournament_id": tournament_id,
                        "round_number": round_num,
                        "round_name": round_name,
                        "is_bracket": is_bracket,
                        "table_number": table_num,
                        "status": table.get("status") or "Completed",
                        "is_draw": is_draw,
                        "winner_id": winner_player_id,
                        "game_key": game_key,
                    }

                    try:
                        game_result = self.supabase.upsert(
                            "games", game_record, on_conflict="game_key"
                        )
                        if game_result:
                            games_processed += 1
                            participant_records: list[dict[str, Any]] = []

                            for seat_num, participant in participant_map.items():
                                entry_id = participant.get("entry_id")
                                if not entry_id:
                                    continue

                                is_winner = (
                                    not is_draw
                                    and participant.get("topdeck_id") == winner_topdeck_id
                                )
                                result_text = "draw" if is_draw else "win" if is_winner else "loss"

                                participant_record = {
                                    "game_id": game_result[0]["id"],
                                    "entry_id": entry_id,
                                    "seat_position": seat_num,
                                    "result": result_text,
                                    "points_earned": 1 if is_draw else 5 if is_winner else 0,
                                }
                                participant_records.append(participant_record)
                            if participant_records:
                                self.supabase.upsert(
                                    "game_participants",
                                    participant_records,
                                    on_conflict="game_id,entry_id",
                                )
                    except Exception as e:
                        logger.warning(f"Failed to upsert game {game_key}: {e}")
                    continue

                # Process legacy TopDeck results.
                results = table.get("results", [])
                for result in results:
                    winner_seats = result.get("winners", [])
                    draws = result.get("draws", [])

                    # Get winner/loser IDs
                    winner_entry_ids = [
                        participant_map[s]["entry_id"]
                        for s in winner_seats
                        if s in participant_map and participant_map[s].get("entry_id")
                    ]
                    if not winner_entry_ids and not draws:
                        continue
                    winner_player_id = None
                    if len(winner_seats) == 1 and winner_seats[0] in participant_map:
                        winner_topdeck_id = participant_map[winner_seats[0]].get("topdeck_id")
                        winner_player_id = player_id_map.get(winner_topdeck_id)

                    # Create game record
                    game_record = {
                        "tournament_id": tournament_id,
                        "round_number": round_num,
                        "round_name": round_name,
                        "is_bracket": is_bracket,
                        "table_number": table_num,
                        "status": table.get("status") or "Completed",
                        "is_draw": bool(draws) and not winner_entry_ids,
                        "winner_id": winner_player_id,
                        "game_key": game_key,
                    }

                    # Upsert game
                    try:
                        game_result = self.supabase.upsert(
                            "games", game_record, on_conflict="game_key"
                        )
                        if game_result:
                            games_processed += 1
                            participant_records: list[dict[str, Any]] = []

                            # Create participant records
                            for seat_num, participant in participant_map.items():
                                entry_id = participant.get("entry_id")
                                if not entry_id:
                                    continue

                                is_winner = seat_num in winner_seats
                                is_draw = seat_num in draws
                                result_text = "draw" if is_draw else "win" if is_winner else "loss"

                                participant_record = {
                                    "game_id": game_result[0]["id"],
                                    "entry_id": entry_id,
                                    "seat_position": seat_num,
                                    "result": result_text,
                                    "points_earned": 1 if is_draw else 5 if is_winner else 0,
                                }
                                participant_records.append(participant_record)
                            if participant_records:
                                self.supabase.upsert(
                                    "game_participants",
                                    participant_records,
                                    on_conflict="game_id,entry_id",
                                )
                    except Exception as e:
                        logger.warning(f"Failed to upsert game {game_key}: {e}")

        logger.info(
            f"Completed {name}: {len(entries)} entries, {games_processed} games"
        )
        return {
            "tournament_id": tournament_id,
            "name": name,
            "topdeck_tid": tid,
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
    round_num: int | None,
    round_name: str | None,
    table_num: int | None,
    is_bracket: bool,
) -> str:
    """Build the canonical game key used by the database trigger."""
    return "|".join(
        [
            tournament_id,
            str(round_num) if round_num is not None else "RNULL",
            round_name if round_name is not None else "RNNULL",
            str(table_num) if table_num is not None else "TNULL",
            str(is_bracket).lower(),
        ]
    )


def is_draw_winner_id(winner_id: Any) -> bool:
    """TopDeck v2 represents drawn pods as winner_id='Draw'."""
    return winner_id is None or str(winner_id).strip().lower() == "draw"


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
        "--stop-on-error",
        action="store_true",
        help="Fail fast instead of continuing to later tournaments after an error in --tids-file mode",
    )
    parser.add_argument("--names-file", type=str, help="Path to file with one tournament name per line")
    parser.add_argument("--resolve-days", type=int, default=120, help="Days back to search when resolving names to IDs")
    parser.add_argument("--tids-out", type=str, help="Write resolved tournament IDs to this file")
    parser.add_argument(
        "--resolve-include-ambiguous",
        action="store_true",
        help="Include all candidate IDs for ambiguous name matches",
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of tournaments to process")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct Postgres connection for faster ingestion",
    )

    args = parser.parse_args()

    # Load environment variables
    load_local_env()
    topdeck_api_key = os.environ.get("TOPDECK_API_KEY")
    supabase_url = os.environ.get("SUPABASE_URL", SUPABASE_REST_BASE)
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not topdeck_api_key or not supabase_key:
        raise SystemExit("TOPDECK_API_KEY and SUPABASE_SERVICE_KEY are required")

    # Initialize clients
    topdeck = TopDeckClient(topdeck_api_key)
    supabase = SupabaseClient(supabase_url, supabase_key)

    # Initialize ingester
    ingester = DataIngester(topdeck, supabase)

    if args.tournament_id:
        # Ingest single tournament
        logger.info(f"Fetching tournament: {args.tournament_id}")
        tournament = topdeck.get_tournament(args.tournament_id)
        tournament["TID"] = args.tournament_id
        if ingester:
            result = ingester.process_tournament(tournament)
            logger.info(f"Result: {result}")
    elif getattr(args, "tids_file", None):
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

        if args.limit > 0 and len(tids) > args.limit:
            logger.info(f"Limiting to {args.limit} tournaments (from {len(tids)})")
            tids = tids[: args.limit]

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
        # Search and ingest recent tournaments
        start_date = (datetime.now() - timedelta(days=args.days)).date().isoformat()
        end_date = datetime.now().date().isoformat()
        logger.info(f"Searching for tournaments from {start_date} through {end_date} ({args.days} days)")
        tournaments = topdeck.search_tournaments(
            start_date=start_date, end_date=end_date
        )
        logger.info(f"Found {len(tournaments)} tournaments to process")

        if args.limit > 0 and len(tournaments) > args.limit:
            logger.info(f"Limiting to {args.limit} tournaments (from {len(tournaments)})")
            tournaments = tournaments[: args.limit]

        for t in tournaments:
            tid = t.get("id") or t.get("TID")
            tournament = t
            if tid:
                tournament = topdeck.get_tournament(tid)
                for key in (
                    "swissNum",
                    "topCut",
                    "averageElo",
                    "medianElo",
                    "topElo",
                    "eventData",
                ):
                    if key not in tournament and key in t:
                        tournament[key] = t[key]
            if ingester:
                try:
                    result = ingester.process_tournament(tournament)
                    if result:
                        logger.info(f"Processed: {result['name']}")
                except Exception as e:
                    logger.error(f"Failed to process {tournament.get('name') or t.get('tournamentName')}: {e}")
            else:
                logger.info(f"Would process: {tournament.get('name')} ({len(tournament.get('standings', []))} players)")

    # Cleanup direct Postgres connection
    if args.direct and db_client:
        db_client.close()
        logger.info("Closed direct Postgres connection")

    logger.info("Ingestion complete")


if __name__ == "__main__":
    main()
