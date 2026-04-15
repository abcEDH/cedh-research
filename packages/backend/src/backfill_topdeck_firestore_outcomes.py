#!/usr/bin/env python3
"""Backfill legacy TopDeck bracket outcomes from Firestore tournament documents."""

from __future__ import annotations

import argparse
import os
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests

from ingest import TopDeckClient


def load_env() -> None:
    for env_path in (Path("packages/backend/.env"), Path(".env"), Path(__file__).resolve().parents[1] / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


class SupabaseRest:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.player_cache: dict[str, str] = {}
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def request_with_retries(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        for attempt in range(4):
            try:
                response = requests.request(method, endpoint, timeout=60, **kwargs)
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(2**attempt)
                    continue
                return response
            except requests.exceptions.RequestException:
                if attempt >= 3:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("unreachable retry state")

    def get(self, table: str, params: dict[str, str], *, page_size: int = 1000) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            headers = self.headers.copy()
            headers["Range"] = f"{offset}-{offset + page_size - 1}"
            response = self.request_with_retries(
                "GET",
                f"{self.url}/rest/v1/{table}",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            page = response.json()
            rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return rows

    def patch(self, table: str, filters: dict[str, str], payload: dict[str, Any]) -> int:
        response = self.request_with_retries(
            "PATCH",
            f"{self.url}/rest/v1/{table}",
            headers=self.headers,
            params=filters,
            json=payload,
        )
        response.raise_for_status()
        rows = response.json()
        return len(rows) if isinstance(rows, list) else 0

    def upsert(
        self,
        table: str,
        payload: dict[str, Any] | list[dict[str, Any]],
        *,
        on_conflict: str | None = None,
    ) -> list[dict[str, Any]]:
        headers = self.headers.copy()
        params = {}
        if on_conflict:
            params["on_conflict"] = on_conflict
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        response = self.request_with_retries(
            "POST",
            f"{self.url}/rest/v1/{table}",
            headers=headers,
            params=params,
            json=payload,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Supabase upsert failed for {table}: {response.status_code} {response.text}"
            )
        response.raise_for_status()
        rows = response.json()
        return rows if isinstance(rows, list) else []


def candidate_has_no_recorded_outcome(row: dict[str, Any]) -> bool:
    participants = row.get("game_participants") or []
    return not any(
        participant.get("result") in ("win", "draw") for participant in participants
    )


def fetch_candidate_games(client: SupabaseRest, only_tid: str | None) -> list[dict[str, Any]]:
    select = (
        "id,round_number,round_name,table_number,status,is_draw,winner_id,"
        "tournaments(topdeck_tid,name),game_participants(result)"
    )
    rows = client.get(
        "games",
        {
            "select": select,
            "winner_id": "is.null",
            "is_draw": "eq.true",
            "order": "tournament_id.asc",
        },
    )
    candidates = [
        row
        for row in rows
        if candidate_has_no_recorded_outcome(row)
        and (not only_tid or (row.get("tournaments") or {}).get("topdeck_tid") == only_tid)
    ]

    active_rows = client.get(
        "games",
        {
            "select": select,
            "winner_id": "is.null",
            "is_draw": "eq.false",
            "status": "eq.Active",
            "order": "tournament_id.asc",
        },
    )
    candidates.extend(
        row
        for row in active_rows
        if candidate_has_no_recorded_outcome(row)
        and (not only_tid or (row.get("tournaments") or {}).get("topdeck_tid") == only_tid)
    )
    return candidates


def table_index(tournament: dict[str, Any]) -> dict[tuple[int | None, str | None, int | None], dict[str, Any]]:
    indexed: dict[tuple[int | None, str | None, int | None], dict[str, Any]] = {}
    for round_data in tournament.get("rounds") or []:
        round_value = round_data.get("round")
        round_number = round_value if isinstance(round_value, int) else None
        round_name = None if isinstance(round_value, int) else str(round_value)
        for table in round_data.get("tables") or []:
            table_number = table.get("table") or table.get("table_number") or table.get("tableNumber")
            indexed[(round_number, round_name, table_number)] = table
    return indexed


def game_key(row: dict[str, Any]) -> tuple[int | None, str | None, int | None]:
    round_name = row.get("round_name") or None
    return (row.get("round_number"), round_name, row.get("table_number"))


def table_player_name(table: dict[str, Any], topdeck_id: str) -> str:
    for player in table.get("players") or []:
        if player.get("id") == topdeck_id:
            return player.get("name") or "Unknown"
    return "Unknown"


def ensure_player(client: SupabaseRest, topdeck_id: str, name: str) -> str | None:
    if topdeck_id in client.player_cache:
        return client.player_cache[topdeck_id]

    result = client.upsert(
        "players",
        {"topdeck_id": topdeck_id, "name": name},
        on_conflict="topdeck_id",
    )
    if result:
        client.player_cache[topdeck_id] = result[0]["id"]
        return result[0]["id"]
    return None


def preload_players(client: SupabaseRest) -> None:
    rows = client.get("players", {"select": "id,topdeck_id"}, page_size=1000)
    for row in rows:
        topdeck_id = row.get("topdeck_id")
        if topdeck_id:
            client.player_cache[topdeck_id] = row["id"]
    print(f"preloaded_players={len(client.player_cache)}")


def chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def fetch_participants_for_games(
    client: SupabaseRest, game_ids: list[str]
) -> list[dict[str, Any]]:
    participants: list[dict[str, Any]] = []
    for game_id_chunk in chunks(game_ids, 100):
        id_filter = ",".join(game_id_chunk)
        participants.extend(
            client.get(
                "game_participants",
                {
                    "select": "id,game_id,tournament_entries(players(topdeck_id))",
                    "game_id": f"in.({id_filter})",
                },
            )
        )
    return participants


def upsert_chunks(
    client: SupabaseRest,
    table: str,
    rows: list[dict[str, Any]],
    *,
    chunk_size: int = 500,
) -> int:
    updated = 0
    for row_chunk in chunks(rows, chunk_size):
        updated += len(client.upsert(table, row_chunk, on_conflict="id"))
    return updated


def patch_game_updates(
    client: SupabaseRest, game_updates: list[dict[str, Any]], *, workers: int
) -> int:
    def patch_one(game_update: dict[str, Any]) -> int:
        payload = dict(game_update)
        game_id = payload.pop("id")
        return client.patch("games", {"id": f"eq.{game_id}"}, payload)

    if workers <= 1 or len(game_updates) <= 1:
        return sum(patch_one(game_update) for game_update in game_updates)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        return sum(executor.map(patch_one, game_updates))


def update_participants(
    client: SupabaseRest,
    game_id: str,
    *,
    winner_topdeck_id: str | None,
    is_draw: bool,
    dry_run: bool,
) -> int:
    participants = client.get(
        "game_participants",
        {
            "select": "id,tournament_entries(players(topdeck_id))",
            "game_id": f"eq.{game_id}",
        },
    )
    updated = 0
    for participant in participants:
        player = ((participant.get("tournament_entries") or {}).get("players") or {})
        topdeck_id = player.get("topdeck_id")
        if is_draw:
            payload = {"result": "draw", "points_earned": 1}
        else:
            is_winner = topdeck_id == winner_topdeck_id
            payload = {
                "result": "win" if is_winner else "loss",
                "points_earned": 5 if is_winner else 0,
            }
        if not dry_run:
            updated += client.patch(
                "game_participants", {"id": f"eq.{participant['id']}"}, payload
            )
        else:
            updated += 1
    return updated


def classify_game_update(
    client: SupabaseRest,
    row: dict[str, Any],
    table: dict[str, Any],
) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    status = table.get("status") or "Completed"
    winner_topdeck_id = table.get("winner_id") or table.get("winnerId")
    if winner_topdeck_id == "Draw":
        return (
            "draw",
            {"id": row["id"], "is_draw": True, "winner_id": None, "status": status},
            {"winner_topdeck_id": None, "is_draw": True},
        )

    if winner_topdeck_id:
        winner_id = ensure_player(
            client,
            str(winner_topdeck_id),
            table_player_name(table, str(winner_topdeck_id)),
        )
        if not winner_id:
            return ("missing_winner_player", None, None)
        return (
            "winner",
            {
                "id": row["id"],
                "is_draw": False,
                "winner_id": winner_id,
                "status": status,
            },
            {"winner_topdeck_id": str(winner_topdeck_id), "is_draw": False},
        )

    if status != "Completed":
        return (
            "active_or_pending",
            {"id": row["id"], "is_draw": False, "winner_id": None, "status": status},
            None,
        )

    return ("completed_null_winner", None, None)


def backfill_game(
    client: SupabaseRest,
    row: dict[str, Any],
    table: dict[str, Any],
    *,
    dry_run: bool,
) -> tuple[str, int]:
    status = table.get("status") or "Completed"
    winner_topdeck_id = table.get("winner_id") or table.get("winnerId")
    if winner_topdeck_id == "Draw":
        payload = {"is_draw": True, "winner_id": None, "status": status}
        if not dry_run:
            client.patch("games", {"id": f"eq.{row['id']}"}, payload)
        participant_updates = update_participants(
            client,
            row["id"],
            winner_topdeck_id=None,
            is_draw=True,
            dry_run=dry_run,
        )
        return ("draw", participant_updates)

    if winner_topdeck_id:
        winner_id = ensure_player(
            client,
            str(winner_topdeck_id),
            table_player_name(table, str(winner_topdeck_id)),
        )
        if not winner_id:
            return ("missing_winner_player", 0)
        payload = {"is_draw": False, "winner_id": winner_id, "status": status}
        if not dry_run:
            client.patch("games", {"id": f"eq.{row['id']}"}, payload)
        participant_updates = update_participants(
            client,
            row["id"],
            winner_topdeck_id=str(winner_topdeck_id),
            is_draw=False,
            dry_run=dry_run,
        )
        return ("winner", participant_updates)

    if status != "Completed":
        payload = {"is_draw": False, "winner_id": None, "status": status}
        if not dry_run:
            client.patch("games", {"id": f"eq.{row['id']}"}, payload)
        return ("active_or_pending", 0)

    return ("completed_null_winner", 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only-tid", help="Backfill one TopDeck tournament ID")
    parser.add_argument("--limit", type=int, default=0, help="Maximum tournaments to process")
    parser.add_argument("--sleep", type=float, default=0, help="Seconds between tournaments")
    parser.add_argument("--dry-run", action="store_true", help="Classify without mutating Supabase")
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Concurrent Supabase game PATCH workers",
    )
    parser.add_argument(
        "--update-participants",
        action="store_true",
        help="Also update existing game_participants result/points rows",
    )
    args = parser.parse_args()

    load_env()
    client = SupabaseRest(require_env("SUPABASE_URL"), require_env("SUPABASE_SERVICE_KEY"))
    topdeck = TopDeckClient(require_env("TOPDECK_API_KEY"))
    preload_players(client)

    candidates = fetch_candidate_games(client, args.only_tid)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        tournament = row.get("tournaments") or {}
        tid = tournament.get("topdeck_tid")
        if tid:
            grouped[tid].append(row)

    tids = sorted(grouped)
    if args.limit > 0:
        tids = tids[: args.limit]

    print(f"candidate_games={len(candidates)}")
    print(f"candidate_tournaments={len(grouped)}")
    print(f"processing_tournaments={len(tids)}")
    if args.dry_run:
        print("dry_run=true")

    counts: Counter[str] = Counter()
    participant_updates = 0
    game_updates_count = 0
    for index, tid in enumerate(tids, start=1):
        tournament = topdeck.get_firestore_tournament(tid)
        if not tournament:
            counts["no_firestore_tournament"] += len(grouped[tid])
            continue

        indexed_tables = table_index(tournament)
        print(f"[{index}/{len(tids)}] tid={tid} games={len(grouped[tid])}")
        game_updates: list[dict[str, Any]] = []
        participant_outcomes: dict[str, dict[str, Any]] = {}
        for row in grouped[tid]:
            table = indexed_tables.get(game_key(row))
            if not table:
                counts["no_matching_table"] += 1
                continue
            status, game_update, participant_outcome = classify_game_update(
                client, row, table
            )
            counts[status] += 1
            if game_update:
                game_updates.append(game_update)
                game_updates_count += 1
            if participant_outcome:
                participant_outcomes[row["id"]] = participant_outcome

        if game_updates and not args.dry_run:
            patch_game_updates(client, game_updates, workers=args.workers)

        if args.update_participants and participant_outcomes:
            participant_rows: list[dict[str, Any]] = []
            participants = fetch_participants_for_games(
                client, list(participant_outcomes.keys())
            )
            for participant in participants:
                outcome = participant_outcomes.get(participant["game_id"])
                if not outcome:
                    continue
                player = (
                    (participant.get("tournament_entries") or {}).get("players")
                    or {}
                )
                topdeck_id = player.get("topdeck_id")
                if outcome["is_draw"]:
                    participant_rows.append(
                        {
                            "id": participant["id"],
                            "result": "draw",
                            "points_earned": 1,
                        }
                    )
                else:
                    is_winner = topdeck_id == outcome["winner_topdeck_id"]
                    participant_rows.append(
                        {
                            "id": participant["id"],
                            "result": "win" if is_winner else "loss",
                            "points_earned": 5 if is_winner else 0,
                        }
                    )

            if participant_rows:
                if args.dry_run:
                    participant_updates += len(participant_rows)
                else:
                    participant_updates += upsert_chunks(
                        client, "game_participants", participant_rows
                    )

        if args.sleep > 0:
            time.sleep(args.sleep)

    print("game_updates=" + str(game_updates_count))
    print("participant_updates=" + str(participant_updates))
    for key, value in counts.most_common():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
