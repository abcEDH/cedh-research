#!/usr/bin/env python3
"""Swiss pairing and top-cut helpers for tournament simulation."""

from __future__ import annotations

import random
from collections import defaultdict

from sim_types import Pod, StandingRow, TournamentState


def match_win_percentage(state: TournamentState, player_id: str) -> float:
    standing = state.standings[player_id]
    if standing.pods_played <= 0:
        return 0.0
    return max(standing.wins / float(standing.pods_played), 0.20)


def opponent_match_win_percentage(state: TournamentState, player_id: str) -> float:
    standing = state.standings[player_id]
    synthetic_opp_count = standing.bye_count * 3
    real_opp_count = len(standing.opponents)
    total_opp_count = real_opp_count + synthetic_opp_count
    if total_opp_count <= 0:
        return 0.0
    total = sum(match_win_percentage(state, opponent_id) for opponent_id in standing.opponents)
    total += synthetic_opp_count * 0.20
    return total / total_opp_count


def standings_sort_key(state: TournamentState, player_id: str) -> tuple[float, float, int, str]:
    standing = state.standings[player_id]
    return (
        -float(standing.points),
        -opponent_match_win_percentage(state, player_id),
        state.players[player_id].tiebreak_seed,
        player_id,
    )


def sort_standings_rows(state: TournamentState) -> list[StandingRow]:
    return sorted(
        state.standings.values(),
        key=lambda row: standings_sort_key(state, row.player_id),
    )


def _sorted_players_for_pairing(state: TournamentState, player_ids: list[str]) -> list[str]:
    return sorted(player_ids, key=lambda player_id: standings_sort_key(state, player_id))


def _pair_meeting_count(state: TournamentState, player_a: str, player_b: str) -> int:
    pair = tuple(sorted((player_a, player_b)))
    return state.feature_context.tournament_pair_meetings.get(pair, 0)


def _pod_repeat_penalty(state: TournamentState, pod_players: list[str]) -> int:
    penalty = 0
    for index, player_id in enumerate(pod_players):
        for opponent_id in pod_players[index + 1 :]:
            meetings = _pair_meeting_count(state, player_id, opponent_id)
            penalty += meetings * meetings
    return penalty


def _build_initial_pods_from_pool(pool: list[str], pod_size: int) -> list[list[str]]:
    pods: list[list[str]] = []
    for index in range(0, len(pool), pod_size):
        chunk = pool[index : index + pod_size]
        if len(chunk) >= 1:
            pods.append(chunk)
    return pods


def _normalize_trailing_pods(pod_groups: list[list[str]]) -> list[list[str]]:
    """Convert odd trailing player counts into explicit bye / 3-pod layouts.

    Desired behavior:
    - 4n + 1 players -> one 1-player bye chunk
    - 4n + 2 players -> two 3-player chunks
    - 4n + 3 players -> one 3-player chunk
    """
    if not pod_groups:
        return pod_groups

    last_chunk = pod_groups[-1]
    if len(last_chunk) == 2 and len(pod_groups) >= 2 and len(pod_groups[-2]) >= 4:
        donor = pod_groups[-2]
        last_chunk.insert(0, donor.pop())
    return pod_groups


def _optimize_pods_for_repeats(state: TournamentState, pods: list[list[str]]) -> list[list[str]]:
    if len(pods) <= 1:
        return pods
    improved = True
    while improved:
        improved = False
        for left_index in range(len(pods)):
            for right_index in range(left_index + 1, len(pods)):
                left_pod = pods[left_index]
                right_pod = pods[right_index]
                left_penalty = _pod_repeat_penalty(state, left_pod)
                right_penalty = _pod_repeat_penalty(state, right_pod)
                baseline = left_penalty + right_penalty
                best_swap: tuple[int, int] | None = None
                best_penalty = baseline
                for i, left_player in enumerate(left_pod):
                    for j, right_player in enumerate(right_pod):
                        swapped_left = left_pod[:]
                        swapped_right = right_pod[:]
                        swapped_left[i] = right_player
                        swapped_right[j] = left_player
                        candidate_penalty = _pod_repeat_penalty(state, swapped_left) + _pod_repeat_penalty(state, swapped_right)
                        if candidate_penalty < best_penalty:
                            best_penalty = candidate_penalty
                            best_swap = (i, j)
                if best_swap is not None:
                    i, j = best_swap
                    left_pod[i], right_pod[j] = right_pod[j], left_pod[i]
                    improved = True
    return pods


