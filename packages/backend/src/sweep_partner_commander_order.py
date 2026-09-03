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
    clean_commander_card_name,
    load_legal_commander_pair_order_map,
)
from supabase import Client
from supabase_client import get_supabase_client


def format_report_line(
    commander_id: str,
    current_name: str,
    target_name: str,
    observations: str,
    current_order: tuple[str, str],
    target_order: tuple[str, str],
    status: str,
) -> str:
    return (
        f'{commander_id},"{current_name}","{target_name}","{observations}",'
        f'"{" / ".join(current_order)}","{" / ".join(target_order)}",{status}'
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


def fetch_entries_for_commander(client: Client, commander_id: str, limit: int) -> list[dict]:
    return (
        client.table("tournament_entries")
        .select("id,decklist_url,players(topdeck_id),tournaments(topdeck_tid,start_date)")
        .eq("commander_id", commander_id)
        .order("tournaments(start_date)", desc=True)
        .limit(limit)
        .execute()
        .data
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
    """Pick the canonical order for a partner pair.

    Consults the same authoritative sources ``ingest.py``'s
    ``normalize_partner_order()`` does -- ``legal_commander_pairings.json`` first,
    then the hand-curated ``PARTNER_ORDER_OVERRIDES`` -- before falling back to
    observed decklist orders. Skipping the legal-pairing map here (as this
    function previously did) meant the sweep could leave two rows unmerged, or
    pick an order that disagreed with what ingestion would write for the same
    pair going forward, re-splitting it on the next tournament import.
    """
    pair_key = canonical_pair_key(list(current_order))
    legal_order = load_legal_commander_pair_order_map().get(pair_key)
    if legal_order:
        return legal_order
    override = PARTNER_ORDER_OVERRIDES.get(pair_key)
    if override:
        return override
    if not observations:
        return current_order

    top_count = max(observations.values())
    top_orders = [order for order, count in observations.items() if count == top_count]
    if current_order in top_orders:
        return current_order
    return sorted(top_orders)[0]


RECONCILABLE_METADATA_COLUMNS = (
    "scryfall_ids",
    "color_identity",
    "archetype",
    "win_condition",
    "notes",
)


def merge_commander_metadata(retained: dict, duplicate: dict) -> dict:
    """Compute the metadata patch to apply to the retained commander row.

    ``commanders`` carries five non-key columns (``scryfall_ids``,
    ``color_identity``, ``archetype``, ``win_condition``, ``notes``) that the
    old merge path discarded outright by deleting the duplicate row without
    ever reading them (#316). This fills any column that is null on the
    retained row with the duplicate's value where the duplicate has a
    non-null one -- the duplicate only fills gaps. A column already non-null
    on the retained row is never overwritten, so last-write-wins can't clobber
    curated data with whatever happened to be on the row being deleted.
    """
    patch: dict = {}
    for column in RECONCILABLE_METADATA_COLUMNS:
        if retained.get(column) is not None:
            continue
        duplicate_value = duplicate.get(column)
        if duplicate_value is None:
            continue
        patch[column] = duplicate_value
    return patch


def update_commander_metadata(client: Client, commander_id: str, patch: dict) -> None:
    if not patch:
        return
    endpoint = f"{client.postgrest.base_url}/commanders"
    response = requests.patch(
        endpoint,
        headers=dict(client.postgrest.headers),
        params={"id": f"eq.{commander_id}"},
        json=patch,
        timeout=60,
    )
    response.raise_for_status()


def repoint_tournament_entries(
    client: Client,
    source_commander_id: str,
    target_commander_id: str,
) -> None:
    endpoint = f"{client.postgrest.base_url}/tournament_entries"
    response = requests.patch(
        endpoint,
        headers=dict(client.postgrest.headers),
        params={"commander_id": f"eq.{source_commander_id}"},
        json={"commander_id": target_commander_id},
        timeout=60,
    )
    response.raise_for_status()


def repoint_commander_matchups(
    client: Client,
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
    endpoint = f"{client.postgrest.base_url}/commander_matchups"
    for column in ("commander_id", "opponent_commander_id"):
        response = requests.patch(
            endpoint,
            headers=dict(client.postgrest.headers),
            params={column: f"eq.{source_commander_id}"},
            json={column: target_commander_id},
            timeout=60,
        )
        response.raise_for_status()


def update_commander_row(
    client: Client,
    commander_id: str,
    target_name: str,
    target_order: tuple[str, str],
) -> None:
    endpoint = f"{client.postgrest.base_url}/commanders"
    response = requests.patch(
        endpoint,
        headers=dict(client.postgrest.headers),
        params={"id": f"eq.{commander_id}"},
        json={"name": target_name, "commander_names": list(target_order)},
        timeout=60,
    )
    response.raise_for_status()


def delete_commander_row(client: Client, commander_id: str) -> None:
    endpoint = f"{client.postgrest.base_url}/commanders"
    response = requests.delete(
        endpoint,
        headers=dict(client.postgrest.headers),
        params={"id": f"eq.{commander_id}"},
        timeout=60,
    )
    response.raise_for_status()


def mark_sweep_pending(client: Client, merged_count: int) -> None:
    """Flag a live merge for the next maintenance run to pick up (#314).

    ``chain-elo`` in ``ci-backend-ingestion.yml`` skips dispatching a
    maintenance refresh when an Elo job is already in flight. If that job has
    already passed its own commander-view rebuild, this sweep's merges land
    after it and the derived views (``commander_weekly_trends``,
    ``commander_monthly_trends``, ``player_commander_profiles``) reference
    merged-away commander IDs until some later, unrelated refresh notices.

    Marking this flag unconditionally on every live merge -- rather than only
    when chain-elo is about to skip, which this script has no way to know in
    advance -- is deliberate: ``ci-backend-maintenance.yml`` consumes and
    clears it on every run regardless of outcome, so the redundant case (a
    normal dispatch that already refreshes everything) just clears the flag
    a beat early rather than doing any harm.

    Best-effort: a failure here must not fail the sweep itself (which has
    already committed real merges by this point) -- it's surfaced as a
    warning instead, matching the sweep's overall best-effort posture.
    """
    endpoint = f"{client.postgrest.base_url}/rpc/mark_partner_commander_sweep_pending"
    try:
        response = requests.post(
            endpoint,
            headers=dict(client.postgrest.headers),
            json={"p_merged_count": merged_count},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"warning: failed to mark partner-commander sweep pending: {exc}")


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
    client = get_supabase_client(supabase_url, supabase_key)
    session = requests.Session()

    commander_select_columns = "id,name,commander_names," + ",".join(RECONCILABLE_METADATA_COLUMNS)
    commanders = (
        client.table("commanders").select(commander_select_columns).order("name", desc=False).limit(5000).execute().data
    )
    partner_rows = [row for row in commanders if current_pair_order(row)]
    name_to_id = {row["name"]: row["id"] for row in commanders if row.get("name")}
    id_to_row = {row["id"]: row for row in commanders if row.get("id")}

    report_lines = ["commander_id,current_name,target_name,observations,current_order,target_order,updated"]
    updated = 0
    merged = 0

    for commander in partner_rows:
        current_order = current_pair_order(commander)
        if not current_order:
            continue
        pair_key = canonical_pair_key(list(current_order))
        known_order = load_legal_commander_pair_order_map().get(pair_key) or PARTNER_ORDER_OVERRIDES.get(pair_key)
        observed_orders: collections.Counter[tuple[str, str]] = collections.Counter()
        if known_order:
            target_order = known_order
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

                observed_row = {**row, "commander_names": list(current_order)}
                observed = observe_pair_order(observed_row, session, args.timeout)
                if not observed:
                    continue
                observed_orders[observed] += 1
                if sum(observed_orders.values()) >= args.observation_limit:
                    break

            target_order = choose_target_order(current_order, observed_orders)
        current_name = commander["name"]
        target_name = " / ".join(target_order)
        observations = "; ".join(f"{left} / {right}:{count}" for (left, right), count in observed_orders.most_common())

        if target_name != current_name:
            conflict_id = name_to_id.get(target_name)
            if conflict_id and conflict_id != commander["id"]:
                if not args.dry_run:
                    # Reconcile the duplicate's metadata onto the retained row
                    # before it's deleted below -- otherwise scryfall_ids,
                    # color_identity, archetype, win_condition, and notes are
                    # silently discarded with the row (#316). Read the
                    # retained row's *current* in-memory state (not the
                    # initial fetch) so a retained row that already picked up
                    # metadata from an earlier merge in this same run doesn't
                    # get gaps re-filled from a now-stale snapshot.
                    retained_row = id_to_row.get(conflict_id, {})
                    metadata_patch = merge_commander_metadata(retained_row, commander)
                    if metadata_patch:
                        update_commander_metadata(client, conflict_id, metadata_patch)
                        retained_row.update(metadata_patch)

                    repoint_tournament_entries(client, commander["id"], conflict_id)
                    # commander_matchups carries two FKs to commanders(id)
                    # (commander_id and opponent_commander_id). Both must be
                    # repointed before the delete below, or Postgres rejects
                    # it with a foreign-key violation -- which aborts the
                    # sweep mid-run and leaves this pair, and every later one
                    # in the same run, unmerged.
                    repoint_commander_matchups(client, commander["id"], conflict_id)
                    delete_commander_row(client, commander["id"])
                merged += 1
                report_lines.append(
                    format_report_line(
                        commander["id"], current_name, target_name, observations, current_order, target_order, "merged"
                    )
                )
                continue
            if not args.dry_run:
                update_commander_row(client, commander["id"], target_name, target_order)
            name_to_id.pop(current_name, None)
            name_to_id[target_name] = commander["id"]
            updated += 1
            report_lines.append(
                format_report_line(
                    commander["id"], current_name, target_name, observations, current_order, target_order, "yes"
                )
            )
        else:
            report_lines.append(
                format_report_line(
                    commander["id"], current_name, target_name, observations, current_order, target_order, "no"
                )
            )

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text("\n".join(report_lines) + "\n")
    print(f"partner_rows={len(partner_rows)}")
    print(f"updated={updated}")
    print(f"merged={merged}")
    print(f"report={args.report}")

    if merged > 0 and not args.dry_run:
        mark_sweep_pending(client, merged)


if __name__ == "__main__":
    main()
