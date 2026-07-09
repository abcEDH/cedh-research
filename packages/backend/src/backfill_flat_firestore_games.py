#!/usr/bin/env python3
"""Backfill flat TopDeck Firestore pod games missing from Supabase."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from ingest import (
    GAME_REGISTRY,
    MTG_GAME,
    SUPABASE_REST_BASE,
    TOPDECK_FIRESTORE_PROJECT,
    SupabaseClient,
    build_game_key,
    decode_firestore_value,
    load_local_env,
)

SUPABASE_PAGE_SIZE = 1000
DEFAULT_FIRESTORE_WORKERS = 24
GAME_UPSERT_CHUNK_SIZE = 500
PARTICIPANT_UPSERT_CHUNK_SIZE = 1000


def relation_value(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        value = value[0] if value else {}
    return value if isinstance(value, dict) else {}


def chunks(values: list[Any], size: int) -> list[list[Any]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def fetch_all(
    client: SupabaseClient,
    table: str,
    params: dict[str, str],
    page_size: int = SUPABASE_PAGE_SIZE,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = client.select(
            table,
            {
                **params,
                "limit": str(page_size),
                "offset": str(offset),
            },
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


def fetch_rows_by_ids(
    client: SupabaseClient,
    table: str,
    column: str,
    values: list[str],
    select: str = "*",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value_chunk in chunks(sorted(set(values)), 100):
        if not value_chunk:
            continue
        rows.extend(
            fetch_all(
                client,
                table,
                {
                    "select": select,
                    column: f"in.({','.join(value_chunk)})",
                },
            )
        )
    return rows


def fetch_firestore_document(tid: str) -> dict[str, Any] | None:
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
    response.raise_for_status()
    fields = response.json().get("fields")
    if not isinstance(fields, dict):
        return None
    return {key: decode_firestore_value(value) for key, value in fields.items()}


def extract_flat_pods(data: dict[str, Any]) -> list[dict[str, Any]]:
    entry_to_player_id: dict[int, str] = {}
    pods: list[dict[str, Any]] = []

    for key, value in data.items():
        entry_match = re.fullmatch(r"E(\d+):P\d+", key)
        if entry_match and value:
            entry_to_player_id[int(entry_match.group(1))] = str(value)

    if not entry_to_player_id:
        return []

    for key, value in data.items():
        table_match = re.fullmatch(r"S(\d+):T(\d+)", key)
        if not table_match or not isinstance(value, dict):
            continue
        if value.get("Mute") or not value.get("End"):
            continue

        winner_entry = value.get("Winner")
        if winner_entry is None:
            continue

        entry_numbers = value.get("Es") or []
        if not isinstance(entry_numbers, list) or len(entry_numbers) < 2:
            continue

        player_topdeck_ids: list[str] = []
        for entry_number in entry_numbers:
            try:
                player_topdeck_id = entry_to_player_id.get(int(entry_number))
            except (TypeError, ValueError):
                player_topdeck_id = None
            if player_topdeck_id:
                player_topdeck_ids.append(player_topdeck_id)

        if len(player_topdeck_ids) < 2:
            continue

        if winner_entry == "_DRAW_":
            winner_topdeck_id = None
            is_draw = True
        else:
            try:
                winner_topdeck_id = entry_to_player_id.get(int(winner_entry))
            except (TypeError, ValueError):
                winner_topdeck_id = None
            if not winner_topdeck_id:
                continue
            is_draw = False

        pods.append(
            {
                "round_number": int(table_match.group(1)),
                "table_number": int(table_match.group(2)),
                "player_topdeck_ids": player_topdeck_ids,
                "winner_topdeck_id": winner_topdeck_id,
                "is_draw": is_draw,
            }
        )

    return pods


def fetch_tournaments(client: SupabaseClient, only_leagues: bool) -> list[dict[str, Any]]:
    # Flat Firestore documents (E{n}:P{n} / S{n}:T{n} keys) are TopDeck's legacy,
    # pre-v2-API storage format — they only exist for old cEDH tournaments run
    # before the multi-game v2 API existed. Riftbound/Gundam/YGO tournaments are
    # all v2-API-era and never have a flat Firestore doc to recover, but without
    # this filter a coincidental Firestore hit would attach the MTG-only
    # "Unknown Commander" fallback (get_unknown_commander_id) to a non-cEDH
    # tournament_entries row, mixing games in the deck-identity read models
    # (ADR 0015; PR #247 review).
    cedh = GAME_REGISTRY["cedh"]
    params = {
        "select": "id,topdeck_tid,name,start_date",
        "topdeck_tid": "not.is.null",
        "game": f"eq.{cedh.db_game}",
        "format": f"eq.{cedh.db_format}",
        "order": "start_date.desc",
    }
    if only_leagues:
        params["name"] = "ilike.*league*"
    return fetch_all(client, "tournaments", params)


def fetch_numeric_game_counts(client: SupabaseClient, tournament_ids: list[str]) -> dict[str, dict[str, int]]:
    counts = {tournament_id: {"total": 0, "numeric": 0} for tournament_id in tournament_ids}
    for tournament_id_chunk in chunks(tournament_ids, 75):
        rows = fetch_all(
            client,
            "games",
            {
                "select": "tournament_id,round_number",
                "tournament_id": f"in.({','.join(tournament_id_chunk)})",
            },
        )
        for row in rows:
            tournament_id = row.get("tournament_id")
            if tournament_id not in counts:
                continue
            counts[tournament_id]["total"] += 1
            if row.get("round_number") is not None:
                counts[tournament_id]["numeric"] += 1
    return counts


def scan_tournament(tournament: dict[str, Any]) -> dict[str, Any]:
    tid = tournament.get("topdeck_tid")
    try:
        data = fetch_firestore_document(str(tid))
        if not data:
            return {**tournament, "firestore_status": 404, "flat_completed": 0}
        pods = extract_flat_pods(data)
        return {
            **tournament,
            "firestore_status": 200,
            "flat_completed": len(pods),
        }
    except Exception as exc:
        return {
            **tournament,
            "firestore_status": "error",
            "error": str(exc),
            "flat_completed": 0,
        }


def scan_for_issues(
    client: SupabaseClient,
    only_leagues: bool,
    workers: int,
) -> list[dict[str, Any]]:
    tournaments = fetch_tournaments(client, only_leagues)
    print(f"Scanning {len(tournaments):,} tournaments", flush=True)

    counts = fetch_numeric_game_counts(client, [row["id"] for row in tournaments])
    results: list[dict[str, Any]] = []
    started = time.time()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(scan_tournament, tournament) for tournament in tournaments]
        for index, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            count = counts.get(row["id"], {"total": 0, "numeric": 0})
            row["db_total_games"] = count["total"]
            row["db_numeric_games"] = count["numeric"]
            row["missing_numeric_games"] = max(0, row["flat_completed"] - count["numeric"])
            if row["missing_numeric_games"] > 0:
                results.append(row)
            if index % 500 == 0:
                elapsed = time.time() - started
                print(f"Checked {index:,}/{len(tournaments):,} in {elapsed:.1f}s", flush=True)

    results.sort(key=lambda row: (row["missing_numeric_games"], row["flat_completed"]), reverse=True)
    return results


def fetch_entry_map(client: SupabaseClient, tournament_id: str) -> dict[str, dict[str, str]]:
    rows = fetch_all(
        client,
        "tournament_entries",
        {
            "select": "id,player_id,players(topdeck_id)",
            "tournament_id": f"eq.{tournament_id}",
        },
    )
    entry_by_topdeck_id: dict[str, dict[str, str]] = {}
    for row in rows:
        player = relation_value(row.get("players"))
        topdeck_id = player.get("topdeck_id")
        if topdeck_id:
            entry_by_topdeck_id[str(topdeck_id)] = {
                "entry_id": row["id"],
                "player_id": row["player_id"],
            }
    return entry_by_topdeck_id


def get_unknown_commander_id(client: SupabaseClient) -> str:
    rows = client.upsert(
        "commanders",
        {
            "name": "Unknown Commander",
            "commander_names": ["Unknown Commander"],
            "game": MTG_GAME,
            "identity_kind": "commander",
        },
        on_conflict="game,name",
        max_retries=8,
    )
    if not rows:
        raise RuntimeError("Unable to upsert Unknown Commander")
    return rows[0]["id"]


def ensure_tournament_entries(
    client: SupabaseClient,
    tournament_id: str,
    pods: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    entry_by_topdeck_id = fetch_entry_map(client, tournament_id)
    pod_topdeck_ids = {topdeck_id for pod in pods for topdeck_id in pod["player_topdeck_ids"]}
    missing_topdeck_ids = sorted(pod_topdeck_ids - set(entry_by_topdeck_id))
    if not missing_topdeck_ids:
        return entry_by_topdeck_id

    existing_players = fetch_rows_by_ids(
        client,
        "players",
        "topdeck_id",
        missing_topdeck_ids,
        select="id,topdeck_id,name",
    )
    player_id_by_topdeck_id = {
        str(row["topdeck_id"]): row["id"] for row in existing_players if row.get("topdeck_id") and row.get("id")
    }

    new_player_ids = [topdeck_id for topdeck_id in missing_topdeck_ids if topdeck_id not in player_id_by_topdeck_id]
    if new_player_ids:
        new_players = (
            client.upsert(
                "players",
                [{"topdeck_id": topdeck_id, "name": "Unknown"} for topdeck_id in new_player_ids],
                on_conflict="topdeck_id",
                max_retries=8,
            )
            or []
        )
        for row in new_players:
            if row.get("topdeck_id") and row.get("id"):
                player_id_by_topdeck_id[str(row["topdeck_id"])] = row["id"]

    commander_id = get_unknown_commander_id(client)
    missing_entries = [
        {
            "tournament_id": tournament_id,
            "player_id": player_id_by_topdeck_id[topdeck_id],
            "commander_id": commander_id,
            "final_standing": None,
            "points": 0,
            "decklist_text": "",
        }
        for topdeck_id in missing_topdeck_ids
        if topdeck_id in player_id_by_topdeck_id
    ]
    for entry_chunk in chunks(missing_entries, 500):
        client.upsert(
            "tournament_entries",
            entry_chunk,
            on_conflict="tournament_id,player_id",
            max_retries=8,
        )

    return fetch_entry_map(client, tournament_id)


def upsert_games_and_participants(
    client: SupabaseClient,
    tournament: dict[str, Any],
    pods: list[dict[str, Any]],
) -> dict[str, int]:
    tournament_id = tournament["id"]
    entry_by_topdeck_id = ensure_tournament_entries(client, tournament_id, pods)

    games: list[dict[str, Any]] = []
    skipped_pods = 0
    for pod in pods:
        participant_entries = [entry_by_topdeck_id.get(topdeck_id) for topdeck_id in pod["player_topdeck_ids"]]
        if any(entry is None for entry in participant_entries):
            skipped_pods += 1
            continue

        winner_player_id = None
        if not pod["is_draw"] and pod["winner_topdeck_id"]:
            winner_entry = entry_by_topdeck_id.get(pod["winner_topdeck_id"])
            if not winner_entry:
                skipped_pods += 1
                continue
            winner_player_id = winner_entry["player_id"]

        game_key = build_game_key(
            tournament_id,
            pod["round_number"],
            None,
            pod["table_number"],
            False,
        )
        games.append(
            {
                "tournament_id": tournament_id,
                "round_number": pod["round_number"],
                "round_name": None,
                "is_bracket": False,
                "table_number": pod["table_number"],
                "status": "Completed",
                "is_draw": pod["is_draw"],
                "winner_id": winner_player_id,
                "game_key": game_key,
                "_pod": pod,
            }
        )

    game_id_by_key: dict[str, str] = {}
    for game_chunk in chunks(games, GAME_UPSERT_CHUNK_SIZE):
        payload = [{key: value for key, value in row.items() if key != "_pod"} for row in game_chunk]
        rows = client.upsert("games", payload, on_conflict="game_key", max_retries=8) or []
        for row in rows:
            if row.get("game_key") and row.get("id"):
                game_id_by_key[row["game_key"]] = row["id"]

    participants: list[dict[str, Any]] = []
    for game in games:
        game_id = game_id_by_key.get(game["game_key"])
        if not game_id:
            skipped_pods += 1
            continue
        pod = game["_pod"]
        for seat_position, topdeck_id in enumerate(pod["player_topdeck_ids"]):
            entry = entry_by_topdeck_id[topdeck_id]
            is_winner = not pod["is_draw"] and topdeck_id == pod["winner_topdeck_id"]
            result = "draw" if pod["is_draw"] else "win" if is_winner else "loss"
            participants.append(
                {
                    "game_id": game_id,
                    "entry_id": entry["entry_id"],
                    "seat_position": seat_position,
                    "result": result,
                    "points_earned": 1 if pod["is_draw"] else 5 if is_winner else 0,
                }
            )

    for participant_chunk in chunks(participants, PARTICIPANT_UPSERT_CHUNK_SIZE):
        client.upsert(
            "game_participants",
            participant_chunk,
            on_conflict="game_id,entry_id",
            max_retries=8,
        )

    return {
        "games": len(games),
        "participants": len(participants),
        "skipped_pods": skipped_pods,
    }


def backfill_issue(client: SupabaseClient, issue: dict[str, Any]) -> dict[str, Any]:
    data = fetch_firestore_document(issue["topdeck_tid"])
    if not data:
        return {**issue, "backfilled_games": 0, "backfilled_participants": 0, "skipped_pods": 0}
    pods = extract_flat_pods(data)
    result = upsert_games_and_participants(client, issue, pods)
    return {
        **issue,
        "backfilled_games": result["games"],
        "backfilled_participants": result["participants"],
        "skipped_pods": result["skipped_pods"],
    }


def load_issues(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        return list(data.get("issues") or data.get("top_issues") or [])
    if isinstance(data, list):
        return data
    raise ValueError(f"Unsupported issue file shape: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write missing flat pod games")
    parser.add_argument("--only-leagues", action="store_true", help="Only scan tournament names containing league")
    parser.add_argument("--workers", type=int, default=DEFAULT_FIRESTORE_WORKERS)
    parser.add_argument("--issues-out", default="")
    parser.add_argument("--issues-in", default="")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    load_local_env()
    url = os.environ.get("SUPABASE_URL", SUPABASE_REST_BASE)
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")

    client = SupabaseClient(url, key)
    issues = (
        load_issues(args.issues_in)
        if args.issues_in
        else scan_for_issues(
            client,
            only_leagues=args.only_leagues,
            workers=args.workers,
        )
    )
    if args.limit > 0:
        issues = issues[: args.limit]

    print(f"Found {len(issues):,} tournaments with missing flat pod games", flush=True)
    if args.issues_out:
        Path(args.issues_out).write_text(json.dumps({"issues": issues}, indent=2))
        print(f"Wrote {args.issues_out}", flush=True)

    if not args.apply:
        print("Dry run complete. Pass --apply to backfill.", flush=True)
        return

    backfilled: list[dict[str, Any]] = []
    for index, issue in enumerate(issues, start=1):
        print(
            f"[{index}/{len(issues)}] Backfilling {issue['name']} "
            f"({issue['topdeck_tid']}) missing={issue['missing_numeric_games']}",
            flush=True,
        )
        backfilled.append(backfill_issue(client, issue))
    print(json.dumps({"backfilled": backfilled}, indent=2), flush=True)


if __name__ == "__main__":
    main()
