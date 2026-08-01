#!/usr/bin/env python3
"""Audit TopDeck posted pairings against normalized Supabase games.

Examples:
  PYTHONPATH=packages/backend/src python3 packages/backend/src/audit_topdeck_pairings.py \
    --topdeck-tid commander-invitational-2

  PYTHONPATH=packages/backend/src python3 packages/backend/src/audit_topdeck_pairings.py \
    --tids-file packages/backend/data/large_tournament_tids.txt

  PYTHONPATH=packages/backend/src python3 packages/backend/src/audit_topdeck_pairings.py \
    --topdeck-tid commander-invitational-2 --apply-dedupe
"""

from __future__ import annotations

import argparse
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests

from ingest import SupabaseClient, TopDeckClient, load_local_env, load_tids


@dataclass(frozen=True)
class PostedTable:
    round_number: int
    table_number: int
    player_topdeck_ids: frozenset[str]


@dataclass(frozen=True)
class StoredGame:
    game_id: str
    round_number: int
    table_number: int
    player_topdeck_ids: frozenset[str]


@dataclass(frozen=True)
class TournamentAudit:
    topdeck_tid: str
    tournament_id: str | None
    tournament_name: str | None
    posted_tables: list[PostedTable]
    stored_games: list[StoredGame]
    source_matching_game_ids: set[str]
    duplicate_delete_candidates: list[StoredGame]
    unsafe_duplicate_groups: list[tuple[tuple[int, frozenset[str]], list[StoredGame], list[PostedTable]]]
    missing_posted_tables: list[PostedTable]
    extra_stored_games: list[StoredGame]

    @property
    def can_apply_dedupe(self) -> bool:
        return (
            self.tournament_id is not None
            and bool(self.duplicate_delete_candidates)
            and not self.unsafe_duplicate_groups
            and not self.missing_posted_tables
        )


