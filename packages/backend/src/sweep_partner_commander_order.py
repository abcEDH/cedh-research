#!/usr/bin/env python3
"""Sweep to normalize partner commander display order.

Originally a one-off/manual script, this is now also wired in as a recurring
maintenance step (see ``.github/workflows/ci-backend-maintenance.yml``, full
refresh mode) so partner pairs don't stay split indefinitely between manual
runs. A pair can end up split across two ``commanders`` rows whenever the
canonical order this script (and ``ingest.py``) would assign to it changes
after the row was first created — e.g. a refreshed
``legal_commander_pairings.json`` snapshot, a newly added
``PARTNER_ORDER_OVERRIDES`` entry, or simply a row that predates either.
Regular ingestion always looks up/creates commanders by canonical name, so it
never mutates or merges a pre-existing row under a different name; only this
sweep repoints tournament entries and deletes the stale row.
"""

from __future__ import annotations

import argparse
import collections
from datetime import UTC, datetime
from pathlib import Path

import requests

from backfill_moxfield_commanders import (
    fetch_topdeck_deck_page_details,
    load_credentials,
)
from ingest import (
    PARTNER_ORDER_OVERRIDES,
    SupabaseClient,
    clean_commander_card_name,
    load_legal_commander_pair_order_map,
)


def canonical_pair_key(names: list[str]) -> tuple[str, ...]:
    cleaned = [clean_commander_card_name(name) for name in names if name and name.strip()]
    return tuple(sorted(cleaned))


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


def resolve_authoritative_order(current_order: tuple[str, str]) -> tuple[str, str] | None:
    """Return the order ``ingest.py`` would assign this pair at write time, if known.

    Checks the same two sources, in the same priority, as
    ``ingest.py``'s ``normalize_partner_order()``: the Scryfall-derived legal
    pairing snapshot first, then the hand-maintained ``PARTNER_ORDER_OVERRIDES``.
    Returns ``None`` when neither has an opinion, meaning the caller has to
    fall back to observed decklist orderings.
    """
    pair_key = canonical_pair_key(list(current_order))
    return load_legal_commander_pair_order_map().get(pair_key) or PARTNER_ORDER_OVERRIDES.get(pair_key)


def choose_target_order(
    current_order: tuple[str, str],
    observations: collections.Counter[tuple[str, str]],
) -> tuple[str, str]:
    """Pick the canonical display order for a partner pair.

    Prefers whatever ``ingest.py`` would authoritatively assign the pair (see
    ``resolve_authoritative_order``) and only falls back to observed decklist
    orderings when neither the legal-pairings snapshot nor the manual override
    table has an entry. Previously this function only consulted
    ``PARTNER_ORDER_OVERRIDES``, so a pair whose canonical order came solely
    from the legal-pairings snapshot (and had no decklists to observe) could be
    left in a stale order that disagreed with what fresh ingestion would
    assign to the same pair, causing it to split into a second row again on
    the very next ingest.
    """
    authoritative_order = resolve_authoritative_order(current_order)
    if authoritative_order:
        return authoritative_order
    if not observations:
        return current_order

    top_count = max(observations.values())
    top_orders = [order for order, count in observations.items() if count == top_count]
    if current_order in top_orders:
        return current_order
    return sorted(top_orders)[0]


def repoint_tournament_entries(
    client: SupabaseClient,
    source_commander_id: str,
    target_commander_id: str,
) -> None:
    endpoint = f"{client.url}/rest/v1/tournament_entries"
    response = requests.patch(
        endpoint,
        headers=client.headers,
        params={"commander_id": f"eq.{source_commander_id}"},
        json={"commander_id": target_commander_id},
        timeout=60,
    )
    response.raise_for_status()


def update_commander_row(
    client: SupabaseClient,
    commander_id: str,
    target_name: str,
    target_order: tuple[str, str],
) -> None:
    endpoint = f"{client.url}/rest/v1/commanders"
    response = requests.patch(
        endpoint,
        headers=client.headers,
        params={"id": f"eq.{commander_id}"},
        json={"name": target_name, "commander_names": list(target_order)},
        timeout=60,
    )
    response.raise_for_status()


def delete_commander_row(client: SupabaseClient, commander_id: str) -> None:
    endpoint = f"{client.url}/rest/v1/commanders"
    response = requests.delete(
        endpoint,
        headers=client.headers,
        params={"id": f"eq.{commander_id}"},
        timeout=60,
    )
    response.raise_for_status()


def format_report_row(
    commander_id: str,
    current_name: str,
    target_name: str,
    observations: str,
    current_order: tuple[str, str],
    target_order: tuple[str, str],
    *,
    status: str,
) -> str:
    return (
        f'{commander_id},"{current_name}","{target_name}","{observations}",'
        f'"{" / ".join(current_order)}","{" / ".join(target_order)}",{status}'
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sweep to normalize partner commander order.")
    parser.add_argument("--sample-limit", type=int, default=40, help="Recent entries to inspect per commander pair")
    parser.add_argument("--observation-limit", type=int, default=10, help="Observed deck orders to collect per pair")
    parser.add_argument("--timeout", type=float, default=10, help="Network timeout for deck page lookups")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without updating Supabase")
    parser.add_argument(
        "--report",
        default=None,
        help=(
            "CSV report path (default: "
            "logs/sweep_partner_commander_order_<UTC timestamp>.csv, "
            "generated fresh each run since this is now invoked repeatedly)"
        ),
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    report_path = args.report or (f"logs/sweep_partner_commander_order_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.csv")

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
        authoritative_order = resolve_authoritative_order(current_order)
        observed_orders: collections.Counter[tuple[str, str]] = collections.Counter()
        if authoritative_order:
            target_order = authoritative_order
        else:
            rows = fetch_entries_for_commander(client, commander["id"], args.sample_limit)
            seen_sources: set[str] = set()

            for row in rows:
                source_key = (row.get("decklist_url") or "").strip()
                if not source_key:
                    players = row.get("players") or {}
                    tournaments = row.get("tournaments") or {}
                    source_key = f"{tournaments.get('topdeck_tid', '')}::{players.get('topdeck_id', '')}"
                if source_key in seen_sources:
                    continue
                seen_sources.add(source_key)

                entry = {**row, "commander_names": list(current_order)}
                observed = observe_pair_order(entry, session, args.timeout)
                if not observed:
                    continue
                observed_orders[observed] += 1
                if sum(observed_orders.values()) >= args.observation_limit:
                    break

            target_order = choose_target_order(current_order, observed_orders)
        current_name = commander["name"]
        target_name = " / ".join(target_order)
        observations = "; ".join(f"{left} / {right}:{count}" for (left, right), count in observed_orders.most_common())

        row_args = (commander["id"], current_name, target_name, observations, current_order, target_order)

        if target_name != current_name:
            conflict_id = name_to_id.get(target_name)
            if conflict_id and conflict_id != commander["id"]:
                if not args.dry_run:
                    repoint_tournament_entries(client, commander["id"], conflict_id)
                    delete_commander_row(client, commander["id"])
                merged += 1
                report_lines.append(format_report_row(*row_args, status="merged"))
                continue
            if not args.dry_run:
                update_commander_row(client, commander["id"], target_name, target_order)
            name_to_id.pop(current_name, None)
            name_to_id[target_name] = commander["id"]
            updated += 1
            report_lines.append(format_report_row(*row_args, status="yes"))
        else:
            report_lines.append(format_report_row(*row_args, status="no"))

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text("\n".join(report_lines) + "\n")
    print(f"partner_rows={len(partner_rows)}")
    print(f"updated={updated}")
    print(f"merged={merged}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
