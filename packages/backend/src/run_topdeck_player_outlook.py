#!/usr/bin/env python3
"""Player-specific outlook for an ongoing TopDeck tournament."""

from __future__ import annotations

import argparse
import json
import os
import random
from collections import defaultdict

from ingest import SupabaseClient, TopDeckClient, load_local_env
from run_topdeck_ongoing_tournament_sim import (
    DEFAULT_DRAW_MODEL_PATH,
    build_base_state,
    collect_players,
    fetch_event_page_html,
    fetch_existing_players,
    infer_structure,
    parse_start_date,
)
from run_historical_tournament_sim import build_feature_context
from sim_engine import (
    apply_pod_result,
    build_tournament_context,
    clone_state,
    simulate_from_state,
    simulate_pod,
)
from sim_models import (
    build_round_snapshot,
    load_draw_model_artifact,
    predict_decisive_win_probabilities,
    predict_draw_probabilities,
)
from sim_pairings import select_top_cut, sort_standings_rows
from sim_types import Pod, PodResult


def normalize_distribution(counts: dict[int, int], total: int) -> dict[str, float]:
    return {str(rank): count / total for rank, count in sorted(counts.items())}


def rank_player_after_swiss(state, target_player_id: str) -> int:
    ranked = sort_standings_rows(state)
    for index, row in enumerate(ranked, start=1):
        if row.player_id == target_player_id:
            return index
    raise RuntimeError(f"Target player {target_player_id} missing from standings")


def resolve_target_player_id(
    player_records: dict[str, dict[str, str]],
    *,
    player_topdeck_id: str | None,
    player_id: str | None,
) -> str:
    if player_id:
        return player_id
    if player_topdeck_id and player_topdeck_id in player_records:
        return player_records[player_topdeck_id]["id"]
    raise RuntimeError("Pass --player-id or a valid --player-topdeck-id for this event")


def force_target_pod_result(
    pod: Pod,
    target_player_id: str,
    outcome: str,
    pod_draw_probability: float,
    pod_win_probabilities: tuple[float, ...],
    rng: random.Random,
) -> PodResult:
    if outcome == "draw":
        return PodResult(
            round_index=pod.round_index,
            table_number=pod.table_number,
            player_ids=pod.player_ids,
            is_draw=True,
            winner_id=None,
            win_probabilities=pod_win_probabilities,
            draw_probability=pod_draw_probability,
        )
    if outcome == "win":
        return PodResult(
            round_index=pod.round_index,
            table_number=pod.table_number,
            player_ids=pod.player_ids,
            is_draw=False,
            winner_id=target_player_id,
            win_probabilities=pod_win_probabilities,
            draw_probability=pod_draw_probability,
        )
    if outcome == "loss":
        opponent_ids = [player_id for player_id in pod.player_ids if player_id != target_player_id]
        opponent_weights = [
            probability
            for player_id, probability in zip(pod.player_ids, pod_win_probabilities, strict=True)
            if player_id != target_player_id
        ]
        total = sum(opponent_weights) or 1.0
        threshold = rng.random()
        cumulative = 0.0
        winner_id = opponent_ids[-1]
        for opponent_id, weight in zip(opponent_ids, opponent_weights, strict=True):
            cumulative += weight / total
            winner_id = opponent_id
            if threshold <= cumulative:
                break
        return PodResult(
            round_index=pod.round_index,
            table_number=pod.table_number,
            player_ids=pod.player_ids,
            is_draw=False,
            winner_id=winner_id,
            win_probabilities=pod_win_probabilities,
            draw_probability=pod_draw_probability,
        )
    raise ValueError(f"Unsupported outcome: {outcome}")


