#!/usr/bin/env python3
"""One-time sweep to normalize partner commander display order by observed usage."""

from __future__ import annotations

import argparse
import collections
from pathlib import Path

import requests

from backfill_moxfield_commanders import (
    fetch_topdeck_deck_page_details,
    load_credentials,
)
from commander_dedup import (
    canonical_pair_key,
    delete_commander_row,
    repoint_tournament_entries,
    update_commander_row,
)
from ingest import (
    PARTNER_ORDER_OVERRIDES,
    SupabaseClient,
    clean_commander_card_name,
)


def current_pair_order(row: dict) -> tuple[str, str] | None:
    names = row.get("commander_names") or []
    if isinstance(names, list) and len(names) == 2:
        return tuple(clean_commander_card_name(name) for name in names)

    raw_name = row.get("name") or ""
    if " / " not in raw_name:
        return None
    parts = [clean_commander_card_name(part) for part in raw_name.split(" / ") if part.strip()]
    if len(parts) != 2:
        return None
    return tuple(parts)


def fetch_entries_for_commander(client: SupabaseClient, commander_id: str, limit: int) -> list[dict]:
    return client.select(
        "tournament_entries",
        {
            "select": "id,decklist_url,players(topdeck_id),tournaments(topdeck_tid,start_date)",
            "commander_id": f"eq.{commander_id}",
            "limit": limit,
            "order": "tournaments(start_date).desc",
        },
    )


def observe_pair_order(
    row: dict,
    session: requests.Session,
    timeout: float,
) -> tuple[str, str] | None:
    expected_key = canonical_pair_key(list(current_pair_order(row) or ()))
    if len(expected_key) != 2:
        return None

    decklist_url = (row.get("decklist_url") or "").strip()
    players = row.get("players") or {}
    tournaments = row.get("tournaments") or {}
    observed: list[str] = []

    try:
        if "topdeck.gg/deck/" in decklist_url:
            player_topdeck_id = players.get("topdeck_id")
            tournament_topdeck_id = tournaments.get("topdeck_tid")
            if player_topdeck_id and tournament_topdeck_id:
                observed, _final_url = fetch_topdeck_deck_page_details(
                    tournament_topdeck_id,
                    player_topdeck_id,
                    session,
                    timeout,
                )
        else:
            player_topdeck_id = players.get("topdeck_id")
            tournament_topdeck_id = tournaments.get("topdeck_tid")
            if player_topdeck_id and tournament_topdeck_id:
                observed, _final_url = fetch_topdeck_deck_page_details(
                    tournament_topdeck_id,
                    player_topdeck_id,
                    session,
                    timeout,
                )
    except requests.RequestException:
        return None
    except RuntimeError:
        return None

    cleaned = [clean_commander_card_name(name) for name in observed if name and name.strip()]
    if len(cleaned) != 2:
        return None
    if canonical_pair_key(cleaned) != expected_key:
        return None
    return (cleaned[0], cleaned[1])


def choose_target_order(
    current_order: tuple[str, str],
    observations: collections.Counter[tuple[str, str]],
) -> tuple[str, str]:
    override = PARTNER_ORDER_OVERRIDES.get(canonical_pair_key(list(current_order)))
    if override:
        return override
    if not observations:
        return current_order

    top_count = max(observations.values())
    top_orders = [order for order, count in observations.items() if count == top_count]
    if current_order in top_orders:
        return current_order
    return sorted(top_orders)[0]




def main() -> None:
    parser = argparse.ArgumentParser(description="One-time sweep to normalize partner commander order.")
    parser.add_argument("--sample-limit", type=int, default=40, help="Recent entries to inspect per commander pair")
    parser.add_argument("--observation-limit", type=int, default=10, help="Observed deck orders to collect per pair")
    parser.add_argument("--timeout", type=float, default=10, help="Network timeout for deck page lookups")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without updating Supabase")
    parser.add_argument(
        "--report",
        default="logs/sweep_partner_commander_order_20260409.csv",
        help="CSV report path",
    )
    args = parser.parse_args()

    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)
    session = requests.Session()

    commanders = client.select("commanders", {"select": "id,name,commander_names", "limit": 5000, "order": "name.asc"})
    partner_rows = [row for row in commanders if current_pair_order(row)]
    name_to_id = {row["name"]: row["id"] for row in commanders if row.get("name")}

    report_lines = ["commander_id,current_name,target_name,observations,current_order,target_order,updated"]
    updated = 0
    merged = 0

    for commander in partner_rows:
        current_order = current_pair_order(commander)
        if not current_order:
            continue
        override = PARTNER_ORDER_OVERRIDES.get(canonical_pair_key(list(current_order)))
        observed_orders: collections.Counter[tuple[str, str]] = collections.Counter()
        if override:
            target_order = override
        else:
            rows = fetch_entries_for_commander(client, commander["id"], args.sample_limit)
            seen_sources: set[str] = set()

            for row in rows:
                source_key = (row.get("decklist_url") or "").strip()
                if not source_key:
                    players = row.get("players") or {}
                    tournaments = row.get("tournaments") or {}
                    source_key = f"{tournaments.get('topdeck_tid','')}::{players.get('topdeck_id','')}"
                if source_key in seen_sources:
                    continue
                seen_sources.add(source_key)

                observed = observe_pair_order({**row, **{"commander_names": list(current_order)}}, session, args.timeout)
                if not observed:
                    continue
                observed_orders[observed] += 1
                if sum(observed_orders.values()) >= args.observation_limit:
                    break

            target_order = choose_target_order(current_order, observed_orders)
        current_name = commander["name"]
        target_name = " / ".join(target_order)
        observations = "; ".join(
            f"{left} / {right}:{count}" for (left, right), count in observed_orders.most_common()
        )

        if target_name != current_name:
            conflict_id = name_to_id.get(target_name)
            if conflict_id and conflict_id != commander["id"]:
                if not args.dry_run:
                    repoint_tournament_entries(client, commander["id"], conflict_id)
                    delete_commander_row(client, commander["id"])
                merged += 1
                report_lines.append(
                    f'{commander["id"]},"{current_name}","{target_name}","{observations}","{" / ".join(current_order)}","{" / ".join(target_order)}",merged'
                )
                continue
            if not args.dry_run:
                update_commander_row(client, commander["id"], target_name, target_order)
            name_to_id.pop(current_name, None)
            name_to_id[target_name] = commander["id"]
            updated += 1
            report_lines.append(
                f'{commander["id"]},"{current_name}","{target_name}","{observations}","{" / ".join(current_order)}","{" / ".join(target_order)}",yes'
            )
        else:
            report_lines.append(
                f'{commander["id"]},"{current_name}","{target_name}","{observations}","{" / ".join(current_order)}","{" / ".join(target_order)}",no'
            )

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text("\n".join(report_lines) + "\n")
    print(f"partner_rows={len(partner_rows)}")
    print(f"updated={updated}")
    print(f"merged={merged}")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
