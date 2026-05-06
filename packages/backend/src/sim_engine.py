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

K_FACTOR_DECISIVE = 64.0
K_FACTOR_DRAW = 24.0


def clone_feature_context(feature_context: FeatureContext | None) -> FeatureContext:
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
        global_pair_meetings=dict(feature_context.global_pair_meetings),
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
        current_round_index=state.current_round_index,
        feature_context=clone_feature_context(state.feature_context),
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
            feature_context.global_pair_meetings[pair] = feature_context.global_pair_meetings.get(pair, 0) + 1
    total_completed = len(state.completed_pods)
    feature_context.global_recent_draw_rate_90d = (
        (feature_context.global_recent_draw_rate_90d * total_completed) + (1 if result.is_draw else 0)
    ) / (total_completed + 1)
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


def apply_round_elo_updates(
    state: TournamentState,
    pods: list[Pod],
    results: list[PodResult],
) -> None:
    pod_by_key = {(pod.round_index, pod.table_number): pod for pod in pods}
    deltas_by_player: dict[str, float] = defaultdict(float)
    for result in results:
        pod = pod_by_key[(result.round_index, result.table_number)]
        player_ids = pod.player_ids
        before_ratings = {player_id: state.players[player_id].elo for player_id in player_ids}
        draw_count = len(player_ids) if result.is_draw else 0
        k_factor = K_FACTOR_DRAW if draw_count else K_FACTOR_DECISIVE
        use_seat_bonus = (
            not result.is_draw
            and len(player_ids) == 4
            and sorted(pod.seats_by_player.get(player_id, -1) for player_id in player_ids) == [1, 2, 3, 4]
        )
        expected_ratings = {}
        for player_id in player_ids:
            expected_rating = before_ratings[player_id]
            if use_seat_bonus:
                seat = pod.seats_by_player.get(player_id)
                if seat in SEAT_ELO_BONUS:
                    expected_rating += SEAT_ELO_BONUS[seat]
            expected_ratings[player_id] = expected_rating
        total_equity = sum(_rating_equity(expected_ratings[player_id]) for player_id in player_ids) or 1.0
        for player_id in player_ids:
            expected = _rating_equity(expected_ratings[player_id]) / total_equity
            if result.is_draw:
                actual = 1.0 / draw_count
            else:
                actual = 1.0 if player_id == result.winner_id else 0.0
            deltas_by_player[player_id] += k_factor * (actual - expected)
    for player_id, delta in deltas_by_player.items():
        state.players[player_id].elo = round(state.players[player_id].elo + delta, 6)


def simulate_swiss(
    state: TournamentState,
    rng: random.Random,
    draw_model: LoadedDrawModel,
    context: TournamentContext,
    *,
    start_round_index: int = 0,
    locked_round_pods: list[Pod] | None = None,
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
        apply_round_elo_updates(state, pods, round_results)


def simulate_bracket_winner(
    qualified_player_ids: list[str],
    state: TournamentState,
    rng: random.Random,
    draw_model: LoadedDrawModel,
    context: TournamentContext,
) -> str:
    remaining = qualified_player_ids[:]
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
        apply_round_elo_updates(state, pods, round_results)
        remaining = sorted(winners, key=lambda player_id: initial_seed_rank[player_id])
        round_index += 1
    return remaining[0]


def simulate_tournament(
    spec: TournamentSpec,
    entrants: list[SimPlayer],
    draw_model: LoadedDrawModel,
    *,
    seed: int | None = None,
    feature_context=None,
) -> tuple[TournamentState, str | None, list[str]]:
    state = initialize_state(spec, entrants, feature_context=feature_context)
    return simulate_from_state(state, draw_model, seed=seed)


def simulate_from_state(
    state: TournamentState,
    draw_model: LoadedDrawModel,
    *,
    seed: int | None = None,
    start_round_index: int | None = None,
    locked_round_pods: list[Pod] | None = None,
) -> tuple[TournamentState, str | None, list[str]]:
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
    )
    top_cut = select_top_cut(state) if state.spec.top_cut > 0 else []
    winner_id = simulate_bracket_winner(top_cut, state, rng, draw_model, context) if top_cut else None
    return state, winner_id, top_cut


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
    expected_points_total: dict[str, float] = defaultdict(float)
    expected_finish_total: dict[str, float] = defaultdict(float)
    round_draw_counts: dict[int, int] = defaultdict(int)
    round_pod_counts: dict[int, int] = defaultdict(int)

    for simulation_index in range(simulations):
        state, winner_id, top_cut = simulate_tournament(
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
) -> SimulationSummary:
    win_counts: dict[str, int] = defaultdict(int)
    top_cut_counts: dict[str, int] = defaultdict(int)
    expected_points_total: dict[str, float] = defaultdict(float)
    expected_finish_total: dict[str, float] = defaultdict(float)
    round_draw_counts: dict[int, int] = defaultdict(int)
    round_pod_counts: dict[int, int] = defaultdict(int)

    for simulation_index in range(simulations):
        state = clone_state(base_state)
        state, winner_id, top_cut = simulate_from_state(
            state,
            draw_model,
            seed=seed + simulation_index,
            start_round_index=start_round_index,
            locked_round_pods=locked_round_pods,
        )
        if winner_id:
            win_counts[winner_id] += 1
        for player_id in top_cut:
            top_cut_counts[player_id] += 1
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
        expected_points_total=dict(expected_points_total),
        expected_finish_total=dict(expected_finish_total),
        round_draw_counts=dict(round_draw_counts),
        round_pod_counts=dict(round_pod_counts),
        simulations=simulations,
    )


def _merge_summaries(summaries: list[SimulationSummary]) -> SimulationSummary:
    win_counts: dict[str, int] = defaultdict(int)
    top_cut_counts: dict[str, int] = defaultdict(int)
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
) -> SimulationSummary:
    effective_workers = workers if workers is not None else max(1, min(4, os.cpu_count() or 1))
    effective_start_round = base_state.current_round_index if start_round_index is None else start_round_index
    if effective_workers <= 1 or simulations <= 1:
        return _run_state_monte_carlo_batch(
            base_state,
            draw_model,
            simulations=simulations,
            seed=seed,
            start_round_index=effective_start_round,
            locked_round_pods=locked_round_pods,
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
            )
        )
    return _merge_summaries(summaries)
