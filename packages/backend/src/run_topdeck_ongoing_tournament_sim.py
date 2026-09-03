#!/usr/bin/env python3
"""Simulate an ongoing TopDeck tournament from its current posted state."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from ingest import TopDeckClient, is_draw_winner_id, load_local_env
from run_historical_tournament_sim import (
    build_feature_context,
    fetch_historical_point_requirement_baseline,
    fetch_pre_tournament_elos,
)
from sim_engine import (
    apply_pod_result,
    build_tournament_context,
    clone_state,
    exact_top_cut_probabilities,
    initialize_state,
    simulate_swiss,
)
from sim_models import (
    ELO_BASE,
    ELO_DIVISOR,
    SEAT_ELO_BONUS,
    build_round_snapshot,
    load_draw_model_artifact,
    predict_decisive_win_probabilities,
    predict_draw_probabilities,
)
from sim_pairings import select_top_cut, sort_standings_rows, topdeck_bye_rank
from sim_types import FeatureContext, Pod, PodResult, SimPlayer, TournamentSpec
from tournament_sim_runner import (
    DEFAULT_ADVANCEMENT_SIZES,
    build_common_output,
    run_simulation_from_state,
)

DEFAULT_DRAW_MODEL_PATH = Path("/tmp/cedh_draw_model_artifact_v4.pkl")
K_FACTOR_DECISIVE = 64
K_FACTOR_DRAW = 26


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
            "Unable to infer total swiss rounds from the TopDeck payload/event page. Pass --swiss-rounds explicitly."
        )
    if top_cut is None:
        raise RuntimeError(
            "Unable to infer top cut size from the TopDeck payload/event page. Pass --top-cut explicitly."
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


def fetch_existing_players(client, topdeck_ids: list[str]) -> dict[str, dict[str, str]]:
    rows = client.table("players").select("id,topdeck_id,name").in_("topdeck_id", topdeck_ids).execute().data
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
            id_map[str(player.get("id"))] for player in players if player.get("id") and str(player.get("id")) in id_map
        ]
        if len(player_ids) < 2:
            continue
        table_number = table.get("table") or table.get("table_number") or table.get("tableNumber") or (len(pods) + 1)
        try:
            parsed_table_number = int(table_number)
        except (TypeError, ValueError):
            parsed_table_number = len(pods) + 1
        pods.append(
            Pod(
                round_index=round_index,
                table_number=parsed_table_number,
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


def build_result_for_table(pod: Pod, table: dict[str, Any], id_map: dict[str, str]) -> PodResult | None:
    winner_id = table.get("winner_id") or table.get("winnerId")
    if not table_completed(table):
        return None
    draw = is_draw_winner_id(winner_id)
    normalized_winner_id = None if draw else id_map.get(str(winner_id), str(winner_id))
    return PodResult(
        round_index=pod.round_index,
        table_number=pod.table_number,
        player_ids=pod.player_ids,
        is_draw=draw,
        winner_id=normalized_winner_id,
        win_probabilities=(),
        draw_probability=0.0,
    )


def update_elos_for_result(state, pod: Pod, result: PodResult) -> None:
    player_ids = list(result.player_ids)
    if len(player_ids) < 2:
        return
    k_factor = K_FACTOR_DRAW if result.is_draw else K_FACTOR_DECISIVE
    use_seat_bonus = len(player_ids) == 4 and sorted(pod.seats_by_player.values()) == [1, 2, 3, 4]
    effective_ratings: dict[str, float] = {}
    for player_id in player_ids:
        rating = float(state.players[player_id].elo)
        if use_seat_bonus:
            rating += SEAT_ELO_BONUS.get(pod.seats_by_player.get(player_id), 0.0)
        effective_ratings[player_id] = rating
    total_equity = sum(math.pow(ELO_BASE, effective_ratings[player_id] / ELO_DIVISOR) for player_id in player_ids)
    if total_equity <= 0:
        return
    for player_id in player_ids:
        expected = math.pow(ELO_BASE, effective_ratings[player_id] / ELO_DIVISOR) / total_equity
        actual = (1.0 / len(player_ids)) if result.is_draw else (1.0 if player_id == result.winner_id else 0.0)
        state.players[player_id].elo = round(float(state.players[player_id].elo) + (k_factor * (actual - expected)), 6)


def split_rounds(
    tournament: dict[str, Any],
    swiss_rounds: int,
    id_map: dict[str, str],
) -> tuple[list[tuple[Pod, PodResult]], int, list[Pod] | None, set[str], dict[str, Any]]:
    completed_tables: list[tuple[Pod, PodResult]] = []
    active_round_index: int | None = None
    active_round_pods: list[Pod] = []
    latest_posted_round_number = 0
    active_player_ids: set[str] = set()
    player_ids_by_round: dict[int, set[str]] = defaultdict(set)
    round_status_counts: list[tuple[int, dict[str, int]]] = []

    for round_data in sorted(
        [row for row in tournament.get("rounds") or [] if isinstance(row.get("round"), int)],
        key=lambda row: int(row.get("round")),
    ):
        round_number = int(round_data["round"])
        if round_number > swiss_rounds:
            continue
        latest_posted_round_number = max(latest_posted_round_number, round_number)
        round_index = round_number - 1
        tables = round_data.get("tables") or []
        round_status_counts.append(
            (
                round_number,
                dict(
                    Counter(
                        str(table.get("status") or "").strip() or ("Completed" if table_completed(table) else "Active")
                        for table in tables
                    )
                ),
            )
        )
        for table in tables:
            pod = build_pods_for_round({"tables": [table]}, round_index, id_map)
            if not pod:
                continue
            table_pod = pod[0]
            player_ids_by_round[round_number].update(table_pod.player_ids)
            if table_completed(table):
                result = build_result_for_table(table_pod, table, id_map)
                if result is not None:
                    completed_tables.append((table_pod, result))
            elif table_active(table):
                active_round_index = round_index
                active_round_pods.append(table_pod)

    if active_round_index is None:
        active_round_index = latest_posted_round_number
    field_round_number = (active_round_index + 1) if active_round_pods else latest_posted_round_number
    if field_round_number in player_ids_by_round:
        active_player_ids = set(player_ids_by_round[field_round_number])
    metadata = {
        "rounds": round_status_counts,
        "active_player_count": len(active_player_ids),
    }
    return completed_tables, active_round_index, active_round_pods or None, active_player_ids, metadata


def build_base_state(
    client,
    tournament: dict[str, Any],
    *,
    swiss_rounds: int,
    top_cut: int,
    feature_context,
    player_records: dict[str, dict[str, str]],
    repeat_avoidance_max_pods: int | None,
    excluded_topdeck_ids: set[str] | None = None,
) -> tuple[Any, int, list[Pod] | None, dict[str, Any]]:
    player_names = collect_players(tournament)
    if excluded_topdeck_ids:
        player_names = {
            topdeck_id: name for topdeck_id, name in player_names.items() if topdeck_id not in excluded_topdeck_ids
        }
    tiebreak_seeds = standings_tiebreak_seed_map(tournament)
    if excluded_topdeck_ids:
        tiebreak_seeds = {
            topdeck_id: seed for topdeck_id, seed in tiebreak_seeds.items() if topdeck_id not in excluded_topdeck_ids
        }
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
        repeat_avoidance_max_pods=repeat_avoidance_max_pods,
        state=((tournament.get("eventData") or {}).get("state")),
        country=((tournament.get("eventData") or {}).get("country")),
    )
    state = initialize_state(spec, players, feature_context=feature_context)
    id_map = {topdeck_id: record["id"] for topdeck_id, record in player_records.items()}
    completed_tables, active_round_index, active_round_pods, active_player_ids, metadata = split_rounds(
        tournament,
        swiss_rounds,
        id_map,
    )
    for pod, result in completed_tables:
        update_elos_for_result(state, pod, result)
        apply_pod_result(state, result)
    if active_player_ids:
        state.eligible_player_ids = active_player_ids
    state.current_round_index = active_round_index
    metadata["locked_current_tables"] = [pod.table_number for pod in active_round_pods or []]
    metadata["completed_tables_applied"] = [
        (
            pod.round_index + 1,
            pod.table_number,
            "Draw"
            if result.is_draw
            else state.players[result.winner_id].name
            if result.winner_id in state.players
            else result.winner_id,
        )
        for pod, result in completed_tables
    ]
    return state, active_round_index, active_round_pods, metadata


def run_live_monte_carlo(
    state,
    draw_model,
    *,
    simulations: int,
    seed: int,
    start_round_index: int,
    locked_round_pods: list[Pod] | None,
    exact_top_cut: bool,
    max_exact_cut_size: int,
    requested_advancement_sizes: tuple[int, ...],
) -> dict[str, Any]:
    context = build_tournament_context(state.spec)
    locked_round_draw_probabilities = None
    locked_round_win_probabilities = None
    if locked_round_pods:
        round_snapshot = build_round_snapshot(state, context, start_round_index + 1)
        locked_round_draw_probabilities = predict_draw_probabilities(
            locked_round_pods,
            state,
            context,
            draw_model,
            round_snapshot,
        )
        locked_round_win_probabilities = predict_decisive_win_probabilities(locked_round_pods, state)

    win_probability_totals: dict[str, float] = defaultdict(float)
    top_cut_counts: dict[str, float] = defaultdict(float)
    advancement_totals: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    expected_points: dict[str, float] = defaultdict(float)
    expected_finish: dict[str, float] = defaultdict(float)
    top_cut_line_point_counts: dict[int, int] = defaultdict(int)
    bye_line_point_counts: dict[int, int] = defaultdict(int)

    for simulation_index in range(simulations):
        simulation_state = clone_state(state)
        rng = random.Random(seed + simulation_index)
        simulate_swiss(
            simulation_state,
            rng,
            draw_model,
            context,
            start_round_index=start_round_index,
            locked_round_pods=locked_round_pods,
            locked_round_draw_probabilities=locked_round_draw_probabilities,
            locked_round_win_probabilities=locked_round_win_probabilities,
        )
        top_cut = select_top_cut(simulation_state) if simulation_state.spec.top_cut > 0 else []
        for player_id in top_cut:
            top_cut_counts[player_id] += 1.0

        if top_cut:
            if exact_top_cut and len(top_cut) <= max_exact_cut_size:
                winner_probabilities, advancement_probabilities = exact_top_cut_probabilities(
                    top_cut,
                    simulation_state,
                    max_exact_cut_size=max_exact_cut_size,
                )
                for player_id, probability in winner_probabilities.items():
                    win_probability_totals[player_id] += probability
                for cut_size in requested_advancement_sizes:
                    for player_id, probability in advancement_probabilities.get(cut_size, {}).items():
                        advancement_totals[cut_size][player_id] += probability
            else:
                from sim_engine import simulate_bracket_winner

                winner_id, advancement_by_size = simulate_bracket_winner(
                    top_cut,
                    simulation_state,
                    rng,
                    draw_model,
                    context,
                )
                win_probability_totals[winner_id] += 1.0
                for cut_size in requested_advancement_sizes:
                    for player_id in advancement_by_size.get(cut_size, []):
                        advancement_totals[cut_size][player_id] += 1.0

        ranked = sort_standings_rows(simulation_state)
        if 0 < simulation_state.spec.top_cut <= len(ranked):
            top_cut_line_point_counts[ranked[simulation_state.spec.top_cut - 1].points] += 1
        bye_rank = topdeck_bye_rank(simulation_state.spec.top_cut)
        if bye_rank is not None and bye_rank <= len(ranked):
            bye_line_point_counts[ranked[bye_rank - 1].points] += 1
        for finish_index, standing in enumerate(ranked, start=1):
            expected_points[standing.player_id] += standing.points
            expected_finish[standing.player_id] += finish_index

    return {
        "win_probability": {
            player_id: probability / simulations for player_id, probability in win_probability_totals.items()
        },
        "top_cut_probability": {player_id: count / simulations for player_id, count in top_cut_counts.items()},
        "advancement_probability": {
            cut_size: {player_id: probability / simulations for player_id, probability in player_probabilities.items()}
            for cut_size, player_probabilities in advancement_totals.items()
        },
        "expected_points": {player_id: total / simulations for player_id, total in expected_points.items()},
        "expected_finish": {player_id: total / simulations for player_id, total in expected_finish.items()},
        "point_requirements": {
            "top_cut": [
                {"points": points, "probability": count / simulations, "count": count}
                for points, count in sorted(top_cut_line_point_counts.items())
            ],
            "bye": [
                {"points": points, "probability": count / simulations, "count": count}
                for points, count in sorted(bye_line_point_counts.items())
            ],
        },
        "simulations": simulations,
        "winner_method": "exact_top_cut" if exact_top_cut else "sampled_top_cut",
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
    parser.add_argument(
        "--repeat-avoidance-max-pods",
        type=int,
        default=32,
        help=(
            "Run repeat-opponent swap optimization only when generated Swiss pod count is at "
            "or below this value. Use 0 to disable."
        ),
    )
    parser.add_argument(
        "--sample-top-cut",
        action="store_true",
        help="Sample top-cut winners instead of exact Elo propagation.",
    )
    parser.add_argument("--max-exact-cut-size", type=int, default=16)
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
    from supabase_client import get_supabase_client  # local import to keep script entry focused

    client = get_supabase_client(url=os.environ["SUPABASE_URL"], key=os.environ["SUPABASE_SERVICE_KEY"])
    existing_players = fetch_existing_players(client, topdeck_ids)
    player_records = {
        topdeck_id: existing_players.get(topdeck_id)
        or {"id": f"topdeck:{topdeck_id}", "name": player_names[topdeck_id]}
        for topdeck_id in topdeck_ids
    }
    known_player_ids = [record["id"] for record in player_records.values() if not record["id"].startswith("topdeck:")]
    feature_context = (
        build_feature_context(client, known_player_ids, start_date.isoformat())
        if known_player_ids
        else FeatureContext()
    )
    state, active_round_index, active_round_pods, live_metadata = build_base_state(
        client,
        tournament,
        swiss_rounds=swiss_rounds,
        top_cut=top_cut,
        feature_context=feature_context,
        player_records=player_records,
        repeat_avoidance_max_pods=args.repeat_avoidance_max_pods,
    )
    state.fast_live_mode = True
    state.track_round_stats = False

    draw_model = load_draw_model_artifact(args.draw_model_path)
    if args.sample_top_cut:
        summary = run_live_monte_carlo(
            state,
            draw_model,
            simulations=args.simulations,
            seed=args.seed,
            start_round_index=active_round_index,
            locked_round_pods=active_round_pods,
            exact_top_cut=False,
            max_exact_cut_size=args.max_exact_cut_size,
            requested_advancement_sizes=DEFAULT_ADVANCEMENT_SIZES,
        )
    else:
        summary = run_simulation_from_state(
            state,
            draw_model,
            simulations=args.simulations,
            seed=args.seed,
            workers=args.workers,
            start_round_index=active_round_index,
            locked_round_pods=active_round_pods,
            requested_advancement_sizes=DEFAULT_ADVANCEMENT_SIZES,
        )
        summary["winner_method"] = "exact_top_cut"
    historical_point_requirements = fetch_historical_point_requirement_baseline(
        client,
        active_player_count=len(state.eligible_player_ids or state.players),
        top_cut=state.spec.top_cut,
        swiss_rounds=state.spec.swiss_rounds,
        exclude_tournament_id=state.spec.tournament_id,
    )

    print(
        json.dumps(
            {
                **build_common_output(
                    summary=summary,
                    state=state,
                    player_name_by_id={player_id: player.name for player_id, player in state.players.items()},
                    active_player_count=len(state.eligible_player_ids or state.players),
                    historical_point_requirements=historical_point_requirements,
                    current_state={
                        "completed_swiss_rounds": active_round_index,
                        "active_round_number": (active_round_index + 1) if active_round_pods else None,
                        "active_tables": len(active_round_pods or []),
                        "eligible_player_count": len(state.eligible_player_ids or state.players),
                        "rounds": live_metadata.get("rounds", []),
                        "locked_current_tables": live_metadata.get("locked_current_tables", []),
                    },
                    top_limit=20,
                ),
                "winner_method": summary.get("winner_method"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