def chunked(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def posted_tables_from_topdeck(tournament: dict) -> list[PostedTable]:
    posted: list[PostedTable] = []
    for round_data in tournament.get("rounds") or []:
        round_number = round_data.get("round")
        if not isinstance(round_number, int):
            continue
        for fallback_table_number, table in enumerate(round_data.get("tables") or [], start=1):
            players = frozenset(
                str(player.get("id"))
                for player in table.get("players") or []
                if player.get("id")
            )
            if len(players) < 2:
                continue
            table_number_value = table.get("table") or table.get("table_number") or table.get("tableNumber")
            try:
                table_number = int(table_number_value)
            except (TypeError, ValueError):
                table_number = fallback_table_number
            posted.append(
                PostedTable(
                    round_number=int(round_number),
                    table_number=table_number,
                    player_topdeck_ids=players,
                )
            )
    return posted


def fetch_tournament_row(client: SupabaseClient, topdeck_tid: str) -> dict | None:
    rows = client.select(
        "tournaments",
        {
            "select": "id,name,topdeck_tid,swiss_rounds,player_count",
            "topdeck_tid": f"eq.{topdeck_tid}",
            "limit": "2",
        },
    )
    if not rows:
        return None
    if len(rows) > 1:
        raise RuntimeError(f"Multiple Supabase tournament rows found for topdeck_tid={topdeck_tid}")
    return rows[0]


def fetch_stored_games(client: SupabaseClient, tournament_id: str) -> list[StoredGame]:
    rows: list[dict] = []
    offset = 0
    limit = 1000
    while True:
        page = client.select(
            "global_elo_game_results",
            {
                "select": "game_id,round_number,table_number,player_id,players(topdeck_id)",
                "tournament_id": f"eq.{tournament_id}",
                "round_number": "not.is.null",
                "order": "round_number.asc,table_number.asc,game_id.asc",
                "limit": str(limit),
                "offset": str(offset),
            },
        )
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit

    grouped: dict[str, dict] = defaultdict(lambda: {"round_number": None, "table_number": None, "players": set()})
    for row in rows:
        game_id = row.get("game_id")
        round_number = row.get("round_number")
        table_number = row.get("table_number")
        if not game_id or round_number is None or table_number is None:
            continue
        grouped[str(game_id)]["round_number"] = int(round_number)
        grouped[str(game_id)]["table_number"] = int(table_number)
        player_payload = row.get("players") or {}
        topdeck_id = player_payload.get("topdeck_id")
        grouped[str(game_id)]["players"].add(str(topdeck_id or row.get("player_id")))

    games: list[StoredGame] = []
    for game_id, payload in grouped.items():
        players = frozenset(payload["players"])
        if len(players) < 2:
            continue
        games.append(
            StoredGame(
                game_id=game_id,
                round_number=int(payload["round_number"]),
                table_number=int(payload["table_number"]),
                player_topdeck_ids=players,
            )
        )
    return games


def audit_tournament(topdeck_client: TopDeckClient, supabase_client: SupabaseClient, topdeck_tid: str) -> TournamentAudit:
    topdeck_tournament = topdeck_client.get_tournament(topdeck_tid)
    posted_tables = posted_tables_from_topdeck(topdeck_tournament)
    tournament_row = fetch_tournament_row(supabase_client, topdeck_tid)
    tournament_id = str(tournament_row["id"]) if tournament_row and tournament_row.get("id") else None
    stored_games = fetch_stored_games(supabase_client, tournament_id) if tournament_id else []

    posted_by_round_players: dict[tuple[int, frozenset[str]], list[PostedTable]] = defaultdict(list)
    for table in posted_tables:
        posted_by_round_players[(table.round_number, table.player_topdeck_ids)].append(table)

    stored_by_round_players: dict[tuple[int, frozenset[str]], list[StoredGame]] = defaultdict(list)
    for game in stored_games:
        stored_by_round_players[(game.round_number, game.player_topdeck_ids)].append(game)

    source_matching_game_ids: set[str] = set()
    duplicate_delete_candidates: list[StoredGame] = []
    unsafe_duplicate_groups: list[tuple[tuple[int, frozenset[str]], list[StoredGame], list[PostedTable]]] = []

    for key, games in stored_by_round_players.items():
        posted_group = posted_by_round_players.get(key, [])
        if not posted_group:
            continue
        posted_table_numbers = {table.table_number for table in posted_group}
        keepers = [game for game in games if game.table_number in posted_table_numbers]
        if len(games) == len(posted_group) and len(keepers) == len(games):
            source_matching_game_ids.update(game.game_id for game in keepers)
            continue
        if len(keepers) == len(posted_group) and len(games) > len(posted_group):
            source_matching_game_ids.update(game.game_id for game in keepers)
            duplicate_delete_candidates.extend(game for game in games if game.game_id not in source_matching_game_ids)
        elif len(games) != len(posted_group):
            unsafe_duplicate_groups.append((key, games, posted_group))

    stored_counter = Counter((game.round_number, game.player_topdeck_ids) for game in stored_games)
    posted_counter = Counter((table.round_number, table.player_topdeck_ids) for table in posted_tables)

    missing_posted_tables: list[PostedTable] = []
    for table in posted_tables:
        key = (table.round_number, table.player_topdeck_ids)
        if stored_counter[key] <= 0:
            missing_posted_tables.append(table)
        else:
            stored_counter[key] -= 1

    extra_stored_games: list[StoredGame] = []
    remaining_posted_counter = Counter((table.round_number, table.player_topdeck_ids) for table in posted_tables)
    for game in stored_games:
        key = (game.round_number, game.player_topdeck_ids)
        if remaining_posted_counter[key] <= 0:
            extra_stored_games.append(game)
        else:
            remaining_posted_counter[key] -= 1

    return TournamentAudit(
        topdeck_tid=topdeck_tid,
        tournament_id=tournament_id,
        tournament_name=str(tournament_row.get("name")) if tournament_row else topdeck_tournament.get("name"),
        posted_tables=posted_tables,
        stored_games=stored_games,
        source_matching_game_ids=source_matching_game_ids,
        duplicate_delete_candidates=duplicate_delete_candidates,
        unsafe_duplicate_groups=unsafe_duplicate_groups,
        missing_posted_tables=missing_posted_tables,
        extra_stored_games=extra_stored_games,
    )


def delete_games(supabase_url: str, service_key: str, game_ids: list[str]) -> int:
    deleted = 0
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    for chunk in chunked(game_ids, 50):
        response = requests.delete(
            f"{supabase_url.rstrip('/')}/rest/v1/games",
            headers=headers,
            params={"id": f"in.({','.join(chunk)})"},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        deleted += len(payload) if isinstance(payload, list) else len(chunk)
    return deleted


def print_audit(audit: TournamentAudit, *, show_samples: int) -> None:
    print(f"\nEVENT {audit.topdeck_tid}")
    print(f"  name={audit.tournament_name}")
    print(f"  tournament_id={audit.tournament_id or 'missing'}")
    print(f"  topdeck_tables={len(audit.posted_tables)} stored_games={len(audit.stored_games)}")
    print(f"  missing_posted_tables={len(audit.missing_posted_tables)}")
    print(f"  extra_stored_games={len(audit.extra_stored_games)}")
    print(f"  duplicate_delete_candidates={len(audit.duplicate_delete_candidates)}")
    print(f"  unsafe_duplicate_groups={len(audit.unsafe_duplicate_groups)}")

    if audit.duplicate_delete_candidates:
        by_round = Counter(game.round_number for game in audit.duplicate_delete_candidates)
        print(f"  delete_candidates_by_round={dict(sorted(by_round.items()))}")
    for game in audit.duplicate_delete_candidates[:show_samples]:
        print(
            "    delete_candidate "
            f"game_id={game.game_id} round={game.round_number} table={game.table_number} players={len(game.player_topdeck_ids)}"
        )
    for table in audit.missing_posted_tables[:show_samples]:
        print(
            "    missing_posted "
            f"round={table.round_number} table={table.table_number} players={len(table.player_topdeck_ids)}"
        )
    for game in audit.extra_stored_games[:show_samples]:
        print(
            "    extra_stored "
            f"game_id={game.game_id} round={game.round_number} table={game.table_number} players={len(game.player_topdeck_ids)}"
        )
    for key, games, posted in audit.unsafe_duplicate_groups[:show_samples]:
        print(
            "    unsafe_group "
            f"round={key[0]} players={len(key[1])} stored={len(games)} posted={len(posted)} "
            f"stored_tables={[game.table_number for game in games]} posted_tables={[table.table_number for table in posted]}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topdeck-tid", action="append", default=[], help="TopDeck tournament id/slug to audit")
    parser.add_argument("--tids-file", type=Path, help="File containing TopDeck tournament ids to audit")
    parser.add_argument(
        "--apply-dedupe",
        action="store_true",
        help="Delete safe duplicate Supabase games, keeping games whose table numbers match TopDeck",
    )
    parser.add_argument("--show-samples", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_local_env()
    topdeck_tids = list(args.topdeck_tid)
    if args.tids_file:
        topdeck_tids.extend(load_tids(args.tids_file))
    seen: set[str] = set()
    topdeck_tids = [tid for tid in topdeck_tids if tid and not (tid in seen or seen.add(tid))]
    if not topdeck_tids:
        raise SystemExit("Provide --topdeck-tid or --tids-file")

    topdeck_api_key = os.environ.get("TOPDECK_API_KEY")
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not topdeck_api_key or not supabase_url or not supabase_key:
        raise SystemExit("TOPDECK_API_KEY, SUPABASE_URL, and SUPABASE_SERVICE_KEY are required")

    topdeck_client = TopDeckClient(topdeck_api_key)
    supabase_client = SupabaseClient(supabase_url, supabase_key)

    total_deleted = 0
    for topdeck_tid in topdeck_tids:
        audit = audit_tournament(topdeck_client, supabase_client, topdeck_tid)
        print_audit(audit, show_samples=args.show_samples)
        if args.apply_dedupe:
            if not audit.can_apply_dedupe:
                print("  dedupe_skipped=unsafe_or_no_candidates")
                continue
            game_ids = [game.game_id for game in audit.duplicate_delete_candidates]
            deleted = delete_games(supabase_url, supabase_key, game_ids)
            total_deleted += deleted
            print(f"  deleted_games={deleted}")
    if args.apply_dedupe:
        print(f"\ntotal_deleted_games={total_deleted}")


if __name__ == "__main__":
    main()
