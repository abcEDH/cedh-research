#!/usr/bin/env python3
"""Model loading and pod-level inference for tournament simulation."""

from __future__ import annotations

import pickle
import re
import os
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

for thread_env_var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(thread_env_var, "1")

import numpy as np

from sim_pairings import opponent_match_win_percentage, topdeck_bye_rank
from sim_types import ALL_DRAW_FEATURES, FeatureContext, Pod, RoundFeatureSnapshot, TournamentContext, TournamentState

ELO_BASE = 2.0
ELO_DIVISOR = 200.0
DEFAULT_DRAW_MODEL_PATH = (
    Path(__file__).resolve().parents[1]
    / "reports"
    / "pod-outcome-model"
    / "v4"
    / "pod_outcome_model_artifact_v4_draw_elo_hybrid.pkl"
)
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
    target: str = "draw"
    classes: tuple[int, ...] = ()
    draw_class: int = 1
    winner_source: str = "external"


@dataclass(slots=True)
class LoadedCandidateWinnerModel:
    features: list[str]
    model: Any
    blend_weight: float = 1.0
    model_type: str = "hist_gradient_boosting"
    classes: tuple[int, ...] = ()


CANDIDATE_WINNER_FEATURES = [
    "pod_size",
    "is_swiss",
    "round_number",
    "swiss_progress",
    "is_last_swiss_round",
    "is_penultimate_swiss_round",
    "tournament_size",
    "cut_fraction",
    "size_bucket",
    "candidate_seat",
    "candidate_has_seat",
    "candidate_seat_bonus",
    "candidate_elo",
    "candidate_effective_elo",
    "candidate_elo_share",
    "candidate_elo_rank",
    "candidate_elo_percentile",
    "candidate_gap_to_best",
    "candidate_gap_to_second",
    "candidate_gap_to_mean",
    "candidate_gap_to_min",
    "candidate_is_best_elo",
    "candidate_is_second_elo",
    "candidate_is_worst_elo",
    "pod_elo_spread",
    "pod_elo_mean",
    "pod_elo_std",
]


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


def smoothed_rate(successes: float, total: float, fallback_rate: float, prior_weight: float) -> float:
    if prior_weight <= 0:
        return (successes / total) if total else fallback_rate
    return (successes + (fallback_rate * prior_weight)) / (total + prior_weight)


def outcome_v3_family_flags(series_key: str | None, tournament_name: str | None) -> dict[str, float]:
    text = f"{series_key or ''} {tournament_name or ''}".lower()
    topdeck_invitational = 1.0 if "topdeck invitational" in text else 0.0
    midseason_showdown = 1.0 if "midseason showdown" in text or "mid season showdown" in text else 0.0
    commander_invitational = 1.0 if "commander invitational" in text else 0.0
    invitational_like = 1.0 if "invitational" in text else 0.0
    championship_like = 1.0 if "championship" in text or "championships" in text else 0.0
    qualifier_like = 1.0 if "qualifier" in text or "qualification" in text else 0.0
    redemption_like = 1.0 if "redemption" in text else 0.0
    league_like = 1.0 if "league" in text else 0.0
    open_like = 1.0 if "open" in text else 0.0
    high_stakes_like = max(
        topdeck_invitational,
        midseason_showdown,
        commander_invitational,
        invitational_like,
        championship_like,
        qualifier_like,
        redemption_like,
    )
    return {
        "is_topdeck_invitational_family": topdeck_invitational,
        "is_midseason_showdown_family": midseason_showdown,
        "is_commander_invitational_family": commander_invitational,
        "is_invitational_like_family": invitational_like,
        "is_championship_like_family": championship_like,
        "is_qualifier_like_family": qualifier_like,
        "is_redemption_like_family": redemption_like,
        "is_league_like_family": league_like,
        "is_open_like_family": open_like,
        "is_high_stakes_like_family": high_stakes_like,
    }


def load_draw_model_artifact(path: Path | str = DEFAULT_DRAW_MODEL_PATH) -> LoadedDrawModel:
    with Path(path).open("rb") as handle:
        artifact = pickle.load(handle)
    selection = artifact["selection"]
    feature_indexes = np.asarray([ALL_DRAW_FEATURES.index(feature) for feature in selection["features"]], dtype=int)
    target = str(artifact.get("target") or "draw")
    return LoadedDrawModel(
        features=list(selection["features"]),
        model=artifact["model"],
        calibration=str(artifact.get("calibration") or "uncalibrated"),
        calibrator=artifact.get("calibrator"),
        feature_indexes=feature_indexes,
        target=target,
        classes=tuple(int(value) for value in artifact.get("classes", ())),
        draw_class=int(artifact.get("draw_class", 0 if target == "pod_outcome" else 1)),
        winner_source=str(
            artifact.get(
                "winner_source",
                "artifact" if target == "pod_outcome" else "external",
            )
        ),
    )


