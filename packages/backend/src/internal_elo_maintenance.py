"""Full-history, atomic publication of the versioned internal Elo model."""

from __future__ import annotations

import csv
import gzip
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json

from internal_elo import (
    LEAGUE_MULTIPLIER,
    MODEL_VERSION,
    SWISS_DRAW_K,
    SWISS_SEAT_OFFSETS,
    SWISS_WIN_K,
    TOPCUT_SEAT_OFFSETS,
    TOPCUT_WIN_K,
)

TABLES = (
    "global_elo_ratings",
    "global_elo_state_activity",
    "global_elo_game_events",
    "global_elo_active_leaderboard",
    "global_elo_player_profile_summaries",
)
SCOPES = (
    "region_type='global' AND region_key='ALL'",
    "region_type='state'",
    "region_type='global' AND region_key='ALL'",
    "TRUE",
    "TRUE",
)
SOURCE = "FROM global_elo_game_results r JOIN tournaments t ON t.id=r.tournament_id WHERE r.start_date <= %s"
FINGERPRINT_SQL = (
    """WITH h AS (
 SELECT md5(jsonb_build_array(r.game_id::text,r.player_id::text,r.entry_id::text,r.result,r.seat_position,
 to_char(r.start_date AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),r.round_number,r.round_name,
 r.table_number,r.is_draw,r.tournament_id::text,r.state,r.country,r.city,r.player_name,r.topdeck_id,
 r.tournament_name,COALESCE(t.is_league,false))::text) h
 """
    + SOURCE
    + """) SELECT count(*),sum((('x'||left(h,16))::bit(64)::bigint)::numeric),
 sum((('x'||right(h,16))::bit(64)::bigint)::numeric) FROM h"""
)


def connect():
    return psycopg2.connect(
        os.environ["SUPABASE_DB_URL"],
        port=5432,
        connect_timeout=30,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )


def fetch_snapshot(heartbeat: Callable[[], None] = lambda: None) -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout='1800s'")
            cur.execute("SELECT now()")
            cutoff = cur.fetchone()[0]
            cur.execute(FINGERPRINT_SQL, (cutoff,))
            fingerprint = list(map(int, cur.fetchone()))
        results = []
        with conn.cursor(name="internal_elo_input") as cur:
            cur.execute("SELECT r.*,COALESCE(t.is_league,false) AS is_league " + SOURCE, (cutoff,))
            while batch := cur.fetchmany(20000):
                columns = [d[0] for d in cur.description]
                for values in batch:
                    row = dict(zip(columns, values, strict=True))
                    row["start_date"] = row["start_date"].isoformat()
                    results.append(row)
                heartbeat()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM topdeck_player_elos")
            columns = [d[0] for d in cur.description]
            key = "topdeck_id" if "topdeck_id" in columns else "uid"
            topdeck = {
                str(row[key]): float(row["elo"])
                for values in cur.fetchall()
                if (row := dict(zip(columns, values, strict=True))).get(key) and row.get("elo") is not None
            }
            cur.execute(FINGERPRINT_SQL, (cutoff,))
            if list(map(int, cur.fetchone())) != fingerprint:
                raise RuntimeError("Elo source changed during snapshot; retry the full rebuild")
    return {
        "results": results,
        "topdeck_elos": topdeck,
        "cutoff": cutoff,
        "fingerprint_sql": FINGERPRINT_SQL,
        "fingerprint": fingerprint,
    }


def prepare(snapshot: dict) -> dict:
    from rebuild_global_elo_tables import build_state_from_results, finalize_rows

    ratings, activity, meta, events = build_state_from_results(snapshot["results"])
    outputs = finalize_rows(snapshot["topdeck_elos"], ratings, activity, meta, events)
    return {
        "cutoff": snapshot["cutoff"],
        "fingerprint_sql": snapshot["fingerprint_sql"],
        "fingerprint": snapshot["fingerprint"],
        "tables": dict(zip(TABLES, outputs, strict=True)),
    }


