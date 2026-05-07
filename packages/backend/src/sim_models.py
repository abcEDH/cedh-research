#!/usr/bin/env python3
"""Model loading and pod-level inference for tournament simulation."""

from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from sim_pairings import opponent_match_win_percentage
from sim_types import ALL_DRAW_FEATURES, FeatureContext, Pod, RoundFeatureSnapshot, TournamentContext, TournamentState

ELO_BASE = 2.0
ELO_DIVISOR = 200.0
DEFAULT_COMMANDER_ELO = 1500.0
COMMANDER_ELO_ALPHA = 0.0
DEFAULT_DRAW_MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "draw_model_artifact.pkl"
SEAT_ELO_BONUS = {
    1: 0.0,
    2: -52.0,
    3: -96.0,
    4: -145.0,
}


@dataclass(slots=True)
class LoadedDrawModel:
    features: list[str]
    model: Any
    calibration: str
    calibrator: Any | None = None
    feature_indexes: np.ndarray | None = None


def normalize_series_key(name: str | None) -> str:
    if not name:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()
    normalized = re.sub(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b",
        " ",
        normalized,
    )
    normalized = re.sub(r"\b20\d{2}\b", " ", normalized)
    normalized = re.sub(r"\b\d{1,2}(st|nd|rd|th)?\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or "unknown_series"


def gini(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(float(value) for value in values)
    total = sum(sorted_values)
    if total <= 0:
        return 0.0
    n = len(sorted_values)
    cumulative = sum((2 * index - n - 1) * value for index, value in enumerate(sorted_values, start=1))
    return cumulative / (n * total)


def small_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def small_median(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    size = len(sorted_values)
    midpoint = size // 2
    if size % 2 == 1:
        return float(sorted_values[midpoint])
    return float((sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2.0)


def small_std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = small_mean(values)
    variance = sum((value - mean) * (value - mean) for value in values) / len(values)
    return variance**0.5


def load_draw_model_artifact(path: Path | str = DEFAULT_DRAW_MODEL_PATH) -> LoadedDrawModel:
    with Path(path).open("rb") as handle:
        artifact = pickle.load(handle)
    selection = artifact["selection"]
    feature_indexes = np.asarray([ALL_DRAW_FEATURES.index(feature) for feature in selection["features"]], dtype=int)
    return LoadedDrawModel(
        features=list(selection["features"]),
        model=artifact["model"],
        calibration=str(artifact.get("calibration") or "uncalibrated"),
        calibrator=artifact.get("calibrator"),
        feature_indexes=feature_indexes,
    )


def rating_equity(rating: float) -> float:
    return pow(ELO_BASE, rating / ELO_DIVISOR)


def effective_player_rating(player, seat: int | None = None) -> float:
    rating = float(player.elo)
    if player.commander_id and getattr(player, "commander_known", False):
        rating += COMMANDER_ELO_ALPHA * (float(player.commander_elo) - DEFAULT_COMMANDER_ELO)
    if seat in SEAT_ELO_BONUS:
        rating += SEAT_ELO_BONUS[seat]
    return rating


def _points_percentiles(points_by_player: dict[str, int]) -> dict[str, float]:
    players = list(points_by_player)
    field_size = max(1, len(players))
    ranked_points = sorted(points_by_player.values(), reverse=True)
    if field_size <= 1:
        return {player_id: 1.0 for player_id in players}
    by_points: dict[int, list[int]] = {}
    for index, points in enumerate(ranked_points):
        by_points.setdefault(points, []).append(index)
    percentile_by_points: dict[int, float] = {}
    for points, indexes in by_points.items():
        avg_rank = (indexes[0] + indexes[-1]) / 2.0
        percentile_by_points[points] = 1.0 - (avg_rank / (field_size - 1))
    return {
        player_id: percentile_by_points.get(points_by_player[player_id], 0.5)
        for player_id in players
    }


def _hypothetical_rank_by_player(
    player_ids: list[str],
    *,
    points_by_player: dict[str, int],
    estimated_omw_by_player: dict[str, float],
    tiebreak_seed_by_player: dict[str, int],
    point_delta: int,
) -> dict[str, int]:
    ranks: dict[str, int] = {}
    fallback_seed = len(player_ids) + 1_000_000
    for player_id in player_ids:
        target_points = points_by_player.get(player_id, 0) + point_delta
        target_omw = estimated_omw_by_player.get(player_id, 0.0)
        target_seed = tiebreak_seed_by_player.get(player_id, fallback_seed)
        better = 0
        for opponent_id in player_ids:
            if opponent_id == player_id:
                continue
            opponent_points = points_by_player.get(opponent_id, 0)
            opponent_omw = estimated_omw_by_player.get(opponent_id, 0.0)
            opponent_seed = tiebreak_seed_by_player.get(opponent_id, fallback_seed)
            if (
                opponent_points > target_points
                or (
                    opponent_points == target_points
                    and (
                        opponent_omw > target_omw
                        or (
                            opponent_omw == target_omw
                            and (
                                opponent_seed < target_seed
                                or (opponent_seed == target_seed and opponent_id < player_id)
                            )
                        )
                    )
                )
            ):
                better += 1
        ranks[player_id] = better + 1
    return ranks


def build_round_snapshot(
    state: TournamentState,
    context: TournamentContext,
    round_number: int,
) -> RoundFeatureSnapshot:
    max_rounds = max(1, context.max_rounds)
    swiss_progress = (round_number - 1) / (max_rounds - 1) if max_rounds > 1 else 0.0
    rounds_remaining = max(0, max_rounds - round_number)
    field_size = max(1, len(state.players))
    cut_fraction = min(1.0, context.top_cut / field_size) if context.top_cut > 0 else 0.0
    cut_size_bucket = (
        0 if context.top_cut <= 0 else 1 if context.top_cut <= 4 else 2 if context.top_cut <= 8 else 3 if context.top_cut <= 16 else 4 if context.top_cut <= 32 else 5
    )
    points_by_player = {player_id: state.standings[player_id].points for player_id in state.players}
    point_percentiles = _points_percentiles(points_by_player)
    sorted_point_values = sorted(points_by_player.values(), reverse=True)
    cut_rank_index = min(max(context.top_cut - 1, 0), max(len(sorted_point_values) - 1, 0)) if sorted_point_values else 0
    cut_line_points = sorted_point_values[cut_rank_index] if sorted_point_values and context.top_cut > 0 else 0
    feature_context = state.feature_context
    history_point_expectations = []
    for player_id in state.players:
        history = feature_context.player_history.get(player_id)
        if history is None:
            history_point_expectations.append(0.0)
            continue
        history_point_expectations.append((5.0 * history.win_rate) + history.draw_rate)
    fallback_round_points = small_mean(history_point_expectations) if history_point_expectations else 1.25
    projected_final_points: list[float] = []
    for player_id, current_points in points_by_player.items():
        history = feature_context.player_history.get(player_id)
        expected_round_points = (5.0 * history.win_rate) + history.draw_rate if history is not None else fallback_round_points
        expected_round_points = max(0.0, min(5.0, expected_round_points))
        projected_final_points.append(current_points + (rounds_remaining * expected_round_points))
    projected_final_points.sort(reverse=True)
    expected_cut_line_points = (
        projected_final_points[cut_rank_index] if projected_final_points and context.top_cut > 0 else float(cut_line_points)
    )
    month = context_top_month(context)
    quarter = (month - 1) // 3 + 1
    tournament_size = context_top_size(context, field_size)
    size_bucket = 0 if tournament_size < 32 else 1 if tournament_size < 64 else 2 if tournament_size < 128 else 3
    cut_line_percentile = 1.0 - cut_fraction if cut_fraction > 0 else 1.0
    bubble_margin = max(0.02, 1.0 / field_size)
    max_future_points = rounds_remaining * 5
    estimated_omw_by_player = {
        player_id: opponent_match_win_percentage(state, player_id) for player_id in state.players
    }
    tiebreak_seed_by_player = {
        player_id: state.players[player_id].tiebreak_seed for player_id in state.players
    }
    same_points_omw_percentile_by_player: dict[str, float] = {}
    players_by_points: dict[int, list[str]] = {}
    for player_id, points in points_by_player.items():
        players_by_points.setdefault(points, []).append(player_id)
    for cohort in players_by_points.values():
        if len(cohort) <= 1:
            for player_id in cohort:
                same_points_omw_percentile_by_player[player_id] = 1.0
            continue
        ordered = sorted(cohort, key=lambda player_id: estimated_omw_by_player[player_id], reverse=True)
        size = len(ordered)
        for index, player_id in enumerate(ordered):
            same_points_omw_percentile_by_player[player_id] = 1.0 - (index / (size - 1))
    ordered_players = sorted(
        state.players,
        key=lambda player_id: (
            -points_by_player[player_id],
            -estimated_omw_by_player[player_id],
            state.players[player_id].tiebreak_seed,
            player_id,
        ),
    )
    current_rank_by_player = {player_id: index + 1 for index, player_id in enumerate(ordered_players)}
    draw_secure_rank_by_player = _hypothetical_rank_by_player(
        ordered_players,
        points_by_player=points_by_player,
        estimated_omw_by_player=estimated_omw_by_player,
        tiebreak_seed_by_player=tiebreak_seed_by_player,
        point_delta=1,
    )
    win_secure_rank_by_player = _hypothetical_rank_by_player(
        ordered_players,
        points_by_player=points_by_player,
        estimated_omw_by_player=estimated_omw_by_player,
        tiebreak_seed_by_player=tiebreak_seed_by_player,
        point_delta=5,
    )
    return RoundFeatureSnapshot(
        round_number=round_number,
        swiss_progress=swiss_progress,
        rounds_remaining=rounds_remaining,
        month=month,
        quarter=quarter,
        tournament_size=tournament_size,
        size_bucket=size_bucket,
        field_size=field_size,
        cut_fraction=cut_fraction,
        cut_size_bucket=cut_size_bucket,
        cut_line_percentile=cut_line_percentile,
        cut_line_points=cut_line_points,
        expected_cut_line_points=expected_cut_line_points,
        max_future_points=max_future_points,
        bubble_margin=bubble_margin,
        points_by_player=points_by_player,
        point_percentiles=point_percentiles,
        estimated_omw_by_player=estimated_omw_by_player,
        same_points_omw_percentile_by_player=same_points_omw_percentile_by_player,
        current_rank_by_player=current_rank_by_player,
        draw_secure_rank_by_player=draw_secure_rank_by_player,
        win_secure_rank_by_player=win_secure_rank_by_player,
    )


def build_draw_feature_row(
    pod: Pod,
    state: TournamentState,
    context: TournamentContext,
    round_snapshot: RoundFeatureSnapshot,
) -> np.ndarray:
    player_ids = pod.player_ids
    ratings = [state.players[player_id].elo for player_id in player_ids]
    sorted_ratings = sorted(ratings, reverse=True)
    mean_elo = small_mean(ratings)
    median_elo = small_median(ratings)
    top2_mean_elo = sum(sorted_ratings[:2]) / min(2, len(sorted_ratings))
    top3_mean_elo = sum(sorted_ratings[:3]) / min(3, len(sorted_ratings))
    top1_minus_top2 = sorted_ratings[0] - sorted_ratings[1] if len(sorted_ratings) > 1 else 0.0
    elo_std = small_std(ratings)
    elo_gini = gini(ratings)
    high_thresholds = {
        "high1550": sum(1 for rating in ratings if rating >= 1550),
        "high1600": sum(1 for rating in ratings if rating >= 1600),
        "high1650": sum(1 for rating in ratings if rating >= 1650),
        "high1700": sum(1 for rating in ratings if rating >= 1700),
        "high1800": sum(1 for rating in ratings if rating >= 1800),
    }
    seat_highest = -1
    seat_second = -1
    top2_adjacent = 0
    if pod.seats_by_player:
        sorted_players = sorted(player_ids, key=lambda player_id: state.players[player_id].elo, reverse=True)
        seat_highest = pod.seats_by_player.get(sorted_players[0], -1)
        seat_second = pod.seats_by_player.get(sorted_players[1], -1) if len(sorted_players) > 1 else seat_highest
        if seat_highest >= 0 and seat_second >= 0 and len(player_ids) == 4:
            seat_gap = abs(seat_highest - seat_second)
            top2_adjacent = 1 if seat_gap in (1, 3) else 0

    round_number = round_snapshot.round_number
    pod_points = [round_snapshot.points_by_player[player_id] for player_id in player_ids]
    pod_percentiles = [round_snapshot.point_percentiles[player_id] for player_id in player_ids]
    pod_estimated_omw = [round_snapshot.estimated_omw_by_player[player_id] for player_id in player_ids]
    pod_same_points_omw_percentiles = [
        round_snapshot.same_points_omw_percentile_by_player[player_id] for player_id in player_ids
    ]
    pod_current_ranks = [round_snapshot.current_rank_by_player[player_id] for player_id in player_ids]
    pod_draw_secure_ranks = [round_snapshot.draw_secure_rank_by_player[player_id] for player_id in player_ids]
    pod_win_secure_ranks = [round_snapshot.win_secure_rank_by_player[player_id] for player_id in player_ids]
    cut_line_percentile = round_snapshot.cut_line_percentile
    cut_margins = [percentile - cut_line_percentile for percentile in pod_percentiles]
    points_to_current_cut = [float(points - round_snapshot.cut_line_points) for points in pod_points]
    points_to_cut = [float(points - round_snapshot.expected_cut_line_points) for points in pod_points]
    max_future_points = round_snapshot.max_future_points
    count_locked_for_current_cut = sum(1 for points in pod_points if points > round_snapshot.cut_line_points + max_future_points)
    count_dead_for_current_cut = sum(1 for points in pod_points if points + max_future_points < round_snapshot.cut_line_points)
    count_draw_safe_for_current_cut = sum(1 for points in pod_points if points + 1 >= round_snapshot.cut_line_points)
    count_must_win_for_current_cut = sum(
        1 for points in pod_points if (points + 1 < round_snapshot.cut_line_points and points + 5 >= round_snapshot.cut_line_points)
    )
    all_players_draw_safe_for_current_cut = 1 if pod_points and count_draw_safe_for_current_cut == len(pod_points) else 0
    count_locked_for_cut = sum(1 for points in pod_points if points > round_snapshot.expected_cut_line_points + max_future_points)
    count_dead_for_cut = sum(1 for points in pod_points if points + max_future_points < round_snapshot.expected_cut_line_points)
    count_live_for_cut = len(pod_points) - count_locked_for_cut - count_dead_for_cut
    count_draw_safe_for_cut = sum(1 for points in pod_points if points + 1 >= round_snapshot.expected_cut_line_points)
    count_must_win_for_cut = sum(
        1
        for points in pod_points
        if (points + 1 < round_snapshot.expected_cut_line_points and points + 5 >= round_snapshot.expected_cut_line_points)
    )
    all_players_draw_safe = 1 if pod_points and count_draw_safe_for_cut == len(pod_points) else 0
    count_currently_in_cut = sum(1 for rank in pod_current_ranks if rank <= context.top_cut) if context.top_cut > 0 else 0
    count_currently_outside_cut = len(pod_current_ranks) - count_currently_in_cut
    count_players_currently_safe = count_locked_for_cut
    count_players_currently_dead = count_dead_for_cut
    all_players_live = 1 if player_ids and count_live_for_cut == len(player_ids) else 0
    count_draw_secures_cut = sum(1 for rank in pod_draw_secure_ranks if rank <= context.top_cut) if context.top_cut > 0 else 0
    count_win_secures_cut = sum(1 for rank in pod_win_secure_ranks if rank <= context.top_cut) if context.top_cut > 0 else 0
    count_must_win_to_stay_live = (
        sum(
            1
            for current_rank, draw_rank, win_rank in zip(
                pod_current_ranks,
                pod_draw_secure_ranks,
                pod_win_secure_ranks,
                strict=True,
            )
            if current_rank > context.top_cut and draw_rank > context.top_cut and win_rank <= context.top_cut
        )
        if context.top_cut > 0
        else 0
    )
    all_players_draw_secures_cut = 1 if player_ids and count_draw_secures_cut == len(player_ids) else 0
    mixed_pod_cut_incentives = (
        1
        if context.top_cut > 0
        and count_draw_secures_cut > 0
        and count_draw_secures_cut < len(player_ids)
        and count_must_win_to_stay_live > 0
        else 0
    )
    some_locked_some_must_win = 1 if count_locked_for_cut > 0 and count_must_win_to_stay_live > 0 else 0
    rank_minus_cut = [float(rank - context.top_cut) for rank in pod_current_ranks] if context.top_cut > 0 else [0.0 for _ in pod_current_ranks]
    draw_secure_rank_delta = [float(current - draw_rank) for current, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True)]
    win_secure_rank_delta = [float(current - win_rank) for current, win_rank in zip(pod_current_ranks, pod_win_secure_ranks, strict=True)]
    count_bottom_quartile_omw_in_same_points_group = sum(1 for value in pod_same_points_omw_percentiles if value <= 0.25)
    count_players_near_cut_band = sum(1 for rank in pod_current_ranks if context.top_cut > 0 and abs(rank - context.top_cut) <= 4)
    is_last_swiss_round = 1 if round_snapshot.rounds_remaining == 0 else 0
    is_penultimate_swiss_round = 1 if round_snapshot.rounds_remaining == 1 else 0
    bubble_margin = round_snapshot.bubble_margin

    feature_context: FeatureContext = state.feature_context
    player_histories = [feature_context.player_history.get(player_id) for player_id in player_ids]
    draw_rates = [history.draw_rate if history else 0.0 for history in player_histories]
    win_rates = [history.win_rate if history else 0.0 for history in player_histories]
    decisive_rates = [history.decisive_rate if history else 0.0 for history in player_histories]
    count_high_draw_players = sum(1 for rate in draw_rates if rate >= 0.25)
    count_high_win_low_draw_players = sum(1 for win_rate, draw_rate in zip(win_rates, draw_rates, strict=True) if win_rate >= 0.35 and draw_rate <= 0.10)
    draw_rate_range_above_threshold = 1 if draw_rates and (max(draw_rates) - min(draw_rates)) >= 0.15 else 0

    tournament_pair_counts = []
    global_pair_counts = []
    for index, player_id in enumerate(player_ids):
        for opponent_id in player_ids[index + 1 :]:
            pair = tuple(sorted((player_id, opponent_id)))
            tournament_pair_counts.append(feature_context.tournament_pair_meetings.get(pair, 0))
            global_pair_counts.append(feature_context.global_pair_meetings.get(pair, 0))

    return np.asarray(
        [
            1.0,
            float(len(player_ids)),
            max(ratings) - min(ratings),
            mean_elo,
            median_elo,
            top2_mean_elo,
            top3_mean_elo,
            top1_minus_top2,
            elo_std,
            elo_gini,
            float(high_thresholds["high1550"]),
            float(high_thresholds["high1600"]),
            float(high_thresholds["high1650"]),
            float(high_thresholds["high1700"]),
            float(high_thresholds["high1800"]),
            float(seat_highest),
            float(seat_second),
            float(top2_adjacent),
            round_snapshot.swiss_progress,
            float(round_number),
            float(round_snapshot.rounds_remaining),
            round_snapshot.cut_fraction,
            float(round_snapshot.cut_size_bucket),
            float(round_snapshot.cut_line_points),
            float(round_snapshot.expected_cut_line_points),
            small_mean(pod_estimated_omw),
            min(pod_estimated_omw) if pod_estimated_omw else 0.0,
            max(pod_estimated_omw) if pod_estimated_omw else 0.0,
            small_std(pod_estimated_omw),
            small_mean(pod_same_points_omw_percentiles),
            min(pod_same_points_omw_percentiles) if pod_same_points_omw_percentiles else 0.0,
            max(pod_same_points_omw_percentiles) if pod_same_points_omw_percentiles else 0.0,
            float(count_bottom_quartile_omw_in_same_points_group),
            float(count_currently_in_cut),
            float(count_currently_outside_cut),
            float(count_players_currently_safe),
            float(count_players_currently_dead),
            float(all_players_live),
            float(count_draw_secures_cut),
            float(count_win_secures_cut),
            float(count_must_win_to_stay_live),
            float(all_players_draw_secures_cut),
            float(mixed_pod_cut_incentives),
            float(some_locked_some_must_win),
            small_mean(rank_minus_cut),
            min(rank_minus_cut) if rank_minus_cut else 0.0,
            float((max(pod_current_ranks) - min(pod_current_ranks)) if pod_current_ranks else 0),
            small_mean(draw_secure_rank_delta),
            small_mean(win_secure_rank_delta),
            sum(pod_percentiles) / len(pod_percentiles),
            max(pod_percentiles),
            small_std([float(points) for points in pod_points]),
            sum(cut_margins) / len(cut_margins),
            min(abs(margin) for margin in cut_margins),
            small_mean(points_to_current_cut),
            min(points_to_current_cut) if points_to_current_cut else 0.0,
            small_mean(points_to_cut),
            min(points_to_cut) if points_to_cut else 0.0,
            float(sum(1 for margin in cut_margins if margin >= 0.0)),
            float(sum(1 for margin in cut_margins if abs(margin) <= bubble_margin)),
            float(count_locked_for_current_cut),
            float(count_dead_for_current_cut),
            float(count_draw_safe_for_current_cut),
            float(count_must_win_for_current_cut),
            float(all_players_draw_safe_for_current_cut),
            float(count_locked_for_cut),
            float(count_dead_for_cut),
            float(count_live_for_cut),
            float(count_draw_safe_for_cut),
            float(count_must_win_for_cut),
            float(all_players_draw_safe),
            float(is_last_swiss_round),
            float(is_penultimate_swiss_round),
            float(round_snapshot.month),
            float(round_snapshot.quarter),
            float(round_snapshot.tournament_size),
            float(round_snapshot.size_bucket),
            feature_context.global_recent_draw_rate_90d,
            small_mean(draw_rates),
            small_median(draw_rates),
            min(draw_rates) if draw_rates else 0.0,
            max(draw_rates) if draw_rates else 0.0,
            small_std(draw_rates),
            (max(draw_rates) - min(draw_rates)) if draw_rates else 0.0,
            float(count_high_draw_players),
            float(count_high_win_low_draw_players),
            float(draw_rate_range_above_threshold),
            small_mean(win_rates),
            max(win_rates) if win_rates else 0.0,
            small_mean(decisive_rates),
            max(decisive_rates) if decisive_rates else 0.0,
            float(sum(tournament_pair_counts) / len(tournament_pair_counts)) if tournament_pair_counts else 0.0,
            float(max(tournament_pair_counts)) if tournament_pair_counts else 0.0,
            float(sum(global_pair_counts) / len(global_pair_counts)) if global_pair_counts else 0.0,
            float(max(global_pair_counts)) if global_pair_counts else 0.0,
            feature_context.series_prior_draw_rate,
            float(feature_context.series_events_seen),
            feature_context.state_prior_draw_rate,
            feature_context.country_prior_draw_rate,
            float(count_players_near_cut_band),
        ],
        dtype=float,
    )


def predict_draw_probabilities(
    pods: list[Pod],
    state: TournamentState,
    context: TournamentContext,
    draw_model: LoadedDrawModel,
    round_snapshot: RoundFeatureSnapshot,
) -> dict[tuple[int, int], float]:
    if not pods:
        return {}
    full_matrix = np.vstack([build_draw_feature_row(pod, state, context, round_snapshot) for pod in pods])
    x_matrix = full_matrix[:, draw_model.feature_indexes]
    probabilities = draw_model.model.predict_proba(x_matrix)[:, 1]
    if draw_model.calibrator is not None:
        if draw_model.calibration == "platt":
            probabilities = draw_model.calibrator.predict_proba(probabilities.reshape(-1, 1))[:, 1]
        else:
            probabilities = draw_model.calibrator.predict(probabilities)
    return {
        (pod.round_index, pod.table_number): float(probability)
        for pod, probability in zip(pods, probabilities, strict=False)
    }


def context_top_month(context: TournamentContext) -> int:
    return context.start_date.month if context.start_date else 1


def context_top_size(context: TournamentContext, fallback: int) -> int:
    return context.player_count or fallback


def predict_draw_probability(
    pod: Pod,
    state: TournamentState,
    context: TournamentContext,
    draw_model: LoadedDrawModel,
) -> float:
    round_snapshot = build_round_snapshot(state, context, pod.round_index + 1)
    return predict_draw_probabilities([pod], state, context, draw_model, round_snapshot)[(pod.round_index, pod.table_number)]


def predict_decisive_win_probs(pod: Pod, state: TournamentState) -> dict[str, float]:
    effective_ratings: dict[str, float] = {}
    for player_id in pod.player_ids:
        seat = pod.seats_by_player.get(player_id) if pod.seats_by_player else None
        effective_ratings[player_id] = effective_player_rating(state.players[player_id], seat)
    equities = {player_id: rating_equity(rating) for player_id, rating in effective_ratings.items()}
    total = sum(equities.values()) or 1.0
    return {player_id: equity / total for player_id, equity in equities.items()}


def predict_decisive_win_probabilities(
    pods: list[Pod],
    state: TournamentState,
) -> dict[tuple[int, int], tuple[float, ...]]:
    probabilities: dict[tuple[int, int], tuple[float, ...]] = {}
    for pod in pods:
        adjusted_ratings = []
        for player_id in pod.player_ids:
            seat = pod.seats_by_player.get(player_id) if pod.seats_by_player else None
            adjusted_ratings.append(effective_player_rating(state.players[player_id], seat))
        equity_values = np.asarray([rating_equity(rating) for rating in adjusted_ratings], dtype=float)
        total = float(equity_values.sum()) or 1.0
        probabilities[(pod.round_index, pod.table_number)] = tuple((equity_values / total).tolist())
    return probabilities
