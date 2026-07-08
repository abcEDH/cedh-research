#!/usr/bin/env python3
"""Generate a flavor-name -> true-name alias map for Universes Beyond commanders.

Companion artifact to ``legal_commander_pairings.json``: instead of the
"legal two-card pairing" rules, this pulls Scryfall's ``default_cards`` bulk
dataset (one row per printing, including UB flavor names) and records, for
every commander-legal card that has ever been printed under an alternate
flavor name, the mapping from that flavor name back to the true Oracle name
sharing its ``oracle_id``.

``ingest.py`` consults the generated ``commander_oracle_aliases.json``
artifact (in addition to the hand-curated ``COMMANDER_NAME_ALIASES`` dict) so
that newly-ingested tournament data normalizes UB alternate names to their
canonical commander automatically, without needing a manual dict entry for
every new Secret Lair / Universes Beyond drop.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from commander_oracle_identity import DEFAULT_CARDS_BULK_TYPE, build_alias_map
from generate_legal_commander_pairings import SCRYFALL_BULK_DATA_URL, fetch_bulk_cards


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the Universes Beyond alternate-name commander alias map."
    )
    parser.add_argument(
        "--output",
        default="packages/backend/data/commander_oracle_aliases.json",
        help="Path to the generated JSON file",
    )
    parser.add_argument("--timeout", type=float, default=120.0, help="HTTP timeout in seconds")
    return parser


def write_output(alias_map: dict[str, str], *, output_path: Path, timeout: float) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "provider": "Scryfall",
            "dataset": DEFAULT_CARDS_BULK_TYPE,
            "bulk_data_url": SCRYFALL_BULK_DATA_URL,
            "timeout_seconds": timeout,
        },
        "alias_count": len(alias_map),
        "aliases": dict(sorted(alias_map.items())),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    args = build_arg_parser().parse_args()

    cards = fetch_bulk_cards(DEFAULT_CARDS_BULK_TYPE, args.timeout)
    alias_map = build_alias_map(cards)
    write_output(alias_map, output_path=Path(args.output), timeout=args.timeout)

    print(f"alias_count={len(alias_map)}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
