#!/usr/bin/env python3
"""Rebuild precomputed player commander profiles for Tournament Prep and profile views."""

from __future__ import annotations

import argparse
import logging
import os
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

import requests
from dateutil import parser as date_parser

from ingest import SUPABASE_REST_BASE, SupabaseClient, load_local_env

try:
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover
    psycopg2 = None


RECENCY_HALF_LIFE_DAYS = 24
PRIMARY_LOOKBACK_MONTHS = 6
FALLBACK_LOOKBACK_MONTHS = 12
MIN_PRIMARY_COMMANDER_ENTRIES = 2
PAGE_SIZE = 1000
UPSERT_CHUNK_SIZE = 200

logger = logging.getLogger("rebuild_player_commander_profiles")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def lookback_start_date(months: int, reference_date: date) -> str:
    year = reference_date.year
    month = reference_date.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(reference_date.day, days_in_month(year, month))
    return date(year, month, day).isoformat()


def days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days


def calculate_recency_weight(event_timestamp_ms: int, reference_timestamp_ms: int) -> float:
    if reference_timestamp_ms <= 0 or event_timestamp_ms <= 0:
        return 0.5
    age_in_days = max(0.0, (reference_timestamp_ms - event_timestamp_ms) / (1000 * 60 * 60 * 24))
    return 0.5 ** (age_in_days / RECENCY_HALF_LIFE_DAYS)


def build_topdeck_decklist_url(tournament_slug: str | None, topdeck_id: str | None) -> str | None:
    return f"https://topdeck.gg/deck/{tournament_slug}/{topdeck_id}" if tournament_slug and topdeck_id else None


def first_relation(value: Any) -> dict[str, Any] | None:
    if isinstance(value, list):
        return value[0] if value else None
    return value if isinstance(value, dict) else None


def is_known_commander(commander_name: str | None) -> bool:
    normalized = (commander_name or "").strip().lower()
    return bool(normalized) and normalized != "unknown commander"


def chunked(values: list[Any], size: int) -> list[list[Any]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def fetch_existing_profile_player_ids(client: SupabaseClient) -> list[str]:
    player_ids: list[str] = []
    last_player_id: str | None = None
    while True:
        filters = {
            "select": "player_id",
            "order": "player_id.asc",
            "limit": str(PAGE_SIZE),
        }
        if last_player_id:
            filters["player_id"] = f"gt.{last_player_id}"
        page = client.select("player_commander_profiles", filters)
        if not page:
            break
        player_ids.extend(
            row["player_id"]
            for row in page
            if isinstance(row.get("player_id"), str) and row["player_id"]
        )
        last_player_id = page[-1].get("player_id")
        if len(page) < PAGE_SIZE:
            break
    return player_ids


def delete_profile_rows_by_player_ids(client: SupabaseClient, player_ids: list[str]) -> int:
    deleted = 0
    endpoint = f"{client.url}/rest/v1/player_commander_profiles"
    for chunk in chunked(player_ids, UPSERT_CHUNK_SIZE):
        if not chunk:
            continue
        response = requests.delete(
            endpoint,
            headers=client.headers,
            params={"player_id": f"in.({','.join(chunk)})"},
            timeout=60,
        )
        response.raise_for_status()
        deleted += len(chunk)
    return deleted


def fetch_usage_rows_via_rest(client: SupabaseClient) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    last_id: str | None = None
    while True:
        filters = {
            "select": "id,player_id,decklist_url,players!inner(topdeck_id,name),commanders!inner(name),tournaments!inner(start_date,topdeck_tid)",
            "order": "id.asc",
            "limit": str(PAGE_SIZE),
        }
        if last_id:
            filters["id"] = f"gt.{last_id}"
        page = client.select(
            "tournament_entries",
            filters,
        )
        if not page:
            break
        rows.extend(page)
        last_id = page[-1].get("id")
        if len(rows) % 10_000 == 0:
            logger.info("Fetched %s rows via REST...", len(rows))
        if len(page) < PAGE_SIZE:
            break
    return rows


def fetch_usage_rows_via_db(db_url: str) -> list[dict[str, Any]]:
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required for direct database reads")

    sql = """
        SELECT
            te.player_id,
            te.decklist_url,
            p.topdeck_id,
            p.name AS player_name,
            c.name AS commander_name,
            t.start_date,
            t.topdeck_tid
        FROM tournament_entries te
        JOIN players p ON p.id = te.player_id
        JOIN commanders c ON c.id = te.commander_id
        JOIN tournaments t ON t.id = te.tournament_id
        WHERE p.topdeck_id IS NOT NULL
          AND c.name IS NOT NULL
        ORDER BY te.player_id ASC
    """

    with psycopg2.connect(db_url) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]


