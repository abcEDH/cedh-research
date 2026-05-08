#!/usr/bin/env python3
"""Resume simulation for a historical tournament from after a given Swiss round."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from typing import Any

from ingest import SupabaseClient, load_local_env
from run_historical_tournament_sim import (
    DEFAULT_DRAW_MODEL_PATH,
    build_spec_and_players,
    derive_top_cut_player_ids,
    fetch_all,
    in_filter,
)
from sim_engine import apply_pod_result, initialize_state, run_monte_carlo_from_state
from sim_models import load_draw_model_artifact
from sim_types import Pod, PodResult


def fetch_round_rows(client: SupabaseClient, tournament_id: str) -> list[dict[str, Any]]:
    return fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": "game_id,player_id,entry_id,round_number,table_number,result",
            "tournament_id": f"eq.{tournament_id}",
            "order": "round_number.asc,table_number.asc,game_id.asc",
        },
    )


def fetch_seat_map(client: SupabaseClient, game_ids: list[str]) -> dict[tuple[str, str], int]:
    rows: list[dict[str, Any]] = []
    for start in range(0, len(game_ids), 100):
        chunk = game_ids[start : start + 100]
        rows.extend(
            fetch_all(
                client,
                "game_participants",
                {
                    "select": "game_id,entry_id,seat_position",
                    "game_id": f"in.{in_filter(chunk)}",
                },
            )
        )
    return {
        (str(row["game_id"]), str(row["entry_id"])): int(row["seat_position"])
        for row in rows
        if row.get("game_id") and row.get("entry_id") and row.get("seat_position") is not None
    }


def build_round_structures(
    round_rows: list[dict[str, Any]],
    seat_map: dict[tuple[str, str], int],
) -> dict[int, tuple[list[Pod], list[PodResult]]]:
    grouped: dict[int, dict[tuple[str, int], list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in round_rows:
        round_number = row.get("round_number")
        table_number = row.get("table_number")
        game_id = row.get("game_id")
        if round_number is None or table_number is None or not game_id:
            continue
        grouped[int(round_number)][(str(game_id), int(table_number))].append(row)

    rounds: dict[int, tuple[list[Pod], list[PodResult]]] = {}
    for round_number, tables in grouped.items():
        pods: list[Pod] = []
        results: list[PodResult] = []
        ordered_tables = sorted(tables.items(), key=lambda item: (item[1][0].get("table_number") or 0, item[0][0]))
        for table_index, ((game_id, table_number), rows) in enumerate(ordered_tables, start=1):
            player_ids = [str(row["player_id"]) for row in rows if row.get("player_id")]
            seats_by_player = {
                str(row["player_id"]): seat_map.get((game_id, str(row["entry_id"])), seat)
                for seat, row in enumerate(rows, start=1)
                if row.get("player_id")
            }
            pod = Pod(
                round_index=round_number - 1,
                table_number=int(table_number or table_index),
                player_ids=player_ids,
                round_name=f"Round {round_number}",
                seats_by_player=seats_by_player,
            )
            winner_ids = [str(row["player_id"]) for row in rows if str(row.get("result") or "").lower() == "win"]
            is_draw = any(str(row.get("result") or "").lower() == "draw" for row in rows)
            result = PodResult(
                round_index=round_number - 1,
                table_number=pod.table_number,
                player_ids=player_ids,
                is_draw=is_draw,
                winner_id=None if is_draw else (winner_ids[0] if winner_ids else None),
                win_probabilities=tuple(),
                draw_probability=0.0,
            )
            pods.append(pod)
            results.append(result)
        rounds[round_number] = (pods, results)
    return rounds


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournament-id", required=True)
    parser.add_argument("--completed-rounds", type=int, required=True)
    parser.add_argument("--draw-model-path", default=str(DEFAULT_DRAW_MODEL_PATH))
    parser.add_argument("--simulations", type=int, default=500)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--lock-next-round", action="store_true")
    args = parser.parse_args()

    load_local_env()
    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])
    spec, players, entries, feature_context = build_spec_and_players(client, args.tournament_id)
    round_rows = fetch_round_rows(client, args.tournament_id)
    game_ids = sorted({str(row["game_id"]) for row in round_rows if row.get("game_id")})
    seat_map = fetch_seat_map(client, game_ids)
    rounds = build_round_structures(round_rows, seat_map)

    state = initialize_state(spec, players, feature_context=feature_context)
    for round_number in range(1, args.completed_rounds + 1):
        pods, results = rounds[round_number]
        for result in results:
            apply_pod_result(state, result)
    state.current_round_index = args.completed_rounds

    locked_round_pods = None
    if args.lock_next_round:
        locked_round_pods = rounds.get(args.completed_rounds + 1, (None, None))[0]

    draw_model = load_draw_model_artifact(args.draw_model_path)
    summary = run_monte_carlo_from_state(
        state,
        draw_model,
        simulations=args.simulations,
        seed=args.seed,
        workers=args.workers,
        start_round_index=args.completed_rounds,
        locked_round_pods=locked_round_pods,
    ).to_dict()

    actual_top_cut = derive_top_cut_player_ids(entries, spec.top_cut)
    actual_winner = next((str(row["player_id"]) for row in entries if row.get("final_standing") == 1), None)
    player_name_by_id = {player.player_id: player.name for player in players}
    top_win = sorted(summary["win_probability"].items(), key=lambda item: item[1], reverse=True)[:10]
    top_cut_prob = sorted(summary["top_cut_probability"].items(), key=lambda item: item[1], reverse=True)[:10]

    output = {
        "tournament": {
            "id": spec.tournament_id,
            "name": spec.name,
            "player_count": spec.player_count,
            "swiss_rounds": spec.swiss_rounds,
            "top_cut": spec.top_cut,
        },
        "resume_state": {
            "completed_rounds": args.completed_rounds,
            "remaining_rounds": max(0, spec.swiss_rounds - args.completed_rounds),
            "locked_next_round": bool(locked_round_pods),
        },
        "actual_winner": {"player_id": actual_winner, "name": player_name_by_id.get(actual_winner or "", actual_winner)},
        "actual_top_cut_count": len(actual_top_cut),
        "top_win_probabilities": [
            {"player_id": player_id, "name": player_name_by_id.get(player_id, player_id), "win_probability": probability}
            for player_id, probability in top_win
        ],
        "top_top_cut_probabilities": [
            {"player_id": player_id, "name": player_name_by_id.get(player_id, player_id), "top_cut_probability": probability}
            for player_id, probability in top_cut_prob
        ],
        "round_draw_rate": summary["round_draw_rate"],
        "simulations": summary["simulations"],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
