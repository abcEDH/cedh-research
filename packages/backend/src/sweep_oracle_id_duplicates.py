#!/usr/bin/env python3
"""Sweep to deduplicate commanders with same Scryfall oracle_id (Universes Beyond variants).

Note: `data/legal_commander_pairings.json` only records `scryfall_ids` (per-print
card IDs from Scryfall's `card.id`), not the stable `oracle_id` that identifies a
card across reprints/alternate-art/alternate-name (Universes Beyond) variants —
the whole point of this sweep. There is no local source of real oracle_id data,
so this script always fetches oracle_ids fresh from Scryfall's bulk data API.
"""

from __future__ import annotations

import argparse
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
    normalize_commander_name,
)


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


def build_oracle_group_key(
    commander_names: list[str],
    name_to_oracle: dict[str, str],
) -> tuple[str, ...] | None:
    """Build the full-identity group key for a commander row, or None if unresolved.

    Two commander rows should only be treated as duplicates when *every* card in
    the row shares an oracle_id with every card in the other row — e.g. "Tymna /
    Kraum" and "Tymna / Thrasios" both contain Tymna but are distinct legal pairs
    and must not merge. Keying off only the first matching card (breaking out of
    the loop early) would incorrectly collapse them. If any name in the row fails
    to resolve to an oracle_id, the whole row is left ungrouped (returns None)
    rather than partially matching on the names that did resolve.
    """
    if not commander_names:
        return None

    oracle_ids: list[str] = []
    for cmd_name in commander_names:
        cleaned = clean_commander_card_name(cmd_name)
        oracle_id = name_to_oracle.get(cleaned)
        if not oracle_id:
            return None
        oracle_ids.append(oracle_id)

    return tuple(sorted(oracle_ids))


def choose_canonical_commander(group: list[dict]) -> dict:
    """Pick the row to keep when merging an oracle_id duplicate group.

    Keeping an un-normalized alias row (e.g. "Chief Jim Hopper" instead of its
    canonical "Sophina, Spearsage Deserter", per COMMANDER_NAME_ALIASES) would
    mean the next ingestion run normalizes new entries to the canonical name,
    finds no existing row for it (since it was just deleted), and recreates the
    very duplicate this sweep was meant to remove. Prefer the row whose stored
    `name` already equals its own normalized form; only fall back to the first
    row (by the caller's sort order) if none qualify.
    """
    normalized_matches = [
        commander
        for commander in group
        if commander.get("name") == normalize_commander_name(commander.get("commander_names") or [])
    ]
    if normalized_matches:
        return normalized_matches[0]
    return group[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep to deduplicate Universes Beyond oracle_id variants.")
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

    print("Fetching oracle_ids from Scryfall...")
    name_to_oracle = fetch_oracle_ids_from_scryfall(args.timeout)
    print(f"Loaded {len(name_to_oracle)} commander oracle_ids")

    # Fetch all commanders
    print("Fetching all commanders from database...")
    commanders = client.select("commanders", {"select": "id,name,commander_names", "limit": 5000, "order": "name.asc"})

    # Group commanders by full-identity oracle_id key (all cards in the row, not
    # just the first match) so distinct partner pairs sharing one card never merge.
    oracle_groups: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    commander_without_oracle = []

    for commander in commanders:
        commander_names = commander.get("commander_names") or []
        group_key = build_oracle_group_key(commander_names, name_to_oracle)

        if group_key is not None:
            oracle_groups[group_key].append(commander)
        else:
            commander_without_oracle.append(commander)

    # Process groups with multiple commanders (duplicates)
    report_lines = ["oracle_ids,canonical_name,duplicate_names,merged"]
    merged_count = 0

    for oracle_key, group in sorted(oracle_groups.items()):
        if len(group) <= 1:
            continue

        # Multiple commanders with same full oracle-id identity - merge them,
        # preferring the already-normalized row as canonical (see
        # choose_canonical_commander) rather than an alphabetically-first alias.
        canonical = choose_canonical_commander(group)
        canonical_id = canonical["id"]
        canonical_name = canonical["name"]

        duplicates = [cmd for cmd in group if cmd["id"] != canonical_id]
        duplicate_names = [cmd["name"] for cmd in duplicates]
        oracle_key_str = "+".join(oracle_key)

        print(f"Merging {len(duplicates)} duplicates of {canonical_name} (oracle_ids={oracle_key_str})")

        for duplicate in duplicates:
            if not args.dry_run:
                # Repoint entries to canonical
                repoint_tournament_entries(client, duplicate["id"], canonical_id)
                # Delete duplicate
                delete_commander_row(client, duplicate["id"])

            merged_count += 1

        report_lines.append(f'{oracle_key_str},"{canonical_name}","{"; ".join(duplicate_names)}",yes')

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text("\n".join(report_lines) + "\n")

    print(f"commander_groups={len(oracle_groups)}")
    print(f"commanders_with_duplicates={len([g for g in oracle_groups.values() if len(g) > 1])}")
    print(f"merged={merged_count}")
    print(f"commanders_without_oracle={len(commander_without_oracle)}")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
