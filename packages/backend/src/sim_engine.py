#!/usr/bin/env python3
"""Monte Carlo tournament simulation using draw and decisive pod models."""

from __future__ import annotations

import math
import os
import random
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

from sim_models import (
    ELO_BASE,
    ELO_DIVISOR,
    SEAT_ELO_BONUS,
    LoadedDrawModel,
    build_round_snapshot,
    predict_decisive_win_probabilities,
    predict_draw_probabilities,
)
from sim_pairings import pair_swiss_round, pair_topdeck_bracket, select_top_cut, sort_standings_rows
from sim_types import (
    FeatureContext,
    PlayerHistory,
    Pod,
    PodResult,
    SimPlayer,
    SimulationSummary,
    StandingRow,
    TournamentContext,
    TournamentSpec,
    TournamentState,
)

def clone_feature_context(
    feature_context: FeatureContext | None,
    *,
    share_global_pair_meetings: bool = False,
) -> FeatureContext:
    if feature_context is None:
        return FeatureContext()
    return FeatureContext(
        player_history={
            player_id: PlayerHistory(
                draw_rate=history.draw_rate,
                win_rate=history.win_rate,
                decisive_rate=history.decisive_rate,
            )
            for player_id, history in feature_context.player_history.items()
        },
        tournament_pair_meetings=dict(feature_context.tournament_pair_meetings),
        global_pair_meetings=(
            feature_context.global_pair_meetings
            if share_global_pair_meetings
            else dict(feature_context.global_pair_meetings)
        ),
        series_prior_draw_rate=feature_context.series_prior_draw_rate,
        series_events_seen=feature_context.series_events_seen,
        state_prior_draw_rate=feature_context.state_prior_draw_rate,
        country_prior_draw_rate=feature_context.country_prior_draw_rate,
        global_recent_draw_rate_90d=feature_context.global_recent_draw_rate_90d,
    )


def initialize_state(
    spec: TournamentSpec,
    entrants: list[SimPlayer],
    *,
    feature_context=None,
) -> TournamentState:
    players = {player.player_id: player for player in entrants}
    standings = {player.player_id: StandingRow(player_id=player.player_id) for player in entrants}
    return TournamentState(
        spec=spec,
        players=players,
        standings=standings,
        feature_context=clone_feature_context(feature_context),
    )


def clone_state(state: TournamentState) -> TournamentState:
    cloned_players = {
        player_id: SimPlayer(
            player_id=player.player_id,
            name=player.name,
            elo=player.elo,
            topdeck_id=player.topdeck_id,
            tiebreak_seed=player.tiebreak_seed,
        )
        for player_id, player in state.players.items()
    }
    cloned_standings = {
        player_id: StandingRow(
            player_id=standing.player_id,
            points=standing.points,
            wins=standing.wins,
            draws=standing.draws,
            losses=standing.losses,
            pods_played=standing.pods_played,
            bye_count=standing.bye_count,
            opponents=set(standing.opponents),
        )
        for player_id, standing in state.standings.items()
    }
    return TournamentState(
        spec=state.spec,
        players=cloned_players,
        standings=cloned_standings,
        completed_pod_count=state.completed_pod_count,
        current_round_index=state.current_round_index,
        feature_context=clone_feature_context(
            state.feature_context,
            share_global_pair_meetings=state.fast_live_mode,
        ),
        fast_live_mode=state.fast_live_mode,
        track_round_stats=state.track_round_stats,
    )


def build_tournament_context(spec: TournamentSpec) -> TournamentContext:
    return TournamentContext(
        series_key=spec.name,
        state_key=(spec.state or "").strip().lower(),
        country_key=(spec.country or "").strip().lower(),
        top_cut=spec.top_cut,
        max_rounds=spec.swiss_rounds,
        start_date=spec.start_date,
        player_count=spec.player_count,
    )


def sample_weighted_choice(probabilities: dict[str, float], rng: random.Random) -> str:
    threshold = rng.random()
    cumulative = 0.0
    last_player_id = next(iter(probabilities))
    for player_id, probability in probabilities.items():
        cumulative += probability
        last_player_id = player_id
        if threshold <= cumulative:
            return player_id
    return last_player_id


