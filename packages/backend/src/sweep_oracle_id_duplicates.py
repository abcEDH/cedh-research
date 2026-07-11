#!/usr/bin/env python3
"""Sweep to deduplicate commanders with same Scryfall oracle_id (Universes Beyond variants)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import requests

from backfill_moxfield_commanders import load_credentials
from commander_dedup import (
    delete_commander_row,
    repoint_tournament_entries,
)
from ingest import (
    SupabaseClient,
    clean_commander_card_name,
)


def build_oracle_id_map() -> dict[str, str]:
    """Build a map of commander name -> oracle_id from legal_commander_pairings.json.

    The legal_commander_pairings.json is generated from Scryfall and contains
    oracle_id for all legal commander cards.
    """
    data_path = Path(__file__).resolve().parents[1] / "data" / "legal_commander_pairings.json"
    if not data_path.exists():
        return {}

    payload = json.loads(data_path.read_text())
    pairs = payload.get("legal_pairs") or []

    name_to_oracle: dict[str, str] = {}
    for pair in pairs:
        commander_names = pair.get("commander_names") or []
        scryfall_ids = pair.get("scryfall_ids") or []

        if len(commander_names) == 2 and len(scryfall_ids) == 2:
            for name, scryfall_id in zip(commander_names, scryfall_ids):
                cleaned = clean_commander_card_name(name)
                if cleaned:
                    name_to_oracle[cleaned] = scryfall_id

    return name_to_oracle


def fetch_oracle_ids_from_scryfall(timeout: float = 60.0) -> dict[str, str]:
    """Fetch oracle_id mapping from Scryfall bulk data.

    Returns mapping of card name -> oracle_id for all legal commander cards.
    """
    bulk_url = "https://api.scryfall.com/bulk-data"
    bulk_response = requests.get(bulk_url, timeout=timeout)
    bulk_response.raise_for_status()
    bulk_payload = bulk_response.json()
    bulk_items = bulk_payload.get("data") or []

    oracle_item = next((item for item in bulk_items if item.get("type") == "oracle_cards"), None)
    if not oracle_item or not oracle_item.get("download_uri"):
        raise RuntimeError("Unable to locate Scryfall oracle_cards bulk download")

    cards_response = requests.get(oracle_item["download_uri"], timeout=timeout)
    cards_response.raise_for_status()
    cards = cards_response.json()

    name_to_oracle: dict[str, str] = {}
    for card in cards:
        legalities = card.get("legalities") or {}
        if legalities.get("commander") != "legal":
            continue

        name = card.get("name", "")
        oracle_id = card.get("oracle_id", "")
        if name and oracle_id:
            front_face = name.split(" // ", 1)[0].strip()
            cleaned = clean_commander_card_name(front_face)
            if cleaned:
                name_to_oracle[cleaned] = str(oracle_id)

    return name_to_oracle


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep to deduplicate Universes Beyond oracle_id variants.")
    parser.add_argument(
        "--fetch-scryfall",
        action="store_true",
        help="Fetch fresh oracle_id mapping from Scryfall instead of using legal_commander_pairings.json",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without updating Supabase",
    )
    parser.add_argument(
        "--report",
        default="logs/sweep_oracle_id_duplicates_20260711.csv",
        help="CSV report path",
    )
    args = parser.parse_args()

    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)

    # Get oracle_id mapping
    if args.fetch_scryfall:
        print("Fetching oracle_ids from Scryfall...")
        name_to_oracle = fetch_oracle_ids_from_scryfall(args.timeout)
    else:
        print("Loading oracle_ids from legal_commander_pairings.json...")
        name_to_oracle = build_oracle_id_map()

    print(f"Loaded {len(name_to_oracle)} commander oracle_ids")

    # Fetch all commanders
    print("Fetching all commanders from database...")
    commanders = client.select("commanders", {"select": "id,name,commander_names", "limit": 5000, "order": "name.asc"})

    # Group commanders by oracle_id
    oracle_groups: dict[str, list[dict]] = defaultdict(list)
    commander_without_oracle = []

    for commander in commanders:
        commander_names = commander.get("commander_names") or []
        found_oracle = False

        for cmd_name in commander_names:
            cleaned = clean_commander_card_name(cmd_name)
            if cleaned in name_to_oracle:
                oracle_id = name_to_oracle[cleaned]
                oracle_groups[oracle_id].append(commander)
                found_oracle = True
                break

        if not found_oracle:
            commander_without_oracle.append(commander)

    # Process groups with multiple commanders (duplicates)
    report_lines = ["oracle_id,canonical_name,duplicate_names,merged"]
    merged_count = 0

    for oracle_id, group in sorted(oracle_groups.items()):
        if len(group) <= 1:
            continue

        # Multiple commanders with same oracle_id - merge them
        canonical = group[0]
        canonical_id = canonical["id"]
        canonical_name = canonical["name"]

        duplicates = group[1:]
        duplicate_names = [cmd["name"] for cmd in duplicates]

        print(f"Merging {len(duplicates)} duplicates of {canonical_name} (oracle_id={oracle_id})")

        for duplicate in duplicates:
            if not args.dry_run:
                # Repoint entries to canonical
                repoint_tournament_entries(client, duplicate["id"], canonical_id)
                # Delete duplicate
                delete_commander_row(client, duplicate["id"])

            merged_count += 1

        report_lines.append(f'{oracle_id},"{canonical_name}","{"; ".join(duplicate_names)}",yes')

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text("\n".join(report_lines) + "\n")

    print(f"commander_groups={len(oracle_groups)}")
    print(f"commanders_with_duplicates={len([g for g in oracle_groups.values() if len(g) > 1])}")
    print(f"merged={merged_count}")
    print(f"commanders_without_oracle={len(commander_without_oracle)}")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
