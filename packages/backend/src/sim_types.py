#!/usr/bin/env python3
"""Core simulation types for pod and tournament Monte Carlo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


ALL_DRAW_FEATURES = [
    "is_swiss",
    "pod_size",
    "spread",
    "mean_elo",
    "median_elo",
    "top2_mean_elo",
    "top3_mean_elo",
    "top1_minus_top2",
    "elo_std",
    "elo_gini",
    "high1550",
    "high1600",
    "high1650",
    "high1700",
    "high1800",
    "seat_highest",
    "seat_second",
    "top2_adjacent",
    "swiss_progress",
    "round_number",
    "rounds_remaining",
    "cut_fraction",
    "cut_size_bucket",
    "current_cut_line_points",
    "expected_cut_line_points",
    "avg_estimated_omw",
    "min_estimated_omw",
    "max_estimated_omw",
    "omw_std_within_pod",
    "avg_same_points_omw_percentile",
    "min_same_points_omw_percentile",
    "max_same_points_omw_percentile",
    "count_bottom_quartile_omw_in_same_points_group",
    "count_currently_in_cut",
    "count_currently_outside_cut",
    "count_players_currently_safe",
    "count_players_currently_dead",
    "all_players_live",
    "count_draw_secures_cut",
    "count_win_secures_cut",
    "count_must_win_to_stay_live",
    "all_players_draw_secures_cut",
    "mixed_pod_cut_incentives",
    "some_locked_some_must_win",
    "avg_rank_minus_cut",
    "min_rank_minus_cut",
    "rank_spread_within_pod",
    "avg_draw_secure_rank_delta",
    "avg_win_secure_rank_delta",
    "avg_points_percentile",
    "max_points_percentile",
    "points_std",
    "avg_cut_margin",
    "min_abs_cut_margin",
    "avg_points_to_current_cut",
    "min_points_to_current_cut",
    "avg_points_to_cut",
    "min_points_to_cut",
    "count_above_cut_line",
    "count_near_cut_line",
    "count_locked_for_current_cut",
    "count_dead_for_current_cut",
    "count_draw_safe_for_current_cut",
    "count_must_win_for_current_cut",
    "all_players_draw_safe_for_current_cut",
    "count_locked_for_cut",
    "count_dead_for_cut",
    "count_live_for_cut",
    "count_draw_safe_for_cut",
    "count_must_win_for_cut",
    "all_players_draw_safe",
    "is_last_swiss_round",
    "is_penultimate_swiss_round",
    "month",
    "quarter",
    "tournament_size",
    "size_bucket",
    "global_recent_draw_rate_90d",
    "avg_player_prior_draw",
    "median_player_prior_draw",
    "min_player_prior_draw",
    "max_player_prior_draw",
    "prior_draw_std",
    "prior_draw_range",
    "count_high_draw_players",
    "count_high_win_low_draw_players",
    "draw_rate_range_above_threshold",
    "avg_player_prior_win",
    "max_player_prior_win",
    "avg_player_prior_decisive",
    "max_player_prior_decisive",
    "prior_pair_meetings_avg",
    "prior_pair_meetings_max",
    "global_pair_meetings_avg",
    "global_pair_meetings_max",
    "series_prior_draw_rate",
    "series_events_seen",
    "state_prior_draw_rate",
    "country_prior_draw_rate",
    "count_players_near_cut_band",
    "series_prior_draw_rate_smoothed_50",
    "series_prior_draw_rate_smoothed_100",
    "series_prior_draw_rate_smoothed_250",
    "series_prior_draw_rate_smoothed_500",
    "series_events_seen_log",
    "avg_player_prior_draw_smoothed_50",
    "median_player_prior_draw_smoothed_50",
    "max_player_prior_draw_smoothed_50",
    "avg_player_prior_games",
    "min_player_prior_games",
    "player_prior_confidence_avg",
    "all_players_can_draw_into_cut",
    "any_player_eliminated_by_draw",
    "all_players_locked_with_draw",
    "count_players_draw_as_good_as_win",
    "count_players_loss_eliminates",
    "draw_preserves_cut_rank_count",
    "win_changes_cut_status_count",
    "same_points_count_in_pod",
    "all_players_same_points",
    "points_range_within_pod",
    "min_points_in_pod",
    "max_points_in_pod",
    "all_players_above_projected_cut_line",
    "all_players_within_one_point_of_cut_line",
    "last_round_cut_fraction",
    "penultimate_round_cut_fraction",
    "round_number_size_bucket",
    "last_round_size_bucket",
    "round_size_cut_bucket_key",
    "round_size_cut_prior_draw_rate_smoothed_100",
    "decisive_win_probability_entropy",
    "max_decisive_win_probability",
    "min_decisive_win_probability",
    "decisive_win_probability_spread",
    "any_repeat_pair",
    "count_repeat_pairs",
    "pod_size_round_number",
    "pod_size_is_last_swiss_round",
    "pod_size_cut_fraction",
    "pod_size_series_prior_draw_rate",
    "series_pod_size_prior_draw_rate_smoothed_100",
    "series_prior_draw_rate_residual",
    "count_players_with_no_history",
    "count_players_with_low_history",
    "all_elos_default",
    "count_default_elos",
    "seat_data_missing",
    "min_draw_secure_rank",
    "max_draw_secure_rank",
    "draw_secure_rank_spread",
    "all_players_draw_rank_within_cut_plus_4",
    "all_players_draw_rank_within_cut_plus_8",
    "bye_fraction",
    "bye_line_points",
    "expected_bye_line_points",
    "count_currently_in_bye",
    "count_draw_secures_bye",
    "count_win_secures_bye",
    "count_must_win_for_bye",
    "count_players_win_only_live",
    "count_players_win_only_live_for_bye",
    "all_players_draw_lock_cut",
    "all_players_draw_lock_bye",
    "min_draw_rank_margin_to_cut",
    "min_draw_rank_margin_to_bye",
    "count_players_draw_makes_cut",
    "count_players_draw_makes_bye",
    "draw_hurts_any_player_cut_status",
    "draw_hurts_any_player_bye_status",
    "draw_hurts_any_player_status",
    "all_players_above_cut_after_draw",
    "all_players_above_bye_after_draw",
    "all_players_above_cut_after_loss",
    "all_players_above_bye_after_loss",
    "pod_has_asymmetric_cut_incentive",
    "pod_has_asymmetric_bye_incentive",
    "pod_has_asymmetric_incentive",
    "draw_vs_win_status_same_count",
    "pairwise_mutual_draw_benefit_count",
    "count_players_draw_as_good_as_win_for_bye",
    "topdeck_elo_spread",
    "topdeck_elo_mean",
    "topdeck_elo_std",
    "topdeck_elo_missing_count",
    "topdeck_elo_minus_internal_mean",
    "count_white_commanders",
    "count_blue_commanders",
    "count_black_commanders",
    "count_red_commanders",
    "count_green_commanders",
    "avg_commander_color_count",
    "max_commander_color_count",
    "unique_commander_color_count",
    "commander_color_data_missing_count",
]

OUTCOME_V3_DRAW_FEATURES = [
    "is_topdeck_invitational_family",
    "is_midseason_showdown_family",
    "is_commander_invitational_family",
    "is_invitational_like_family",
    "is_championship_like_family",
    "is_qualifier_like_family",
    "is_redemption_like_family",
    "is_league_like_family",
    "is_open_like_family",
    "is_high_stakes_like_family",
    "elite_count_1600_x_cut_fraction",
    "elite_count_1700_x_cut_fraction",
    "elite_count_1800_x_cut_fraction",
    "elite_count_1700_x_series_prior",
    "elite_count_1800_x_series_prior",
    "all_players_1700_plus",
    "all_players_1800_plus",
    "top2_mean_elo_x_series_prior",
    "top3_mean_elo_x_series_prior",
    "top3_mean_elo_x_round_number",
    "mean_elo_x_global_recent_draw_rate_90d",
    "series_minus_global_prior",
    "series_minus_global_prior_abs",
    "topdeck_invitational_x_series_prior",
    "midseason_showdown_x_series_prior",
    "invitational_like_x_series_prior",
    "high_stakes_like_x_series_prior",
    "invitational_like_x_high1700",
    "high_stakes_like_x_high1700",
    "high_stakes_like_x_cut_fraction",
    "high_stakes_like_x_round_number",
    "cut_or_bye_pressure_count",
    "draw_locks_cut_or_bye",
    "draw_hurts_cut_or_bye_status",
    "asymmetric_cut_or_bye_incentive",
    "draw_as_good_as_win_cut_or_bye_count",
    "must_win_cut_or_bye_count",
]

ALL_DRAW_FEATURES.extend(OUTCOME_V3_DRAW_FEATURES)

COMMANDER_DRAW_FEATURES = {
    "count_white_commanders",
    "count_blue_commanders",
    "count_black_commanders",
    "count_red_commanders",
    "count_green_commanders",
    "avg_commander_color_count",
    "max_commander_color_count",
    "unique_commander_color_count",
    "commander_color_data_missing_count",
}

LIVE_DEFAULTED_DRAW_FEATURES = {
    "global_recent_draw_rate_90d",
    "series_prior_draw_rate",
    "series_events_seen",
    "state_prior_draw_rate",
    "country_prior_draw_rate",
    "series_prior_draw_rate_smoothed_50",
    "series_prior_draw_rate_smoothed_100",
    "series_prior_draw_rate_smoothed_250",
    "series_prior_draw_rate_smoothed_500",
    "series_events_seen_log",
    "avg_player_prior_draw_smoothed_50",
    "median_player_prior_draw_smoothed_50",
    "max_player_prior_draw_smoothed_50",
    "round_size_cut_prior_draw_rate_smoothed_100",
    "pod_size_series_prior_draw_rate",
    "series_pod_size_prior_draw_rate_smoothed_100",
    "series_prior_draw_rate_residual",
}

TOPDECK_ELO_DRAW_FEATURES = {
    "topdeck_elo_spread",
    "topdeck_elo_mean",
    "topdeck_elo_std",
    "topdeck_elo_missing_count",
    "topdeck_elo_minus_internal_mean",
}

DEFAULT_EXCLUDED_DRAW_FEATURES = (
    COMMANDER_DRAW_FEATURES | LIVE_DEFAULTED_DRAW_FEATURES | TOPDECK_ELO_DRAW_FEATURES | set(OUTCOME_V3_DRAW_FEATURES)
)

DEFAULT_DRAW_MODEL_FEATURES = [
    feature for feature in ALL_DRAW_FEATURES if feature not in DEFAULT_EXCLUDED_DRAW_FEATURES
]


@dataclass(slots=True)
class SimPlayer:
    player_id: str
    name: str
    elo: float
    topdeck_id: str | None = None
    topdeck_elo: float | None = None
    commander_colors: tuple[str, ...] = ()
    tiebreak_seed: int = 0


@dataclass(slots=True)
class StandingRow:
    player_id: str
    points: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    pods_played: int = 0
    bye_count: int = 0
    opponents: set[str] = field(default_factory=set)


@dataclass(slots=True)
class Pod:
    round_index: int
    table_number: int
    player_ids: list[str]
    round_name: str | None = None
    seats_by_player: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class PodResult:
    round_index: int
    table_number: int
    player_ids: list[str]
    is_draw: bool
    winner_id: str | None
    win_probabilities: tuple[float, ...]
    draw_probability: float


@dataclass(slots=True)
class TournamentSpec:
    tournament_id: str
    name: str
    start_date: datetime
    swiss_rounds: int
    top_cut: int
    player_count: int
    pod_size: int = 4
    repeat_avoidance_max_pods: int | None = None
    state: str | None = None
    country: str | None = None
    drop_after_round: int | None = None
    drop_min_points: int | None = None


@dataclass(slots=True)
class TournamentContext:
    start_date: datetime | None = None
    player_count: int = 0
    series_key: str = "unknown_series"
    state_key: str = ""
    country_key: str = ""
    top_cut: int = 0
    max_rounds: int = 0


@dataclass(slots=True)
class PlayerHistory:
    draw_rate: float = 0.0
    win_rate: float = 0.0
    decisive_rate: float = 0.0
    games_played: int = 0


@dataclass(slots=True)
class FeatureContext:
    player_history: dict[str, PlayerHistory] = field(default_factory=dict)
    tournament_pair_meetings: dict[tuple[str, str], int] = field(default_factory=dict)
    global_pair_meetings: dict[tuple[str, str], int] = field(default_factory=dict)
    series_prior_draw_rate: float = 0.0
    series_events_seen: int = 0
    state_prior_draw_rate: float = 0.0
    country_prior_draw_rate: float = 0.0
    global_recent_draw_rate_90d: float = 0.0


@dataclass(slots=True)
class RoundFeatureSnapshot:
    round_number: int
    swiss_progress: float
    rounds_remaining: int
    month: int
    quarter: int
    tournament_size: int
    size_bucket: int
    field_size: int
    cut_fraction: float
    cut_size_bucket: int
    cut_line_percentile: float
    cut_line_points: int
    expected_cut_line_points: float
    max_future_points: int
    bubble_margin: float
    points_by_player: dict[str, int]
    point_percentiles: dict[str, float]
    estimated_omw_by_player: dict[str, float]
    same_points_omw_percentile_by_player: dict[str, float]
    current_rank_by_player: dict[str, int]
    draw_secure_rank_by_player: dict[str, int]
    win_secure_rank_by_player: dict[str, int]


@dataclass(slots=True)
class TournamentState:
    spec: TournamentSpec
    players: dict[str, SimPlayer]
    standings: dict[str, StandingRow]
    completed_pods: list[PodResult] = field(default_factory=list)
    completed_pod_count: int = 0
    current_round_index: int = 0
    feature_context: FeatureContext = field(default_factory=FeatureContext)
    eligible_player_ids: set[str] | None = None
    fast_live_mode: bool = False
    track_round_stats: bool = True
    round_draw_counts: dict[int, int] = field(default_factory=dict)
    round_pod_counts: dict[int, int] = field(default_factory=dict)
    standings_random_tiebreakers: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class SimulationSummary:
    win_counts: dict[str, float]
    top_cut_counts: dict[str, float]
    expected_points_total: dict[str, float]
    expected_finish_total: dict[str, float]
    round_draw_counts: dict[int, int]
    round_pod_counts: dict[int, int]
    simulations: int
    advancement_counts: dict[int, dict[str, float]] = field(default_factory=dict)
    top_cut_line_point_counts: dict[int, int] = field(default_factory=dict)
    bye_line_point_counts: dict[int, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "win_probability": {
                player_id: count / self.simulations for player_id, count in self.win_counts.items()
            },
            "top_cut_probability": {
                player_id: count / self.simulations for player_id, count in self.top_cut_counts.items()
            },
            "advancement_probability": {
                cut_size: {
                    player_id: count / self.simulations for player_id, count in player_counts.items()
                }
                for cut_size, player_counts in self.advancement_counts.items()
            },
            "expected_points": {
                player_id: total / self.simulations for player_id, total in self.expected_points_total.items()
            },
            "expected_finish": {
                player_id: total / self.simulations for player_id, total in self.expected_finish_total.items()
            },
            "round_draw_rate": {
                round_index: (
                    self.round_draw_counts.get(round_index, 0) / self.round_pod_counts.get(round_index, 1)
                )
                for round_index in self.round_pod_counts
            },
            "point_requirements": {
                "top_cut": [
                    {"points": points, "probability": count / self.simulations, "count": count}
                    for points, count in sorted(self.top_cut_line_point_counts.items())
                ],
                "bye": [
                    {"points": points, "probability": count / self.simulations, "count": count}
                    for points, count in sorted(self.bye_line_point_counts.items())
                ],
            },
            "simulations": self.simulations,
        }
