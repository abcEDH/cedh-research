#!/usr/bin/env python3
"""Import TopDeck's published EDH Elo snapshot into Supabase."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
import requests

from ingest import load_local_env


DEFAULT_ELO_URL = "https://images.topdeck.gg/elo/magic-the-gathering-edh.json"


def normalize_name(value: Any) -> str:
    name = str(value or "").strip()
    return name or "Unknown"


def normalize_username(value: Any) -> str | None:
    username = str(value or "").strip()
    return username or None


def load_elo_rows(url: str) -> list[dict[str, Any]]:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(f"Expected TopDeck Elo payload list, got {type(payload).__name__}")

    rows: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            continue
        topdeck_id = str(item.get("uid") or "").strip()
        if not topdeck_id:
            continue
        try:
            elo = float(item["elo"])
            games_played = int(item["gamesPlayed"])
            ranking = int(item["ranking"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Elo row at index {index}: {item}") from exc

        rows.append(
            {
                "topdeck_id": topdeck_id,
                "name": normalize_name(item.get("name")),
                "username": normalize_username(item.get("username")),
                "profile_image_url": normalize_username(item.get("profileImage")),
                "elo": elo,
                "games_played": games_played,
                "ranking": ranking,
            }
        )
    return rows


def apply_schema(conn: psycopg2.extensions.connection, migration_path: Path) -> None:
    with conn.cursor() as cursor:
        cursor.execute(migration_path.read_text())
    conn.commit()


def fetch_players_by_topdeck_id(
    conn: psycopg2.extensions.connection,
    topdeck_ids: list[str],
) -> dict[str, dict[str, Any]]:
    players: dict[str, dict[str, Any]] = {}
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
        for start in range(0, len(topdeck_ids), 1000):
            chunk = topdeck_ids[start : start + 1000]
            cursor.execute(
                """
                SELECT id, topdeck_id, name, topdeck_handle
                FROM players
                WHERE topdeck_id = ANY(%s)
                """,
                (chunk,),
            )
            for row in cursor.fetchall():
                players[str(row["topdeck_id"])] = dict(row)
    return players


def upsert_elo_rows(
    conn: psycopg2.extensions.connection,
    rows: list[dict[str, Any]],
    players_by_topdeck_id: dict[str, dict[str, Any]],
    source_url: str,
) -> int:
    """Upsert the fetched TopDeck Elo snapshot and prune rows that fell off it.

    This is a replace-snapshot import: any row in `topdeck_player_elos` whose
    `topdeck_id` is not present in the newly fetched `rows` is deleted in the
    same transaction as the upsert. TopDeck's published leaderboard drops
    players (e.g. banned cheaters) without notice, and previously a stale row
    for a delisted player would survive indefinitely, letting a defunct
    topdeck_elo/ranking snapshot linger and misrank real, active players on
    the homepage (see PR #263 / issue #252).

    As a safety guard, if `rows` is empty (e.g. a transient fetch/parse
    problem upstream) this aborts without deleting anything, since an empty
    snapshot is far more likely to indicate a fetch failure than a genuine
    leaderboard wipe.

    Returns the number of rows pruned.
    """
    if not rows:
        print("TopDeck Elo snapshot is empty; skipping upsert and prune to avoid data loss.")
        return 0

    fetched_at = datetime.now(timezone.utc)
    db_rows = [
        (
            row["topdeck_id"],
            players_by_topdeck_id.get(row["topdeck_id"], {}).get("id"),
            row["name"],
            row["username"],
            row["profile_image_url"],
            row["elo"],
            row["games_played"],
            row["ranking"],
            source_url,
            fetched_at,
        )
        for row in rows
    ]
    snapshot_topdeck_ids = [row["topdeck_id"] for row in rows]

    with conn.cursor() as cursor:
        psycopg2.extras.execute_values(
            cursor,
            """
            INSERT INTO topdeck_player_elos (
              topdeck_id, player_id, name, username, profile_image_url,
              elo, games_played, ranking, source_url, fetched_at
            )
            VALUES %s
            ON CONFLICT (topdeck_id) DO UPDATE SET
              player_id = EXCLUDED.player_id,
              name = EXCLUDED.name,
              username = EXCLUDED.username,
              profile_image_url = EXCLUDED.profile_image_url,
              elo = EXCLUDED.elo,
              games_played = EXCLUDED.games_played,
              ranking = EXCLUDED.ranking,
              source_url = EXCLUDED.source_url,
              fetched_at = EXCLUDED.fetched_at,
              updated_at = now()
            """,
            db_rows,
            page_size=1000,
        )

        cursor.execute(
            """
            DELETE FROM topdeck_player_elos
            WHERE NOT (topdeck_id = ANY(%s))
            """,
            (snapshot_topdeck_ids,),
        )
        pruned_count = cursor.rowcount

    conn.commit()
    print(f"Pruned {pruned_count} stale topdeck_player_elos row(s) not present in the latest snapshot.")
    return pruned_count


def repair_players_from_elo(
    conn: psycopg2.extensions.connection,
    rows: list[dict[str, Any]],
    players_by_topdeck_id: dict[str, dict[str, Any]],
) -> int:
    repair_rows: list[tuple[str, str, str | None]] = []
    for row in rows:
        player = players_by_topdeck_id.get(row["topdeck_id"])
        if not player:
            continue
        existing_name = str(player.get("name") or "").strip().lower()
        name = row["name"]
        username = row["username"]
        should_update_name = existing_name in ("", "unknown") and name.lower() != "unknown"
        should_update_handle = username and not player.get("topdeck_handle")
        if should_update_name or should_update_handle:
            repair_rows.append(
                (
                    row["topdeck_id"],
                    name if should_update_name else player["name"],
                    username if should_update_handle else player.get("topdeck_handle"),
                )
            )

    if not repair_rows:
        return 0

    with conn.cursor() as cursor:
        psycopg2.extras.execute_values(
            cursor,
            """
            UPDATE players AS p
            SET
              name = data.name,
              topdeck_handle = data.topdeck_handle,
              updated_at = now()
            FROM (VALUES %s) AS data(topdeck_id, name, topdeck_handle)
            WHERE p.topdeck_id = data.topdeck_id
            """,
            repair_rows,
            page_size=1000,
        )
    conn.commit()
    return len(repair_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import TopDeck published EDH Elo snapshot")
    parser.add_argument("--url", default=DEFAULT_ELO_URL)
    parser.add_argument("--skip-schema", action="store_true", help="Do not apply the table migration first")
    parser.add_argument("--no-player-repair", action="store_true", help="Do not repair Unknown player names/handles")
    args = parser.parse_args()

    load_local_env()
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("SUPABASE_DB_URL is required")

    rows = load_elo_rows(args.url)
    topdeck_ids = [row["topdeck_id"] for row in rows]

    conn = psycopg2.connect(db_url)
    try:
        if not args.skip_schema:
            migration_path = (
                Path(__file__).resolve().parents[1]
                / "supabase"
                / "migrations"
                / "20260415020000_topdeck_player_elos.sql"
            )
            apply_schema(conn, migration_path)

        players_by_topdeck_id = fetch_players_by_topdeck_id(conn, topdeck_ids)
        pruned_count = upsert_elo_rows(conn, rows, players_by_topdeck_id, args.url)
        repaired_count = 0
        if not args.no_player_repair:
            repaired_count = repair_players_from_elo(conn, rows, players_by_topdeck_id)
    finally:
        conn.close()

    print(
        "Imported "
        f"{len(rows)} TopDeck Elo rows; matched {len(players_by_topdeck_id)} existing players; "
        f"pruned {pruned_count} stale rows; repaired {repaired_count} player rows."
    )


if __name__ == "__main__":
    main()
