"""Read-only historical usage data for commander backtests."""

from __future__ import annotations

import os
import sys
from datetime import UTC, date, datetime, time
from typing import Any

import psycopg2
import psycopg2.extras

from ingest import SUPABASE_REST_BASE, load_local_env
from rebuild_player_commander_profiles import fetch_usage_rows_via_db, fetch_usage_rows_via_rest, normalize_usage_rows
from supabase import create_client

UTC = UTC


def normalize_usage_start_dates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        start_date = row.get("start_date")
        if isinstance(start_date, datetime):
            normalized.append({**row, "start_date": start_date.isoformat()})
        elif isinstance(start_date, date):
            normalized.append({**row, "start_date": datetime.combine(start_date, time.min).isoformat()})
        else:
            normalized.append(row)
    return normalized


def fetch_usage_rows_for_target_window_via_db(
    db_url: str,
    *,
    since: date,
    limit_targets: int | None = None,
) -> list[dict[str, Any]]:
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required for direct database reads")

    limit_clause = "LIMIT %(limit_targets)s" if limit_targets else ""
    sql = f"""
        WITH target_rows AS (
            SELECT te.player_id, t.start_date, te.id
            FROM tournament_entries te
            JOIN players p ON p.id = te.player_id
            JOIN commanders c ON c.id = te.commander_id
            JOIN tournaments t ON t.id = te.tournament_id
            WHERE p.topdeck_id IS NOT NULL
              AND c.name IS NOT NULL
              AND lower(btrim(c.name)) <> 'unknown commander'
              AND t.start_date::date >= %(since)s
            ORDER BY t.start_date DESC, te.id DESC
            {limit_clause}
        ),
        target_players AS (
            SELECT DISTINCT player_id FROM target_rows
        )
        SELECT
            te.player_id,
            te.decklist_url,
            p.topdeck_id,
            p.name AS player_name,
            c.name AS commander_name,
            t.id AS tournament_id,
            t.name AS tournament_name,
            t.start_date,
            t.topdeck_tid
        FROM tournament_entries te
        JOIN target_players tp ON tp.player_id = te.player_id
        JOIN players p ON p.id = te.player_id
        JOIN commanders c ON c.id = te.commander_id
        JOIN tournaments t ON t.id = te.tournament_id
        WHERE p.topdeck_id IS NOT NULL
          AND c.name IS NOT NULL
        ORDER BY te.player_id ASC, t.start_date ASC, te.id ASC
    """
    params: dict[str, Any] = {"since": since.isoformat()}
    if limit_targets:
        params["limit_targets"] = int(limit_targets)

    with psycopg2.connect(db_url, connect_timeout=15) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]


def load_usage_rows(since: date | None = None, limit_targets: int | None = None) -> list[dict[str, Any]]:
    load_local_env()
    supabase_url = os.environ.get("SUPABASE_URL", SUPABASE_REST_BASE)
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_key:
        raise SystemExit("SUPABASE_SERVICE_KEY is required")
    db_url = os.environ.get("SUPABASE_DB_URL")
    if db_url:
        try:
            if since:
                return normalize_usage_start_dates(
                    normalize_usage_rows(
                        fetch_usage_rows_for_target_window_via_db(
                            db_url,
                            since=since,
                            limit_targets=limit_targets,
                        ),
                        datetime.now(UTC).date(),
                    )
                )
            return normalize_usage_start_dates(
                normalize_usage_rows(fetch_usage_rows_via_db(db_url), datetime.now(UTC).date())
            )
        except Exception as exc:
            print(f"Direct database read failed, falling back to REST: {exc}", file=sys.stderr)
    client = create_client(supabase_url, supabase_key)
    return normalize_usage_start_dates(
        normalize_usage_rows(fetch_usage_rows_via_rest(client), datetime.now(UTC).date())
    )
