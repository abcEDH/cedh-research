#!/usr/bin/env python3
"""Backfill tournament_entries W/L/D records from game_participants."""

from __future__ import annotations

import argparse
import os
from collections import Counter, defaultdict
from typing import Any

from ingest import DataIngester, TopDeckClient, load_local_env
from supabase import Client
from supabase_client import fetch_all, get_supabase_client, upsert_batched


def parse_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def fetch_target_tournaments(
    client: Client,
    *,
    tournament_id: str | None,
    min_player_count: int,
) -> list[dict[str, Any]]:
    if tournament_id:
        return fetch_all(
            client,
            "tournaments",
            columns="id,name,player_count,top_cut,swiss_rounds,start_date",
            filters=[("id", "eq", tournament_id)],
        )
    return fetch_all(
        client,
        "tournaments",
        columns="id,name,player_count,top_cut,swiss_rounds,start_date",
        filters=[("player_count", "gte", min_player_count)],
        order=("start_date", True),
    )


ZERO_RECORD_FILTERS = [
    ("wins", "eq", 0),
    ("losses", "eq", 0),
    ("draws", "eq", 0),
    ("byes", "eq", 0),
]


def fetch_zero_record_entries(client: Client) -> list[dict[str, Any]]:
    return fetch_all(
        client,
        "tournament_entries",
        columns="id,tournament_id,player_id,commander_id,points,wins,losses,draws,byes",
        filters=ZERO_RECORD_FILTERS,
    )


def fetch_zero_record_tournaments(client: Client) -> list[dict[str, Any]]:
    entries = fetch_all(
        client,
        "tournament_entries",
        columns="tournament_id,tournaments(id,topdeck_tid,name,start_date,player_count)",
        filters=ZERO_RECORD_FILTERS,
    )
    tournaments: dict[str, dict[str, Any]] = {}
    zero_entry_counts: Counter[str] = Counter()
    for entry in entries:
        tournament = entry.get("tournaments") or {}
        tournament_id = str(entry.get("tournament_id") or tournament.get("id") or "")
        topdeck_tid = tournament.get("topdeck_tid")
        if not tournament_id or not topdeck_tid:
            continue
        zero_entry_counts[tournament_id] += 1
        tournaments[tournament_id] = {
            "id": tournament_id,
            "topdeck_tid": topdeck_tid,
            "name": tournament.get("name"),
            "start_date": tournament.get("start_date"),
            "player_count": tournament.get("player_count"),
        }

    rows = list(tournaments.values())
    for row in rows:
        row["zero_record_entries"] = zero_entry_counts[str(row["id"])]
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("start_date") or ""),
            str(row.get("topdeck_tid") or ""),
        ),
    )


def participant_counts_by_entry(client: Client, entry_ids: list[str]) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for batch in (entry_ids[index : index + 80] for index in range(0, len(entry_ids), 80)):
        rows = fetch_all(
            client,
            "game_participants",
            columns="entry_id,result",
            filters=[("entry_id", "in", batch)],
        )
        for row in rows:
            entry_id = row.get("entry_id")
            result = str(row.get("result") or "").lower()
            if entry_id and result in {"win", "loss", "draw", "bye"}:
                counts[str(entry_id)][result] += 1
    return counts


def count_api_tables(tournament: dict[str, Any]) -> dict[str, int]:
    rounds = tournament.get("rounds") or []
    tables = 0
    result_tables = 0
    winner_tables = 0
    participant_slots = 0
    for round_data in rounds:
        for table in round_data.get("tables") or []:
            tables += 1
            if table.get("results"):
                result_tables += 1
            if "winner_id" in table or "winnerId" in table:
                winner_tables += 1
            participant_slots += len(table.get("players") or table.get("seats") or [])
    return {
        "rounds": len(rounds),
        "tables": tables,
        "result_tables": result_tables,
        "winner_tables": winner_tables,
        "participant_slots": participant_slots,
    }


