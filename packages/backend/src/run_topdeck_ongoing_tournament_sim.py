#!/usr/bin/env python3
"""Simulate an ongoing TopDeck tournament from its current posted state."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from ingest import TopDeckClient, is_draw_winner_id, load_local_env
from run_historical_tournament_sim import build_feature_context, fetch_pre_tournament_elos
from sim_engine import (
    apply_pod_result,
    apply_round_elo_updates,
    initialize_state,
    run_monte_carlo_from_state,
)
from sim_models import load_draw_model_artifact
from sim_types import FeatureContext, Pod, PodResult, SimPlayer, TournamentSpec

DEFAULT_DRAW_MODEL_PATH = Path("/tmp/cedh_draw_model_artifact_v4.pkl")


def fetch_event_page_html(event_id: str) -> str:
    response = requests.get(f"https://topdeck.gg/event/{event_id}", timeout=30)
    response.raise_for_status()
    return response.text


def extract_numeric_value(payload: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = payload.get(key)
        if value in (None, ""):
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed >= 0:
            return parsed
    return None


def infer_structure(
    tournament: dict[str, Any],
    event_html: str,
    *,
    swiss_rounds_override: int | None,
    top_cut_override: int | None,
) -> tuple[int, int]:
    event_data = tournament.get("eventData") or {}
    swiss_rounds = (
        swiss_rounds_override
        or extract_numeric_value(tournament, "swissNum", "swissRounds", "numRounds")
        or extract_numeric_value(event_data, "swissNum", "swissRounds", "numRounds")
    )
    top_cut = (
        top_cut_override
        or extract_numeric_value(tournament, "topCut")
        or extract_numeric_value(event_data, "topCut", "cutTo")
    )

    if swiss_rounds is None:
        swiss_patterns = [
            r"(\d+)\s+Rounds?\s+of\s+Swiss",
            r"(\d+)\s+Round(?:s)?\s+Swiss",
            r"Swiss[^0-9]{0,20}(\d+)\s+Rounds?",
        ]
        for pattern in swiss_patterns:
            match = re.search(pattern, event_html, flags=re.I)
            if match:
                swiss_rounds = int(match.group(1))
                break

    if top_cut is None:
        top_cut_patterns = [
            r"Top\s+(\d+)\s+Cut",
            r"Cut\s+to\s+Top\s+(\d+)",
            r"Top\s+(\d+)\b",
        ]
        for pattern in top_cut_patterns:
            match = re.search(pattern, event_html, flags=re.I)
            if match:
                candidate = int(match.group(1))
                if candidate > 0:
                    top_cut = candidate
                    break

    if swiss_rounds is None:
        raise RuntimeError(
            "Unable to infer total swiss rounds from the TopDeck payload/event page. "
            "Pass --swiss-rounds explicitly."
        )
    if top_cut is None:
        raise RuntimeError(
            "Unable to infer top cut size from the TopDeck payload/event page. "
            "Pass --top-cut explicitly."
        )
    return swiss_rounds, top_cut


def collect_players(tournament: dict[str, Any]) -> dict[str, str]:
    players: dict[str, str] = {}
    for standing in tournament.get("standings") or []:
        player_id = standing.get("id")
        if player_id:
            players[str(player_id)] = str(standing.get("name") or player_id)
    for round_data in tournament.get("rounds") or []:
        for table in round_data.get("tables") or []:
            for player in table.get("players") or []:
                player_id = player.get("id")
                if player_id:
                    players[str(player_id)] = str(player.get("name") or players.get(str(player_id)) or player_id)
    return players


def standings_tiebreak_seed_map(tournament: dict[str, Any]) -> dict[str, int]:
    seeds: dict[str, int] = {}
    standings = tournament.get("standings") or []
    for index, standing in enumerate(standings, start=1):
        player_id = standing.get("id")
        if player_id:
            seeds[str(player_id)] = index
    return seeds


def in_filter(values: list[str]) -> str:
    escaped = [value.replace('"', '\\"') for value in values]
    return "(" + ",".join(f'"{value}"' for value in escaped) + ")"


def fetch_existing_players(client, topdeck_ids: list[str]) -> dict[str, dict[str, str]]:
    rows = client.select(
        "players",
        {
            "select": "id,topdeck_id,name",
            "topdeck_id": f"in.{in_filter(topdeck_ids)}",
        },
        max_retries=8,
    )
    return {
        str(row["topdeck_id"]): {
            "id": str(row["id"]),
            "name": str(row.get("name") or row["topdeck_id"]),
        }
        for row in rows
        if row.get("topdeck_id") and row.get("id")
    }


def parse_start_date(value: Any) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value)).astimezone()
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def build_pods_for_round(round_data: dict[str, Any], round_index: int, id_map: dict[str, str]) -> list[Pod]:
    pods: list[Pod] = []
    for table in round_data.get("tables") or []:
        players = table.get("players") or []
        player_ids = [
            id_map[str(player.get("id"))]
            for player in players
            if player.get("id") and str(player.get("id")) in id_map
        ]
        if len(player_ids) < 2:
            continue
        table_number = table.get("table") or table.get("table_number") or table.get("tableNumber") or (len(pods) + 1)
        pods.append(
            Pod(
                round_index=round_index,
                table_number=int(table_number),
                player_ids=player_ids,
                round_name=f"Round {round_index + 1}",
                seats_by_player={player_id: seat for seat, player_id in enumerate(player_ids, start=1)},
            )
        )
    return pods


def table_completed(table: dict[str, Any]) -> bool:
    winner_id = table.get("winner_id") or table.get("winnerId")
    status = str(table.get("status") or "").strip().lower()
    if winner_id not in (None, ""):
        return True
    return status == "completed"


def table_active(table: dict[str, Any]) -> bool:
    status = str(table.get("status") or "").strip().lower()
    if status in {"active", "pending"}:
        return True
    winner_id = table.get("winner_id") or table.get("winnerId")
    return winner_id in (None, "")


def build_result_for_table(pod: Pod, table: dict[str, Any]) -> PodResult | None:
    winner_id = table.get("winner_id") or table.get("winnerId")
    if not table_completed(table):
        return None
    draw = is_draw_winner_id(winner_id)
    normalized_winner_id = None if draw else str(winner_id)
    return PodResult(
        round_index=pod.round_index,
        table_number=pod.table_number,
        player_ids=pod.player_ids,
        is_draw=draw,
        winner_id=normalized_winner_id,
        win_probabilities=tuple(),
        draw_probability=0.0,
    )


def split_rounds(
    tournament: dict[str, Any],
    swiss_rounds: int,
    id_map: dict[str, str],
) -> tuple[list[tuple[list[Pod], list[PodResult]]], int, list[Pod] | None]:
    completed_rounds: list[tuple[list[Pod], list[PodResult]]] = []
    active_round_index: int | None = None
    active_round_pods: list[Pod] | None = None

    for round_data in sorted(
        [row for row in tournament.get("rounds") or [] if isinstance(row.get("round"), int)],
        key=lambda row: int(row.get("round")),
    ):
        round_number = int(round_data["round"])
        if round_number > swiss_rounds:
            continue
        round_index = round_number - 1
        pods = build_pods_for_round(round_data, round_index, id_map)
        if not pods:
            continue
        tables = round_data.get("tables") or []
        if any(table_active(table) for table in tables):
            active_round_index = round_index
            active_round_pods = pods
            break
        results = [
            result
            for pod, table in zip(pods, tables, strict=False)
            if (result := build_result_for_table(pod, table)) is not None
        ]
        if len(results) == len(pods):
            completed_rounds.append((pods, results))

    if active_round_index is None:
        active_round_index = len(completed_rounds)
    return completed_rounds, active_round_index, active_round_pods


def build_base_state(
    client,
    tournament: dict[str, Any],
    *,
    swiss_rounds: int,
    top_cut: int,
    feature_context,
    player_records: dict[str, dict[str, str]],
) -> tuple[Any, int, list[Pod] | None]:
    player_names = collect_players(tournament)
    tiebreak_seeds = standings_tiebreak_seed_map(tournament)
    topdeck_ids = sorted(player_names)
    start_date = parse_start_date(tournament.get("startDate"))
    known_player_ids = [
        player_records[topdeck_id]["id"]
        for topdeck_id in topdeck_ids
        if not player_records[topdeck_id]["id"].startswith("topdeck:")
    ]
    pre_elos = fetch_pre_tournament_elos(client, known_player_ids, start_date.isoformat())
    fallback_topdeck_ids = [topdeck_id for topdeck_id in topdeck_ids if topdeck_id not in tiebreak_seeds]
    fallback_rng = random.Random(f"ongoing:{tournament.get('id') or tournament.get('TID') or tournament.get('name')}")
    fallback_rng.shuffle(fallback_topdeck_ids)
    fallback_seed_by_topdeck_id = {
        topdeck_id: len(tiebreak_seeds) + index + 1 for index, topdeck_id in enumerate(fallback_topdeck_ids)
    }
    players = [
        SimPlayer(
            player_id=player_records[topdeck_id]["id"],
            name=player_names[topdeck_id],
            elo=float(pre_elos.get(player_records[topdeck_id]["id"], 1500.0)),
            topdeck_id=topdeck_id,
            tiebreak_seed=tiebreak_seeds[topdeck_id]
            if topdeck_id in tiebreak_seeds
            else fallback_seed_by_topdeck_id[topdeck_id],
        )
        for topdeck_id in topdeck_ids
    ]
    spec = TournamentSpec(
        tournament_id=str(tournament.get("id") or tournament.get("TID")),
        name=str(tournament.get("name") or tournament.get("id") or "TopDeck Event"),
        start_date=start_date,
        swiss_rounds=swiss_rounds,
        top_cut=top_cut,
        player_count=len(players),
        state=((tournament.get("eventData") or {}).get("state")),
        country=((tournament.get("eventData") or {}).get("country")),
    )
    state = initialize_state(spec, players, feature_context=feature_context)
    id_map = {topdeck_id: record["id"] for topdeck_id, record in player_records.items()}
    completed_rounds, active_round_index, active_round_pods = split_rounds(tournament, swiss_rounds, id_map)
    for pods, results in completed_rounds:
        for result in results:
            apply_pod_result(state, result)
        apply_round_elo_updates(state, pods, results)
    state.current_round_index = active_round_index
    return state, active_round_index, active_round_pods


def build_output(summary: dict[str, Any], state, active_round_index: int, active_round_pods: list[Pod] | None) -> dict[str, Any]:
    player_name_by_id = {player_id: player.name for player_id, player in state.players.items()}
    top_win = sorted(summary["win_probability"].items(), key=lambda item: item[1], reverse=True)[:10]
    advancement_probability = summary.get("advancement_probability", {})
    top40 = sorted(advancement_probability.get(40, {}).items(), key=lambda item: item[1], reverse=True)[:10]
    top16 = sorted(advancement_probability.get(16, {}).items(), key=lambda item: item[1], reverse=True)[:10]
    top4 = sorted(advancement_probability.get(4, {}).items(), key=lambda item: item[1], reverse=True)[:10]
    return {
        "tournament": {
            "id": state.spec.tournament_id,
            "name": state.spec.name,
            "player_count": state.spec.player_count,
            "swiss_rounds": state.spec.swiss_rounds,
            "top_cut": state.spec.top_cut,
        },
        "current_state": {
            "completed_swiss_rounds": active_round_index,
            "active_round_number": (active_round_index + 1) if active_round_pods else None,
            "active_tables": len(active_round_pods or []),
        },
        "top_win_probabilities": [
            {"player_id": player_id, "name": player_name_by_id.get(player_id, player_id), "win_probability": probability}
            for player_id, probability in top_win
        ],
        "top_top40_probabilities": [
            {"player_id": player_id, "name": player_name_by_id.get(player_id, player_id), "top40_probability": probability}
            for player_id, probability in top40
        ],
        "top_top16_probabilities": [
            {"player_id": player_id, "name": player_name_by_id.get(player_id, player_id), "top16_probability": probability}
            for player_id, probability in top16
        ],
        "top_top4_probabilities": [
            {"player_id": player_id, "name": player_name_by_id.get(player_id, player_id), "top4_probability": probability}
            for player_id, probability in top4
        ],
        "simulations": summary["simulations"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-id", required=True, help="TopDeck event slug/TID")
    parser.add_argument("--draw-model-path", default=str(DEFAULT_DRAW_MODEL_PATH))
    parser.add_argument("--simulations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--swiss-rounds", type=int, default=None)
    parser.add_argument("--top-cut", type=int, default=None)
    args = parser.parse_args()

    load_local_env()
    topdeck = TopDeckClient(os.environ["TOPDECK_API_KEY"])
    tournament = topdeck.get_tournament(args.event_id)
    event_html = fetch_event_page_html(args.event_id)
    swiss_rounds, top_cut = infer_structure(
        tournament,
        event_html,
        swiss_rounds_override=args.swiss_rounds,
        top_cut_override=args.top_cut,
    )

    player_names = collect_players(tournament)
    topdeck_ids = sorted(player_names)
    start_date = parse_start_date(tournament.get("startDate"))
    from ingest import SupabaseClient  # local import to keep script entry focused

    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])
    existing_players = fetch_existing_players(client, topdeck_ids)
    player_records = {
        topdeck_id: existing_players.get(topdeck_id) or {"id": f"topdeck:{topdeck_id}", "name": player_names[topdeck_id]}
        for topdeck_id in topdeck_ids
    }
    known_player_ids = [record["id"] for record in player_records.values() if not record["id"].startswith("topdeck:")]
    feature_context = (
        build_feature_context(client, known_player_ids, start_date.isoformat())
        if known_player_ids
        else FeatureContext()
    )
    state, active_round_index, active_round_pods = build_base_state(
        client,
        tournament,
        swiss_rounds=swiss_rounds,
        top_cut=top_cut,
        feature_context=feature_context,
        player_records=player_records,
    )
    state.track_round_stats = False

    draw_model = load_draw_model_artifact(args.draw_model_path)
    summary = run_monte_carlo_from_state(
        state,
        draw_model,
        simulations=args.simulations,
        seed=args.seed,
        workers=args.workers,
        start_round_index=active_round_index,
        locked_round_pods=active_round_pods,
        requested_advancement_sizes=(40, 16, 4),
        collect_detailed_metrics=False,
    ).to_dict()

    print(json.dumps(build_output(summary, state, active_round_index, active_round_pods), indent=2))


if __name__ == "__main__":
    main()