def sample_index(probabilities: tuple[float, ...], rng: random.Random) -> int:
    threshold = rng.random()
    cumulative = 0.0
    last_index = 0
    for index, probability in enumerate(probabilities):
        cumulative += probability
        last_index = index
        if threshold <= cumulative:
            return index
    return last_index


def _rating_equity(rating: float) -> float:
    return pow(ELO_BASE, rating / ELO_DIVISOR)


def simulate_pod(
    pod: Pod,
    rng: random.Random,
    draw_probability: float,
    win_probabilities: tuple[float, ...],
) -> PodResult:
    is_draw = rng.random() < draw_probability
    winner_id = None if is_draw else pod.player_ids[sample_index(win_probabilities, rng)]
    return PodResult(
        round_index=pod.round_index,
        table_number=pod.table_number,
        player_ids=pod.player_ids,
        is_draw=is_draw,
        winner_id=winner_id,
        win_probabilities=win_probabilities,
        draw_probability=draw_probability,
    )


def apply_pod_result(state: TournamentState, result: PodResult) -> None:
    feature_context = state.feature_context
    for player_id in result.player_ids:
        standing = state.standings[player_id]
        standing.pods_played += 1
        if result.is_draw:
            standing.points += 1
            standing.draws += 1
        elif player_id == result.winner_id:
            standing.points += 5
            standing.wins += 1
        else:
            standing.losses += 1
        history = feature_context.player_history.get(player_id, PlayerHistory())
        prior_games = standing.pods_played - 1
        total_games = max(1, standing.pods_played)
        prior_draws = history.draw_rate * prior_games
        prior_wins = history.win_rate * prior_games
        prior_decisive = history.decisive_rate * prior_games
        history.draw_rate = (prior_draws + (1 if result.is_draw else 0)) / total_games
        history.win_rate = (prior_wins + (1 if player_id == result.winner_id else 0)) / total_games
        history.decisive_rate = (prior_decisive + (0 if result.is_draw else 1)) / total_games
        feature_context.player_history[player_id] = history
    for index, player_id in enumerate(result.player_ids):
        for opponent_id in result.player_ids[index + 1 :]:
            state.standings[player_id].opponents.add(opponent_id)
            state.standings[opponent_id].opponents.add(player_id)
    for index, player_id in enumerate(result.player_ids):
        for opponent_id in result.player_ids[index + 1 :]:
            pair = tuple(sorted((player_id, opponent_id)))
            feature_context.tournament_pair_meetings[pair] = feature_context.tournament_pair_meetings.get(pair, 0) + 1
            if not state.fast_live_mode:
                feature_context.global_pair_meetings[pair] = feature_context.global_pair_meetings.get(pair, 0) + 1
    total_completed = state.completed_pod_count
    if not state.fast_live_mode:
        feature_context.global_recent_draw_rate_90d = (
            (feature_context.global_recent_draw_rate_90d * total_completed) + (1 if result.is_draw else 0)
        ) / (total_completed + 1)
    state.completed_pod_count += 1
    if state.track_round_stats:
        state.round_pod_counts[result.round_index + 1] = state.round_pod_counts.get(result.round_index + 1, 0) + 1
        if result.is_draw:
            state.round_draw_counts[result.round_index + 1] = state.round_draw_counts.get(result.round_index + 1, 0) + 1


def apply_bye(state: TournamentState, player_id: str) -> None:
    standing = state.standings[player_id]
    standing.pods_played += 1
    standing.bye_count += 1
    standing.points += 5
    standing.wins += 1
    history = state.feature_context.player_history.get(player_id, PlayerHistory())
    prior_games = standing.pods_played - 1
    total_games = max(1, standing.pods_played)
    prior_draws = history.draw_rate * prior_games
    prior_wins = history.win_rate * prior_games
    prior_decisive = history.decisive_rate * prior_games
    history.draw_rate = prior_draws / total_games
    history.win_rate = (prior_wins + 1) / total_games
    history.decisive_rate = (prior_decisive + 1) / total_games
    state.feature_context.player_history[player_id] = history