def load_candidate_winner_model_artifact(path: Path | str) -> LoadedCandidateWinnerModel:
    with Path(path).open("rb") as handle:
        artifact = pickle.load(handle)
    features = list(artifact.get("features") or artifact.get("candidate_features") or CANDIDATE_WINNER_FEATURES)
    unknown_features = [feature for feature in features if feature not in CANDIDATE_WINNER_FEATURES]
    if unknown_features:
        raise ValueError(f"candidate winner artifact references unknown features: {unknown_features}")
    return LoadedCandidateWinnerModel(
        features=features,
        model=artifact["model"],
        blend_weight=max(0.0, min(1.0, float(artifact.get("blend_weight", artifact.get("selected_blend_weight", 1.0))))),
        model_type=str(artifact.get("model_type") or "hist_gradient_boosting"),
        classes=tuple(int(value) for value in artifact.get("classes", ())),
    )


def rating_equity(rating: float) -> float:
    return pow(ELO_BASE, rating / ELO_DIVISOR)


def effective_player_rating(player, seat: int | None = None) -> float:
    rating = float(player.elo)
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
    fallback_seed = len(player_ids) + 1_000_000
    sort_keys = sorted(
        (
            -points_by_player.get(player_id, 0),
            -estimated_omw_by_player.get(player_id, 0.0),
            tiebreak_seed_by_player.get(player_id, fallback_seed),
            player_id,
        )
        for player_id in player_ids
    )

    ranks: dict[str, int] = {}
    for player_id in player_ids:
        target_key = (
            -(points_by_player.get(player_id, 0) + point_delta),
            -estimated_omw_by_player.get(player_id, 0.0),
            tiebreak_seed_by_player.get(player_id, fallback_seed),
            player_id,
        )
        ranks[player_id] = bisect_left(sort_keys, target_key) + 1
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
    topdeck_ratings = [
        state.players[player_id].topdeck_elo
        for player_id in player_ids
        if state.players[player_id].topdeck_elo is not None
    ]
    topdeck_elo_mean = small_mean([float(rating) for rating in topdeck_ratings])
    topdeck_elo_std = small_std([float(rating) for rating in topdeck_ratings])
    topdeck_elo_spread = (
        float(max(topdeck_ratings) - min(topdeck_ratings)) if len(topdeck_ratings) >= 2 else 0.0
    )
    topdeck_elo_missing_count = len(player_ids) - len(topdeck_ratings)
    topdeck_elo_minus_internal_mean = topdeck_elo_mean - small_mean(ratings) if topdeck_ratings else 0.0
    commander_color_sets = [
        tuple(sorted({color.upper() for color in state.players[player_id].commander_colors if color}))
        for player_id in player_ids
    ]
    commander_color_data_missing_count = sum(1 for colors in commander_color_sets if not colors)
    commander_color_counts = [len(colors) for colors in commander_color_sets]
    unique_commander_colors = sorted({color for colors in commander_color_sets for color in colors})
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
    prior_games = [float(history.games_played if history else 0) for history in player_histories]
    smoothed_draw_rates = [
        smoothed_rate((history.draw_rate * history.games_played) if history else 0.0, history.games_played if history else 0.0, feature_context.global_recent_draw_rate_90d, 50.0)
        for history in player_histories
    ]
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
    count_repeat_pairs = sum(1 for count in tournament_pair_counts if count > 0)
    points_by_value: dict[int, int] = {}
    for points in pod_points:
        points_by_value[points] = points_by_value.get(points, 0) + 1
    same_points_count_in_pod = max(points_by_value.values()) if points_by_value else 0
    min_points_in_pod = min(pod_points) if pod_points else 0
    max_points_in_pod = max(pod_points) if pod_points else 0
    points_range_within_pod = max_points_in_pod - min_points_in_pod
    draw_as_good_as_win = [
        (draw_rank <= context.top_cut) == (win_rank <= context.top_cut) if context.top_cut > 0 else True
        for draw_rank, win_rank in zip(pod_draw_secure_ranks, pod_win_secure_ranks, strict=True)
    ]
    loss_eliminates = [
        points + max_future_points < round_snapshot.expected_cut_line_points
        for points in pod_points
    ]
    draw_preserves_cut_rank = [
        current_rank <= context.top_cut and draw_rank <= context.top_cut
        for current_rank, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True)
    ] if context.top_cut > 0 else []
    win_changes_cut_status = [
        (current_rank <= context.top_cut) != (win_rank <= context.top_cut)
        for current_rank, win_rank in zip(pod_current_ranks, pod_win_secure_ranks, strict=True)
    ] if context.top_cut > 0 else []
    adjusted_ratings = [
        effective_player_rating(state.players[player_id], pod.seats_by_player.get(player_id) if pod.seats_by_player else None)
        for player_id in player_ids
    ]
    equity_values = np.asarray([rating_equity(rating) for rating in adjusted_ratings], dtype=float)
    total_equity = float(equity_values.sum()) or 1.0
    decisive_probabilities = equity_values / total_equity if len(equity_values) else np.asarray([], dtype=float)
    decisive_entropy = (
        -float(np.sum(decisive_probabilities * np.log(np.clip(decisive_probabilities, 1e-12, 1.0))))
        / float(np.log(len(decisive_probabilities)))
        if len(decisive_probabilities) > 1
        else 0.0
    )
    decisive_max = float(decisive_probabilities.max()) if len(decisive_probabilities) else 0.0
    decisive_min = float(decisive_probabilities.min()) if len(decisive_probabilities) else 0.0
    count_default_elos = sum(1 for rating in ratings if abs(rating - 1500.0) < 1e-9)
    min_draw_secure_rank = min(pod_draw_secure_ranks) if pod_draw_secure_ranks else 0
    max_draw_secure_rank = max(pod_draw_secure_ranks) if pod_draw_secure_ranks else 0
    bye_rank = topdeck_bye_rank(context.top_cut)
    bye_fraction = (bye_rank / round_snapshot.field_size) if bye_rank else 0.0
    sorted_point_values = sorted(round_snapshot.points_by_player.values(), reverse=True)
    bye_rank_index = min(max((bye_rank or 1) - 1, 0), max(len(sorted_point_values) - 1, 0)) if sorted_point_values else 0
    bye_line_points = sorted_point_values[bye_rank_index] if bye_rank and sorted_point_values else 0
    projected_bye_points = [
        points + (round_snapshot.rounds_remaining * 1.25)
        for points in round_snapshot.points_by_player.values()
    ]
    projected_bye_points.sort(reverse=True)
    expected_bye_line_points = projected_bye_points[bye_rank_index] if bye_rank and projected_bye_points else 0.0
    pod_loss_ranks = pod_current_ranks
    count_currently_in_bye = sum(1 for rank in pod_current_ranks if bye_rank and rank <= bye_rank)
    count_draw_secures_bye = sum(1 for rank in pod_draw_secure_ranks if bye_rank and rank <= bye_rank)
    count_win_secures_bye = sum(1 for rank in pod_win_secure_ranks if bye_rank and rank <= bye_rank)
    count_must_win_for_bye = sum(
        1
        for draw_rank, win_rank in zip(pod_draw_secure_ranks, pod_win_secure_ranks, strict=True)
        if bye_rank and draw_rank > bye_rank and win_rank <= bye_rank
    )
    count_players_win_only_live = sum(
        1
        for draw_rank, win_rank in zip(pod_draw_secure_ranks, pod_win_secure_ranks, strict=True)
        if context.top_cut > 0 and draw_rank > context.top_cut and win_rank <= context.top_cut
    )
    count_players_win_only_live_for_bye = count_must_win_for_bye
    all_players_draw_lock_cut = 1 if context.top_cut > 0 and pod_draw_secure_ranks and max_draw_secure_rank <= context.top_cut else 0
    all_players_draw_lock_bye = 1 if bye_rank and pod_draw_secure_ranks and max_draw_secure_rank <= bye_rank else 0
    min_draw_rank_margin_to_cut = (
        min(float(context.top_cut - rank) for rank in pod_draw_secure_ranks)
        if context.top_cut > 0 and pod_draw_secure_ranks
        else 0.0
    )
    min_draw_rank_margin_to_bye = (
        min(float(bye_rank - rank) for rank in pod_draw_secure_ranks)
        if bye_rank and pod_draw_secure_ranks
        else 0.0
    )
    count_players_draw_makes_cut = sum(
        1
        for current_rank, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True)
        if context.top_cut > 0 and current_rank > context.top_cut and draw_rank <= context.top_cut
    )
    count_players_draw_makes_bye = sum(
        1
        for current_rank, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True)
        if bye_rank and current_rank > bye_rank and draw_rank <= bye_rank
    )
    draw_hurts_any_player_cut_status = (
        1
        if context.top_cut > 0
        and any(current_rank <= context.top_cut and draw_rank > context.top_cut for current_rank, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True))
        else 0
    )
    draw_hurts_any_player_bye_status = (
        1
        if bye_rank
        and any(current_rank <= bye_rank and draw_rank > bye_rank for current_rank, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True))
        else 0
    )
    draw_hurts_any_player_status = 1 if draw_hurts_any_player_cut_status or draw_hurts_any_player_bye_status else 0
    all_players_above_cut_after_draw = all_players_draw_lock_cut
    all_players_above_bye_after_draw = all_players_draw_lock_bye
    all_players_above_cut_after_loss = 1 if context.top_cut > 0 and pod_loss_ranks and max(pod_loss_ranks) <= context.top_cut else 0
    all_players_above_bye_after_loss = 1 if bye_rank and pod_loss_ranks and max(pod_loss_ranks) <= bye_rank else 0
    pod_has_asymmetric_cut_incentive = 1 if context.top_cut > 0 and count_draw_secures_cut > 0 and count_draw_secures_cut < len(player_ids) else 0
    pod_has_asymmetric_bye_incentive = 1 if bye_rank and count_draw_secures_bye > 0 and count_draw_secures_bye < len(player_ids) else 0
    pod_has_asymmetric_incentive = 1 if pod_has_asymmetric_cut_incentive or pod_has_asymmetric_bye_incentive else 0
    draw_cut_status = [rank <= context.top_cut if context.top_cut > 0 else False for rank in pod_draw_secure_ranks]
    win_cut_status = [rank <= context.top_cut if context.top_cut > 0 else False for rank in pod_win_secure_ranks]
    draw_bye_status = [rank <= bye_rank if bye_rank else False for rank in pod_draw_secure_ranks]
    win_bye_status = [rank <= bye_rank if bye_rank else False for rank in pod_win_secure_ranks]
    player_draw_as_good_as_win = [
        (draw_cut == win_cut) and (draw_bye == win_bye)
        for draw_cut, win_cut, draw_bye, win_bye in zip(draw_cut_status, win_cut_status, draw_bye_status, win_bye_status, strict=True)
    ]
    draw_vs_win_status_same_count = sum(1 for value in player_draw_as_good_as_win if value)
    pairwise_mutual_draw_benefit_count = 0
    for left_index in range(len(player_draw_as_good_as_win)):
        for right_index in range(left_index + 1, len(player_draw_as_good_as_win)):
            if player_draw_as_good_as_win[left_index] and player_draw_as_good_as_win[right_index]:
                pairwise_mutual_draw_benefit_count += 1
    count_players_draw_as_good_as_win_for_bye = sum(
        1
        for draw_status, win_status in zip(draw_bye_status, win_bye_status, strict=True)
        if bye_rank and draw_status == win_status
    )
    series_draws = feature_context.series_prior_draw_rate * feature_context.series_events_seen
    series_total = float(feature_context.series_events_seen)
    series_smoothed_50 = smoothed_rate(series_draws, series_total, feature_context.global_recent_draw_rate_90d, 50.0)
    series_smoothed_100 = smoothed_rate(series_draws, series_total, feature_context.global_recent_draw_rate_90d, 100.0)
    series_smoothed_250 = smoothed_rate(series_draws, series_total, feature_context.global_recent_draw_rate_90d, 250.0)
    series_smoothed_500 = smoothed_rate(series_draws, series_total, feature_context.global_recent_draw_rate_90d, 500.0)
    family_flags = outcome_v3_family_flags(context.series_key, state.spec.name)
    series_minus_global_prior = feature_context.series_prior_draw_rate - feature_context.global_recent_draw_rate_90d
    high_stakes_like = family_flags["is_high_stakes_like_family"]
    high1700 = float(high_thresholds["high1700"])
    high1800 = float(high_thresholds["high1800"])
    pod_size = len(player_ids)

    return np.asarray(
        [
            1.0,
            float(pod_size),
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
            series_smoothed_50,
            series_smoothed_100,
            series_smoothed_250,
            series_smoothed_500,
            float(np.log1p(feature_context.series_events_seen)),
            small_mean(smoothed_draw_rates),
            small_median(smoothed_draw_rates),
            max(smoothed_draw_rates) if smoothed_draw_rates else 0.0,
            small_mean(prior_games),
            min(prior_games) if prior_games else 0.0,
            small_mean([games / (games + 50.0) for games in prior_games]),
            float(all_players_draw_safe),
            float(count_must_win_to_stay_live > 0),
            float(all_players_draw_secures_cut),
            float(sum(1 for value in draw_as_good_as_win if value)),
            float(sum(1 for value in loss_eliminates if value)),
            float(sum(1 for value in draw_preserves_cut_rank if value)),
            float(sum(1 for value in win_changes_cut_status if value)),
            float(same_points_count_in_pod),
            float(1 if pod_points and same_points_count_in_pod == len(pod_points) else 0),
            float(points_range_within_pod),
            float(min_points_in_pod),
            float(max_points_in_pod),
            float(1 if pod_points and all(points >= round_snapshot.expected_cut_line_points for points in pod_points) else 0),
            float(1 if pod_points and all(abs(points - round_snapshot.expected_cut_line_points) <= 1 for points in pod_points) else 0),
            round_snapshot.cut_fraction if is_last_swiss_round else 0.0,
            round_snapshot.cut_fraction if is_penultimate_swiss_round else 0.0,
            float(round_number * (round_snapshot.size_bucket + 1)),
            float(round_snapshot.size_bucket if is_last_swiss_round else 0),
            float((round_number * 100) + (round_snapshot.size_bucket * 10) + round_snapshot.cut_size_bucket),
            feature_context.global_recent_draw_rate_90d,
            decisive_entropy,
            decisive_max,
            decisive_min,
            decisive_max - decisive_min,
            float(count_repeat_pairs > 0),
            float(count_repeat_pairs),
            float(len(player_ids) * round_number),
            float(len(player_ids) if is_last_swiss_round else 0),
            float(len(player_ids) * round_snapshot.cut_fraction),
            float(len(player_ids) * feature_context.series_prior_draw_rate),
            series_smoothed_100,
            feature_context.series_prior_draw_rate - feature_context.global_recent_draw_rate_90d,
            float(sum(1 for games in prior_games if games == 0)),
            float(sum(1 for games in prior_games if games < 10)),
            float(1 if ratings and count_default_elos == len(ratings) else 0),
            float(count_default_elos),
            float(1 if not pod.seats_by_player else 0),
            float(min_draw_secure_rank),
            float(max_draw_secure_rank),
            float(max_draw_secure_rank - min_draw_secure_rank),
            float(1 if context.top_cut > 0 and pod_draw_secure_ranks and max_draw_secure_rank <= context.top_cut + 4 else 0),
            float(1 if context.top_cut > 0 and pod_draw_secure_ranks and max_draw_secure_rank <= context.top_cut + 8 else 0),
            float(bye_fraction),
            float(bye_line_points),
            float(expected_bye_line_points),
            float(count_currently_in_bye),
            float(count_draw_secures_bye),
            float(count_win_secures_bye),
            float(count_must_win_for_bye),
            float(count_players_win_only_live),
            float(count_players_win_only_live_for_bye),
            float(all_players_draw_lock_cut),
            float(all_players_draw_lock_bye),
            float(min_draw_rank_margin_to_cut),
            float(min_draw_rank_margin_to_bye),
            float(count_players_draw_makes_cut),
            float(count_players_draw_makes_bye),
            float(draw_hurts_any_player_cut_status),
            float(draw_hurts_any_player_bye_status),
            float(draw_hurts_any_player_status),
            float(all_players_above_cut_after_draw),
            float(all_players_above_bye_after_draw),
            float(all_players_above_cut_after_loss),
            float(all_players_above_bye_after_loss),
            float(pod_has_asymmetric_cut_incentive),
            float(pod_has_asymmetric_bye_incentive),
            float(pod_has_asymmetric_incentive),
            float(draw_vs_win_status_same_count),
            float(pairwise_mutual_draw_benefit_count),
            float(count_players_draw_as_good_as_win_for_bye),
            topdeck_elo_spread,
            topdeck_elo_mean,
            topdeck_elo_std,
            float(topdeck_elo_missing_count),
            topdeck_elo_minus_internal_mean,
            float(sum(1 for colors in commander_color_sets if "W" in colors)),
            float(sum(1 for colors in commander_color_sets if "U" in colors)),
            float(sum(1 for colors in commander_color_sets if "B" in colors)),
            float(sum(1 for colors in commander_color_sets if "R" in colors)),
            float(sum(1 for colors in commander_color_sets if "G" in colors)),
            small_mean([float(count) for count in commander_color_counts]),
            float(max(commander_color_counts) if commander_color_counts else 0),
            float(len(unique_commander_colors)),
            float(commander_color_data_missing_count),
            family_flags["is_topdeck_invitational_family"],
            family_flags["is_midseason_showdown_family"],
            family_flags["is_commander_invitational_family"],
            family_flags["is_invitational_like_family"],
            family_flags["is_championship_like_family"],
            family_flags["is_qualifier_like_family"],
            family_flags["is_redemption_like_family"],
            family_flags["is_league_like_family"],
            family_flags["is_open_like_family"],
            high_stakes_like,
            float(high_thresholds["high1600"]) * round_snapshot.cut_fraction,
            high1700 * round_snapshot.cut_fraction,
            high1800 * round_snapshot.cut_fraction,
            high1700 * feature_context.series_prior_draw_rate,
            high1800 * feature_context.series_prior_draw_rate,
            1.0 if pod_size > 0 and high1700 >= pod_size else 0.0,
            1.0 if pod_size > 0 and high1800 >= pod_size else 0.0,
            top2_mean_elo * feature_context.series_prior_draw_rate,
            top3_mean_elo * feature_context.series_prior_draw_rate,
            top3_mean_elo * float(round_number),
            mean_elo * feature_context.global_recent_draw_rate_90d,
            series_minus_global_prior,
            abs(series_minus_global_prior),
            family_flags["is_topdeck_invitational_family"] * feature_context.series_prior_draw_rate,
            family_flags["is_midseason_showdown_family"] * feature_context.series_prior_draw_rate,
            family_flags["is_invitational_like_family"] * feature_context.series_prior_draw_rate,
            high_stakes_like * feature_context.series_prior_draw_rate,
            family_flags["is_invitational_like_family"] * high1700,
            high_stakes_like * high1700,
            high_stakes_like * round_snapshot.cut_fraction,
            high_stakes_like * float(round_number),
            float(count_must_win_for_cut + count_must_win_for_bye),
            1.0 if all_players_draw_lock_cut or all_players_draw_lock_bye else 0.0,
            1.0 if draw_hurts_any_player_cut_status or draw_hurts_any_player_bye_status else 0.0,
            1.0 if pod_has_asymmetric_cut_incentive or pod_has_asymmetric_bye_incentive else 0.0,
            float(draw_vs_win_status_same_count + count_players_draw_as_good_as_win_for_bye),
            float(count_players_win_only_live + count_players_win_only_live_for_bye),
        ],
        dtype=float,
    )


