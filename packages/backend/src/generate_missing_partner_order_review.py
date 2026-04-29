#!/usr/bin/env python3
"""Generate a review CSV for legal partner pairings not yet stored in Supabase.

The goal is to support manual community-order review using discussion sources
like Reddit and X instead of relying on TopDeck deck page ordering.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import requests

from ingest import SupabaseClient


def load_credentials() -> tuple[str, str]:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
    return url, key


def canonical_pair_key(names: list[str]) -> tuple[str, str]:
    return tuple(sorted(names))  # type: ignore[return-value]


def fetch_stored_pair_keys(client: SupabaseClient) -> set[tuple[str, str]]:
    rows = client.select(
        "commanders",
        {
            "select": "commander_names",
            "limit": 5000,
            "order": "name.asc",
        },
    )
    stored: set[tuple[str, str]] = set()
    for row in rows:
        names = row.get("commander_names") or []
        if isinstance(names, list) and len(names) == 2:
            stored.add(canonical_pair_key(list(names)))
    return stored


def build_reddit_search_url(left: str, right: str) -> str:
    query = f'site:reddit.com cEDH "{left}" "{right}"'
    return f"https://www.google.com/search?q={quote_plus(query)}"


def build_x_search_url(left: str, right: str) -> str:
    query = f'"{left}" "{right}" MTG OR cEDH'
    return f"https://x.com/search?q={quote_plus(query)}&src=typed_query"


def build_generic_search_url(left: str, right: str) -> str:
    query = f'"{left}" "{right}" cEDH commander'
    return f"https://www.google.com/search?q={quote_plus(query)}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate missing partner community-order review CSV.")
    parser.add_argument(
        "--legal-pairs",
        default="packages/backend/data/legal_commander_pairings.json",
        help="Path to generated legal pairings JSON",
    )
    parser.add_argument(
        "--output",
        default="packages/backend/logs/missing_partner_community_order_review.csv",
        help="CSV output path",
    )
    args = parser.parse_args()

    legal_payload = json.loads(Path(args.legal_pairs).read_text())
    legal_pairs = legal_payload.get("legal_pairs") or []

    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)
    stored_pair_keys = fetch_stored_pair_keys(client)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "project_name",
        "sorted_name",
        "commander_1",
        "commander_2",
        "rule",
        "detail",
        "reddit_search_url",
        "x_search_url",
        "generic_search_url",
        "review_status",
        "reviewed_order",
        "evidence_notes",
    ]

    missing_count = 0
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for pair in legal_pairs:
            names = pair.get("commander_names") or []
            if not isinstance(names, list) or len(names) != 2:
                continue
            pair_key = canonical_pair_key(names)
            if pair_key in stored_pair_keys:
                continue

            left, right = names
            writer.writerow(
                {
                    "project_name": pair.get("project_name", ""),
                    "sorted_name": pair.get("sorted_name", ""),
                    "commander_1": left,
                    "commander_2": right,
                    "rule": pair.get("rule", ""),
                    "detail": pair.get("detail", "") or "",
                    "reddit_search_url": build_reddit_search_url(left, right),
                    "x_search_url": build_x_search_url(left, right),
                    "generic_search_url": build_generic_search_url(left, right),
                    "review_status": "",
                    "reviewed_order": "",
                    "evidence_notes": "",
                }
            )
            missing_count += 1

    print(f"missing_pairs={missing_count}")
    print(f"output={output_path}")


if __name__ == "__main__":
    main()