def simulate_swiss(
    state: TournamentState,
    rng: random.Random,
    draw_model: LoadedDrawModel,
    context: TournamentContext,
    *,
    start_round_index: int = 0,
    locked_round_pods: list[Pod] | None = None,
    locked_round_draw_probabilities: dict[tuple[int, int], float] | None = None,
    locked_round_win_probabilities: dict[tuple[int, int], tuple[float, ...]] | None = None,
) -> None:
    for round_index in range(start_round_index, state.spec.swiss_rounds):
        state.current_round_index = round_index
        if locked_round_pods is not None and round_index == start_round_index:
            pods = locked_round_pods
        else:
            pods = pair_swiss_round(state, round_index, rng)
        bye_pods = [pod for pod in pods if len(pod.player_ids) == 1]
        pods = [pod for pod in pods if len(pod.player_ids) >= 2]
        for bye_pod in bye_pods:
            apply_bye(state, bye_pod.player_ids[0])
        if not pods:
            continue
        if (
            locked_round_pods is not None
            and round_index == start_round_index
            and locked_round_draw_probabilities is not None
            and locked_round_win_probabilities is not None
        ):
            draw_probabilities = locked_round_draw_probabilities
            win_probabilities = locked_round_win_probabilities
        else:
            round_snapshot = build_round_snapshot(state, context, round_index + 1)
            draw_probabilities = predict_draw_probabilities(pods, state, context, draw_model, round_snapshot)
            win_probabilities = predict_decisive_win_probabilities(pods, state)
        round_results: list[PodResult] = []
        for pod in pods:
            result = simulate_pod(
                pod,
                rng,
                draw_probabilities[(pod.round_index, pod.table_number)],
                win_probabilities[(pod.round_index, pod.table_number)],
            )
            round_results.append(result)
            apply_pod_result(state, result)


def simulate_bracket_winner(
    qualified_player_ids: list[str],
    state: TournamentState,
    rng: random.Random,
    draw_model: LoadedDrawModel,
    context: TournamentContext,
) -> tuple[str, dict[int, list[str]]]:
    remaining = qualified_player_ids[:]
    advancement_by_size: dict[int, list[str]] = {}
    if remaining:
        advancement_by_size[len(remaining)] = remaining[:]
    initial_seed_rank = {player_id: index for index, player_id in enumerate(qualified_player_ids)}
    round_index = state.spec.swiss_rounds
    while len(remaining) > 1:
        auto_advancers, pods = pair_topdeck_bracket(remaining, round_index)
        winners: list[str] = auto_advancers[:]
        win_probabilities = predict_decisive_win_probabilities(pods, state)
        round_results: list[PodResult] = []
        for pod in pods:
            pod_win_probabilities = win_probabilities[(pod.round_index, pod.table_number)]
            winner_id = pod.player_ids[sample_index(pod_win_probabilities, rng)]
            result = PodResult(
                round_index=pod.round_index,
                table_number=pod.table_number,
                player_ids=pod.player_ids,
                is_draw=False,
                winner_id=winner_id,
                win_probabilities=pod_win_probabilities,
                draw_probability=0.0,
            )
            round_results.append(result)
            winners.append(result.winner_id)
        remaining = sorted(winners, key=lambda player_id: initial_seed_rank[player_id])
        advancement_by_size[len(remaining)] = remaining[:]
        round_index += 1
    return remaining[0], advancement_by_size


def simulate_tournament(
    spec: TournamentSpec,
    entrants: list[SimPlayer],
    draw_model: LoadedDrawModel,
    *,
    seed: int | None = None,
    feature_context=None,
) -> tuple[TournamentState, str | None, list[str], dict[int, list[str]]]:
    state = initialize_state(spec, entrants, feature_context=feature_context)
    return simulate_from_state(state, draw_model, seed=seed)


