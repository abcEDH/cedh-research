"""Reconstruct simulation state from posted TopDeck rounds."""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from typing import Any

from ingest import is_draw_winner_id
from ongoing_tournament_inputs import (
    collect_players,
    parse_start_date,
    parse_table_number,
    standings_tiebreak_seed_map,
)
from run_historical_tournament_sim import (
    fetch_pre_tournament_elos,
    fetch_topdeck_elos_for_topdeck_ids,
)
from sim_engine import (
    apply_bye,
    apply_pod_result,
    initialize_state,
)
from sim_models import (
    ELO_BASE,
    ELO_DIVISOR,
)
from sim_types import Pod, PodResult, SimPlayer, TournamentSpec


def build_pods_for_round(
    round_data: dict[str, Any],
    round_index: int,
    id_map: dict[str, str],
    *,
    table_number_offset: int = 0,
) -> list[Pod]:
    pods: list[Pod] = []
    for table in round_data.get("tables") or []:
        players = table.get("players") or []
        player_ids = [
            id_map[str(player.get("id"))] for player in players if player.get("id") and str(player.get("id")) in id_map
        ]
        if table_is_bye(table):
            fallback_table_number = table_number_offset + len(pods) + 1
            parsed_table_number = parse_table_number(table, fallback_table_number)
            for bye_index, player_id in enumerate(player_ids):
                pods.append(
                    Pod(
                        round_index=round_index,
                        table_number=parsed_table_number + bye_index,
                        player_ids=[player_id],
                        round_name=f"Round {round_index + 1}",
                        seats_by_player={player_id: 1},
                    )
                )
            continue
        if len(player_ids) < 2:
            continue
        parsed_table_number = parse_table_number(table, table_number_offset + len(pods) + 1)
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


def table_is_bye(table: dict[str, Any]) -> bool:
    return str(table.get("status") or "").strip().lower() == "bye"


def table_completed(table: dict[str, Any]) -> bool:
    if table_is_bye(table):
        return True
    winner_id = table.get("winner_id") or table.get("winnerId")
    status = str(table.get("status") or "").strip().lower()
    if winner_id not in (None, ""):
        return True
    return status == "completed"


def table_active(table: dict[str, Any]) -> bool:
    status = str(table.get("status") or "").strip().lower()
    if status in {"active", "pending"}:
        return True
    if status in {"bye", "completed"}:
        return False
    winner_id = table.get("winner_id") or table.get("winnerId")
    return winner_id in (None, "")


def build_result_for_table(pod: Pod, table: dict[str, Any], id_map: dict[str, str]) -> PodResult | None:
    winner_id = table.get("winner_id") or table.get("winnerId")
    if not table_completed(table):
        return None
    if table_is_bye(table) and len(pod.player_ids) == 1:
        winner_id = pod.player_ids[0]
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
    from internal_elo import is_top_cut, learning_rate, seat_offsets

    player_ids = list(result.player_ids)
    if len(player_ids) < 2:
        return
    top_cut = is_top_cut(pod.round_name)
    if top_cut and result.is_draw:
        winners = [pid for pid in player_ids if pod.seats_by_player.get(pid) == 1]
        if len(winners) != 1:
            raise ValueError("Top-cut draw requires a unique seat 1")
        result.is_draw = False
        result.winner_id = winners[0]
    k_factor = learning_rate(top_cut=top_cut, draw=result.is_draw, league=state.spec.is_league)
    use_seat_bonus = len(player_ids) == 4 and sorted(pod.seats_by_player.values()) == [1, 2, 3, 4]
    effective_ratings: dict[str, float] = {}
    for player_id in player_ids:
        rating = float(state.players[player_id].elo)
        if use_seat_bonus:
            rating += seat_offsets(top_cut).get(pod.seats_by_player.get(player_id), 0.0)
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
        for table_position, table in enumerate(tables, start=1):
            table_pods = build_pods_for_round(
                {"tables": [table]},
                round_index,
                id_map,
                table_number_offset=table_position - 1,
            )
            if not table_pods:
                continue
            for table_pod in table_pods:
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
    drop_after_round: int | None = None,
    drop_min_points: int | None = None,
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
    topdeck_elos = fetch_topdeck_elos_for_topdeck_ids(client, topdeck_ids)
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
            topdeck_elo=topdeck_elos.get(topdeck_id),
            tiebreak_seed=tiebreak_seeds[topdeck_id]
            if topdeck_id in tiebreak_seeds
            else fallback_seed_by_topdeck_id[topdeck_id],
        )
        for topdeck_id in topdeck_ids
    ]
    if "is_league" not in tournament:
        league_rows = (
            client.table("tournaments")
            .select("is_league")
            .eq("topdeck_tid", str(tournament.get("id") or tournament.get("TID")))
            .limit(1)
            .execute()
            .data
        )
        tournament["is_league"] = bool(league_rows and league_rows[0].get("is_league"))
    spec = TournamentSpec(
        tournament_id=str(tournament.get("id") or tournament.get("TID")),
        name=str(tournament.get("name") or tournament.get("id") or "TopDeck Event"),
        start_date=start_date,
        swiss_rounds=swiss_rounds,
        top_cut=top_cut,
        player_count=len(players),
        is_league=bool(tournament.get("is_league", False)),
        repeat_avoidance_max_pods=repeat_avoidance_max_pods,
        state=((tournament.get("eventData") or {}).get("state")),
        country=((tournament.get("eventData") or {}).get("country")),
        drop_after_round=drop_after_round,
        drop_min_points=drop_min_points,
    )
    state = initialize_state(spec, players, feature_context=feature_context)
    id_map = {topdeck_id: record["id"] for topdeck_id, record in player_records.items()}
    completed_tables, active_round_index, active_round_pods, active_player_ids, metadata = split_rounds(
        tournament,
        swiss_rounds,
        id_map,
    )
    state.fast_live_mode = True
    for pod, result in completed_tables:
        if len(pod.player_ids) == 1 and result.winner_id == pod.player_ids[0]:
            apply_bye(state, pod.player_ids[0])
        else:
            update_elos_for_result(state, pod, result)
            apply_pod_result(state, result)
    if active_player_ids:
        state.eligible_player_ids = active_player_ids
    state.current_round_index = active_round_index
    current_round_completed_index = active_round_index if active_round_pods else max(active_round_index - 1, 0)
    metadata["locked_current_tables"] = [pod.table_number for pod in active_round_pods or []]
    metadata["completed_current_round_pods"] = [
        {
            "round_number": pod.round_index + 1,
            "table_number": pod.table_number,
            "result": "Draw"
            if result.is_draw
            else state.players[result.winner_id].name
            if result.winner_id in state.players
            else result.winner_id,
            "winner_id": None if result.is_draw else result.winner_id,
            "is_draw": result.is_draw,
            "players": [
                {
                    "player_id": player_id,
                    "name": state.players[player_id].name,
                    "seat": pod.seats_by_player.get(player_id),
                    "result": "draw" if result.is_draw else "win" if player_id == result.winner_id else "loss",
                }
                for player_id in pod.player_ids
            ],
        }
        for pod, result in completed_tables
        if pod.round_index == current_round_completed_index
    ]
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
