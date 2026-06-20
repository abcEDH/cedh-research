#!/usr/bin/env python3
"""Fetch service-role-only pg_stat_statements data for Regional Elo queries."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests

DEFAULT_SEARCH_TERMS = [
    "global_elo_active_leaderboard",
    "global_elo_leaderboard",
    "regional_elo_leaderboard",
    "topdeck_player_elos",
    "tournament_entries",
    "player_commander_profiles",
]


def load_credentials() -> tuple[str, str]:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        for env_path in (Path(".env"), Path("packages/backend/.env")):
            if not env_path.exists():
                continue
            for raw_line in env_path.read_text().splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                value = value.strip().strip('"').strip("'")
                if key == "SUPABASE_URL" and not supabase_url:
                    supabase_url = value
                elif key in {"SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY"} and not supabase_key:
                    supabase_key = value

    if not supabase_url or not supabase_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")

    return supabase_url.rstrip("/"), supabase_key


def fetch_query_stats(url: str, service_key: str, terms: list[str], limit: int) -> list[dict[str, Any]]:
    response = requests.post(
        f"{url}/rest/v1/rpc/get_regional_elo_query_stats",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        },
        json={"p_limit": limit, "p_search_terms": terms},
        timeout=60,
    )
    if response.status_code >= 400:
        raise SystemExit(
            "Unable to fetch query stats. Ensure migration "
            "20260430010000_query_performance_observability.sql has been applied "
            f"and the service-role key is in use. HTTP {response.status_code}: {response.text}"
        )
    payload = response.json()
    if not isinstance(payload, list):
        raise SystemExit(f"Unexpected response payload: {payload!r}")
    return payload


def fmt_ms(value: object) -> str:
    if not isinstance(value, int | float):
        return "-"
    return f"{value:,.1f}"


def fmt_int(value: object) -> str:
    if not isinstance(value, int):
        return "-"
    return f"{value:,}"


def print_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("No matching pg_stat_statements rows found.")
        return

    print("calls  mean_ms  total_ms  rows  shared_hit  shared_read  temp_read  query")
    print("-" * 120)
    for row in rows:
        query = " ".join(str(row.get("query", "")).split())
        if len(query) > 92:
            query = f"{query[:89]}..."
        print(
            f"{fmt_int(row.get('calls')):>5}  "
            f"{fmt_ms(row.get('mean_exec_time_ms')):>7}  "
            f"{fmt_ms(row.get('total_exec_time_ms')):>8}  "
            f"{fmt_int(row.get('rows_returned')):>5}  "
            f"{fmt_int(row.get('shared_blks_hit')):>10}  "
            f"{fmt_int(row.get('shared_blks_read')):>11}  "
            f"{fmt_int(row.get('temp_blks_read')):>9}  "
            f"{query}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Show Regional Elo query timing stats from Supabase")
    parser.add_argument("--limit", type=int, default=50, help="Maximum rows to return")
    parser.add_argument(
        "--term",
        action="append",
        default=[],
        help="Search term to match in pg_stat_statements query text. May be repeated.",
    )
    parser.add_argument("--json", action="store_true", help="Print raw JSON")
    args = parser.parse_args()

    url, key = load_credentials()
    terms = args.term or DEFAULT_SEARCH_TERMS
    rows = fetch_query_stats(url, key, terms, args.limit)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print_table(rows)


if __name__ == "__main__":
    main()