def simulate_from_state(
    state: TournamentState,
    draw_model: LoadedDrawModel,
    *,
    seed: int | None = None,
    start_round_index: int | None = None,
    locked_round_pods: list[Pod] | None = None,
    locked_round_draw_probabilities: dict[tuple[int, int], float] | None = None,
    locked_round_win_probabilities: dict[tuple[int, int], tuple[float, ...]] | None = None,
) -> tuple[TournamentState, str | None, list[str], dict[int, list[str]]]:
    rng = random.Random(seed)
    context = build_tournament_context(state.spec)
    effective_start_round = state.current_round_index if start_round_index is None else start_round_index
    simulate_swiss(
        state,
        rng,
        draw_model,
        context,
        start_round_index=effective_start_round,
        locked_round_pods=locked_round_pods,
        locked_round_draw_probabilities=locked_round_draw_probabilities,
        locked_round_win_probabilities=locked_round_win_probabilities,
    )
    top_cut = select_top_cut(state) if state.spec.top_cut > 0 else []
    if top_cut:
        winner_id, advancement_by_size = simulate_bracket_winner(top_cut, state, rng, draw_model, context)
    else:
        winner_id, advancement_by_size = None, {}
    return state, winner_id, top_cut, advancement_by_size


def _run_monte_carlo_batch(
    spec: TournamentSpec,
    entrants: list[SimPlayer],
    draw_model: LoadedDrawModel,
    simulations: int,
    seed: int,
    feature_context: FeatureContext | None,
) -> SimulationSummary:
    win_counts: dict[str, int] = defaultdict(int)
    top_cut_counts: dict[str, int] = defaultdict(int)
    advancement_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    expected_points_total: dict[str, float] = defaultdict(float)
    expected_finish_total: dict[str, float] = defaultdict(float)
    round_draw_counts: dict[int, int] = defaultdict(int)
    round_pod_counts: dict[int, int] = defaultdict(int)

    for simulation_index in range(simulations):
        state, winner_id, top_cut, advancement_by_size = simulate_tournament(
            spec,
            entrants,
            draw_model,
            seed=seed + simulation_index,
            feature_context=feature_context,
        )
        if winner_id:
            win_counts[winner_id] += 1
        for player_id in top_cut:
            top_cut_counts[player_id] += 1
        for cut_size, player_ids in advancement_by_size.items():
            for player_id in player_ids:
                advancement_counts[cut_size][player_id] += 1
        ranked = sort_standings_rows(state)
        for finish_index, standing in enumerate(ranked, start=1):
            expected_points_total[standing.player_id] += standing.points
            expected_finish_total[standing.player_id] += finish_index
        for round_index, count in state.round_pod_counts.items():
            round_pod_counts[round_index] += count
        for round_index, count in state.round_draw_counts.items():
            round_draw_counts[round_index] += count

    return SimulationSummary(
        win_counts=dict(win_counts),
        top_cut_counts=dict(top_cut_counts),
        advancement_counts={cut_size: dict(player_counts) for cut_size, player_counts in advancement_counts.items()},
        expected_points_total=dict(expected_points_total),
        expected_finish_total=dict(expected_finish_total),
        round_draw_counts=dict(round_draw_counts),
        round_pod_counts=dict(round_pod_counts),
        simulations=simulations,
    )


