#!/usr/bin/env python3
"""Simulate an ongoing TopDeck tournament from its current posted state."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import random
import re
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
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
    fetch_topdeck_elos_for_topdeck_ids,
)
from sim_engine import (
    _merge_summaries,
    _run_state_monte_carlo_batch,
    apply_bye,
    apply_points_drop_if_due,
    apply_pod_result,
    build_tournament_context,
    clone_state,
    initialize_state,
    resolve_bracket_probabilities,
    simulate_swiss,
)
from sim_models import (
    DEFAULT_DRAW_MODEL_PATH,
    ELO_BASE,
    ELO_DIVISOR,
    SEAT_ELO_BONUS,
    LoadedCandidateWinnerModel,
    LoadedDrawModel,
    build_round_snapshot,
    load_candidate_winner_model_artifact,
    load_draw_model_artifact,
    predict_pod_outcome_probabilities,
)
from sim_pairings import select_top_cut, sort_standings_rows, topdeck_bye_rank
from sim_types import FeatureContext, Pod, PodResult, SimPlayer, TournamentSpec
from tournament_sim_runner import (
    build_common_output,
    run_simulation_from_state,
)

DEFAULT_PREPARED_STATE_CACHE_DIR = Path(".cache/tournament-sim")
PREPARED_STATE_CACHE_VERSION = 8
K_FACTOR_DECISIVE = 64
K_FACTOR_DRAW = 26
STREAM_INITIAL_EMIT_SIMULATIONS = 5
STREAM_EMIT_SIMULATION_INTERVAL = 5


def relevant_advancement_sizes(top_cut: int) -> tuple[int, ...]:
    if top_cut <= 0:
        return ()

    candidates = [top_cut]
    if top_cut in {40, 64}:
        candidates.extend([16, 4])
    elif top_cut > 4:
        candidates.append(4)

    selected: list[int] = []
    for size in candidates:
        if size > 0 and size <= top_cut and size not in selected:
            selected.append(size)
    return tuple(selected)


def eligible_player_count(state) -> int:
    return len(state.eligible_player_ids) if state.eligible_player_ids is not None else len(state.players)


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


def tournament_state_fingerprint(
    tournament: dict[str, Any],
    *,
    swiss_rounds: int,
    top_cut: int,
    drop_after_round: int | None = None,
    drop_min_points: int | None = None,
) -> str:
    payload = {
        "cache_version": PREPARED_STATE_CACHE_VERSION,
        "id": tournament.get("id") or tournament.get("TID"),
        "startDate": tournament.get("startDate"),
        "swiss_rounds": swiss_rounds,
        "top_cut": top_cut,
        "drop_after_round": drop_after_round,
        "drop_min_points": drop_min_points,
        "standings": [
            {
                "id": standing.get("id"),
                "standing": standing.get("standing"),
                "points": standing.get("points"),
                "wins": standing.get("wins"),
                "draws": standing.get("draws"),
                "losses": standing.get("losses"),
            }
            for standing in tournament.get("standings") or []
        ],
        "rounds": tournament.get("rounds") or [],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepared_state_cache_path(cache_dir: Path, event_id: str, fingerprint: str) -> Path:
    safe_event_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", event_id).strip("-") or "event"
    return cache_dir / f"{safe_event_id}-{fingerprint[:16]}.pkl"


def load_prepared_state_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def save_prepared_state_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_path.replace(path)


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


def parse_table_number(table: dict[str, Any], fallback: int) -> int:
    table_number = table.get("table") or table.get("table_number") or table.get("tableNumber") or fallback
    try:
        return int(table_number)
    except (TypeError, ValueError):
        return fallback


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
            id_map[str(player.get("id"))]
            for player in players
            if player.get("id") and str(player.get("id")) in id_map
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
        win_probabilities=tuple(),
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
                        str(table.get("status") or "").strip()
                        or ("Completed" if table_completed(table) else "Active")
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
            topdeck_id: name
            for topdeck_id, name in player_names.items()
            if topdeck_id not in excluded_topdeck_ids
        }
    tiebreak_seeds = standings_tiebreak_seed_map(tournament)
    if excluded_topdeck_ids:
        tiebreak_seeds = {
            topdeck_id: seed
            for topdeck_id, seed in tiebreak_seeds.items()
            if topdeck_id not in excluded_topdeck_ids
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
                    "result": "draw"
                    if result.is_draw
                    else "win"
                    if player_id == result.winner_id
                    else "loss",
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


def run_live_monte_carlo(
    state,
    draw_model: LoadedDrawModel,
    winner_model: LoadedCandidateWinnerModel | None = None,
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
        locked_round_draw_probabilities, locked_round_win_probabilities = predict_pod_outcome_probabilities(
            locked_round_pods,
            state,
            context,
            draw_model,
            round_snapshot,
            winner_model,
        )

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
            winner_model,
            start_round_index=start_round_index,
            locked_round_pods=locked_round_pods,
            locked_round_draw_probabilities=locked_round_draw_probabilities,
            locked_round_win_probabilities=locked_round_win_probabilities,
        )
        top_cut = select_top_cut(simulation_state, rng=rng) if simulation_state.spec.top_cut > 0 else []
        for player_id in top_cut:
            top_cut_counts[player_id] += 1.0

        if top_cut:
            if exact_top_cut:
                winner_probabilities, advancement_probabilities = resolve_bracket_probabilities(
                    top_cut,
                    simulation_state,
                    rng,
                    draw_model,
                    context,
                    winner_model,
                    exact_cut_sizes=tuple(cut_size for cut_size in (16, 10, 4) if cut_size <= max_exact_cut_size),
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
                    winner_model,
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
            player_id: probability / simulations
            for player_id, probability in win_probability_totals.items()
        },
        "top_cut_probability": {
            player_id: count / simulations
            for player_id, count in top_cut_counts.items()
        },
        "advancement_probability": {
            cut_size: {
                player_id: probability / simulations
                for player_id, probability in player_probabilities.items()
            }
            for cut_size, player_probabilities in advancement_totals.items()
        },
        "expected_points": {
            player_id: total / simulations
            for player_id, total in expected_points.items()
        },
        "expected_finish": {
            player_id: total / simulations
            for player_id, total in expected_finish.items()
        },
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


def run_live_monte_carlo_stream(
    state,
    draw_model: LoadedDrawModel,
    winner_model: LoadedCandidateWinnerModel | None = None,
    *,
    simulations: int,
    seed: int,
    start_round_index: int,
    locked_round_pods: list[Pod] | None,
    max_exact_cut_size: int,
    requested_advancement_sizes: tuple[int, ...],
    stream_interval_seconds: float,
    stream_batch_size: int,
    player_name_by_id: dict[str, str],
    active_player_count: int,
    historical_point_requirements: dict[str, Any] | None,
    current_state: dict[str, Any],
    workers: int | None,
    top_limit: int = 20,
    stream_duration_seconds: float | None = None,
) -> None:
    context = build_tournament_context(state.spec)
    locked_round_draw_probabilities = None
    locked_round_win_probabilities = None
    if locked_round_pods:
        round_snapshot = build_round_snapshot(state, context, start_round_index + 1)
        locked_round_draw_probabilities, locked_round_win_probabilities = predict_pod_outcome_probabilities(
            locked_round_pods,
            state,
            context,
            draw_model,
            round_snapshot,
            winner_model,
        )

    active_pods = []
    for pod in locked_round_pods or []:
        pod_key = (pod.round_index, pod.table_number)
        draw_probability = (locked_round_draw_probabilities or {}).get(pod_key, 0.0)
        decisive_win_probabilities = (locked_round_win_probabilities or {}).get(pod_key, tuple())
        active_pods.append(
            {
                "round_number": pod.round_index + 1,
                "table_number": pod.table_number,
                "draw_probability": draw_probability,
                "players": [
                    {
                        "player_id": player_id,
                        "name": player_name_by_id.get(player_id, state.players[player_id].name),
                        "win_probability": (1.0 - draw_probability) * decisive_probability,
                        "decisive_win_probability": decisive_probability,
                        "seat": pod.seats_by_player.get(player_id),
                    }
                    for player_id, decisive_probability in zip(
                        pod.player_ids,
                        decisive_win_probabilities,
                        strict=False,
                    )
                ],
            }
        )

    started_at = time.monotonic()
    deadline = (
        started_at + stream_duration_seconds
        if stream_duration_seconds is not None and stream_duration_seconds > 0
        else None
    )

    def time_budget_exhausted() -> bool:
        return deadline is not None and time.monotonic() >= deadline

    def snapshot(summary, *, force_complete: bool = False) -> dict[str, Any]:
        completed = summary.simulations
        winner_method = "hybrid_exact_top16_top10_top4"
        elapsed_seconds = max(0.0, time.monotonic() - started_at)
        simulations_per_second = completed / elapsed_seconds if elapsed_seconds > 0 else 0.0
        duration_progress = (
            min(elapsed_seconds / stream_duration_seconds, 1.0)
            if stream_duration_seconds is not None and stream_duration_seconds > 0
            else None
        )
        status = "complete" if force_complete or completed >= simulations else "running"
        output = {
            "status": status,
            "completed": completed,
            "total": simulations,
            "simulations_per_second": simulations_per_second,
            "progress_percent": (duration_progress * 100) if duration_progress is not None else None,
            **build_common_output(
                summary={**summary.to_dict(), "winner_method": winner_method},
                state=state,
                player_name_by_id=player_name_by_id,
                active_player_count=active_player_count,
                historical_point_requirements=historical_point_requirements,
                current_state=current_state,
                top_limit=top_limit,
            ),
        }
        if active_pods:
            output["active_pods"] = active_pods
        completed_pods = current_state.get("completed_current_round_pods", [])
        if completed_pods:
            output["completed_pods"] = completed_pods
        for unused_key in ("current_state", "round_draw_rate", "tournament"):
            output.pop(unused_key, None)
        return output

    effective_stream_batch_size = max(1, stream_batch_size)
    assigned = 0

    def next_batch_spec(initial: bool = False) -> tuple[int, int] | None:
        nonlocal assigned
        if assigned >= simulations or time_budget_exhausted():
            return None
        batch_size = min(
            STREAM_INITIAL_EMIT_SIMULATIONS if initial else effective_stream_batch_size,
            simulations - assigned,
        )
        batch_seed = seed + assigned
        assigned += batch_size
        return batch_size, batch_seed

    effective_workers = workers if workers is not None else max(1, min(4, os.cpu_count() or 1))
    accumulated = []
    initial_batch = next_batch_spec(initial=True)
    if initial_batch:
        batch_size, batch_seed = initial_batch
        accumulated.append(
            _run_state_monte_carlo_batch(
                state,
                draw_model,
                winner_model,
                simulations=batch_size,
                seed=batch_seed,
                start_round_index=start_round_index,
                locked_round_pods=locked_round_pods,
                locked_round_draw_probabilities=locked_round_draw_probabilities,
                locked_round_win_probabilities=locked_round_win_probabilities,
                requested_advancement_sizes=requested_advancement_sizes,
                collect_detailed_metrics=True,
                collect_player_metrics=False,
            )
        )
        print(json.dumps(snapshot(_merge_summaries(accumulated)), separators=(",", ":")), flush=True)

    if effective_workers <= 1:
        while (batch_spec := next_batch_spec()) is not None:
            batch_size, batch_seed = batch_spec
            accumulated.append(
                _run_state_monte_carlo_batch(
                    state,
                    draw_model,
                    winner_model,
                    simulations=batch_size,
                    seed=batch_seed,
                    start_round_index=start_round_index,
                    locked_round_pods=locked_round_pods,
                    locked_round_draw_probabilities=locked_round_draw_probabilities,
                    locked_round_win_probabilities=locked_round_win_probabilities,
                    requested_advancement_sizes=requested_advancement_sizes,
                    collect_detailed_metrics=True,
                    collect_player_metrics=False,
                )
            )
            summary = _merge_summaries(accumulated)
            print(json.dumps(snapshot(summary, force_complete=time_budget_exhausted()), separators=(",", ":")), flush=True)
            if time_budget_exhausted():
                break
        return

    with ProcessPoolExecutor(max_workers=effective_workers) as executor:
        futures = {}
        final_summary = _merge_summaries(accumulated) if accumulated else None
        final_snapshot_emitted = False

        def submit_next_batch() -> None:
            batch_spec = next_batch_spec()
            if batch_spec is None:
                return
            batch_size, batch_seed = batch_spec
            future = executor.submit(
                _run_state_monte_carlo_batch,
                state,
                draw_model,
                winner_model,
                batch_size,
                batch_seed,
                start_round_index,
                locked_round_pods,
                locked_round_draw_probabilities,
                locked_round_win_probabilities,
                requested_advancement_sizes,
                True,
                False,
            )
            futures[future] = None

        for _ in range(effective_workers):
            submit_next_batch()

        while futures:
            timeout = None
            if deadline is not None:
                timeout = max(0.0, deadline - time.monotonic())
            done, _ = wait(list(futures), timeout=timeout, return_when=FIRST_COMPLETED)
            if not done and time_budget_exhausted():
                for pending in futures:
                    pending.cancel()
                if final_summary is not None and not final_snapshot_emitted:
                    print(json.dumps(snapshot(final_summary, force_complete=True), separators=(",", ":")), flush=True)
                return
            for future in done:
                futures.pop(future, None)
                accumulated.append(future.result())
                summary = _merge_summaries(accumulated)
                final_summary = summary
                force_complete = time_budget_exhausted()
                print(json.dumps(snapshot(summary, force_complete=force_complete), separators=(",", ":")), flush=True)
                final_snapshot_emitted = force_complete or summary.simulations >= simulations
                if summary.simulations >= simulations or time_budget_exhausted():
                    for pending in futures:
                        pending.cancel()
                    if time_budget_exhausted() and final_summary is not None and not final_snapshot_emitted:
                        print(json.dumps(snapshot(final_summary, force_complete=True), separators=(",", ":")), flush=True)
                    return
                submit_next_batch()
                break
        if time_budget_exhausted() and final_summary is not None and not final_snapshot_emitted:
            print(json.dumps(snapshot(final_summary, force_complete=True), separators=(",", ":")), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-id", required=True, help="TopDeck event slug/TID")
    parser.add_argument("--draw-model-path", default=str(DEFAULT_DRAW_MODEL_PATH))
    parser.add_argument("--winner-model-path", default=None)
    parser.add_argument("--simulations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--swiss-rounds", type=int, default=None)
    parser.add_argument("--top-cut", type=int, default=None)
    parser.add_argument(
        "--drop-after-round",
        type=int,
        default=None,
        help="After this 1-based Swiss round completes, drop players below --drop-min-points.",
    )
    parser.add_argument(
        "--drop-min-points",
        type=int,
        default=None,
        help="Minimum points required to keep playing after --drop-after-round.",
    )
    parser.add_argument(
        "--repeat-avoidance-max-pods",
        type=int,
        default=32,
        help="Run repeat-opponent swap optimization only when generated Swiss pod count is at or below this value. Use 0 to disable.",
    )
    parser.add_argument(
        "--sample-top-cut",
        action="store_true",
        help="Sample top-cut winners instead of exact Elo propagation.",
    )
    parser.add_argument("--max-exact-cut-size", type=int, default=16)
    parser.add_argument("--stream", action="store_true", help="Emit newline-delimited live snapshots.")
    parser.add_argument(
        "--milestones",
        default="10,200,400,600,800,1000,2000,4000,6000,8000,10000,25000,50000,100000",
        help="Deprecated. Streaming emits after the first 100 simulations, then every 50 simulations by default.",
    )
    parser.add_argument("--stream-interval-seconds", type=float, default=5.0)
    parser.add_argument("--stream-batch-size", type=int, default=STREAM_EMIT_SIMULATION_INTERVAL)
    parser.add_argument(
        "--stream-duration-seconds",
        type=float,
        default=None,
        help="When streaming, stop after this many seconds even if --simulations has not been reached.",
    )
    parser.add_argument(
        "--prepared-state-cache-dir",
        type=Path,
        default=DEFAULT_PREPARED_STATE_CACHE_DIR,
        help="Directory for prepared tournament-state cache files. Use --no-prepared-state-cache to disable.",
    )
    parser.add_argument("--no-prepared-state-cache", action="store_true")
    args = parser.parse_args()
    if (args.drop_after_round is None) != (args.drop_min_points is None):
        parser.error("--drop-after-round and --drop-min-points must be provided together.")
    if args.drop_after_round is not None and args.drop_after_round <= 0:
        parser.error("--drop-after-round must be a positive round number.")
    if args.drop_min_points is not None and args.drop_min_points < 0:
        parser.error("--drop-min-points must be non-negative.")

    load_local_env()
    topdeck = TopDeckClient(os.environ["TOPDECK_API_KEY"])
    tournament = topdeck.get_tournament(args.event_id)
    event_html = "" if args.swiss_rounds is not None and args.top_cut is not None else fetch_event_page_html(args.event_id)
    swiss_rounds, top_cut = infer_structure(
        tournament,
        event_html,
        swiss_rounds_override=args.swiss_rounds,
        top_cut_override=args.top_cut,
    )

    player_names = collect_players(tournament)
    topdeck_ids = sorted(player_names)
    from ingest import SupabaseClient  # local import to keep script entry focused

    state_fingerprint = tournament_state_fingerprint(
        tournament,
        swiss_rounds=swiss_rounds,
        top_cut=top_cut,
        drop_after_round=args.drop_after_round,
        drop_min_points=args.drop_min_points,
    )
    cache_path = prepared_state_cache_path(args.prepared_state_cache_dir, args.event_id, state_fingerprint)
    cached_state = None if args.no_prepared_state_cache else load_prepared_state_cache(cache_path)
    client = None
    if cached_state:
        state = cached_state["state"]
        active_round_index = cached_state["active_round_index"]
        active_round_pods = cached_state["active_round_pods"]
        live_metadata = cached_state["live_metadata"]
    else:
        start_date = parse_start_date(tournament.get("startDate"))
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
        state, active_round_index, active_round_pods, live_metadata = build_base_state(
            client,
            tournament,
            swiss_rounds=swiss_rounds,
            top_cut=top_cut,
            feature_context=feature_context,
            player_records=player_records,
            repeat_avoidance_max_pods=args.repeat_avoidance_max_pods,
            drop_after_round=args.drop_after_round,
            drop_min_points=args.drop_min_points,
        )
        if not args.no_prepared_state_cache:
            save_prepared_state_cache(
                cache_path,
                {
                    "state": state,
                    "active_round_index": active_round_index,
                    "active_round_pods": active_round_pods,
                    "live_metadata": live_metadata,
                },
            )
    if apply_points_drop_if_due(state, active_round_index):
        if active_round_pods:
            active_round_pods = None
            live_metadata["locked_current_tables"] = []
        live_metadata["points_drop_applied"] = {
            "after_round": args.drop_after_round,
            "min_points": args.drop_min_points,
            "eligible_player_count": eligible_player_count(state),
        }
    state.fast_live_mode = True
    state.track_round_stats = False

    draw_model = load_draw_model_artifact(args.draw_model_path)
    winner_model = load_candidate_winner_model_artifact(args.winner_model_path) if args.winner_model_path else None
    requested_advancement_sizes = relevant_advancement_sizes(top_cut)
    if args.stream:
        run_live_monte_carlo_stream(
            state,
            draw_model,
            winner_model,
            simulations=args.simulations,
            seed=args.seed,
            start_round_index=active_round_index,
            locked_round_pods=active_round_pods,
            max_exact_cut_size=args.max_exact_cut_size,
            requested_advancement_sizes=requested_advancement_sizes,
            stream_interval_seconds=max(0.0, args.stream_interval_seconds),
            stream_batch_size=args.stream_batch_size,
            player_name_by_id={player_id: player.name for player_id, player in state.players.items()},
            active_player_count=eligible_player_count(state),
            historical_point_requirements=None,
            current_state={
                "completed_swiss_rounds": active_round_index,
                "active_round_number": (active_round_index + 1) if active_round_pods else None,
                "active_tables": len(active_round_pods or []),
                "eligible_player_count": eligible_player_count(state),
                "rounds": live_metadata.get("rounds", []),
                "locked_current_tables": live_metadata.get("locked_current_tables", []),
                "completed_current_round_pods": live_metadata.get("completed_current_round_pods", []),
                "drop_after_round": args.drop_after_round,
                "drop_min_points": args.drop_min_points,
                "points_drop_applied": live_metadata.get("points_drop_applied"),
            },
            workers=args.workers,
            top_limit=100,
            stream_duration_seconds=args.stream_duration_seconds,
        )
        return

    if args.sample_top_cut:
        summary = run_live_monte_carlo(
            state,
            draw_model,
            winner_model,
            simulations=args.simulations,
            seed=args.seed,
            start_round_index=active_round_index,
            locked_round_pods=active_round_pods,
            exact_top_cut=False,
            max_exact_cut_size=args.max_exact_cut_size,
            requested_advancement_sizes=requested_advancement_sizes,
        )
    else:
        summary = run_simulation_from_state(
            state,
            draw_model,
            winner_model=winner_model,
            simulations=args.simulations,
            seed=args.seed,
            workers=args.workers,
            start_round_index=active_round_index,
            locked_round_pods=active_round_pods,
            requested_advancement_sizes=requested_advancement_sizes,
        )
        summary["winner_method"] = "exact_top_cut"
    historical_point_requirements = fetch_historical_point_requirement_baseline(
        client or SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"]),
        active_player_count=eligible_player_count(state),
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
                    active_player_count=eligible_player_count(state),
                    historical_point_requirements=historical_point_requirements,
                    current_state={
                        "completed_swiss_rounds": active_round_index,
                        "active_round_number": (active_round_index + 1) if active_round_pods else None,
                        "active_tables": len(active_round_pods or []),
                        "eligible_player_count": eligible_player_count(state),
                        "rounds": live_metadata.get("rounds", []),
                        "locked_current_tables": live_metadata.get("locked_current_tables", []),
                        "drop_after_round": args.drop_after_round,
                        "drop_min_points": args.drop_min_points,
                        "points_drop_applied": live_metadata.get("points_drop_applied"),
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
