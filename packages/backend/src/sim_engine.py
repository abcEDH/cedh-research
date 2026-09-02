#!/usr/bin/env python3
"""Monte Carlo tournament simulation using draw and decisive pod models."""

from __future__ import annotations

import math
import os
import random
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from itertools import product

from sim_models import (
    ELO_BASE,
    ELO_DIVISOR,
    LoadedCandidateWinnerModel,
    LoadedDrawModel,
    build_round_snapshot,
    predict_decisive_win_probabilities,
    predict_pod_outcome_probabilities,
)
from sim_pairings import pair_swiss_round, pair_topdeck_bracket, select_top_cut, sort_standings_rows, topdeck_bye_rank
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
    share_player_history: bool = False,
) -> FeatureContext:
    if feature_context is None:
        return FeatureContext()
    return FeatureContext(
        player_history=(
            feature_context.player_history
            if share_player_history
            else {
                player_id: PlayerHistory(
                    draw_rate=history.draw_rate,
                    win_rate=history.win_rate,
                    decisive_rate=history.decisive_rate,
                    games_played=history.games_played,
                )
                for player_id, history in feature_context.player_history.items()
            }
        ),
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
        players=state.players,
        standings=cloned_standings,
        completed_pod_count=state.completed_pod_count,
        current_round_index=state.current_round_index,
        feature_context=clone_feature_context(
            state.feature_context,
            share_global_pair_meetings=state.fast_live_mode,
            share_player_history=state.fast_live_mode,
        ),
        eligible_player_ids=set(state.eligible_player_ids) if state.eligible_player_ids is not None else None,
        fast_live_mode=state.fast_live_mode,
        track_round_stats=state.track_round_stats,
        standings_random_tiebreakers=dict(state.standings_random_tiebreakers),
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
        if not state.fast_live_mode:
            history = feature_context.player_history.get(player_id, PlayerHistory())
            prior_games = standing.pods_played - 1
            total_games = max(1, standing.pods_played)
            prior_draws = history.draw_rate * prior_games
            prior_wins = history.win_rate * prior_games
            prior_decisive = history.decisive_rate * prior_games
            history.draw_rate = (prior_draws + (1 if result.is_draw else 0)) / total_games
            history.win_rate = (prior_wins + (1 if player_id == result.winner_id else 0)) / total_games
            history.decisive_rate = (prior_decisive + (0 if result.is_draw else 1)) / total_games
            history.games_played = total_games
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
    if not state.fast_live_mode:
        history = state.feature_context.player_history.get(player_id, PlayerHistory())
        prior_games = standing.pods_played - 1
        total_games = max(1, standing.pods_played)
        prior_draws = history.draw_rate * prior_games
        prior_wins = history.win_rate * prior_games
        prior_decisive = history.decisive_rate * prior_games
        history.draw_rate = prior_draws / total_games
        history.win_rate = (prior_wins + 1) / total_games
        history.decisive_rate = (prior_decisive + 1) / total_games
        history.games_played = total_games
        state.feature_context.player_history[player_id] = history


def apply_points_drop_if_due(state: TournamentState, completed_round_number: int) -> bool:
    drop_after_round = state.spec.drop_after_round
    drop_min_points = state.spec.drop_min_points
    if drop_after_round is None or drop_min_points is None:
        return False
    if drop_after_round <= 0 or drop_min_points < 0:
        return False
    if completed_round_number < drop_after_round:
        return False

    current_eligible = state.eligible_player_ids if state.eligible_player_ids is not None else set(state.standings)
    next_eligible = {
        player_id
        for player_id in current_eligible
        if state.standings[player_id].points >= drop_min_points
    }
    changed = state.eligible_player_ids != next_eligible
    state.eligible_player_ids = next_eligible
    return changed


def simulate_swiss(
    state: TournamentState,
    rng: random.Random,
    draw_model: LoadedDrawModel,
    context: TournamentContext,
    winner_model: LoadedCandidateWinnerModel | None = None,
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
            apply_points_drop_if_due(state, round_index + 1)
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
            draw_probabilities, win_probabilities = predict_pod_outcome_probabilities(
                pods,
                state,
                context,
                draw_model,
                round_snapshot,
                winner_model,
            )
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
        apply_points_drop_if_due(state, round_index + 1)


def simulate_bracket_winner(
    qualified_player_ids: list[str],
    state: TournamentState,
    rng: random.Random,
    draw_model: LoadedDrawModel,
    context: TournamentContext,
    winner_model: LoadedCandidateWinnerModel | None = None,
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
        win_probabilities = predict_decisive_win_probabilities(pods, state, context, winner_model)
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


def exact_top_cut_probabilities(
    qualified_player_ids: list[str],
    state: TournamentState,
    *,
    max_exact_cut_size: int = 16,
    start_round_index: int | None = None,
    context: TournamentContext | None = None,
    winner_model: LoadedCandidateWinnerModel | None = None,
) -> tuple[dict[str, float], dict[int, dict[str, float]]]:
    if len(qualified_player_ids) > max_exact_cut_size:
        raise ValueError(f"exact top-cut propagation is capped at {max_exact_cut_size} players")

    initial_seed_rank = {player_id: index for index, player_id in enumerate(qualified_player_ids)}
    winner_probabilities: dict[str, float] = defaultdict(float)
    advancement_probabilities: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    current_states: dict[tuple[str, ...], float] = {tuple(qualified_player_ids): 1.0}
    round_index = state.spec.swiss_rounds if start_round_index is None else start_round_index

    while current_states:
        branch_specs: list[tuple[tuple[str, ...], float, list[str], list[Pod]]] = []
        batched_pods: list[Pod] = []
        next_states: dict[tuple[str, ...], float] = defaultdict(float)

        for remaining_tuple, branch_probability in current_states.items():
            if not remaining_tuple or branch_probability <= 0:
                continue
            remaining = list(remaining_tuple)
            for player_id in remaining:
                advancement_probabilities[len(remaining)][player_id] += branch_probability
            if len(remaining) == 1:
                winner_probabilities[remaining[0]] += branch_probability
                continue

            auto_advancers, pods = pair_topdeck_bracket(remaining, round_index)
            if not pods:
                if auto_advancers:
                    split_probability = branch_probability / len(auto_advancers)
                    for player_id in auto_advancers:
                        winner_probabilities[player_id] += split_probability
                continue

            copied_pods: list[Pod] = []
            for pod in pods:
                # Batch all branch pods into one model call per bracket round.
                copied_pod = Pod(
                    round_index=pod.round_index,
                    table_number=len(batched_pods) + 1,
                    player_ids=pod.player_ids,
                    round_name=pod.round_name,
                    seats_by_player=pod.seats_by_player,
                )
                copied_pods.append(copied_pod)
                batched_pods.append(copied_pod)
            branch_specs.append((remaining_tuple, branch_probability, auto_advancers, copied_pods))

        if not branch_specs:
            break

        win_probabilities = predict_decisive_win_probabilities(batched_pods, state, context, winner_model)
        for _remaining_tuple, branch_probability, auto_advancers, pods in branch_specs:
            pod_options = [
                list(zip(pod.player_ids, win_probabilities[(pod.round_index, pod.table_number)], strict=False))
                for pod in pods
            ]
            for outcome in product(*pod_options):
                winners = auto_advancers + [player_id for player_id, _probability in outcome]
                probability = branch_probability
                for _player_id, player_probability in outcome:
                    probability *= player_probability
                ordered_winners = tuple(sorted(winners, key=lambda player_id: initial_seed_rank[player_id]))
                next_states[ordered_winners] += probability

        current_states = next_states
        round_index += 1

    return dict(winner_probabilities), {
        cut_size: dict(player_probabilities)
        for cut_size, player_probabilities in advancement_probabilities.items()
    }


def resolve_bracket_probabilities(
    qualified_player_ids: list[str],
    state: TournamentState,
    rng: random.Random,
    draw_model: LoadedDrawModel,
    context: TournamentContext,
    winner_model: LoadedCandidateWinnerModel | None = None,
    *,
    exact_cut_sizes: tuple[int, ...] = (16, 10, 4),
) -> tuple[dict[str, float], dict[int, dict[str, float]]]:
    exact_cut_sizes = tuple(sorted({cut_size for cut_size in exact_cut_sizes if cut_size > 0}, reverse=True))
    if not exact_cut_sizes:
        winner_id, advancement_by_size = simulate_bracket_winner(
            qualified_player_ids,
            state,
            rng,
            draw_model,
            context,
            winner_model,
        )
        winner_probabilities = {winner_id: 1.0} if winner_id else {}
        advancement_probabilities = {
            cut_size: {player_id: 1.0 for player_id in player_ids}
            for cut_size, player_ids in advancement_by_size.items()
        }
        return winner_probabilities, advancement_probabilities

    if len(qualified_player_ids) in exact_cut_sizes:
        return exact_top_cut_probabilities(
            qualified_player_ids,
            state,
            max_exact_cut_size=max(exact_cut_sizes),
            context=context,
            winner_model=winner_model,
        )

    remaining = qualified_player_ids[:]
    initial_seed_rank = {player_id: index for index, player_id in enumerate(qualified_player_ids)}
    round_index = state.spec.swiss_rounds
    advancement_probabilities: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for player_id in remaining:
        advancement_probabilities[len(remaining)][player_id] += 1.0

    while len(remaining) > 1:
        auto_advancers, pods = pair_topdeck_bracket(remaining, round_index)
        if not pods:
            if auto_advancers:
                split_probability = 1.0 / len(auto_advancers)
                winner_probabilities = {player_id: split_probability for player_id in auto_advancers}
                return winner_probabilities, {
                    cut_size: dict(player_probabilities)
                    for cut_size, player_probabilities in advancement_probabilities.items()
                }
            break

        next_size = len(auto_advancers) + len(pods)
        win_probabilities = predict_decisive_win_probabilities(pods, state, context, winner_model)
        if next_size in exact_cut_sizes:
            for player_id in auto_advancers:
                advancement_probabilities[next_size][player_id] += 1.0
            sampled_winners = auto_advancers[:]
            for pod in pods:
                pod_win_probabilities = win_probabilities[(pod.round_index, pod.table_number)]
                for player_id, probability in zip(pod.player_ids, pod_win_probabilities, strict=False):
                    advancement_probabilities[next_size][player_id] += probability
                sampled_winners.append(pod.player_ids[sample_index(pod_win_probabilities, rng)])

            exact_players = sorted(sampled_winners, key=lambda player_id: initial_seed_rank[player_id])
            winner_probabilities, exact_advancement_probabilities = exact_top_cut_probabilities(
                exact_players,
                state,
                max_exact_cut_size=max(exact_cut_sizes),
                start_round_index=round_index + 1,
                context=context,
                winner_model=winner_model,
            )
            for cut_size, player_probabilities in exact_advancement_probabilities.items():
                if cut_size == next_size:
                    continue
                for player_id, probability in player_probabilities.items():
                    advancement_probabilities[cut_size][player_id] += probability
            return dict(winner_probabilities), {
                cut_size: dict(player_probabilities)
                for cut_size, player_probabilities in advancement_probabilities.items()
            }

        winners = auto_advancers[:]
        for pod in pods:
            pod_win_probabilities = win_probabilities[(pod.round_index, pod.table_number)]
            winners.append(pod.player_ids[sample_index(pod_win_probabilities, rng)])
        remaining = sorted(winners, key=lambda player_id: initial_seed_rank[player_id])
        for player_id in remaining:
            advancement_probabilities[len(remaining)][player_id] += 1.0
        round_index += 1

    winner_probabilities = {remaining[0]: 1.0} if remaining else {}
    return winner_probabilities, {
        cut_size: dict(player_probabilities)
        for cut_size, player_probabilities in advancement_probabilities.items()
    }


def simulate_tournament(
    spec: TournamentSpec,
    entrants: list[SimPlayer],
    draw_model: LoadedDrawModel,
    *,
    seed: int | None = None,
    feature_context=None,
    winner_model: LoadedCandidateWinnerModel | None = None,
) -> tuple[TournamentState, dict[str, float], list[str], dict[int, dict[str, float]]]:
    state = initialize_state(spec, entrants, feature_context=feature_context)
    return simulate_from_state(state, draw_model, seed=seed, winner_model=winner_model)


def simulate_from_state(
    state: TournamentState,
    draw_model: LoadedDrawModel,
    *,
    seed: int | None = None,
    winner_model: LoadedCandidateWinnerModel | None = None,
    start_round_index: int | None = None,
    locked_round_pods: list[Pod] | None = None,
    locked_round_draw_probabilities: dict[tuple[int, int], float] | None = None,
    locked_round_win_probabilities: dict[tuple[int, int], tuple[float, ...]] | None = None,
) -> tuple[TournamentState, dict[str, float], list[str], dict[int, dict[str, float]]]:
    rng = random.Random(seed)
    context = build_tournament_context(state.spec)
    effective_start_round = state.current_round_index if start_round_index is None else start_round_index
    if apply_points_drop_if_due(state, effective_start_round):
        locked_round_pods = None
        locked_round_draw_probabilities = None
        locked_round_win_probabilities = None
    simulate_swiss(
        state,
        rng,
        draw_model,
        context,
        winner_model,
        start_round_index=effective_start_round,
        locked_round_pods=locked_round_pods,
        locked_round_draw_probabilities=locked_round_draw_probabilities,
        locked_round_win_probabilities=locked_round_win_probabilities,
    )
    top_cut = select_top_cut(state, rng=rng) if state.spec.top_cut > 0 else []
    if top_cut:
        winner_probabilities, advancement_probabilities = resolve_bracket_probabilities(
            top_cut,
            state,
            rng,
            draw_model,
            context,
            winner_model,
        )
    else:
        winner_probabilities, advancement_probabilities = {}, {}
    return state, winner_probabilities, top_cut, advancement_probabilities


def _run_monte_carlo_batch(
    spec: TournamentSpec,
    entrants: list[SimPlayer],
    draw_model: LoadedDrawModel,
    winner_model: LoadedCandidateWinnerModel | None,
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
    top_cut_line_point_counts: dict[int, int] = defaultdict(int)
    bye_line_point_counts: dict[int, int] = defaultdict(int)

    for simulation_index in range(simulations):
        state, winner_probabilities, top_cut, advancement_probabilities = simulate_tournament(
            spec,
            entrants,
            draw_model,
            seed=seed + simulation_index,
            feature_context=feature_context,
            winner_model=winner_model,
        )
        for player_id, probability in winner_probabilities.items():
            win_counts[player_id] += probability
        for player_id in top_cut:
            top_cut_counts[player_id] += 1
        for cut_size, player_probabilities in advancement_probabilities.items():
            for player_id, probability in player_probabilities.items():
                advancement_counts[cut_size][player_id] += probability
        ranked = sort_standings_rows(state)
        if 0 < spec.top_cut <= len(ranked):
            top_cut_line_point_counts[ranked[spec.top_cut - 1].points] += 1
        bye_rank = topdeck_bye_rank(spec.top_cut)
        if bye_rank is not None and bye_rank <= len(ranked):
            bye_line_point_counts[ranked[bye_rank - 1].points] += 1
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
        top_cut_line_point_counts=dict(top_cut_line_point_counts),
        bye_line_point_counts=dict(bye_line_point_counts),
    )


def _run_state_monte_carlo_batch(
    base_state: TournamentState,
    draw_model: LoadedDrawModel,
    winner_model: LoadedCandidateWinnerModel | None,
    simulations: int,
    seed: int,
    start_round_index: int,
    locked_round_pods: list[Pod] | None,
    locked_round_draw_probabilities: dict[tuple[int, int], float] | None,
    locked_round_win_probabilities: dict[tuple[int, int], tuple[float, ...]] | None,
    requested_advancement_sizes: tuple[int, ...] | None,
    collect_detailed_metrics: bool,
    collect_player_metrics: bool,
) -> SimulationSummary:
    win_counts: dict[str, int] = defaultdict(int)
    top_cut_counts: dict[str, int] = defaultdict(int)
    advancement_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    expected_points_total: dict[str, float] = defaultdict(float)
    expected_finish_total: dict[str, float] = defaultdict(float)
    round_draw_counts: dict[int, int] = defaultdict(int)
    round_pod_counts: dict[int, int] = defaultdict(int)
    top_cut_line_point_counts: dict[int, int] = defaultdict(int)
    bye_line_point_counts: dict[int, int] = defaultdict(int)
    for simulation_index in range(simulations):
        state = clone_state(base_state)
        state, winner_probabilities, top_cut, advancement_probabilities = simulate_from_state(
            state,
            draw_model,
            seed=seed + simulation_index,
            winner_model=winner_model,
            start_round_index=start_round_index,
            locked_round_pods=locked_round_pods,
            locked_round_draw_probabilities=locked_round_draw_probabilities,
            locked_round_win_probabilities=locked_round_win_probabilities,
        )
        for player_id, probability in winner_probabilities.items():
            win_counts[player_id] += probability
        for player_id in top_cut:
            top_cut_counts[player_id] += 1
        if requested_advancement_sizes:
            for cut_size in requested_advancement_sizes:
                for player_id, probability in advancement_probabilities.get(cut_size, {}).items():
                    advancement_counts[cut_size][player_id] += probability
        if collect_detailed_metrics:
            ranked = sort_standings_rows(state)
            if 0 < state.spec.top_cut <= len(ranked):
                top_cut_line_point_counts[ranked[state.spec.top_cut - 1].points] += 1
            bye_rank = topdeck_bye_rank(state.spec.top_cut)
            if bye_rank is not None and bye_rank <= len(ranked):
                bye_line_point_counts[ranked[bye_rank - 1].points] += 1
            if collect_player_metrics:
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
        top_cut_line_point_counts=dict(top_cut_line_point_counts),
        bye_line_point_counts=dict(bye_line_point_counts),
    )


def _merge_summaries(summaries: list[SimulationSummary]) -> SimulationSummary:
    win_counts: dict[str, int] = defaultdict(int)
    top_cut_counts: dict[str, int] = defaultdict(int)
    advancement_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    expected_points_total: dict[str, float] = defaultdict(float)
    expected_finish_total: dict[str, float] = defaultdict(float)
    round_draw_counts: dict[int, int] = defaultdict(int)
    round_pod_counts: dict[int, int] = defaultdict(int)
    top_cut_line_point_counts: dict[int, int] = defaultdict(int)
    bye_line_point_counts: dict[int, int] = defaultdict(int)
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
        for points, count in summary.top_cut_line_point_counts.items():
            top_cut_line_point_counts[points] += count
        for points, count in summary.bye_line_point_counts.items():
            bye_line_point_counts[points] += count

    return SimulationSummary(
        win_counts=dict(win_counts),
        top_cut_counts=dict(top_cut_counts),
        advancement_counts={cut_size: dict(player_counts) for cut_size, player_counts in advancement_counts.items()},
        expected_points_total=dict(expected_points_total),
        expected_finish_total=dict(expected_finish_total),
        round_draw_counts=dict(round_draw_counts),
        round_pod_counts=dict(round_pod_counts),
        simulations=total_simulations,
        top_cut_line_point_counts=dict(top_cut_line_point_counts),
        bye_line_point_counts=dict(bye_line_point_counts),
    )


def run_monte_carlo(
    spec: TournamentSpec,
    entrants: list[SimPlayer],
    draw_model: LoadedDrawModel,
    *,
    simulations: int = 10_000,
    seed: int = 1,
    feature_context=None,
    winner_model: LoadedCandidateWinnerModel | None = None,
    workers: int | None = None,
) -> SimulationSummary:
    effective_workers = workers if workers is not None else max(1, min(4, os.cpu_count() or 1))
    if effective_workers <= 1 or simulations <= 1:
        return _run_monte_carlo_batch(
            spec,
            entrants,
            draw_model,
            winner_model,
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
                [winner_model] * len(batch_specs),
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
    winner_model: LoadedCandidateWinnerModel | None = None,
    workers: int | None = None,
    start_round_index: int | None = None,
    locked_round_pods: list[Pod] | None = None,
    requested_advancement_sizes: tuple[int, ...] | None = None,
    collect_detailed_metrics: bool = True,
    collect_player_metrics: bool = True,
) -> SimulationSummary:
    effective_workers = workers if workers is not None else max(1, min(4, os.cpu_count() or 1))
    effective_start_round = base_state.current_round_index if start_round_index is None else start_round_index
    locked_round_draw_probabilities: dict[tuple[int, int], float] | None = None
    locked_round_win_probabilities: dict[tuple[int, int], tuple[float, ...]] | None = None
    if locked_round_pods is not None:
        context = build_tournament_context(base_state.spec)
        round_snapshot = build_round_snapshot(base_state, context, effective_start_round + 1)
        locked_round_draw_probabilities, locked_round_win_probabilities = predict_pod_outcome_probabilities(
            locked_round_pods,
            base_state,
            context,
            draw_model,
            round_snapshot,
            winner_model,
        )
    if effective_workers <= 1 or simulations <= 1:
        return _run_state_monte_carlo_batch(
            base_state,
            draw_model,
            winner_model,
            simulations=simulations,
            seed=seed,
            start_round_index=effective_start_round,
            locked_round_pods=locked_round_pods,
            locked_round_draw_probabilities=locked_round_draw_probabilities,
            locked_round_win_probabilities=locked_round_win_probabilities,
            requested_advancement_sizes=requested_advancement_sizes,
            collect_detailed_metrics=collect_detailed_metrics,
            collect_player_metrics=collect_player_metrics,
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
                [winner_model] * len(batch_specs),
                [simulation_count for simulation_count, _ in batch_specs],
                [batch_seed for _, batch_seed in batch_specs],
                [effective_start_round] * len(batch_specs),
                [locked_round_pods] * len(batch_specs),
                [locked_round_draw_probabilities] * len(batch_specs),
                [locked_round_win_probabilities] * len(batch_specs),
                [requested_advancement_sizes] * len(batch_specs),
                [collect_detailed_metrics] * len(batch_specs),
                [collect_player_metrics] * len(batch_specs),
            )
        )
    return _merge_summaries(summaries)
