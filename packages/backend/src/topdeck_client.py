"""TopDeck.gg API v2 client and Firestore payload normalizers."""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import requests
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

TOPDECK_API_BASE = "https://topdeck.gg/api/v2"
TOPDECK_FIRESTORE_PROJECT = "eminence-1b40b"


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


def firestore_timestamp_seconds(value: Any) -> int | float | None:
    """Convert Firestore millisecond timestamps to TopDeck's second timestamps."""
    if not isinstance(value, (int, float)):
        return None
    if value > 10_000_000_000:
        return value / 1000
    return value


def normalize_standing_row(standing: dict[str, Any]) -> dict[str, Any]:
    """Preserve current TopDeck standing fields in the legacy ingester shape."""
    normalized = dict(standing)
    normalized["rank"] = standing.get("rank") or standing.get("standing")
    return normalized


def flat_firestore_league_to_topdeck_payload(
    tid: str,
    data: dict[str, Any],
    base_tournament: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Convert TopDeck's flat league bracket document to v2-like data."""
    table_rows: list[tuple[int, int, dict[str, Any]]] = []
    entry_to_player_id: dict[int, str] = {}

    for key, value in data.items():
        table_match = re.fullmatch(r"S(\d+):T(\d+)", key)
        if table_match and isinstance(value, dict):
            table_rows.append((int(table_match.group(1)), int(table_match.group(2)), value))
            continue

        entry_match = re.fullmatch(r"E(\d+):P\d+", key)
        if entry_match and value:
            entry_to_player_id[int(entry_match.group(1))] = str(value)

    if not table_rows or not entry_to_player_id:
        return None

    base_tournament = base_tournament or {}
    base_standings = base_tournament.get("standings") or []
    standing_by_player_id = {
        str(standing.get("id")): normalize_standing_row(standing)
        for standing in base_standings
        if isinstance(standing, dict) and standing.get("id")
    }

    players_by_id: dict[str, dict[str, Any]] = {}
    for player_id in entry_to_player_id.values():
        standing = standing_by_player_id.get(player_id, {})
        players_by_id[player_id] = {
            "id": player_id,
            "name": standing.get("name") or "Unknown",
            "decklist": standing.get("decklist") or "",
        }

    if standing_by_player_id:
        standings = list(standing_by_player_id.values())
        for player_id in players_by_id:
            if player_id in standing_by_player_id:
                continue
            standings.append(
                {
                    "id": player_id,
                    "name": players_by_id[player_id]["name"],
                    "decklist": players_by_id[player_id]["decklist"],
                    "rank": None,
                    "points": 0,
                }
            )
    else:
        standings = [
            {
                "id": player_id,
                "name": players_by_id[player_id]["name"],
                "decklist": players_by_id[player_id]["decklist"],
                "rank": None,
            }
            for player_id in sorted(players_by_id)
        ]
    standings.sort(key=lambda row: row.get("rank") or 999999)

    rounds_by_number: dict[int, list[dict[str, Any]]] = {}
    for stage_number, table_number, table_data in sorted(table_rows):
        if table_data.get("Mute"):
            continue

        winner_entry = table_data.get("Winner")
        if winner_entry is None:
            continue

        entry_numbers = table_data.get("Es") or []
        if not isinstance(entry_numbers, list):
            continue

        players: list[dict[str, Any]] = []
        for entry_number in entry_numbers:
            try:
                player_id = entry_to_player_id.get(int(entry_number))
            except (TypeError, ValueError):
                player_id = None
            if not player_id:
                continue
            players.append(players_by_id[player_id])

        if not players:
            continue

        if winner_entry == "_DRAW_":
            winner_id = "Draw"
            winner_name = None
        else:
            try:
                winner_player_id = entry_to_player_id.get(int(winner_entry))
            except (TypeError, ValueError):
                winner_player_id = None
            if not winner_player_id:
                continue
            winner_id = winner_player_id
            winner_name = players_by_id.get(winner_player_id, {}).get("name")

        rounds_by_number.setdefault(stage_number, []).append(
            {
                "table": table_number,
                "players": players,
                "winner_id": winner_id,
                "winner": winner_name,
                "status": "Completed" if table_data.get("End") else "Active",
            }
        )

    converted_rounds = [
        {"round": round_number, "tables": tables}
        for round_number, tables in sorted(rounds_by_number.items())
    ]
    if not converted_rounds:
        return None

    start_date = (
        firestore_timestamp_seconds(data.get("StartDate"))
        or firestore_timestamp_seconds(data.get("DateCreated"))
        or base_tournament.get("startDate")
    )

    return {
        "id": tid,
        "TID": tid,
        "name": data.get("Name") or base_tournament.get("name") or tid,
        "game": data.get("Game") or base_tournament.get("game"),
        "format": data.get("Format") or base_tournament.get("format"),
        "startDate": start_date,
        "swissNum": max(rounds_by_number) if rounds_by_number else 0,
        "topCut": base_tournament.get("topCut") or 0,
        "standings": standings,
        "rounds": converted_rounds,
        "eventData": base_tournament.get("eventData") or {},
        "_source": "topdeck_firestore_flat_league",
    }


def merge_firestore_flat_league_rounds(
    primary_tournament: dict[str, Any] | None,
    flat_league_tournament: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Merge flat Firestore league pods into another TopDeck-like payload."""
    if not primary_tournament:
        return flat_league_tournament
    if not flat_league_tournament:
        return primary_tournament

    existing_rounds = list(primary_tournament.get("rounds") or [])
    existing_round_keys = {str(round_row.get("round")) for round_row in existing_rounds}
    flat_rounds = [
        round_row
        for round_row in flat_league_tournament.get("rounds") or []
        if str(round_row.get("round")) not in existing_round_keys
    ]
    if not flat_rounds:
        return primary_tournament

    merged = dict(primary_tournament)
    merged["rounds"] = flat_rounds + existing_rounds
    merged["swissNum"] = max(
        int(primary_tournament.get("swissNum") or 0),
        int(flat_league_tournament.get("swissNum") or 0),
    )
    merged["_source"] = "+".join(
        source
        for source in (
            primary_tournament.get("_source"),
            flat_league_tournament.get("_source"),
        )
        if source
    ) or primary_tournament.get("_source") or flat_league_tournament.get("_source")
    return merged


def is_placeholder_player_name(name: Any) -> bool:
    """Return true for names synthesized when TopDeck only exposes a player id."""
    return not name or str(name).strip().lower() == "unknown"


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
                    response = requests.get(url, headers=headers, timeout=90)
                elif method == "POST":
                    response = requests.post(
                        url, json=json_payload, headers=headers, timeout=90
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if response.status_code == 429:
                    retry_after = 60
                    try:
                        retry_after = int(response.json().get("retryAfterSeconds", retry_after))
                    except (
                        TypeError,
                        ValueError,
                        requests.exceptions.JSONDecodeError,
                    ) as e:
                        logger.debug(
                            "Unable to parse TopDeck retryAfterSeconds; using default %ss (%s)",
                            retry_after,
                            e,
                        )
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
        leagues: bool = False,
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
        if leagues:
            params["leagues"] = True

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

        # If standings are empty, try PublicPData (common for upcoming events)
        if not tournament.get("standings"):
            public_players = self.get_public_player_data(tid)
            if public_players:
                tournament["standings"] = [
                    {
                        "id": p.get("uid"),
                        "name": p.get("name"),
                        "username": p.get("username"),
                        "decklist": p.get("decklist"),
                        "standing": i + 1,
                    }
                    for i, p in enumerate(public_players)
                    if p.get("uid")
                ]

        if should_use_firestore_tournament_fallback(tournament) or not tournament.get("rounds"):
            firestore_tournament = self.get_firestore_tournament(tid, tournament)
            if firestore_tournament:
                return firestore_tournament
        elif flat_firestore_tournament := self.get_firestore_flat_tournament(tid, tournament):
            return merge_firestore_flat_league_rounds(tournament, flat_firestore_tournament) or tournament
        return tournament

    def get_firestore_tournament(
        self,
        tid: str,
        base_tournament: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Fetch a legacy bracket tournament from TopDeck's Firestore document."""
        firestore_api_key = os.environ.get("TOPDECK_FIRESTORE_API_KEY")
        url = (
            "https://firestore.googleapis.com/v1/projects/"
            f"{TOPDECK_FIRESTORE_PROJECT}/databases/(default)/documents/"
            f"tournaments/{tid}"
        )
        if firestore_api_key:
            url = f"{url}?key={firestore_api_key}"

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
        firestore_tournament = firestore_tournament_to_topdeck_payload(tid, data)
        flat_league_tournament = flat_firestore_league_to_topdeck_payload(
            tid,
            data,
            base_tournament or firestore_tournament,
        )
        return merge_firestore_flat_league_rounds(
            firestore_tournament,
            flat_league_tournament,
        )

    def get_firestore_flat_tournament(
        self,
        tid: str,
        base_tournament: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Load only TopDeck's flat Firestore pod rows for API payload augmentation."""
        firestore_api_key = os.environ.get("TOPDECK_FIRESTORE_API_KEY")
        url = (
            "https://firestore.googleapis.com/v1/projects/"
            f"{TOPDECK_FIRESTORE_PROJECT}/databases/(default)/documents/"
            f"tournaments/{tid}"
        )
        if firestore_api_key:
            url = f"{url}?key={firestore_api_key}"

        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            logger.warning(
                "TopDeck Firestore flat tournament fetch failed for %s: %s %s",
                tid,
                response.status_code,
                response.text[:200],
            )
            return None

        fields = response.json().get("fields")
        if not isinstance(fields, dict):
            return None

        data = {key: decode_firestore_value(value) for key, value in fields.items()}
        return flat_firestore_league_to_topdeck_payload(tid, data, base_tournament)

    def get_public_player_data(self, tid: str) -> list[dict[str, Any]]:
        """Fetch public player registration data from TopDeck.gg."""
        url = f"https://topdeck.gg/PublicPData/{tid}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    return list(data.values())
        except Exception as e:
            logger.warning(f"Failed to fetch public player data for {tid}: {e}")
        return []

    def get_tournament_tier(self, tid: str) -> str | None:
        """Fetch the tournament tier (Platinum, Diamond, etc.) from Firestore otherEvents."""
        firestore_api_key = os.environ.get("TOPDECK_FIRESTORE_API_KEY")
        url = (
            "https://firestore.googleapis.com/v1/projects/"
            f"{TOPDECK_FIRESTORE_PROJECT}/databases/(default)/documents/"
            f"otherEvents/{tid}"
        )
        if firestore_api_key:
            url = f"{url}?key={firestore_api_key}"

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                fields = response.json().get("fields", {})
                if "tier" in fields:
                    return decode_firestore_value(fields["tier"])
        except Exception as e:
            logger.warning(f"Failed to fetch tier for {tid}: {e}")
        return None
