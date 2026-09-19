"""TopDeck event inputs, structure inference, and prepared-state caching."""

from __future__ import annotations

import hashlib
import json
import pickle
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

DEFAULT_PREPARED_STATE_CACHE_DIR = Path(".cache/tournament-sim")
PREPARED_STATE_CACHE_VERSION = 9


def relevant_advancement_sizes(top_cut: int) -> tuple[int, ...]:
    if top_cut <= 0:
        return ()

    candidates = [top_cut]
    if top_cut in {40, 64}:
        candidates.extend([16, 4])
    elif top_cut > 4:
        candidates.append(4)

    selected: list[int] = []
    for size in candidates:
        if size > 0 and size <= top_cut and size not in selected:
            selected.append(size)
    return tuple(selected)


def eligible_player_count(state) -> int:
    return len(state.eligible_player_ids) if state.eligible_player_ids is not None else len(state.players)


def fetch_event_page_html(event_id: str) -> str:
    response = requests.get(f"https://topdeck.gg/event/{event_id}", timeout=30)
    response.raise_for_status()
    return response.text


def extract_numeric_value(payload: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = payload.get(key)
        if value in (None, ""):
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed >= 0:
            return parsed
    return None


def infer_structure(
    tournament: dict[str, Any],
    event_html: str,
    *,
    swiss_rounds_override: int | None,
    top_cut_override: int | None,
) -> tuple[int, int]:
    event_data = tournament.get("eventData") or {}
    swiss_rounds = swiss_rounds_override
    top_cut = top_cut_override
    for source in (tournament, event_data):
        if swiss_rounds is None:
            swiss_rounds = extract_numeric_value(source, "swissNum", "swissRounds", "numRounds")
        if top_cut is None:
            top_cut = extract_numeric_value(source, "topCut", "cutTo")

    if swiss_rounds is None:
        swiss_patterns = [
            r"(\d+)\s+Rounds?\s+of\s+Swiss",
            r"(\d+)\s+Round(?:s)?\s+Swiss",
            r"Swiss[^0-9]{0,20}(\d+)\s+Rounds?",
        ]
        for pattern in swiss_patterns:
            match = re.search(pattern, event_html, flags=re.I)
            if match:
                swiss_rounds = int(match.group(1))
                break

    if top_cut is None:
        top_cut_patterns = [
            r"Top\s+(\d+)\s+Cut",
            r"Cut\s+to\s+Top\s+(\d+)",
            r"Top\s+(\d+)\b",
        ]
        for pattern in top_cut_patterns:
            match = re.search(pattern, event_html, flags=re.I)
            if match:
                candidate = int(match.group(1))
                if candidate > 0:
                    top_cut = candidate
                    break

    if swiss_rounds is None:
        raise RuntimeError(
            "Unable to infer total swiss rounds from the TopDeck payload/event page. Pass --swiss-rounds explicitly."
        )
    if top_cut is None:
        raise RuntimeError(
            "Unable to infer top cut size from the TopDeck payload/event page. Pass --top-cut explicitly."
        )
    return swiss_rounds, top_cut


def collect_players(tournament: dict[str, Any]) -> dict[str, str]:
    players: dict[str, str] = {}
    for standing in tournament.get("standings") or []:
        player_id = standing.get("id")
        if player_id:
            players[str(player_id)] = str(standing.get("name") or player_id)
    for round_data in tournament.get("rounds") or []:
        for table in round_data.get("tables") or []:
            for player in table.get("players") or []:
                player_id = player.get("id")
                if player_id:
                    players[str(player_id)] = str(player.get("name") or players.get(str(player_id)) or player_id)
    return players


def tournament_state_fingerprint(
    tournament: dict[str, Any],
    *,
    swiss_rounds: int,
    top_cut: int,
    drop_after_round: int | None = None,
    drop_min_points: int | None = None,
) -> str:
    payload = {
        "cache_version": PREPARED_STATE_CACHE_VERSION,
        "id": tournament.get("id") or tournament.get("TID"),
        "startDate": tournament.get("startDate"),
        "swiss_rounds": swiss_rounds,
        "top_cut": top_cut,
        "drop_after_round": drop_after_round,
        "drop_min_points": drop_min_points,
        "standings": [
            {
                "id": standing.get("id"),
                "standing": standing.get("standing"),
                "points": standing.get("points"),
                "wins": standing.get("wins"),
                "draws": standing.get("draws"),
                "losses": standing.get("losses"),
            }
            for standing in tournament.get("standings") or []
        ],
        "rounds": tournament.get("rounds") or [],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepared_state_cache_path(cache_dir: Path, event_id: str, fingerprint: str) -> Path:
    safe_event_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", event_id).strip("-") or "event"
    return cache_dir / f"{safe_event_id}-{fingerprint[:16]}.pkl"


def load_prepared_state_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def save_prepared_state_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_path.replace(path)


def standings_tiebreak_seed_map(tournament: dict[str, Any]) -> dict[str, int]:
    seeds: dict[str, int] = {}
    standings = tournament.get("standings") or []
    for index, standing in enumerate(standings, start=1):
        player_id = standing.get("id")
        if player_id:
            seeds[str(player_id)] = index
    return seeds


def fetch_existing_players(client, topdeck_ids: list[str]) -> dict[str, dict[str, str]]:
    rows = client.table("players").select("id,topdeck_id,name").in_("topdeck_id", topdeck_ids).execute().data
    return {
        str(row["topdeck_id"]): {
            "id": str(row["id"]),
            "name": str(row.get("name") or row["topdeck_id"]),
        }
        for row in rows
        if row.get("topdeck_id") and row.get("id")
    }


def parse_start_date(value: Any) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value)).astimezone()
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def parse_table_number(table: dict[str, Any], fallback: int) -> int:
    table_number = table.get("table") or table.get("table_number") or table.get("tableNumber") or fallback
    try:
        return int(table_number)
    except (TypeError, ValueError):
        return fallback
