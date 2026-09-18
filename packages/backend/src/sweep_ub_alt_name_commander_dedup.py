#!/usr/bin/env python3
"""Sweep to merge Universes Beyond alternate-name/printing commander rows.

Two ``commanders`` rows should be treated as the same commander when the
Scryfall ``oracle_id``(s) of their underlying card(s) match, even when
``name``/``commander_names`` differ — e.g. a Secret Lair "Stranger Things"
alternate-name printing versus the card's original name. This mirrors the
merge mechanics in ``sweep_partner_commander_order.py`` (used there for
"A, B" vs "B, A" partner-order duplicates), reusing its
``repoint_tournament_entries``/``repoint_commander_matchups``/
``delete_commander_row`` helpers rather than re-implementing the merge
itself.

Identity resolution (oracle_id signature per row, canonical-row selection)
lives in ``commander_oracle_identity.py`` and is shared with
``generate_commander_oracle_aliases.py``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from backfill_moxfield_commanders import load_credentials
from commander_oracle_identity import (
    DEFAULT_CARDS_BULK_TYPE,
    build_name_to_oracle_id_map,
    choose_canonical_row,
    collect_true_oracle_names,
    group_duplicate_commander_rows,
)
from generate_legal_commander_pairings import fetch_bulk_cards
from supabase import Client
from supabase_client import get_supabase_client
from sweep_partner_commander_order import (
    delete_commander_row,
    repoint_commander_matchups,
    repoint_tournament_entries,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sweep to merge Universes Beyond alternate-name commander rows by oracle_id."
    )
    parser.add_argument("--timeout", type=float, default=120.0, help="Scryfall bulk-data HTTP timeout")
    parser.add_argument("--commander-limit", type=int, default=5000, help="Max commander rows to inspect")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without updating Supabase")
    parser.add_argument(
        "--report",
        default="logs/sweep_ub_alt_name_commander_dedup.csv",
        help="CSV report path",
    )
    return parser


def fetch_commander_rows(client: Client, limit: int) -> list[dict]:
    return (
        client.table("commanders")
        .select("id,name,commander_names")
        .order("name", desc=False)
        .limit(limit)
        .execute()
        .data
    )


def merge_duplicate_group(
    client: Client,
    signature: tuple[str, ...],
    rows: list[dict],
    true_oracle_names: set[str],
    *,
    dry_run: bool,
) -> tuple[dict, list[dict]]:
    """Merge every duplicate row in ``rows`` into a single canonical row.

    Every reference to the duplicate commander must be repointed to the
    canonical commander *before* the duplicate row is deleted — otherwise
    Postgres rejects the delete with a foreign-key violation (rows in
    ``commander_matchups`` reference ``commanders`` via both
    ``commander_id`` and ``opponent_commander_id``, in addition to
    ``tournament_entries.commander_id``). Repointing is idempotent, so if a
    prior run was interrupted after repointing but before deleting, re-running
    this simply repoints zero additional rows and retries the delete.
    """
    canonical, duplicates = choose_canonical_row(rows, true_oracle_names)
    for duplicate in duplicates:
        if not dry_run:
            repoint_tournament_entries(client, duplicate["id"], canonical["id"])
            repoint_commander_matchups(client, duplicate["id"], canonical["id"])
            delete_commander_row(client, duplicate["id"])
    return canonical, duplicates


def run_sweep(
    client: Client,
    cards: list[dict],
    *,
    commander_limit: int,
    dry_run: bool,
) -> list[str]:
    name_to_oracle_id = build_name_to_oracle_id_map(cards)
    true_oracle_names = collect_true_oracle_names(cards)

    commanders = fetch_commander_rows(client, commander_limit)
    duplicate_groups = group_duplicate_commander_rows(commanders, name_to_oracle_id)

    report_lines = ["oracle_signature,canonical_id,canonical_name,duplicate_id,duplicate_name,merged"]
    for signature, rows in duplicate_groups.items():
        canonical, duplicates = merge_duplicate_group(client, signature, rows, true_oracle_names, dry_run=dry_run)
        for duplicate in duplicates:
            report_lines.append(
                ",".join(
                    [
                        "|".join(signature),
                        str(canonical["id"]),
                        f'"{canonical.get("name", "")}"',
                        str(duplicate["id"]),
                        f'"{duplicate.get("name", "")}"',
                        "no" if dry_run else "yes",
                    ]
                )
            )
    return report_lines


def main() -> None:
    args = build_arg_parser().parse_args()

    supabase_url, supabase_key = load_credentials()
    client = get_supabase_client(supabase_url, supabase_key)

    cards = fetch_bulk_cards(DEFAULT_CARDS_BULK_TYPE, args.timeout)
    report_lines = run_sweep(
        client,
        cards,
        commander_limit=args.commander_limit,
        dry_run=args.dry_run,
    )

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text("\n".join(report_lines) + "\n")

    merged = len(report_lines) - 1
    print(f"merged={merged}")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