def normalize_probability_tuple(probabilities: list[float], size: int) -> tuple[float, ...]:
    values = [max(0.0, float(probability)) for probability in probabilities[:size]]
    if len(values) < size:
        values.extend([0.0] * (size - len(values)))
    total = sum(values)
    if total <= 0:
        return tuple([1.0 / size] * size) if size > 0 else tuple()
    return tuple(value / total for value in values)


def _model_class_labels(model: Any, stored_classes: tuple[int, ...], class_count: int) -> list[int]:
    raw_classes = getattr(model, "classes_", stored_classes)
    labels = [int(value) for value in raw_classes] if raw_classes is not None else []
    if len(labels) == class_count:
        return labels
    if class_count == 2:
        return [0, 1]
    return list(range(class_count))


def _candidate_seat_bonus(seat: int | None, *, use_seat_bonus: bool) -> float:
    if seat is None or not use_seat_bonus:
        return 0.0
    return float(SEAT_ELO_BONUS.get(seat, 0.0))


def build_candidate_winner_feature_row(
    pod: Pod,
    state: TournamentState,
    context: TournamentContext,
    round_snapshot: RoundFeatureSnapshot,
    player_id: str,
    elo_shares: dict[str, float],
) -> np.ndarray:
    player_ids = [candidate_id for candidate_id in pod.player_ids if candidate_id in state.players]
    pod_size = len(player_ids)
    seats = pod.seats_by_player or {}
    seat_values = [seats.get(candidate_id) for candidate_id in player_ids]
    use_seat_bonus = pod_size == 4 and all(seat is not None for seat in seat_values) and sorted(seat_values) == [1, 2, 3, 4]

    effective_elos: dict[str, float] = {}
    for candidate_id in player_ids:
        seat = seats.get(candidate_id)
        effective_elos[candidate_id] = float(state.players[candidate_id].elo) + _candidate_seat_bonus(
            seat,
            use_seat_bonus=use_seat_bonus,
        )

    raw_seat = seats.get(player_id)
    candidate_elo = float(state.players[player_id].elo)
    candidate_seat_bonus = _candidate_seat_bonus(raw_seat, use_seat_bonus=use_seat_bonus)
    candidate_effective_elo = candidate_elo + candidate_seat_bonus
    sorted_elos = sorted(effective_elos.values(), reverse=True)
    candidate_rank = 1 + sum(1 for value in effective_elos.values() if value > candidate_effective_elo)
    candidate_percentile = 1.0 if pod_size <= 1 else 1.0 - ((candidate_rank - 1) / (pod_size - 1))
    best_elo = sorted_elos[0] if sorted_elos else candidate_effective_elo
    second_elo = sorted_elos[1] if len(sorted_elos) > 1 else best_elo
    min_elo = sorted_elos[-1] if sorted_elos else candidate_effective_elo
    mean_elo = small_mean(sorted_elos)
    std_elo = small_std(sorted_elos)
    is_swiss = pod.round_index < state.spec.swiss_rounds
    swiss_progress = round_snapshot.swiss_progress if is_swiss else 1.0

    values = {
        "pod_size": float(pod_size),
        "is_swiss": 1.0 if is_swiss else 0.0,
        "round_number": float(pod.round_index + 1),
        "swiss_progress": float(swiss_progress),
        "is_last_swiss_round": 1.0 if is_swiss and pod.round_index == state.spec.swiss_rounds - 1 else 0.0,
        "is_penultimate_swiss_round": 1.0 if is_swiss and pod.round_index == state.spec.swiss_rounds - 2 else 0.0,
        "tournament_size": float(context_top_size(context, len(state.players))),
        "cut_fraction": float(round_snapshot.cut_fraction),
        "size_bucket": float(round_snapshot.size_bucket),
        "candidate_seat": float(raw_seat or 0),
        "candidate_has_seat": 1.0 if raw_seat is not None else 0.0,
        "candidate_seat_bonus": candidate_seat_bonus,
        "candidate_elo": candidate_elo,
        "candidate_effective_elo": candidate_effective_elo,
        "candidate_elo_share": float(elo_shares.get(player_id, 1.0 / max(1, pod_size))),
        "candidate_elo_rank": float(candidate_rank),
        "candidate_elo_percentile": float(candidate_percentile),
        "candidate_gap_to_best": candidate_effective_elo - best_elo,
        "candidate_gap_to_second": candidate_effective_elo - second_elo,
        "candidate_gap_to_mean": candidate_effective_elo - mean_elo,
        "candidate_gap_to_min": candidate_effective_elo - min_elo,
        "candidate_is_best_elo": 1.0 if candidate_rank == 1 else 0.0,
        "candidate_is_second_elo": 1.0 if candidate_rank == 2 else 0.0,
        "candidate_is_worst_elo": 1.0 if candidate_rank == pod_size else 0.0,
        "pod_elo_spread": best_elo - min_elo,
        "pod_elo_mean": mean_elo,
        "pod_elo_std": std_elo,
    }
    return np.asarray([values[feature] for feature in CANDIDATE_WINNER_FEATURES], dtype=float)