def publish(
    prepared: dict, backup_dir: Path, heartbeat: Callable[[], None] = lambda: None, migration: str | None = None
) -> dict:
    """Stage and back up all outputs, then swap them under one transaction.

    Abort if any source row changed since preparation. Raw game outcomes stay
    intact. New model results, ratings, and version marker commit together.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SET statement_timeout='1800s'")
        cur.execute("SET lock_timeout='30s'")
        cur.execute("SELECT pg_try_advisory_xact_lock(hashtext('elo-future-date-recovery'))")
        if not cur.fetchone()[0]:
            raise RuntimeError("Another Elo publication is running")
        for table in TABLES:
            rows = prepared["tables"][table]
            if not rows:
                raise ValueError(f"Refusing to publish empty {table}")
            columns = sorted({key for row in rows for key in row})
            if table != "global_elo_game_events":
                columns.append("updated_at")
            stage = "tuned_" + table
            cur.execute(
                sql.SQL("CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(
                    sql.Identifier(stage), sql.Identifier(table)
                )
            )
            csv_path = backup_dir / (table + ".prepared.csv")

            def value(row, key):
                v = prepared["cutoff"].isoformat() if key == "updated_at" else row.get(key)
                if v is None:
                    return "\\N"
                return json.dumps(v) if isinstance(v, (dict, list, bool)) else v

            with csv_path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerows([value(row, col) for col in columns] for row in rows)
            command = sql.SQL(r"COPY {} ({}) FROM STDIN WITH (FORMAT CSV, NULL '\N')").format(
                sql.Identifier(stage), sql.SQL(",").join(map(sql.Identifier, columns))
            )
            with csv_path.open("rb") as handle:
                cur.copy_expert(command.as_string(conn), handle, size=1024 * 1024)
            cur.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(stage)))
            if cur.fetchone()[0] != len(rows):
                raise RuntimeError(f"Incomplete staging: {table}")
            print(f"Staged {table}: {len(rows):,}", flush=True)
            heartbeat()
        cur.execute("CREATE UNIQUE INDEX ON tuned_global_elo_game_events(game_id,player_id)")
        cur.execute("CREATE INDEX ON tuned_global_elo_game_events(player_id)")
        cur.execute("ANALYZE tuned_global_elo_game_events")
        # Lock inputs before the final check and backups so rollback artifacts
        # represent the exact state replaced by this transaction.
        for table in sorted(
            set(TABLES) | {"games", "game_participants", "tournament_entries", "tournaments", "players"}
        ):
            cur.execute(sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(sql.Identifier(table)))
        cur.execute(prepared["fingerprint_sql"], (prepared["cutoff"],))
        if list(map(int, cur.fetchone())) != prepared["fingerprint"]:
            raise RuntimeError("Live source changed after preparation; publication aborted")
        for table in TABLES:
            with gzip.open(backup_dir / (table + ".before.csv.gz"), "wb", compresslevel=1) as handle:
                cur.copy_expert(
                    sql.SQL("COPY {} TO STDOUT WITH (FORMAT CSV, HEADER TRUE)")
                    .format(sql.Identifier(table))
                    .as_string(conn),
                    handle,
                )
            print(f"Backed up {table}", flush=True)
            heartbeat()
        cur.execute(
            "SELECT count(*) FROM tuned_global_elo_game_events WHERE game_date > %s OR game_date IS NULL",
            (prepared["cutoff"],),
        )
        if cur.fetchone()[0]:
            raise RuntimeError("Future/undated events in staged Elo")
        cur.execute("""SELECT count(*) FROM tuned_global_elo_ratings r WHERE
          r.games_played != (SELECT count(*) FROM tuned_global_elo_game_events e WHERE e.player_id=r.player_id)
          OR r.games_played != r.wins+r.losses+r.draws""")
        if cur.fetchone()[0]:
            raise RuntimeError("Staged Elo counts do not match game events")
        cur.execute(
            """WITH eligible AS MATERIALIZED (
          SELECT game_id,player_id,result FROM global_elo_game_results WHERE start_date <= %s
          AND result IN ('win','draw','loss')),
          scoreable AS (SELECT game_id FROM eligible GROUP BY game_id
          HAVING count(DISTINCT player_id)>=2 AND bool_or(result IN ('win','draw')))
          SELECT count(*) FROM eligible r JOIN scoreable s USING(game_id)
          LEFT JOIN tuned_global_elo_game_events e ON e.game_id=r.game_id AND e.player_id=r.player_id
          WHERE e.game_id IS NULL""",
            (prepared["cutoff"],),
        )
        if cur.fetchone()[0]:
            raise RuntimeError("Staged Elo is missing eligible participants")
        # Preserve commander annotations maintained by the separate profile job.
        cur.execute("""UPDATE tuned_global_elo_player_profile_summaries n SET
          primary_commander_name=o.primary_commander_name,
          primary_commander_known_pct=o.primary_commander_known_pct
          FROM global_elo_player_profile_summaries o WHERE o.player_id=n.player_id""")
        if migration:
            cur.execute(migration)
        for table, scope in zip(TABLES, SCOPES, strict=True):
            cur.execute(sql.SQL("DELETE FROM {} WHERE " + scope).format(sql.Identifier(table)))
            cur.execute(
                sql.SQL("INSERT INTO {} SELECT * FROM {}").format(
                    sql.Identifier(table), sql.Identifier("tuned_" + table)
                )
            )
        parameters = {
            "swiss_seat_offsets": SWISS_SEAT_OFFSETS,
            "topcut_seat_offsets": TOPCUT_SEAT_OFFSETS,
            "swiss_win_K": SWISS_WIN_K,
            "swiss_draw_K": SWISS_DRAW_K,
            "topcut_win_K": TOPCUT_WIN_K,
            "league_multiplier": LEAGUE_MULTIPLIER,
            "divisor": 200,
        }
        cur.execute(
            """INSERT INTO internal_elo_model_runs(model_version,source_cutoff,parameters,counts)
          VALUES (%s,%s,%s,%s)""",
            (
                MODEL_VERSION,
                prepared["cutoff"],
                Json(parameters),
                Json({k: len(v) for k, v in prepared["tables"].items()}),
            ),
        )
        conn.commit()
    result = {
        "model_version": MODEL_VERSION,
        "source_cutoff": str(prepared["cutoff"]),
        "published_at": datetime.now(UTC).isoformat(),
        "counts": {k: len(v) for k, v in prepared["tables"].items()},
    }
    (backup_dir / "published.json").write_text(json.dumps(result, indent=2))
    return result


def run(*, apply: bool = False, heartbeat: Callable[[], None] = lambda: None) -> dict:
    snapshot = fetch_snapshot(heartbeat)
    prepared = prepare(snapshot)
    if not apply:
        return {k: len(v) for k, v in prepared["tables"].items()}
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return publish(prepared, Path("packages/backend/logs") / f"internal-elo-{stamp}", heartbeat)