def _run_state_monte_carlo_batch(
    base_state: TournamentState,
    draw_model: LoadedDrawModel,
    simulations: int,
    seed: int,
    start_round_index: int,
    locked_round_pods: list[Pod] | None,
    locked_round_draw_probabilities: dict[tuple[int, int], float] | None,
    locked_round_win_probabilities: dict[tuple[int, int], tuple[float, ...]] | None,
    requested_advancement_sizes: tuple[int, ...] | None,
    collect_detailed_metrics: bool,
) -> SimulationSummary:
    win_counts: dict[str, int] = defaultdict(int)
    top_cut_counts: dict[str, int] = defaultdict(int)
    advancement_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    expected_points_total: dict[str, float] = defaultdict(float)
    expected_finish_total: dict[str, float] = defaultdict(float)
    round_draw_counts: dict[int, int] = defaultdict(int)
    round_pod_counts: dict[int, int] = defaultdict(int)
    for simulation_index in range(simulations):
        state = clone_state(base_state)
        state, winner_id, top_cut, advancement_by_size = simulate_from_state(
            state,
            draw_model,
            seed=seed + simulation_index,
            start_round_index=start_round_index,
            locked_round_pods=locked_round_pods,
            locked_round_draw_probabilities=locked_round_draw_probabilities,
            locked_round_win_probabilities=locked_round_win_probabilities,
        )
        if winner_id:
            win_counts[winner_id] += 1
        for player_id in top_cut:
            top_cut_counts[player_id] += 1
        if requested_advancement_sizes:
            for cut_size in requested_advancement_sizes:
                for player_id in advancement_by_size.get(cut_size, []):
                    advancement_counts[cut_size][player_id] += 1
        if collect_detailed_metrics:
            ranked = sort_standings_rows(state)
            for finish_index, standing in enumerate(ranked, start=1):
                expected_points_total[standing.player_id] += standing.points
                expected_finish_total[standing.player_id] += finish_index
            for round_index, count in state.round_pod_counts.items():
                round_pod_counts[round_index] += count
            for round_index, count in state.round_draw_counts.items():
                round_draw_counts[round_index] += count

    return SimulationSummary(
        win_counts=dict(win_counts),
        top_cut_counts=dict(top_cut_counts),
        advancement_counts={cut_size: dict(player_counts) for cut_size, player_counts in advancement_counts.items()},
        expected_points_total=dict(expected_points_total),
        expected_finish_total=dict(expected_finish_total),
        round_draw_counts=dict(round_draw_counts),
        round_pod_counts=dict(round_pod_counts),
        simulations=simulations,
    )


def _merge_summaries(summaries: list[SimulationSummary]) -> SimulationSummary:
    win_counts: dict[str, int] = defaultdict(int)
    top_cut_counts: dict[str, int] = defaultdict(int)
    advancement_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    expected_points_total: dict[str, float] = defaultdict(float)
    expected_finish_total: dict[str, float] = defaultdict(float)
    round_draw_counts: dict[int, int] = defaultdict(int)
    round_pod_counts: dict[int, int] = defaultdict(int)
    total_simulations = 0

    for summary in summaries:
        total_simulations += summary.simulations
        for player_id, count in summary.win_counts.items():
            win_counts[player_id] += count
        for player_id, count in summary.top_cut_counts.items():
            top_cut_counts[player_id] += count
        for cut_size, player_counts in summary.advancement_counts.items():
            for player_id, count in player_counts.items():
                advancement_counts[cut_size][player_id] += count
        for player_id, total in summary.expected_points_total.items():
            expected_points_total[player_id] += total
        for player_id, total in summary.expected_finish_total.items():
            expected_finish_total[player_id] += total
        for round_index, count in summary.round_draw_counts.items():
            round_draw_counts[round_index] += count
        for round_index, count in summary.round_pod_counts.items():
            round_pod_counts[round_index] += count

    return SimulationSummary(
        win_counts=dict(win_counts),
        top_cut_counts=dict(top_cut_counts),
        advancement_counts={cut_size: dict(player_counts) for cut_size, player_counts in advancement_counts.items()},
        expected_points_total=dict(expected_points_total),
        expected_finish_total=dict(expected_finish_total),
        round_draw_counts=dict(round_draw_counts),
        round_pod_counts=dict(round_pod_counts),
        simulations=total_simulations,
    )