def existing_game_counts_by_tournament(client: Client, tournament_ids: list[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for batch in (tournament_ids[index : index + 80] for index in range(0, len(tournament_ids), 80)):
        rows = fetch_all(
            client,
            "games",
            columns="tournament_id",
            filters=[("tournament_id", "in", batch)],
        )
        for row in rows:
            tournament_id = row.get("tournament_id")
            if tournament_id:
                counts[str(tournament_id)] += 1
    return counts


def refresh_topdeck_zero_record_tournaments(
    client: Client,
    topdeck: TopDeckClient,
    *,
    apply: bool,
    limit: int,
    only_no_games: bool,
) -> dict[str, Any]:
    tournaments = fetch_zero_record_tournaments(client)
    if only_no_games:
        game_counts = existing_game_counts_by_tournament(client, [str(row["id"]) for row in tournaments])
        tournaments = [row for row in tournaments if game_counts[str(row["id"])] == 0]
    if limit:
        tournaments = tournaments[:limit]

    ingester = DataIngester(topdeck, client)
    summary: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for index, row in enumerate(tournaments, start=1):
        topdeck_tid = str(row["topdeck_tid"])
        try:
            tournament = topdeck.get_tournament(topdeck_tid)
        except Exception as exc:
            summary["api_errors"] += 1
            if len(examples["api_errors"]) < 10:
                examples["api_errors"].append(
                    {
                        "topdeck_tid": topdeck_tid,
                        "name": row.get("name"),
                        "error": str(exc)[:200],
                    }
                )
            print(
                {
                    "index": index,
                    "total": len(tournaments),
                    "topdeck_tid": topdeck_tid,
                    "status": "api_error",
                    "error": str(exc)[:200],
                },
                flush=True,
            )
            continue

        table_counts = count_api_tables(tournament)
        if table_counts["tables"] == 0 or table_counts["participant_slots"] == 0:
            summary["no_api_tables"] += 1
            if len(examples["no_api_tables"]) < 20:
                examples["no_api_tables"].append(
                    {
                        "topdeck_tid": topdeck_tid,
                        "name": row.get("name"),
                        "zero_record_entries": row.get("zero_record_entries"),
                        **table_counts,
                    }
                )
            print(
                {
                    "index": index,
                    "total": len(tournaments),
                    "topdeck_tid": topdeck_tid,
                    "status": "no_api_tables",
                    **table_counts,
                },
                flush=True,
            )
            continue

        summary["api_table_tournaments"] += 1
        if not apply:
            print(
                {
                    "index": index,
                    "total": len(tournaments),
                    "topdeck_tid": topdeck_tid,
                    "status": "would_reingest",
                    "zero_record_entries": row.get("zero_record_entries"),
                    **table_counts,
                },
                flush=True,
            )
            continue

        result = ingester.process_tournament(tournament)
        summary["reingested"] += 1
        print(
            {
                "index": index,
                "total": len(tournaments),
                "topdeck_tid": topdeck_tid,
                "status": "reingested",
                "zero_record_entries": row.get("zero_record_entries"),
                "result": result,
                **table_counts,
            },
            flush=True,
        )

    post_backfill = backfill_zero_entries_global(client, apply=apply)
    return {
        "candidate_tournaments": len(tournaments),
        "summary": dict(summary),
        "examples": dict(examples),
        "post_reingest_zero_entry_backfill": post_backfill,
        "applied": apply,
    }


def update_entry_counts(client: Client, updates: list[dict[str, Any]]) -> None:
    for start in range(0, len(updates), 200):
        chunk = updates[start : start + 200]
        upsert_batched(client, "tournament_entries", chunk, on_conflict="id")


def backfill_tournament(
    client: Client,
    tournament: dict[str, Any],
    *,
    apply: bool,
    only_zero_records: bool,
) -> dict[str, Any]:
    tournament_id = str(tournament["id"])
    entries = fetch_all(
        client,
        "tournament_entries",
        columns="id,tournament_id,player_id,commander_id,points,wins,losses,draws,byes",
        filters=[("tournament_id", "eq", tournament_id)],
    )
    entry_ids = [str(row["id"]) for row in entries if row.get("id")]
    observed_by_entry = participant_counts_by_entry(client, entry_ids)

    updates: list[dict[str, Any]] = []
    entries_with_games = 0
    for entry in entries:
        entry_id = str(entry["id"])
        observed = observed_by_entry.get(entry_id)
        if not observed:
            continue
        entries_with_games += 1
        current = Counter(
            {
                "win": parse_int(entry.get("wins")),
                "loss": parse_int(entry.get("losses")),
                "draw": parse_int(entry.get("draws")),
                "bye": parse_int(entry.get("byes")),
            }
        )
        if only_zero_records and sum(current.values()) != 0:
            continue
        if any(current[result] != observed.get(result, 0) for result in ("win", "loss", "draw", "bye")):
            updates.append(
                {
                    "id": entry_id,
                    "tournament_id": entry["tournament_id"],
                    "player_id": entry["player_id"],
                    "commander_id": entry["commander_id"],
                    "points": parse_int(entry.get("points")),
                    "wins": observed.get("win", 0),
                    "losses": observed.get("loss", 0),
                    "draws": observed.get("draw", 0),
                    "byes": observed.get("bye", 0),
                }
            )

    if apply:
        update_entry_counts(client, updates)

    return {
        "id": tournament_id,
        "name": tournament.get("name"),
        "player_count": tournament.get("player_count"),
        "entries": len(entries),
        "entries_with_games": entries_with_games,
        "updates": len(updates),
        "applied": apply,
    }


def backfill_zero_entries_global(client: Client, *, apply: bool) -> dict[str, Any]:
    entries = fetch_zero_record_entries(client)
    entry_ids = [str(row["id"]) for row in entries if row.get("id")]
    observed_by_entry = participant_counts_by_entry(client, entry_ids)

    updates: list[dict[str, Any]] = []
    tournament_ids: set[str] = set()
    for entry in entries:
        entry_id = str(entry["id"])
        observed = observed_by_entry.get(entry_id)
        if not observed or sum(observed.values()) == 0:
            continue
        tournament_ids.add(str(entry["tournament_id"]))
        updates.append(
            {
                "id": entry_id,
                "tournament_id": entry["tournament_id"],
                "player_id": entry["player_id"],
                "commander_id": entry["commander_id"],
                "points": parse_int(entry.get("points")),
                "wins": observed.get("win", 0),
                "losses": observed.get("loss", 0),
                "draws": observed.get("draw", 0),
                "byes": observed.get("bye", 0),
            }
        )

    if apply:
        update_entry_counts(client, updates)

    return {
        "zero_record_entries": len(entries),
        "entries_with_games": len(updates),
        "tournaments_with_updates": len(tournament_ids),
        "total_updates": len(updates),
        "applied": apply,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournament-id", default=None)
    parser.add_argument("--min-player-count", type=int, default=200)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--global-zero-records",
        action="store_true",
        help="Backfill all zero-record entries directly instead of scanning tournament-by-tournament.",
    )
    parser.add_argument(
        "--refresh-topdeck-zero-record-tournaments",
        action="store_true",
        help=(
            "Fetch zero-record tournaments from TopDeck, reingest games/game_participants "
            "when tables are available, then backfill entry records."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit for --refresh-topdeck-zero-record-tournaments.",
    )
    parser.add_argument(
        "--only-no-games",
        action="store_true",
        help="With --refresh-topdeck-zero-record-tournaments, only reingest tournaments with no existing games.",
    )
    parser.add_argument(
        "--only-zero-records",
        action="store_true",
        help="Only update entries whose current wins+losses+draws+byes total is zero.",
    )
    args = parser.parse_args()

    load_local_env()
    client = get_supabase_client(url=os.environ["SUPABASE_URL"], key=os.environ["SUPABASE_SERVICE_KEY"])
    if args.refresh_topdeck_zero_record_tournaments:
        topdeck_api_key = os.environ.get("TOPDECK_API_KEY")
        if not topdeck_api_key:
            raise SystemExit("TOPDECK_API_KEY is required")
        topdeck = TopDeckClient(topdeck_api_key)
        print(
            refresh_topdeck_zero_record_tournaments(
                client,
                topdeck,
                apply=args.apply,
                limit=args.limit,
                only_no_games=args.only_no_games,
            ),
            flush=True,
        )
        return

    if args.global_zero_records:
        print(backfill_zero_entries_global(client, apply=args.apply), flush=True)
        return

    tournaments = fetch_target_tournaments(
        client,
        tournament_id=args.tournament_id,
        min_player_count=args.min_player_count,
    )
    total_updates = 0
    for tournament in tournaments:
        result = backfill_tournament(
            client,
            tournament,
            apply=args.apply,
            only_zero_records=args.only_zero_records,
        )
        total_updates += result["updates"]
        print(result, flush=True)
    print(
        {
            "tournaments": len(tournaments),
            "total_updates": total_updates,
            "applied": args.apply,
        },
        flush=True,
    )


if __name__ == "__main__":
    main()
