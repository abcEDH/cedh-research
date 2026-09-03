#!/usr/bin/env python3
"""Export an ordered TID manifest from the currently ingested Supabase tournaments.

Usage:
  python src/export_all_time_tids.py
  python src/export_all_time_tids.py --out data/all_time_tids.txt

Important:
  This script is not a true all-time discovery job. It only exports tournament IDs
  that are already present in public.tournaments. Use it to stabilize/replay an
  existing ingest set, optionally merged with a supplemental manifest of known
  missing IDs discovered outside the database.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from supabase import Client
from supabase_client import fetch_all, get_supabase_client


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


def fetch_all_tournaments(client: Client) -> list[dict[str, Any]]:
    return fetch_all(
        client,
        "tournaments",
        columns="topdeck_tid,start_date,player_count",
        filters=[("topdeck_tid", "not_is", "null")],
        order=[("start_date", False), ("topdeck_tid", False)],
        label="tournaments",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export all-time tournament IDs from Supabase")
    parser.add_argument("--out", default="data/all_time_tids.txt", help="Output manifest path")
    parser.add_argument(
        "--supplemental",
        action="append",
        default=[],
        help="Optional newline-delimited TID file to append after Supabase export",
    )
    args = parser.parse_args()

    supabase_url, supabase_key = load_credentials()
    client = get_supabase_client(supabase_url, supabase_key)
    rows = fetch_all_tournaments(client)

    filtered = [row["topdeck_tid"].strip() for row in rows if row.get("topdeck_tid")]

    deduped: list[str] = []
    seen: set[str] = set()
    for tid in filtered:
        if tid in seen:
            continue
        seen.add(tid)
        deduped.append(tid)

    for supplemental_path in args.supplemental:
        for line in Path(supplemental_path).read_text().splitlines():
            tid = line.strip()
            if not tid or tid.startswith("#") or tid in seen:
                continue
            seen.add(tid)
            deduped.append(tid)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(
            [
                "# All-time tournament ID manifest",
                "# Source: Supabase public.tournaments.topdeck_tid plus optional supplemental files",
                "# Ordering: start_date ASC, topdeck_tid ASC",
                "# Note: this is not true all-time discovery; it only exports already-ingested tournaments",
                "# Refresh with: python src/export_all_time_tids.py "
                "[--supplemental data/all_time_tids.supplemental.txt]",
                "",
                *deduped,
                "",
            ]
        )
    )
    print(f"Wrote {len(deduped)} tournament IDs to {out_path}")


if __name__ == "__main__":
    main()