def run_monte_carlo(
    spec: TournamentSpec,
    entrants: list[SimPlayer],
    draw_model: LoadedDrawModel,
    *,
    simulations: int = 10_000,
    seed: int = 1,
    feature_context=None,
    workers: int | None = None,
) -> SimulationSummary:
    effective_workers = workers if workers is not None else max(1, min(4, os.cpu_count() or 1))
    if effective_workers <= 1 or simulations <= 1:
        return _run_monte_carlo_batch(
            spec,
            entrants,
            draw_model,
            simulations=simulations,
            seed=seed,
            feature_context=feature_context,
        )

    batch_count = min(effective_workers, simulations)
    batch_size = math.ceil(simulations / batch_count)
    batch_specs: list[tuple[int, int]] = []
    assigned = 0
    for batch_index in range(batch_count):
        this_batch = min(batch_size, simulations - assigned)
        if this_batch <= 0:
            break
        batch_specs.append((this_batch, seed + assigned))
        assigned += this_batch

    with ProcessPoolExecutor(max_workers=len(batch_specs)) as executor:
        summaries = list(
            executor.map(
                _run_monte_carlo_batch,
                [spec] * len(batch_specs),
                [entrants] * len(batch_specs),
                [draw_model] * len(batch_specs),
                [simulation_count for simulation_count, _ in batch_specs],
                [batch_seed for _, batch_seed in batch_specs],
                [feature_context] * len(batch_specs),
            )
        )
    return _merge_summaries(summaries)


def run_monte_carlo_from_state(
    base_state: TournamentState,
    draw_model: LoadedDrawModel,
    *,
    simulations: int = 10_000,
    seed: int = 1,
    workers: int | None = None,
    start_round_index: int | None = None,
    locked_round_pods: list[Pod] | None = None,
    requested_advancement_sizes: tuple[int, ...] | None = None,
    collect_detailed_metrics: bool = True,
) -> SimulationSummary:
    effective_workers = workers if workers is not None else max(1, min(4, os.cpu_count() or 1))
    effective_start_round = base_state.current_round_index if start_round_index is None else start_round_index
    locked_round_draw_probabilities: dict[tuple[int, int], float] | None = None
    locked_round_win_probabilities: dict[tuple[int, int], tuple[float, ...]] | None = None
    if locked_round_pods is not None:
        context = build_tournament_context(base_state.spec)
        round_snapshot = build_round_snapshot(base_state, context, effective_start_round + 1)
        locked_round_draw_probabilities = predict_draw_probabilities(
            locked_round_pods,
            base_state,
            context,
            draw_model,
            round_snapshot,
        )
        locked_round_win_probabilities = predict_decisive_win_probabilities(locked_round_pods, base_state)
    if effective_workers <= 1 or simulations <= 1:
        return _run_state_monte_carlo_batch(
            base_state,
            draw_model,
            simulations=simulations,
            seed=seed,
            start_round_index=effective_start_round,
            locked_round_pods=locked_round_pods,
            locked_round_draw_probabilities=locked_round_draw_probabilities,
            locked_round_win_probabilities=locked_round_win_probabilities,
            requested_advancement_sizes=requested_advancement_sizes,
            collect_detailed_metrics=collect_detailed_metrics,
        )

    batch_count = min(effective_workers, simulations)
    batch_size = math.ceil(simulations / batch_count)
    batch_specs: list[tuple[int, int]] = []
    assigned = 0
    for _batch_index in range(batch_count):
        this_batch = min(batch_size, simulations - assigned)
        if this_batch <= 0:
            break
        batch_specs.append((this_batch, seed + assigned))
        assigned += this_batch

    with ProcessPoolExecutor(max_workers=len(batch_specs)) as executor:
        summaries = list(
            executor.map(
                _run_state_monte_carlo_batch,
                [base_state] * len(batch_specs),
                [draw_model] * len(batch_specs),
                [simulation_count for simulation_count, _ in batch_specs],
                [batch_seed for _, batch_seed in batch_specs],
                [effective_start_round] * len(batch_specs),
                [locked_round_pods] * len(batch_specs),
                [locked_round_draw_probabilities] * len(batch_specs),
                [locked_round_win_probabilities] * len(batch_specs),
                [requested_advancement_sizes] * len(batch_specs),
                [collect_detailed_metrics] * len(batch_specs),
            )
        )
    return _merge_summaries(summaries)