def _pods_from_brackets(
    state: TournamentState,
    grouped: dict[int, list[str]],
    pod_size: int,
) -> list[list[str]]:
    point_values = sorted(grouped.keys(), reverse=True)
    carry_down: list[str] = []
    pod_groups: list[list[str]] = []

    for bracket_index, points in enumerate(point_values):
        bucket = _sorted_players_for_pairing(state, grouped[points])
        pool = carry_down + bucket
        carry_down = []
        is_last_bracket = bracket_index == len(point_values) - 1
        if not is_last_bracket:
            remainder = len(pool) % pod_size
            if remainder:
                carry_count = remainder
                carry_down = pool[-carry_count:]
                pool = pool[:-carry_count]
        if pool:
            pod_groups.extend(_build_initial_pods_from_pool(pool, pod_size))

    if carry_down:
        pod_groups.extend(_build_initial_pods_from_pool(carry_down, pod_size))
    pod_groups = _normalize_trailing_pods(pod_groups)
    return _optimize_pods_for_repeats(state, pod_groups)


def pair_swiss_round(state: TournamentState, round_index: int, rng: random.Random) -> list[Pod]:
    grouped: dict[int, list[str]] = defaultdict(list)
    for player_id, standing in state.standings.items():
        grouped[standing.points].append(player_id)

    pod_size = state.spec.pod_size
    pod_groups = _pods_from_brackets(state, grouped, pod_size)
    pods: list[Pod] = []
    for index, pod_players in enumerate(pod_groups, start=1):
        pod_players = _sorted_players_for_pairing(state, pod_players)
        if len(pod_players) < 1:
            continue
        seats_by_player = {player_id: seat for seat, player_id in enumerate(pod_players, start=1)}
        pods.append(
            Pod(
                round_index=round_index,
                table_number=index,
                player_ids=pod_players,
                round_name=f"Round {round_index + 1}",
                seats_by_player=seats_by_player,
            )
        )
    return pods


def select_top_cut(state: TournamentState) -> list[str]:
    rows = sort_standings_rows(state)
    return [row.player_id for row in rows[: state.spec.top_cut]]


def pair_bracket(players: list[str], round_index: int, pod_size: int) -> list[Pod]:
    pods: list[Pod] = []
    for index in range(0, len(players), pod_size):
        pod_players = players[index : index + pod_size]
        if len(pod_players) < 2:
            continue
        pods.append(
            Pod(
                round_index=round_index,
                table_number=(index // pod_size) + 1,
                player_ids=pod_players,
                round_name=f"Top {len(players)}" if len(players) > pod_size else "Finals",
                seats_by_player={player_id: seat for seat, player_id in enumerate(pod_players, start=1)},
            )
        )
    return pods


def pair_topdeck_bracket(players: list[str], round_index: int) -> tuple[list[str], list[Pod]]:
    auto_advancers: list[str] = []
    pod_groups: list[list[str]]

    if len(players) == 40:
        auto_advancers = players[:8]
        play_in = players[8:]
        pod_groups = [
            [play_in[0], play_in[15], play_in[16], play_in[31]],
            [play_in[1], play_in[14], play_in[17], play_in[30]],
            [play_in[2], play_in[13], play_in[18], play_in[29]],
            [play_in[3], play_in[12], play_in[19], play_in[28]],
            [play_in[4], play_in[11], play_in[20], play_in[27]],
            [play_in[5], play_in[10], play_in[21], play_in[26]],
            [play_in[6], play_in[9], play_in[22], play_in[25]],
            [play_in[7], play_in[8], play_in[23], play_in[24]],
        ]
    elif len(players) == 16:
        pod_groups = [
            [players[0], players[7], players[8], players[15]],
            [players[1], players[6], players[9], players[14]],
            [players[2], players[5], players[10], players[13]],
            [players[3], players[4], players[11], players[12]],
        ]
    elif len(players) == 10:
        auto_advancers = [players[0], players[1]]
        pod_groups = [
            [players[2], players[5], players[6], players[9]],
            [players[3], players[4], players[7], players[8]],
        ]
    else:
        pod_groups = [players[index : index + 4] for index in range(0, len(players), 4)]

    pods: list[Pod] = []
    for table_number, pod_players in enumerate(pod_groups, start=1):
        if len(pod_players) < 2:
            continue
        pods.append(
            Pod(
                round_index=round_index,
                table_number=table_number,
                player_ids=pod_players,
                round_name=f"Top {len(players)}" if len(players) > 4 else "Finals",
                seats_by_player={player_id: seat for seat, player_id in enumerate(pod_players, start=1)},
            )
        )
    return auto_advancers, pods
