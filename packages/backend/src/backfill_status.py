#!/usr/bin/env python3
"""Summarize historical backfill progress from Supabase."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from ingest import SupabaseClient


def load_credentials() -> tuple[str, str]:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" not in line:
                    continue
                key, value = line.strip().split("=", 1)
                if key == "SUPABASE_URL" and not supabase_url:
                    supabase_url = value
                elif key == "SUPABASE_SERVICE_KEY" and not supabase_key:
                    supabase_key = value

    if not supabase_url or not supabase_key:
        raise SystemExit("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

    return supabase_url, supabase_key


def format_pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description="Show backfill run progress")
    parser.add_argument("--run-key", required=True, help="Run key recorded in ingestion_backfill_runs")
    args = parser.parse_args()

    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)

    rows = client.select(
        "ingestion_backfill_runs",
        {
            "select": ",".join(
                [
                    "id",
                    "run_key",
                    "status",
                    "discovered_tournament_count",
                    "processed_tournament_count",
                    "succeeded_tournament_count",
                    "failed_tournament_count",
                    "total_batches",
                    "current_batch_index",
                    "current_tid",
                    "last_completed_tid",
                    "current_batch_processed_count",
                    "current_batch_succeeded_count",
                    "current_batch_failed_count",
                    "last_success_at",
                    "heartbeat_at",
                    "updated_at",
                ]
            ),
            "run_key": f"eq.{args.run_key}",
            "limit": 1,
        },
    )
    if not rows:
        raise SystemExit(f"No backfill run found for run_key={args.run_key}")

    run = rows[0]

    event_rows = client.select(
        "ingestion_backfill_events",
        {
            "select": "event_type,tid,created_at",
            "run_id": f"eq.{run['id']}",
            "order": "created_at.desc",
            "limit": 5,
        },
    )

    print(f"run_key: {run['run_key']}")
    print(f"status: {run['status']}")
    print(
        "progress: "
        f"{run['processed_tournament_count']}/{run['discovered_tournament_count']} "
        f"({format_pct(run['processed_tournament_count'], run['discovered_tournament_count'])})"
    )
    print(
        "results: "
        f"{run['succeeded_tournament_count']} succeeded, "
        f"{run['failed_tournament_count']} failed"
    )
    print(
        "current_batch: "
        f"{run.get('current_batch_index')} "
        f"({run.get('current_batch_processed_count', 0)} processed / "
        f"{run.get('current_batch_succeeded_count', 0)} succeeded / "
        f"{run.get('current_batch_failed_count', 0)} failed)"
    )
    print(f"current_tid: {run.get('current_tid')}")
    print(f"last_completed_tid: {run.get('last_completed_tid')}")
    print(f"last_success_at: {run.get('last_success_at')}")
    print(f"heartbeat_at: {run.get('heartbeat_at')}")
    print(f"updated_at: {run.get('updated_at')}")

    if event_rows:
        print("recent_events:")
        for event in event_rows:
            suffix = f" {event['tid']}" if event.get("tid") else ""
            print(f"- {event['created_at']} {event['event_type']}{suffix}")


if __name__ == "__main__":
    main()
