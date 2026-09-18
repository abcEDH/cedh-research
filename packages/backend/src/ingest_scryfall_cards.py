#!/usr/bin/env python3
"""Cache Scryfall card art server-side instead of live per-name client fetches (#321).

Problem: `apps/web/src/lib/scryfall/client.ts` fetches card art live, per
card name, from `api.scryfall.com/cards/named?fuzzy=` on every page load
(commanders list, commander detail, tournament standings). That adds
per-page-load latency and depends on Scryfall's live API/rate limits at
render time.

Fix: pull Scryfall's `default_cards` bulk-data dump (one HTTP request, per
Scryfall's own guidance -- see `scryfall_bulk_client.py`), filter it down to
the individual commander names actually referenced by this project's
`commanders` rows, and upsert the matches into the already-scaffolded
`scryfall_cards` table (`packages/backend/supabase/migrations/20260110000001_initial_schema.sql`).
`apps/web/src/lib/commanders/fetchers.ts` joins against this table to
server-render `art_crop`/`normal` URLs instead of depending on a live
client-side fetch; that client-side path
(`apps/web/src/lib/scryfall/client.ts` + `apps/web/src/hooks/use-scryfall-art.ts`)
remains as a fallback for cache misses -- names not yet in the bulk dump.

Scheduling (daily/weekly cron, matching the cadence of the other ingestion
jobs in this project) is intentionally left as follow-up; this script is run
manually or on demand until that's wired up.
"""

from __future__ import annotations

import argparse

import requests

from backfill_moxfield_commanders import load_credentials
from scryfall_bulk_client import (
    DEFAULT_CARDS_BULK_TYPE,
    fetch_bulk_data_cards,
    fetch_bulk_data_index,
    find_bulk_data_download_uri,
)
from supabase_client import SupabaseClient

UPSERT_CHUNK_SIZE = 500


def split_commander_names(names_column: list[str] | None) -> set[str]:
    """Flatten a `commanders.commander_names` array cell into individual names."""
    if not names_column:
        return set()
    return {name.strip() for name in names_column if name and name.strip()}


def fetch_referenced_card_names(client: SupabaseClient) -> set[str]:
    """Collect every individual commander name referenced in `commanders`.

    Partner pairs are stored as a two-element `commander_names` array (see
    the `commanders` table in `20260110000001_initial_schema.sql`); this
    flattens both solo and partnered rows down to the individual
    Scryfall-lookup names the frontend actually needs art for --
    `CommanderArtThumb`/`ArtCropStack` resolve one face at a time, splitting
    partner pairs the same way `splitCardName()` does in
    `apps/web/src/lib/scryfall/client.ts`.
    """
    rows = client.select("commanders", {"select": "commander_names", "limit": 5000})
    names: set[str] = set()
    for row in rows:
        names |= split_commander_names(row.get("commander_names"))
    return names


def select_best_printing_per_name(cards: list[dict], names: set[str]) -> dict[str, dict]:
    """Pick one printing per referenced name from the bulk dump.

    The dump carries many printings per name, and `scryfall_cards.name` has
    a plain index rather than a UNIQUE constraint (see
    `idx_scryfall_name` in the initial schema migration) -- so without a
    tiebreak, upserting every printing that matches a referenced name would
    leave which one "wins" nondeterministic across runs. Prefer the most
    recently released printing that actually carries `image_uris` (or
    per-face `image_uris` on a double-faced card); some promo/digital
    printings omit them.
    """
    best: dict[str, dict] = {}
    for card in cards:
        name = (card.get("name") or "").strip()
        if name not in names:
            continue
        if not card.get("image_uris") and not card.get("card_faces"):
            continue
        current = best.get(name)
        if current is None or (card.get("released_at") or "") > (current.get("released_at") or ""):
            best[name] = card
    return best


def build_scryfall_card_row(card: dict) -> dict:
    """Map a bulk-data card object onto `scryfall_cards` columns."""
    image_uris = card.get("image_uris")
    if not image_uris and card.get("card_faces"):
        # Double-faced/split/MDFC cards carry image_uris per face rather than
        # at the top level; use the front face, matching how
        # `fetchScryfallArt()` in client.ts picks the matched face.
        faces = card["card_faces"]
        image_uris = faces[0].get("image_uris") if faces else None

    return {
        "scryfall_id": card.get("id"),
        "name": card.get("name"),
        "oracle_text": card.get("oracle_text"),
        "mana_cost": card.get("mana_cost"),
        "cmc": card.get("cmc"),
        "type_line": card.get("type_line"),
        "colors": card.get("colors"),
        "color_identity": card.get("color_identity"),
        "keywords": card.get("keywords"),
        "legalities": card.get("legalities"),
        "image_uris": image_uris,
        "prices": card.get("prices"),
        "released_at": card.get("released_at"),
        "set_code": card.get("set"),
        "rarity": card.get("rarity"),
    }


def chunked(values: list[dict], size: int) -> list[list[dict]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def upsert_scryfall_cards(client: SupabaseClient, rows: list[dict]) -> int:
    total = 0
    for chunk in chunked(rows, UPSERT_CHUNK_SIZE):
        client.upsert("scryfall_cards", chunk, on_conflict="scryfall_id")
        total += len(chunk)
    return total


def sync_commander_color_identities(client: SupabaseClient) -> int:
    """Persist Scryfall color identities on solo commanders and partner pairs."""
    result = client.rpc("sync_commander_scryfall_color_identities")
    return int(result or 0)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cache Scryfall card art server-side from the default_cards bulk dump."
    )
    parser.add_argument("--dry-run", action="store_true", help="Report matches without upserting")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)
    session = requests.Session()

    print("Fetching referenced commander names...")
    names = fetch_referenced_card_names(client)
    print(f"referenced_names={len(names)}")

    print("Fetching Scryfall bulk-data index...")
    index = fetch_bulk_data_index(session)
    download_uri = find_bulk_data_download_uri(index, DEFAULT_CARDS_BULK_TYPE)

    print(f"Downloading {DEFAULT_CARDS_BULK_TYPE} bulk data...")
    cards = fetch_bulk_data_cards(download_uri, session)
    print(f"bulk_cards={len(cards)}")

    matched = select_best_printing_per_name(cards, names)
    print(f"matched_names={len(matched)}")

    rows = [build_scryfall_card_row(card) for card in matched.values()]

    if args.dry_run:
        print(f"[DRY RUN] Would upsert {len(rows)} scryfall_cards rows")
        return

    upserted = upsert_scryfall_cards(client, rows)
    print(f"upserted={upserted}")
    updated_commanders = sync_commander_color_identities(client)
    print(f"updated_commander_color_identities={updated_commanders}")


if __name__ == "__main__":
    main()