def predict_candidate_winner_probabilities(
    pods: list[Pod],
    state: TournamentState,
    context: TournamentContext,
    winner_model: LoadedCandidateWinnerModel,
) -> dict[tuple[int, int], tuple[float, ...]]:
    if not pods:
        return {}

    elo_probabilities = predict_decisive_win_probabilities(pods, state)
    rows: list[np.ndarray] = []
    row_refs: list[tuple[Pod, str]] = []
    round_snapshots: dict[int, RoundFeatureSnapshot] = {}
    for pod in pods:
        round_number = pod.round_index + 1
        round_snapshot = round_snapshots.get(round_number)
        if round_snapshot is None:
            round_snapshot = build_round_snapshot(state, context, round_number)
            round_snapshots[round_number] = round_snapshot
        elo_shares = {
            player_id: probability
            for player_id, probability in zip(
                pod.player_ids,
                elo_probabilities.get((pod.round_index, pod.table_number), ()),
                strict=False,
            )
        }
        for player_id in pod.player_ids:
            rows.append(build_candidate_winner_feature_row(pod, state, context, round_snapshot, player_id, elo_shares))
            row_refs.append((pod, player_id))

    if not rows:
        return {}

    feature_indexes = [CANDIDATE_WINNER_FEATURES.index(feature) for feature in winner_model.features]
    x_matrix = np.vstack(rows)[:, feature_indexes]
    probabilities = winner_model.model.predict_proba(x_matrix)
    model_classes = [int(value) for value in getattr(winner_model.model, "classes_", winner_model.classes)]
    positive_index = model_classes.index(1) if 1 in model_classes else -1

    raw_scores_by_pod: dict[tuple[int, int], dict[str, float]] = defaultdict(dict)
    for (pod, player_id), row_probabilities in zip(row_refs, probabilities, strict=False):
        score = float(row_probabilities[positive_index]) if positive_index >= 0 else 0.0
        raw_scores_by_pod[(pod.round_index, pod.table_number)][player_id] = max(0.0, score)

    output: dict[tuple[int, int], tuple[float, ...]] = {}
    for pod in pods:
        key = (pod.round_index, pod.table_number)
        normalized_candidate = normalize_probability_tuple(
            [raw_scores_by_pod.get(key, {}).get(player_id, 0.0) for player_id in pod.player_ids],
            len(pod.player_ids),
        )
        elo_tuple = elo_probabilities.get(key, tuple([1.0 / len(pod.player_ids)] * len(pod.player_ids)))
        weight = winner_model.blend_weight
        output[key] = normalize_probability_tuple(
            [
                (weight * candidate_probability) + ((1.0 - weight) * elo_probability)
                for candidate_probability, elo_probability in zip(normalized_candidate, elo_tuple, strict=False)
            ],
            len(pod.player_ids),
        )
    return output


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
    probability_matrix = draw_model.model.predict_proba(x_matrix)
    model_classes = _model_class_labels(draw_model.model, draw_model.classes, probability_matrix.shape[1])
    if draw_model.draw_class in model_classes:
        probabilities = probability_matrix[:, model_classes.index(draw_model.draw_class)].astype(float)
    else:
        probabilities = np.zeros(x_matrix.shape[0], dtype=float)
    if draw_model.calibrator is not None:
        if draw_model.calibration == "platt":
            probabilities = draw_model.calibrator.predict_proba(probabilities.reshape(-1, 1))[:, 1]
        else:
            probabilities = draw_model.calibrator.predict(probabilities)
    output: dict[tuple[int, int], float] = {}
    for pod, probability in zip(pods, probabilities, strict=False):
        is_top_cut_pod = draw_model.target == "pod_outcome" and pod.round_index >= state.spec.swiss_rounds
        output[(pod.round_index, pod.table_number)] = (
            0.0 if is_top_cut_pod else float(max(0.0, min(1.0, probability)))
        )
    return output


