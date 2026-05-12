#!/usr/bin/env python3
"""Repair tournament_entries top-cut flags from final standings and tournament structure."""

from __future__ import annotations

import json
import os
from collections import defaultdict

from ingest import SupabaseClient, load_local_env
from run_historical_tournament_sim import fetch_all, in_filter


def batched(values: list[str], batch_size: int) -> list[list[str]]:
    return [values[index : index + batch_size] for index in range(0, len(values), batch_size)]


def main() -> None:
    load_local_env()
    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])

    tournaments = fetch_all(
        client,
        "tournaments",
        {
            "select": "id,top_cut,player_count",
            "top_cut": "gt.0",
        },
    )

    top_cut_groups: dict[int, list[str]] = defaultdict(list)
    small_tournament_ids: list[str] = []
    large_tournament_ids: list[str] = []
    for row in tournaments:
        tournament_id = row.get("id")
        if not tournament_id:
            continue
        tid = str(tournament_id)
        top_cut = int(row.get("top_cut") or 0)
        player_count = int(row.get("player_count") or 0)
        top_cut_groups[top_cut].append(tid)
        if player_count <= 34:
            small_tournament_ids.append(tid)
        else:
            large_tournament_ids.append(tid)

    operations = 0
    for top_cut, tournament_ids in sorted(top_cut_groups.items()):
        for chunk in batched(tournament_ids, 100):
            filters = {"tournament_id": f"in.{in_filter(chunk)}"}
            client.update(
                "tournament_entries",
                {"made_top_cut": True},
                filters={**filters, "final_standing": f"lte.{top_cut}"},
                max_retries=8,
            )
            client.update(
                "tournament_entries",
                {"made_top_cut": False},
                filters={**filters, "final_standing": f"gt.{top_cut}"},
                max_retries=8,
            )
            operations += 2

    for threshold, tournament_ids in ((4, small_tournament_ids), (16, large_tournament_ids)):
        for chunk in batched(tournament_ids, 100):
            filters = {"tournament_id": f"in.{in_filter(chunk)}"}
            client.update(
                "tournament_entries",
                {"made_top_16": True},
                filters={**filters, "final_standing": f"lte.{threshold}"},
                max_retries=8,
            )
            client.update(
                "tournament_entries",
                {"made_top_16": False},
                filters={**filters, "final_standing": f"gt.{threshold}"},
                max_retries=8,
            )
            operations += 2

    entries = fetch_all(
        client,
        "tournament_entries",
        {
            "select": "tournament_id,final_standing,made_top_cut,made_top_16,tournaments!inner(top_cut,player_count)",
        },
    )
    mismatch_top_cut = 0
    mismatch_top_16 = 0
    for row in entries:
        tournament = row.get("tournaments") or {}
        final_standing = row.get("final_standing")
        if final_standing is None:
            continue
        try:
            standing_value = int(final_standing)
        except (TypeError, ValueError):
            continue
        top_cut = int(tournament.get("top_cut") or 0)
        player_count = int(tournament.get("player_count") or 0)
        expected_top_cut = standing_value <= top_cut if top_cut > 0 else False
        expected_top_16 = standing_value <= (4 if player_count <= 34 else 16)
        if bool(row.get("made_top_cut")) != expected_top_cut:
            mismatch_top_cut += 1
        if bool(row.get("made_top_16")) != expected_top_16:
            mismatch_top_16 += 1

    print(
        json.dumps(
            {
                "tournaments_with_top_cut": len(tournaments),
                "distinct_top_cut_values": sorted(top_cut_groups),
                "operations": operations,
                "remaining_mismatch_top_cut": mismatch_top_cut,
                "remaining_mismatch_top_16": mismatch_top_16,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