def simulate_distribution(
    base_state,
    active_round_index: int,
    active_round_pods: list[Pod],
    target_player_id: str,
    target_pod: Pod,
    draw_model,
    *,
    simulations: int,
    seed: int,
    forced_outcome: str | None = None,
) -> tuple[dict[str, float], float]:
    standing_counts: dict[int, int] = defaultdict(int)
    tournament_wins = 0
    tournament_context = build_tournament_context(base_state.spec)
    for simulation_index in range(simulations):
        rng = random.Random(seed + simulation_index)
        state = clone_state(base_state)
        round_snapshot = build_round_snapshot(state, tournament_context, active_round_index + 1)
        draw_probabilities = predict_draw_probabilities(active_round_pods, state, tournament_context, draw_model, round_snapshot)
        win_probabilities = predict_decisive_win_probabilities(active_round_pods, state)
        round_results: list[PodResult] = []
        for pod in active_round_pods:
            pod_key = (pod.round_index, pod.table_number)
            pod_draw_probability = draw_probabilities[pod_key]
            pod_win_probabilities = win_probabilities[pod_key]
            if pod.table_number == target_pod.table_number and forced_outcome is not None:
                result = force_target_pod_result(
                    pod,
                    target_player_id,
                    forced_outcome,
                    pod_draw_probability,
                    pod_win_probabilities,
                    rng,
                )
            else:
                result = simulate_pod(pod, rng, pod_draw_probability, pod_win_probabilities)
            round_results.append(result)
            apply_pod_result(state, result)
        state.current_round_index = active_round_index + 1
        state, winner_probabilities, _, _ = simulate_from_state(
            state,
            draw_model,
            seed=seed + simulation_index + 100_000,
            start_round_index=active_round_index + 1,
            locked_round_pods=None,
        )
        standing_counts[rank_player_after_swiss(state, target_player_id)] += 1
        tournament_wins += winner_probabilities.get(target_player_id, 0.0)
    return normalize_distribution(standing_counts, simulations), tournament_wins / simulations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--player-topdeck-id")
    parser.add_argument("--player-id")
    parser.add_argument("--draw-model-path", default=str(DEFAULT_DRAW_MODEL_PATH))
    parser.add_argument("--simulations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
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
    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])
    existing_players = fetch_existing_players(client, topdeck_ids)
    player_records = {
        topdeck_id: existing_players.get(topdeck_id) or {"id": f"topdeck:{topdeck_id}", "name": player_names[topdeck_id]}
        for topdeck_id in topdeck_ids
    }
    known_player_ids = [record["id"] for record in player_records.values() if not record["id"].startswith("topdeck:")]
    feature_context = build_feature_context(client, known_player_ids, start_date.isoformat()) if known_player_ids else None
    state, active_round_index, active_round_pods = build_base_state(
        client,
        tournament,
        swiss_rounds=swiss_rounds,
        top_cut=top_cut,
        feature_context=feature_context,
        player_records=player_records,
    )
    if not active_round_pods or active_round_index >= swiss_rounds:
        raise RuntimeError("This script currently supports active Swiss rounds with posted pods")

    target_player_id = resolve_target_player_id(
        player_records,
        player_topdeck_id=args.player_topdeck_id,
        player_id=args.player_id,
    )
    target_pod = next((pod for pod in active_round_pods if target_player_id in pod.player_ids), None)
    if target_pod is None:
        raise RuntimeError("Target player is not in a currently posted active Swiss pod")

    draw_model = load_draw_model_artifact(args.draw_model_path)
    tournament_context = __import__("sim_engine").build_tournament_context(state.spec)
    round_snapshot = build_round_snapshot(state, tournament_context, active_round_index + 1)
    draw_probabilities = predict_draw_probabilities(active_round_pods, state, tournament_context, draw_model, round_snapshot)
    win_probabilities = predict_decisive_win_probabilities(active_round_pods, state)
    pod_key = (target_pod.round_index, target_pod.table_number)
    pod_draw_probability = draw_probabilities[pod_key]
    pod_win_probabilities = win_probabilities[pod_key]

    table_players = []
    for player_id, decisive_probability in zip(target_pod.player_ids, pod_win_probabilities, strict=True):
        overall_win_probability = (1.0 - pod_draw_probability) * decisive_probability
        table_players.append(
            {
                "player_id": player_id,
                "name": state.players[player_id].name,
                "decisive_win_probability": decisive_probability,
                "overall_pod_win_probability": overall_win_probability,
            }
        )

    final_distribution, tournament_win_probability = simulate_distribution(
        state,
        active_round_index,
        active_round_pods,
        target_player_id,
        target_pod,
        draw_model,
        simulations=args.simulations,
        seed=args.seed,
        forced_outcome=None,
    )
    distribution_given_win, tournament_win_given_win = simulate_distribution(
        state,
        active_round_index,
        active_round_pods,
        target_player_id,
        target_pod,
        draw_model,
        simulations=args.simulations,
        seed=args.seed + 1_000_000,
        forced_outcome="win",
    )
    distribution_given_loss, tournament_win_given_loss = simulate_distribution(
        state,
        active_round_index,
        active_round_pods,
        target_player_id,
        target_pod,
        draw_model,
        simulations=args.simulations,
        seed=args.seed + 2_000_000,
        forced_outcome="loss",
    )
    distribution_given_draw, tournament_win_given_draw = simulate_distribution(
        state,
        active_round_index,
        active_round_pods,
        target_player_id,
        target_pod,
        draw_model,
        simulations=args.simulations,
        seed=args.seed + 3_000_000,
        forced_outcome="draw",
    )

    currently_in_top_cut = target_player_id in set(select_top_cut(state))
    target_overall_pod_win_probability = next(
        player["overall_pod_win_probability"] for player in table_players if player["player_id"] == target_player_id
    )

    output = {
        "tournament": {
            "id": state.spec.tournament_id,
            "name": state.spec.name,
            "player_count": state.spec.player_count,
            "swiss_rounds": state.spec.swiss_rounds,
            "top_cut": state.spec.top_cut,
        },
        "player": {
            "player_id": target_player_id,
            "name": state.players[target_player_id].name,
            "currently_in_top_cut": currently_in_top_cut,
        },
        "current_round": {
            "round_number": active_round_index + 1,
            "table_number": target_pod.table_number,
            "draw_probability": pod_draw_probability,
            "table_win_probabilities": table_players,
        },
        "final_swiss_standing_distribution": final_distribution,
        "final_swiss_standing_distribution_given_win": distribution_given_win,
        "final_swiss_standing_distribution_given_loss": distribution_given_loss,
        "final_swiss_standing_distribution_given_draw": distribution_given_draw,
        "target_player": {
            "current_pod_win_probability": target_overall_pod_win_probability,
            "current_pod_loss_probability": max(
                0.0,
                1.0 - pod_draw_probability - target_overall_pod_win_probability,
            ),
            "current_pod_draw_probability": pod_draw_probability,
        },
        "simulations": args.simulations,
    }
    if currently_in_top_cut:
        output["target_player"]["tournament_win_probability"] = tournament_win_probability
        output["target_player"]["tournament_win_probability_given_win"] = tournament_win_given_win
        output["target_player"]["tournament_win_probability_given_loss"] = tournament_win_given_loss
        output["target_player"]["tournament_win_probability_given_draw"] = tournament_win_given_draw

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