def predict_pod_outcome_probabilities(
    pods: list[Pod],
    state: TournamentState,
    context: TournamentContext,
    draw_model: LoadedDrawModel,
    round_snapshot: RoundFeatureSnapshot,
    winner_model: LoadedCandidateWinnerModel | None = None,
) -> tuple[dict[tuple[int, int], float], dict[tuple[int, int], tuple[float, ...]]]:
    """Return draw and per-seat overall win probabilities for each pod.

    Draw-only artifacts retain the historical behavior: the model predicts
    P(draw), then non-draw winner share comes from internal Elo or an external
    candidate-winner model. ``target=pod_outcome`` artifacts with
    ``winner_source="artifact"`` predict class 0 as draw and classes 1..N as
    the winner position in ``pod.player_ids``. Pod-outcome artifacts with an
    external winner source use only the configured draw class.
    """
    if not pods:
        return {}, {}
    if draw_model.target != "pod_outcome" or draw_model.winner_source != "artifact":
        return (
            predict_draw_probabilities(pods, state, context, draw_model, round_snapshot),
            predict_candidate_winner_probabilities(pods, state, context, winner_model)
            if winner_model is not None
            else predict_decisive_win_probabilities(pods, state),
        )

    full_matrix = np.vstack([build_draw_feature_row(pod, state, context, round_snapshot) for pod in pods])
    x_matrix = full_matrix[:, draw_model.feature_indexes]
    probabilities = draw_model.model.predict_proba(x_matrix)
    model_classes = _model_class_labels(draw_model.model, draw_model.classes, probabilities.shape[1])
    draw_probabilities: dict[tuple[int, int], float] = {}
    win_probabilities: dict[tuple[int, int], tuple[float, ...]] = {}
    for pod, row_probabilities in zip(pods, probabilities, strict=False):
        class_probability = {
            class_label: float(probability)
            for class_label, probability in zip(model_classes, row_probabilities, strict=False)
        }
        overall_wins = [class_probability.get(index + 1, 0.0) for index in range(len(pod.player_ids))]
        is_top_cut_pod = pod.round_index >= state.spec.swiss_rounds
        draw_probability = 0.0 if is_top_cut_pod else max(0.0, min(1.0, class_probability.get(0, 0.0)))
        decisive_probability = max(1e-12, 1.0 - draw_probability)
        win_probabilities[(pod.round_index, pod.table_number)] = normalize_probability_tuple(
            overall_wins if is_top_cut_pod else [probability / decisive_probability for probability in overall_wins],
            len(pod.player_ids),
        )
        draw_probabilities[(pod.round_index, pod.table_number)] = draw_probability
    return draw_probabilities, win_probabilities


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
    context: TournamentContext | None = None,
    winner_model: LoadedCandidateWinnerModel | None = None,
) -> dict[tuple[int, int], tuple[float, ...]]:
    if winner_model is not None and context is not None:
        return predict_candidate_winner_probabilities(pods, state, context, winner_model)

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
