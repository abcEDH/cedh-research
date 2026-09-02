#!/usr/bin/env python3
"""Swiss pairing and top-cut helpers for tournament simulation."""

from __future__ import annotations

import random
from collections import defaultdict

from sim_types import Pod, StandingRow, TournamentState


def match_point_percentage(state: TournamentState, player_id: str) -> float:
    standing = state.standings[player_id]
    if standing.pods_played <= 0:
        return 0.0
    return max(standing.points / float(standing.pods_played * 5), 0.20)


def match_win_percentage(state: TournamentState, player_id: str) -> float:
    return match_point_percentage(state, player_id)


def opponent_match_win_percentage(state: TournamentState, player_id: str) -> float:
    standing = state.standings[player_id]
    synthetic_opp_count = standing.bye_count * 3
    real_opp_count = len(standing.opponents)
    total_opp_count = real_opp_count + synthetic_opp_count
    if total_opp_count <= 0:
        return 0.0
    total = sum(match_point_percentage(state, opponent_id) for opponent_id in sorted(standing.opponents))
    total += synthetic_opp_count * 0.20
    return total / total_opp_count


def assign_standings_random_tiebreakers(state: TournamentState, rng: random.Random) -> None:
    eligible_player_ids = state.eligible_player_ids
    player_ids = (
        player_id
        for player_id in sorted(state.standings)
        if eligible_player_ids is None or player_id in eligible_player_ids
    )
    for player_id in player_ids:
        state.standings_random_tiebreakers.setdefault(player_id, rng.random())


def standings_sort_key(state: TournamentState, player_id: str) -> tuple[float, float, int, float, str]:
    standing = state.standings[player_id]
    return (
        -float(standing.points),
        -opponent_match_win_percentage(state, player_id),
        state.players[player_id].tiebreak_seed,
        state.standings_random_tiebreakers.get(player_id, 0.0),
        player_id,
    )


def sort_standings_rows(state: TournamentState, rng: random.Random | None = None) -> list[StandingRow]:
    if rng is not None:
        assign_standings_random_tiebreakers(state, rng)
    eligible_player_ids = state.eligible_player_ids
    return sorted(
        (
            row
            for row in state.standings.values()
            if eligible_player_ids is None or row.player_id in eligible_player_ids
        ),
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


def _topdeck_pod_sizes(player_count: int, pod_size: int) -> list[int]:
    if player_count <= 0:
        return []
    if pod_size != 4:
        return [min(pod_size, player_count - index) for index in range(0, player_count, pod_size)]

    full_pods, remainder = divmod(player_count, pod_size)
    if remainder == 0:
        return [4] * full_pods
    if remainder == 1 and full_pods >= 2:
        return [4] * (full_pods - 2) + [3, 3, 3]
    if remainder == 2 and full_pods >= 1:
        return [4] * (full_pods - 1) + [3, 3]
    if remainder == 3:
        return [4] * full_pods + [3]
    return [player_count]


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
    grouped: dict[tuple[int, int, int, int], list[str]],
    pod_size: int,
    rng: random.Random,
) -> list[list[str]]:
    ordered_players: list[str] = []
    for record in sorted(grouped.keys(), reverse=True):
        bucket = grouped[record][:]
        rng.shuffle(bucket)
        ordered_players.extend(bucket)

    pod_groups: list[list[str]] = []
    start = 0
    for size in _topdeck_pod_sizes(len(ordered_players), pod_size):
        pod_groups.append(ordered_players[start : start + size])
        start += size

    repeat_avoidance_max_pods = state.spec.repeat_avoidance_max_pods
    if (
        repeat_avoidance_max_pods is not None
        and repeat_avoidance_max_pods > 0
        and len(pod_groups) <= repeat_avoidance_max_pods
    ):
        return _optimize_pods_for_repeats(state, pod_groups)
    return pod_groups


def pair_swiss_round(state: TournamentState, round_index: int, rng: random.Random) -> list[Pod]:
    grouped: dict[tuple[int, int, int, int], list[str]] = defaultdict(list)
    eligible_player_ids = state.eligible_player_ids
    for player_id, standing in state.standings.items():
        if eligible_player_ids is not None and player_id not in eligible_player_ids:
            continue
        grouped[(standing.points, standing.wins, standing.draws, -standing.losses)].append(player_id)

    pod_size = state.spec.pod_size
    pod_groups = _pods_from_brackets(state, grouped, pod_size, rng)
    pods: list[Pod] = []
    for index, pod_players in enumerate(pod_groups, start=1):
        if len(pod_players) < 1:
            continue
        seated_players = pod_players[:]
        rng.shuffle(seated_players)
        seats_by_player = {player_id: seat for seat, player_id in enumerate(seated_players, start=1)}
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


def select_top_cut(state: TournamentState, rng: random.Random | None = None) -> list[str]:
    rows = sort_standings_rows(state, rng=rng)
    return [row.player_id for row in rows[: state.spec.top_cut]]


def topdeck_bye_rank(cut_size: int) -> int | None:
    if cut_size == 40:
        return 8
    if cut_size == 10:
        return 2
    return None


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

    if len(players) == 64:
        pod_groups = [
            [players[index], players[31 - index], players[32 + index], players[63 - index]]
            for index in range(16)
        ]
    elif len(players) == 40:
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
