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
from ingest import (
    PARTNER_ORDER_OVERRIDES,
    SupabaseClient,
    clean_commander_card_name,
    load_legal_commander_pair_order_map,
    normalize_partner_order,
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


def choose_target_order(
    current_order: tuple[str, str],
    observations: collections.Counter[tuple[str, str]],
) -> tuple[str, str]:
    """Pick the canonical display order for an existing partner-pair row.

    Bug (#260): this used to consult only ``PARTNER_ORDER_OVERRIDES`` before
    falling back to per-run TopDeck deck-page observation. ``ingest.py``'s
    ``normalize_partner_order`` -- the function that decides the order for
    *every future* partner-pair write -- checks the generated legal-pair
    order map (``load_legal_commander_pair_order_map()``, ~3,100 pairs)
    *first* and only falls back to ``PARTNER_ORDER_OVERRIDES`` after that.
    Because the sweep never consulted the legal-pair order map, it picked an
    order from network observation for the vast majority of pairs while
    fresh ingestion picked the (possibly different) legal-pair-map order for
    the exact same pair -- so a pair "fixed" by the sweep would immediately
    re-split the next time it was ingested. Always defer to
    ``normalize_partner_order`` when it has an opinion (legal-pair map or
    override) so a swept row can never diverge from what ingestion produces
    for the same pair going forward. Only fall back to the historical
    observation heuristic for pairs neither source recognizes.
    """
    pair_key = canonical_pair_key(list(current_order))
    has_canonical_source = pair_key in load_legal_commander_pair_order_map() or pair_key in PARTNER_ORDER_OVERRIDES
    if has_canonical_source:
        canonical_order = tuple(normalize_partner_order(list(current_order)))
        if len(canonical_order) == 2:
            return canonical_order
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


def repoint_commander_matchups(
    client: SupabaseClient,
    source_commander_id: str,
    target_commander_id: str,
) -> None:
    """Repoint ``commander_matchups`` rows from a duplicate commander to its canonical row.

    ``commander_matchups`` has foreign keys from both ``commander_id`` and
    ``opponent_commander_id`` to ``commanders(id)`` (see the
    ``20260110000001_initial_schema.sql`` migration), so both columns must be
    repointed away from a duplicate commander before that commander row can
    be deleted, or Postgres will reject the delete with a foreign-key
    violation. There is no unique constraint on ``commander_matchups`` beyond
    its own ``id``, so repointing either column can never collide with an
    existing row. Filtering by ``eq.<source_commander_id>`` also makes this
    safely re-runnable: once a column has been repointed, re-running finds no
    matching rows and is a no-op.
    """
    endpoint = f"{client.url}/rest/v1/commander_matchups"
    for column in ("commander_id", "opponent_commander_id"):
        response = requests.patch(
            endpoint,
            headers=client.headers,
            params={column: f"eq.{source_commander_id}"},
            json={column: target_commander_id},
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
        pair_key = canonical_pair_key(list(current_order))
        canonical_source_order = PARTNER_ORDER_OVERRIDES.get(pair_key) or load_legal_commander_pair_order_map().get(
            pair_key
        )
        observed_orders: collections.Counter[tuple[str, str]] = collections.Counter()
        if canonical_source_order:
            target_order = canonical_source_order
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

                observed = observe_pair_order(
                    {**row, **{"commander_names": list(current_order)}}, session, args.timeout
                )
                if not observed:
                    continue
                observed_orders[observed] += 1
                if sum(observed_orders.values()) >= args.observation_limit:
                    break

            target_order = choose_target_order(current_order, observed_orders)
        current_name = commander["name"]
        target_name = " / ".join(target_order)
        current_order_display = " / ".join(current_order)
        target_order_display = " / ".join(target_order)
        observations = "; ".join(f"{left} / {right}:{count}" for (left, right), count in observed_orders.most_common())
        report_row = (
            f'{commander["id"]},"{current_name}","{target_name}","{observations}",'
            f'"{current_order_display}","{target_order_display}"'
        )

        if target_name != current_name:
            conflict_id = name_to_id.get(target_name)
            if conflict_id and conflict_id != commander["id"]:
                if not args.dry_run:
                    repoint_tournament_entries(client, commander["id"], conflict_id)
                    delete_commander_row(client, commander["id"])
                merged += 1
                report_lines.append(f"{report_row},merged")
                continue
            if not args.dry_run:
                update_commander_row(client, commander["id"], target_name, target_order)
            name_to_id.pop(current_name, None)
            name_to_id[target_name] = commander["id"]
            updated += 1
            report_lines.append(f"{report_row},yes")
        else:
            report_lines.append(f"{report_row},no")

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text("\n".join(report_lines) + "\n")
    print(f"partner_rows={len(partner_rows)}")
    print(f"updated={updated}")
    print(f"merged={merged}")
    print(f"report={args.report}")


if __name__ == "__main__":
    main()