def normalize_usage_rows(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in raw_rows:
        player = first_relation(row.get("players"))
        commander = first_relation(row.get("commanders"))
        tournament = first_relation(row.get("tournaments"))
        topdeck_id = row.get("topdeck_id") or (player.get("topdeck_id") if player else None)
        commander_name = row.get("commander_name") or (commander.get("name") if commander else None)
        player_name = row.get("player_name") or (player.get("name") if player else None)
        start_date = row.get("start_date") or (tournament.get("start_date") if tournament else None)
        topdeck_tid = row.get("topdeck_tid") or (tournament.get("topdeck_tid") if tournament else None)
        if not topdeck_id or not is_known_commander(commander_name):
            continue
        normalized.append(
            {
                "player_id": row.get("player_id"),
                "topdeck_id": topdeck_id,
                "player_name": player_name or "Unknown",
                "commander_name": commander_name,
                "start_date": start_date,
                "decklist_url": row.get("decklist_url"),
                "topdeck_decklist_url": build_topdeck_decklist_url(
                    topdeck_tid,
                    topdeck_id,
                ),
            }
        )
    return normalized


def latest_usage_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(rows, key=lambda row: row.get("start_date") or "", default=None)


def select_commander_forecast_rows(
    rows_by_topdeck_id: dict[str, list[dict[str, Any]]],
    reference_date: date,
) -> dict[str, list[dict[str, Any]]]:
    primary_lookback_start = lookback_start_date(PRIMARY_LOOKBACK_MONTHS, reference_date)
    fallback_lookback_start = lookback_start_date(FALLBACK_LOOKBACK_MONTHS, reference_date)
    selected: dict[str, list[dict[str, Any]]] = {}

    for topdeck_id, player_rows in rows_by_topdeck_id.items():
        player_rows = [row for row in player_rows if row.get("commander_name") and row.get("start_date")]
        primary_rows = [
            row
            for row in player_rows
            if row["start_date"] and row["start_date"] >= primary_lookback_start
        ]
        chosen_rows = list(primary_rows)

        if len(primary_rows) < MIN_PRIMARY_COMMANDER_ENTRIES:
            fallback_rows = [
                row
                for row in player_rows
                if row["start_date"]
                and fallback_lookback_start <= row["start_date"] < primary_lookback_start
            ]
            chosen_rows.extend(fallback_rows)

        if not chosen_rows:
            older_rows = [
                row for row in player_rows if row["start_date"] and row["start_date"] < fallback_lookback_start
            ]
            last_known = latest_usage_row(older_rows)
            if last_known:
                chosen_rows.append(last_known)

        selected[topdeck_id] = chosen_rows

    return selected


def build_profile_rows(usage_rows: list[dict[str, Any]], reference_date: date) -> list[dict[str, Any]]:
    rows_by_topdeck_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    player_ids_by_topdeck_id: dict[str, str] = {}
    player_names_by_topdeck_id: dict[str, str] = {}

    for row in usage_rows:
        topdeck_id = row["topdeck_id"]
        rows_by_topdeck_id[topdeck_id].append(row)
        if row.get("player_id"):
            player_ids_by_topdeck_id[topdeck_id] = row["player_id"]
        if row.get("player_name"):
            player_names_by_topdeck_id[topdeck_id] = row["player_name"]

    selected_by_topdeck_id = select_commander_forecast_rows(rows_by_topdeck_id, reference_date)
    reference_timestamp_ms = int(
        datetime.combine(reference_date, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000
    )

    profile_rows: list[dict[str, Any]] = []
    for topdeck_id, selected_rows in selected_by_topdeck_id.items():
        if not selected_rows:
            continue

        per_commander: dict[str, dict[str, Any]] = {}
        latest_row: dict[str, Any] | None = None

        for row in selected_rows:
            commander_name = row["commander_name"]
            current = per_commander.get(commander_name)
            if current is None:
                current = {
                    "commander": commander_name,
                    "entries": 0,
                    "prediction_score": 0.0,
                    "latest_date": None,
                    "latest_decklist_url": None,
                }
                per_commander[commander_name] = current

            start_date = row.get("start_date")
            event_timestamp_ms = 0
            if start_date:
                parsed = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                event_timestamp_ms = int(parsed.timestamp() * 1000)
            current["entries"] += 1
            current["prediction_score"] += calculate_recency_weight(
                event_timestamp_ms, reference_timestamp_ms
            )
            if not current["latest_date"] or (start_date and start_date > current["latest_date"]):
                current["latest_date"] = start_date
                current["latest_decklist_url"] = row.get("decklist_url") or row.get("topdeck_decklist_url")

            if latest_row is None or (start_date or "") > (latest_row.get("start_date") or ""):
                latest_row = row

        sorted_commanders = sorted(
            per_commander.values(),
            key=lambda value: (
                -value["prediction_score"],
                -value["entries"],
                -(int(datetime.fromisoformat(value["latest_date"].replace("Z", "+00:00")).timestamp()) if value["latest_date"] else 0),
                value["commander"],
            ),
        )
        total_entries = sum(value["entries"] for value in sorted_commanders)
        total_prediction = sum(value["prediction_score"] for value in sorted_commanders)
        commander_predictions = []
        for value in sorted_commanders[:3]:
            share = (value["entries"] / total_entries) if total_entries else 0
            prediction_share = (
                value["prediction_score"] / total_prediction if total_prediction else share
            )
            commander_predictions.append(
                {
                    "commander": value["commander"],
                    "entries": value["entries"],
                    "share": share,
                    "weighted_share": prediction_share,
                    "prediction_share": prediction_share,
                    "prediction_score": round(value["prediction_score"], 6),
                    "latest_date": value["latest_date"],
                    "latest_decklist_url": value["latest_decklist_url"],
                }
            )

        active = commander_predictions[0] if commander_predictions else None
        profile_rows.append(
            {
                "player_id": player_ids_by_topdeck_id[topdeck_id],
                "topdeck_id": topdeck_id,
                "player_name": player_names_by_topdeck_id.get(topdeck_id) or "Unknown",
                "active_commander": active["commander"] if active else None,
                "active_commander_entries": active["entries"] if active else 0,
                "active_commander_prediction_score": active["prediction_score"] if active else 0,
                "total_entries": total_entries,
                "commander_predictions": commander_predictions,
                "latest_commander": latest_row.get("commander_name") if latest_row else None,
                "latest_commander_date": (latest_row.get("start_date") or "")[:10] or None,
                "latest_decklist_url": (
                    latest_row.get("decklist_url") or latest_row.get("topdeck_decklist_url")
                    if latest_row
                    else None
                ),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return profile_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild player_commander_profiles")
    parser.add_argument(
        "--reference-date",
        type=str,
        help="Reference date in YYYY-MM-DD form. Defaults to today UTC.",
    )
    args = parser.parse_args()

    load_local_env()
    supabase_url = os.environ.get("SUPABASE_URL", SUPABASE_REST_BASE)
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_key:
        raise SystemExit("SUPABASE_SERVICE_KEY is required")

    reference_date = (
        date_parser.parse(args.reference_date).date()
        if args.reference_date
        else datetime.now(timezone.utc).date()
    )
    client = SupabaseClient(supabase_url, supabase_key)
    db_url = os.environ.get("SUPABASE_DB_URL")

    logger.info("Fetching tournament entry usage rows...")
    if db_url:
        try:
            raw_rows = fetch_usage_rows_via_db(db_url)
        except Exception as exc:
            logger.warning("Direct database read failed, falling back to REST: %s", exc)
            raw_rows = fetch_usage_rows_via_rest(client)
    else:
        raw_rows = fetch_usage_rows_via_rest(client)
    usage_rows = normalize_usage_rows(raw_rows)
    logger.info("Fetched %s qualifying usage rows", len(usage_rows))

    logger.info("Building player commander profiles using reference date %s", reference_date.isoformat())
    profile_rows = build_profile_rows(usage_rows, reference_date)
    logger.info("Built %s player commander profiles", len(profile_rows))

    existing_player_ids = set(fetch_existing_profile_player_ids(client))
    rebuilt_player_ids = {
        row["player_id"]
        for row in profile_rows
        if isinstance(row.get("player_id"), str) and row["player_id"]
    }
    stale_player_ids = sorted(existing_player_ids - rebuilt_player_ids)
    if stale_player_ids:
        deleted = delete_profile_rows_by_player_ids(client, stale_player_ids)
        logger.info("Deleted %s stale player commander profiles", deleted)

    total_upserted = 0
    for chunk in chunked(profile_rows, UPSERT_CHUNK_SIZE):
        client.upsert("player_commander_profiles", chunk, on_conflict="player_id")
        total_upserted += len(chunk)
        logger.info("Upserted %s/%s profiles", total_upserted, len(profile_rows))

    logger.info("Player commander profile rebuild complete")


if __name__ == "__main__":
    main()
