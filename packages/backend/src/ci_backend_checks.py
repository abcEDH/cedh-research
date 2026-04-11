"""Backend maintenance validations used by GitHub Actions and local runs."""

from __future__ import annotations

import argparse
import json
import os
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

import requests

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2
PAGE_SIZE = 100
STATE_SAMPLE_SIZE = 25


VIEW_SPECS: list[tuple[str, int]] = [
    ("commander_stats", 10),
    ("seat_position_stats", 4),
    ("commander_seat_stats", 10),
    ("card_frequencies_global", 100),
    ("card_frequencies_by_commander", 100),
    ("trap_cards_report", 1),
    ("spice_cards_report", 1),
    ("seat_survival_by_commander", 10),
    ("seat_survival_by_round", 4),
    ("commander_survival_curve", 10),
    ("commander_tournament_depth", 10),
    ("player_survival_stats", 10),
    ("commander_meta_monthly", 5),
    ("commander_momentum", 1),
    ("commander_first_appearances", 10),
    ("survival_summary", 10),
    ("regional_elo_player_stats", 10),
    ("regional_elo_regions", 2),
    ("regional_elo_game_event_log", 100),
]

RPC_SPECS: list[tuple[str, dict[str, Any], bool, tuple[str, ...]]] = [
    (
        "get_notable_players_for_commander",
        {"p_commander_id": "00000000-0000-0000-0000-000000000000"},
        False,
        ("player_id", "player_name", "win_rate", "entries"),
    ),
    (
        "get_commander_matchups",
        {"p_commander_id": "00000000-0000-0000-0000-000000000000"},
        False,
        ("opponent_commander_name", "games_played", "wins", "losses"),
    ),
    (
        "get_commanders_for_card",
        {"p_card_name": "Sol Ring"},
        True,
        ("commander_id", "commander_name", "deck_count", "inclusion_rate"),
    ),
]

TABLE_SPECS: list[tuple[str, int, bool]] = [
    ("tournaments", 50, False),
    ("commanders", 100, False),
    ("tournament_entries", 3000, False),
    ("games", 5000, False),
    ("game_participants", 15000, False),
    ("players", 2000, False),
    ("regional_elo_state_activity", 10, True),
    ("regional_elo_game_events", 100, True),
]


@dataclass(frozen=True)
class BenchmarkRequest:
    method: str
    url: str
    params: dict[str, Any] | None = None
    json_body: dict[str, Any] | None = None


@dataclass(frozen=True)
class BenchmarkFixture:
    commander_id: str
    commander_name: str
    card_name: str
    region_key: str
    region_player_id: str


@dataclass(frozen=True)
class BenchmarkSpec:
    name: str
    request_builder: Callable[[str, BenchmarkFixture], BenchmarkRequest]
    expected_columns: tuple[str, ...]
    min_rows: int = 1
    smoke: bool = True


@dataclass(frozen=True)
class BenchmarkOutcome:
    name: str
    runs: int
    row_count: int
    columns: tuple[str, ...]
    best_ms: float
    median_ms: float
    worst_ms: float
    passed: bool
    notes: tuple[str, ...] = ()
    error: str | None = None


BENCHMARK_RUNS_DEFAULT = 3
BENCHMARK_WARMUPS_DEFAULT = 1
BENCHMARK_FAILURE_REGRESSION_PCT_DEFAULT = 25.0


def _rest_url(supabase_url: str, path: str) -> str:
    return f"{supabase_url.rstrip('/')}/rest/v1/{path.lstrip('/')}"


def _select_params(
    select: str,
    *,
    limit: int | None = None,
    order: str | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"select": select}
    if limit is not None:
        params["limit"] = limit
    if order is not None:
        params["order"] = order
    if offset is not None:
        params["offset"] = offset
    return params


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _fetch_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: int = 30,
) -> requests.Response:
    return request_with_retry(
        method,
        url,
        session=session,
        headers=headers,
        params=params,
        json=json_body,
        timeout=timeout,
    )


def resolve_benchmark_fixture(supabase_url: str, headers: dict[str, str]) -> BenchmarkFixture:
    session = requests.Session()

    candidate_sources = [
        (
            "commander_weekly_trends",
            _select_params("commander_id,commander_name,entries", limit=25, order="entries.desc"),
        ),
        (
            "commander_monthly_trends",
            _select_params("commander_id,commander_name,entries", limit=25, order="entries.desc"),
        ),
        (
            "commander_stats",
            _select_params("commander_id,commander_name,total_entries", limit=25, order="total_entries.desc"),
        ),
    ]

    commander_rows: list[dict[str, Any]] = []
    for source, params in candidate_sources:
        commander_resp = _fetch_json(
            session,
            "GET",
            _rest_url(supabase_url, source),
            headers=headers,
            params=params,
        )
        if commander_resp.status_code != 200:
            failure = response_failure(commander_resp)
            raise RuntimeError(f"Unable to resolve benchmark commander fixture from {source}: {failure}")
        commander_rows = commander_resp.json()
        if commander_rows:
            break

    if not commander_rows:
        raise RuntimeError("Unable to resolve benchmark commander fixture: no commander sources returned rows")

    preferred_commander_rows = [
        row for row in commander_rows if str(row.get("commander_name", "")).strip().lower() != "unknown commander"
    ]
    if preferred_commander_rows:
        commander_rows = preferred_commander_rows

    chosen_commander: dict[str, Any] | None = None
    for commander_row in commander_rows:
        commander_id = str(commander_row["commander_id"])
        notable_resp = _fetch_json(
            session,
            "POST",
            _rest_url(supabase_url, "rpc/get_notable_players_for_commander"),
            headers=headers,
            json_body={"p_commander_id": commander_id},
        )
        matchups_resp = _fetch_json(
            session,
            "POST",
            _rest_url(supabase_url, "rpc/get_commander_matchups"),
            headers=headers,
            json_body={"p_commander_id": commander_id},
        )
        performance_resp = _fetch_json(
            session,
            "GET",
            _rest_url(supabase_url, "card_performance_by_commander"),
            headers=headers,
            params=_select_params(
                "commander_id,commander,card_name,deck_count,total_decks,inclusion_rate,avg_win_rate,baseline_win_rate,win_rate_delta,std_win_rate,top_16_count,top_cut_count,top_16_rate,avg_standing,performance_tier",
                limit=1,
                order="win_rate_delta.desc",
            )
            | {"commander_id": f"eq.{commander_id}"},
        )
        if (
            notable_resp.status_code == 200
            and matchups_resp.status_code == 200
            and performance_resp.status_code == 200
            and notable_resp.json()
            and matchups_resp.json()
            and performance_resp.json()
        ):
            chosen_commander = commander_row
            break

    if chosen_commander is None:
        chosen_commander = commander_rows[0]

    card_resp = _fetch_json(
        session,
        "GET",
        _rest_url(supabase_url, "card_frequencies_global"),
        headers=headers,
        params=_select_params("card_name,deck_count", limit=1, order="deck_count.desc"),
    )
    if card_resp.status_code != 200:
        raise RuntimeError(f"Unable to resolve benchmark card fixture: {response_failure(card_resp)}")

    card_rows = card_resp.json()
    if not card_rows:
        raise RuntimeError("Unable to resolve benchmark card fixture: card_frequencies_global returned no rows")

    regional_rows: list[dict[str, Any]] = []
    for source in ("regional_elo_player_stats", "regional_elo_leaderboard"):
        regional_resp = _fetch_json(
            session,
            "GET",
            _rest_url(supabase_url, source),
            headers=headers,
            params={
                **_select_params("region_key,player_id,games_played", limit=PAGE_SIZE, order="games_played.desc"),
                "region_type": "eq.state",
            },
        )
        if regional_resp.status_code != 200:
            raise RuntimeError(
                f"Unable to resolve benchmark regional fixture from {source}: {response_failure(regional_resp)}"
            )

        regional_rows = [row for row in regional_resp.json() if row.get("region_key") and row.get("player_id")]
        if regional_rows:
            break

    if not regional_rows:
        raise RuntimeError("Unable to resolve benchmark regional fixture: no state leaderboard rows found")

    commander_row = chosen_commander
    card_row = card_rows[0]
    regional_row = regional_rows[0]
    return BenchmarkFixture(
        commander_id=str(commander_row["commander_id"]),
        commander_name=str(commander_row["commander_name"]),
        card_name=str(card_row["card_name"]),
        region_key=str(regional_row["region_key"]),
        region_player_id=str(regional_row["player_id"]),
    )


def benchmark_specs() -> list[BenchmarkSpec]:
    return [
        BenchmarkSpec(
            name="commander_stats",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "commander_stats"),
                params=_select_params(
                    "commander_id,commander_name,total_entries,tournaments_played,total_wins,total_losses,total_draws,avg_win_rate,top_16_count,conversion_rate_top_16,top_cut_count,conversion_rate_top_cut",
                    limit=1,
                    order="total_entries.desc",
                ),
            ),
            expected_columns=(
                "commander_id",
                "commander_name",
                "total_entries",
                "tournaments_played",
                "total_wins",
                "total_losses",
                "total_draws",
                "avg_win_rate",
                "top_16_count",
                "conversion_rate_top_16",
                "top_cut_count",
                "conversion_rate_top_cut",
            ),
        ),
        BenchmarkSpec(
            name="commander_weekly_trends",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "commander_weekly_trends"),
                params={
                    **_select_params(
                        ("commander_id,week_key,week_start_date,entries,wins,losses,draws,win_rate"),
                        limit=25,
                        order="week_start_date.desc",
                    ),
                    "commander_id": f"eq.{fixture.commander_id}",
                },
            ),
            expected_columns=(
                "commander_id",
                "week_key",
                "week_start_date",
                "entries",
                "wins",
                "losses",
                "draws",
                "win_rate",
            ),
        ),
        BenchmarkSpec(
            name="commander_monthly_trends",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "commander_monthly_trends"),
                params={
                    **_select_params(
                        ("commander_id,month_key,month_start_date,entries,wins,losses,draws,win_rate"),
                        limit=25,
                        order="month_start_date.desc",
                    ),
                    "commander_id": f"eq.{fixture.commander_id}",
                },
            ),
            expected_columns=(
                "commander_id",
                "month_key",
                "month_start_date",
                "entries",
                "wins",
                "losses",
                "draws",
                "win_rate",
            ),
        ),
        BenchmarkSpec(
            name="regional_elo_leaderboard_state",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "regional_elo_leaderboard"),
                params={
                    **_select_params(
                        "region_type,region_key,player_id,player_name,topdeck_id,rating,games_played,wins,draws,losses,last_game_date,rank",
                        limit=25,
                        order="games_played.desc",
                    ),
                    "region_type": "eq.state",
                    "region_key": f"eq.{fixture.region_key}",
                },
            ),
            expected_columns=(
                "region_type",
                "region_key",
                "player_id",
                "player_name",
                "topdeck_id",
                "rating",
                "games_played",
                "wins",
                "draws",
                "losses",
                "last_game_date",
                "rank",
            ),
            smoke=False,
        ),
        BenchmarkSpec(
            name="regional_elo_player_stats",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "regional_elo_player_stats"),
                params={
                    **_select_params(
                        (
                            "region_type,region_key,player_id,games_played,wins,draws,"
                            "losses,last_game_date,activity_score,games_30d,games_90d,"
                            "games_365d"
                        ),
                        limit=1,
                    ),
                    "region_type": "eq.state",
                    "region_key": f"eq.{fixture.region_key}",
                    "player_id": f"eq.{fixture.region_player_id}",
                },
            ),
            expected_columns=(
                "region_type",
                "region_key",
                "player_id",
                "games_played",
                "wins",
                "draws",
                "losses",
                "last_game_date",
                "activity_score",
                "games_30d",
                "games_90d",
                "games_365d",
            ),
        ),
        BenchmarkSpec(
            name="regional_elo_regions",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "regional_elo_regions"),
                params=_select_params(
                    "region_type,region_key,player_count,updated_at",
                    limit=100,
                    order="region_key.asc",
                ),
            ),
            expected_columns=(
                "region_type",
                "region_key",
                "player_count",
                "updated_at",
            ),
        ),
        BenchmarkSpec(
            name="regional_elo_data_validity",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "regional_elo_data_validity"),
                params=_select_params(
                    (
                        "region_type,region_key,scope,total_tournaments,"
                        "tournaments_with_state,tournaments_missing_state,total_games,"
                        "included_games,excluded_games_missing_state,"
                        "excluded_games_with_byes,excluded_games_insufficient_players,"
                        "included_players,earliest_game_date,latest_game_date"
                    ),
                    limit=100,
                    order="region_key.asc",
                ),
            ),
            expected_columns=(
                "region_type",
                "region_key",
                "scope",
                "total_tournaments",
                "tournaments_with_state",
                "tournaments_missing_state",
                "total_games",
                "included_games",
                "excluded_games_missing_state",
                "excluded_games_with_byes",
                "excluded_games_insufficient_players",
                "included_players",
                "earliest_game_date",
                "latest_game_date",
            ),
            smoke=False,
        ),
        BenchmarkSpec(
            name="card_frequencies_global",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "card_frequencies_global"),
                params=_select_params(
                    "card_name,deck_count,total_decks,inclusion_rate,commander_count,tier",
                    limit=25,
                    order="deck_count.desc",
                ),
            ),
            expected_columns=(
                "card_name",
                "deck_count",
                "total_decks",
                "inclusion_rate",
                "commander_count",
                "tier",
            ),
        ),
        BenchmarkSpec(
            name="card_frequencies_by_commander",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "card_frequencies_by_commander"),
                params={
                    **_select_params(
                        ("commander_id,commander,card_name,deck_count,total_decks,inclusion_rate,tier"),
                        limit=25,
                        order="deck_count.desc",
                    ),
                    "commander_id": f"eq.{fixture.commander_id}",
                },
            ),
            expected_columns=(
                "commander_id",
                "commander",
                "card_name",
                "deck_count",
                "total_decks",
                "inclusion_rate",
                "tier",
            ),
        ),
        BenchmarkSpec(
            name="card_performance_by_commander",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "card_performance_by_commander"),
                params={
                    **_select_params(
                        (
                            "commander_id,commander,card_name,deck_count,"
                            "total_decks,inclusion_rate,avg_win_rate,baseline_win_rate,"
                            "win_rate_delta,std_win_rate,top_16_count,top_cut_count,"
                            "top_16_rate,avg_standing,performance_tier"
                        ),
                        limit=25,
                        order="win_rate_delta.desc",
                    ),
                    "commander_id": f"eq.{fixture.commander_id}",
                },
            ),
            expected_columns=(
                "commander_id",
                "commander",
                "card_name",
                "deck_count",
                "total_decks",
                "inclusion_rate",
                "avg_win_rate",
                "baseline_win_rate",
                "win_rate_delta",
                "std_win_rate",
                "top_16_count",
                "top_cut_count",
                "top_16_rate",
                "avg_standing",
                "performance_tier",
            ),
        ),
        BenchmarkSpec(
            name="get_notable_players_for_commander",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "POST",
                _rest_url(supabase_url, "rpc/get_notable_players_for_commander"),
                json_body={"p_commander_id": fixture.commander_id},
            ),
            expected_columns=(
                "player_id",
                "player_name",
                "topdeck_handle",
                "topdeck_id",
                "entries",
                "total_wins",
                "total_losses",
                "total_draws",
                "total_games",
                "win_rate",
                "top_16_count",
                "avg_standing",
            ),
        ),
        BenchmarkSpec(
            name="get_commander_matchups",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "POST",
                _rest_url(supabase_url, "rpc/get_commander_matchups"),
                json_body={"p_commander_id": fixture.commander_id},
            ),
            expected_columns=(
                "opponent_commander_id",
                "opponent_commander_name",
                "games_played",
                "wins",
                "losses",
                "draws",
                "win_rate",
                "loss_rate",
                "draw_rate",
                "expected_win_rate",
                "win_rate_vs_expected",
                "is_statistically_significant",
                "confidence_level",
            ),
        ),
        BenchmarkSpec(
            name="commander_meta_monthly",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "commander_meta_monthly"),
                params=_select_params(
                    "month,commander_name,entries,meta_share,avg_win_rate,top_16_count,top_16_rate",
                    limit=25,
                    order="month.desc",
                ),
            ),
            expected_columns=(
                "month",
                "commander_name",
                "entries",
                "meta_share",
                "avg_win_rate",
                "top_16_count",
                "top_16_rate",
            ),
        ),
        BenchmarkSpec(
            name="commander_momentum",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "commander_momentum"),
                params=_select_params(
                    (
                        "month,commander_name,entries,meta_share,prev_meta_share,"
                        "meta_share_delta,avg_win_rate,prev_win_rate,win_rate_delta,"
                        "momentum_score"
                    ),
                    limit=25,
                    order="momentum_score.desc",
                ),
            ),
            expected_columns=(
                "month",
                "commander_name",
                "entries",
                "meta_share",
                "prev_meta_share",
                "meta_share_delta",
                "avg_win_rate",
                "prev_win_rate",
                "win_rate_delta",
                "momentum_score",
            ),
        ),
        BenchmarkSpec(
            name="commander_first_appearances",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "commander_first_appearances"),
                params=_select_params(
                    "commander_name,first_seen,total_entries,tournaments,avg_win_rate,top_16s",
                    limit=25,
                    order="first_seen.desc",
                ),
            ),
            expected_columns=(
                "commander_name",
                "first_seen",
                "total_entries",
                "tournaments",
                "avg_win_rate",
                "top_16s",
            ),
        ),
        BenchmarkSpec(
            name="survival_summary",
            request_builder=lambda supabase_url, fixture: BenchmarkRequest(
                "GET",
                _rest_url(supabase_url, "survival_summary"),
                params=_select_params(
                    "commander_name,total_entries,tournaments,total_games,overall_win_rate,avg_percentile,top_cut_rate,tournament_win_rate,recent_entries,recent_win_rate",
                    limit=25,
                    order="total_entries.desc",
                ),
            ),
            expected_columns=(
                "commander_name",
                "total_entries",
                "tournaments",
                "total_games",
                "overall_win_rate",
                "avg_percentile",
                "top_cut_rate",
                "tournament_win_rate",
                "recent_entries",
                "recent_win_rate",
            ),
        ),
    ]


def _benchmark_response_columns(response_rows: list[dict[str, Any]]) -> tuple[str, ...]:
    if not response_rows:
        return ()
    return tuple(response_rows[0].keys())


def _run_benchmark_request(
    session: requests.Session,
    request: BenchmarkRequest,
    headers: dict[str, str],
) -> tuple[float, list[dict[str, Any]]]:
    start = time.perf_counter()
    resp = _fetch_json(
        session,
        request.method,
        request.url,
        headers=headers,
        params=request.params,
        json_body=request.json_body,
        timeout=60,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if resp.status_code != 200:
        raise RuntimeError(response_failure(resp))
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Expected list response but received {type(data).__name__}")
    return elapsed_ms, data


def _serialize_benchmark_results(
    results: list[BenchmarkOutcome],
    *,
    fixture: BenchmarkFixture,
    runs: int,
    warmups: int,
) -> dict[str, Any]:
    return {
        "captured_at": utc_now_iso(),
        "runs": runs,
        "warmups": warmups,
        "fixture": asdict(fixture),
        "results": [asdict(result) for result in results],
    }


def _compare_benchmark_results(
    current: list[BenchmarkOutcome],
    baseline_path: Path,
    *,
    max_regression_pct: float,
) -> list[str]:
    baseline_data = json.loads(baseline_path.read_text())
    baseline_rows = {row["name"]: row for row in baseline_data.get("results", [])}
    failures: list[str] = []

    for result in current:
        baseline = baseline_rows.get(result.name)
        if baseline is None:
            failures.append(f"{result.name}: missing from baseline {baseline_path}")
            continue

        baseline_columns = tuple(baseline.get("columns", []))
        if result.columns != baseline_columns:
            failures.append(
                f"{result.name}: column drift current={list(result.columns)} baseline={list(baseline_columns)}"
            )

        if result.row_count != baseline.get("row_count"):
            failures.append(
                f"{result.name}: row-count drift current={result.row_count} baseline={baseline.get('row_count')}"
            )

        baseline_median = float(baseline.get("median_ms", 0.0))
        if baseline_median > 0:
            regression_pct = ((result.median_ms - baseline_median) / baseline_median) * 100.0
            if regression_pct > max_regression_pct:
                failures.append(
                    f"{result.name}: median regression {regression_pct:.1f}% "
                    f"(current={result.median_ms:.1f}ms baseline={baseline_median:.1f}ms)"
                )

    return failures


def benchmark_queries(
    *,
    compare_to: str | None = None,
    output: str | None = None,
    runs: int = BENCHMARK_RUNS_DEFAULT,
    warmups: int = BENCHMARK_WARMUPS_DEFAULT,
    max_regression_pct: float = BENCHMARK_FAILURE_REGRESSION_PCT_DEFAULT,
    only: set[str] | None = None,
    smoke_only: bool = False,
) -> None:
    supabase_url, _ = get_supabase_env()
    headers = supabase_headers()
    fixture = resolve_benchmark_fixture(supabase_url, headers)
    session = requests.Session()

    specs = [
        spec for spec in benchmark_specs() if (only is None or spec.name in only) and (not smoke_only or spec.smoke)
    ]
    if not specs:
        raise SystemExit("No benchmark specs matched the requested filters.")

    outcomes: list[BenchmarkOutcome] = []
    failures: list[str] = []

    print("=" * 60)
    print("BENCHMARKING ANALYTICS SURFACES")
    print("=" * 60)
    print(
        f"Fixture: commander={fixture.commander_name} ({fixture.commander_id}), "
        f"card={fixture.card_name}, state={fixture.region_key}"
    )
    print(f"Warmups: {warmups}, runs: {runs}")
    print()

    for spec in specs:
        request = spec.request_builder(supabase_url, fixture)
        run_times: list[float] = []
        row_count = 0
        actual_columns: tuple[str, ...] = ()
        sample_notes: list[str] = []
        error_message: str | None = None

        try:
            for _ in range(warmups):
                elapsed_ms, data = _run_benchmark_request(session, request, headers)
                if not data:
                    raise RuntimeError("warmup returned no data")

            for _ in range(runs):
                elapsed_ms, data = _run_benchmark_request(session, request, headers)
                run_times.append(elapsed_ms)
                if not data:
                    sample_notes.append("empty result set")
                    continue
                row_count = len(data)
                actual_columns = _benchmark_response_columns(data)
        except Exception as exc:
            error_message = str(exc)
            failures.append(f"{spec.name}: {error_message}")

        passed = error_message is None
        if error_message is None:
            if row_count < spec.min_rows:
                passed = False
                failures.append(f"{spec.name}: row count {row_count} < expected minimum {spec.min_rows}")
            if actual_columns != spec.expected_columns:
                passed = False
                failures.append(
                    f"{spec.name}: column drift current={list(actual_columns)} expected={list(spec.expected_columns)}"
                )

            if not run_times:
                passed = False
                failures.append(f"{spec.name}: no benchmark runs completed")

        outcome = BenchmarkOutcome(
            name=spec.name,
            runs=len(run_times),
            row_count=row_count,
            columns=actual_columns,
            best_ms=min(run_times) if run_times else 0.0,
            median_ms=median(run_times) if run_times else 0.0,
            worst_ms=max(run_times) if run_times else 0.0,
            passed=passed,
            notes=tuple(sample_notes),
            error=error_message,
        )
        outcomes.append(outcome)

    if compare_to:
        compare_failures = _compare_benchmark_results(outcomes, Path(compare_to), max_regression_pct=max_regression_pct)
        failures.extend(compare_failures)

    print(f"{'query':36} {'rows':>6} {'best ms':>10} {'median ms':>10} {'worst ms':>10}  status")
    for outcome in outcomes:
        status = "PASS" if outcome.passed else "FAIL"
        print(
            f"{outcome.name[:36]:36} {outcome.row_count:6d} "
            f"{outcome.best_ms:10.1f} {outcome.median_ms:10.1f} {outcome.worst_ms:10.1f}  {status}"
        )
        if outcome.error:
            print(f"{'':36} {'':6} {'':10} {'':10} {'':10}  error: {outcome.error}")
        if outcome.notes:
            for note in outcome.notes:
                print(f"{'':36} {'':6} {'':10} {'':10} {'':10}  note: {note}")

    print()
    print(
        f"Completed {len(outcomes)} benchmarks. "
        f"{sum(1 for result in outcomes if result.passed)} passed, "
        f"{sum(1 for result in outcomes if not result.passed)} failed."
    )

    if output:
        payload = _serialize_benchmark_results(outcomes, fixture=fixture, runs=runs, warmups=warmups)
        Path(output).write_text(json.dumps(payload, indent=2, sort_keys=True))
        print(f"Wrote benchmark results to {output}")

    if failures:
        print("\nBenchmark regression failures:")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print("\nBenchmark checks passed.")


def get_supabase_env() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY.")
    return url, key


def supabase_headers(*, count_prefer: str | None = None) -> dict[str, str]:
    _, key = get_supabase_env()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if count_prefer:
        headers["Prefer"] = count_prefer
    return headers


def request_with_retry(
    method: str,
    url: str,
    *,
    session: requests.Session | None = None,
    **kwargs: Any,
) -> requests.Response:
    last_response: requests.Response | None = None
    for attempt in range(RETRY_ATTEMPTS):
        request_fn = session.request if session is not None else requests.request
        response = request_fn(method, url, **kwargs)
        last_response = response
        if response.status_code < 500:
            return response
        if attempt < RETRY_ATTEMPTS - 1:
            time.sleep(RETRY_BACKOFF_SECONDS**attempt)
    assert last_response is not None
    return last_response


def response_failure(response: requests.Response) -> str:
    body = response.text[:500] if response.text else "<empty body>"
    return f"HTTP {response.status_code}: {body}"


def validate_views() -> None:
    supabase_url, _ = get_supabase_env()
    headers = supabase_headers()
    failed: list[tuple[str, str]] = []
    passed: list[str] = []

    print("=" * 60)
    print("VALIDATING VIEWS")
    print("=" * 60)

    for view_name, min_rows in VIEW_SPECS:
        try:
            url = f"{supabase_url}/rest/v1/{view_name}?select=*&limit=100"
            resp = request_with_retry("GET", url, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                row_count = len(data)
                if row_count >= min_rows:
                    print(f"✓ {view_name}: {row_count} rows (expected >= {min_rows})")
                    passed.append(view_name)
                else:
                    print(f"✗ {view_name}: {row_count} rows (expected >= {min_rows})")
                    failed.append((view_name, f"Only {row_count} rows"))
            else:
                reason = response_failure(resp)
                print(f"✗ {view_name}: {reason}")
                failed.append((view_name, reason))
        except Exception as exc:  # pragma: no cover - CI diagnostic path
            print(f"✗ {view_name}: {exc}")
            failed.append((view_name, str(exc)))

    print()
    print("=" * 60)
    print("VALIDATING RPC FUNCTIONS")
    print("=" * 60)

    for func_name, params, expect_data, expected_cols in RPC_SPECS:
        try:
            url = f"{supabase_url}/rest/v1/rpc/{func_name}"
            resp = request_with_retry("POST", url, headers=headers, json=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                rows = data if isinstance(data, list) else [data]
                row_count = len(rows)

                if expect_data and row_count == 0:
                    print(f"✗ {func_name}: Expected data but got empty result")
                    failed.append((func_name, "Expected data but got empty"))
                elif row_count > 0:
                    # Validate columns
                    actual_cols = set(rows[0].keys())
                    missing = [c for c in expected_cols if c not in actual_cols]
                    if missing:
                        print(f"✗ {func_name}: Missing columns {missing}")
                        failed.append((func_name, f"Missing columns: {missing}"))
                    else:
                        print(f"✓ {func_name}: {row_count} rows returned with valid schema")
                        passed.append(func_name)
                else:
                    print(f"✓ {func_name}: 0 rows returned (as expected for dummy ID)")
                    passed.append(func_name)
            else:
                reason = response_failure(resp)
                print(f"✗ {func_name}: {reason}")
                failed.append((func_name, reason))
        except Exception as exc:  # pragma: no cover - CI diagnostic path
            print(f"✗ {func_name}: {exc}")
            failed.append((func_name, str(exc)))

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nFailed items:")
        for item, reason in failed:
            print(f"  - {item}: {reason}")
        raise SystemExit(1)

    print("\nAll validations passed!")


def get_table_count(supabase_url: str, headers: dict[str, str], table_name: str) -> tuple[int, str]:
    methods = [
        ("HEAD", "count=exact", f"{supabase_url}/rest/v1/{table_name}?select=count", None),
        ("GET", "count=exact", f"{supabase_url}/rest/v1/{table_name}?select=id", {"limit": 1}),
        ("GET", "count=planned", f"{supabase_url}/rest/v1/{table_name}?select=id", {"limit": 1}),
        ("GET", "count=estimated", f"{supabase_url}/rest/v1/{table_name}?select=id", {"limit": 1}),
    ]

    errors: list[str] = []
    for method, prefer, url, params in methods:
        try:
            attempt_headers = headers.copy()
            attempt_headers["Prefer"] = prefer
            resp = requests.request(method, url, headers=attempt_headers, params=params, timeout=30)
            if resp.status_code not in (200, 206):
                errors.append(f"{method} {prefer}: HTTP {resp.status_code}")
                continue

            content_range = resp.headers.get("content-range", "0-0/0")
            count = int(content_range.split("/")[1])
            return count, f"{method} {prefer}"
        except Exception as exc:  # pragma: no cover - CI diagnostic path
            errors.append(f"{method} {prefer}: {exc}")

    raise RuntimeError("; ".join(errors))


def validate_data_integrity() -> None:
    supabase_url, _ = get_supabase_env()
    headers = supabase_headers(count_prefer="count=exact")
    failed: list[tuple[str, str]] = []

    print("=" * 60)
    print("DATA INTEGRITY CHECK")
    print("=" * 60)

    for table_name, min_count, optional in TABLE_SPECS:
        try:
            count, strategy = get_table_count(supabase_url, headers, table_name)
            status = "✓" if count >= min_count else "✗"
            print(f"{status} {table_name}: {count:,} rows (expected >= {min_count:,}; via {strategy})")
            if count < min_count:
                if optional:
                    print(f"  (Warning: Optional table {table_name} below threshold)")
                else:
                    failed.append((table_name, f"{count} < {min_count} via {strategy}"))
        except Exception as exc:  # pragma: no cover - CI diagnostic path
            if optional:
                print(f"○ {table_name}: Skipped (Optional table not found or error: {exc})")
            else:
                print(f"✗ {table_name}: {exc}")
                failed.append((table_name, str(exc)))

    print()
    if failed:
        print(f"Data integrity issues found: {len(failed)}")
        for item, reason in failed:
            print(f"  - {item}: {reason}")
        raise SystemExit(1)

    print("Data integrity check passed!")


def fetch_state_samples(supabase_url: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    player_stats_rows: list[dict[str, Any]] = []
    offset = 0

    while len(player_stats_rows) < STATE_SAMPLE_SIZE:
        stats_resp = request_with_retry(
            "GET",
            f"{supabase_url}/rest/v1/regional_elo_player_stats",
            headers=headers,
            params={
                "select": (
                    "region_type,region_key,player_id,games_played,wins,draws,losses,"
                    "primary_country_key,primary_region_key"
                ),
                "order": "games_played.desc",
                "limit": PAGE_SIZE,
                "offset": offset,
            },
            timeout=30,
        )
        if stats_resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch regional Elo player stats sample: {response_failure(stats_resp)}"
            )

        page_rows = stats_resp.json()
        player_stats_rows.extend(
            row for row in page_rows if row.get("region_type") == "state" and row.get("games_played", 0) > 0
        )

        if len(page_rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return player_stats_rows[:STATE_SAMPLE_SIZE]


def validate_regional_elo_consistency() -> None:
    supabase_url, _ = get_supabase_env()
    headers = supabase_headers()
    stat_rows = fetch_state_samples(supabase_url, headers)

    if not stat_rows:
        raise SystemExit("No regional Elo player stats rows found to validate.")

    failures: list[tuple[dict[str, Any], str]] = []
    for row in stat_rows:
        stats_resp = request_with_retry(
            "GET",
            f"{supabase_url}/rest/v1/regional_elo_state_activity",
            headers=headers,
            params={
                "select": "games_lifetime,wins,draws,losses",
                "region_type": f"eq.{row['region_type']}",
                "region_key": f"eq.{row['region_key']}",
                "player_id": f"eq.{row['player_id']}",
                "is_primary_state": "eq.true",
            },
            timeout=30,
        )
        if stats_resp.status_code != 200:
            failures.append((row, f"failed to fetch canonical state activity: {response_failure(stats_resp)}"))
            continue

        stats_rows = stats_resp.json()
        if not stats_rows:
            failures.append((row, "missing primary state activity row"))
            continue

        stats = stats_rows[0]
        comparisons = (
            ("games_played", "games_lifetime"),
            ("wins", "wins"),
            ("draws", "draws"),
            ("losses", "losses"),
        )
        for observed_field, canonical_field in comparisons:
            if row[observed_field] != stats[canonical_field]:
                failures.append(
                    (
                        row,
                        f"{observed_field}: player_stats={row[observed_field]} "
                        f"state_activity={stats[canonical_field]}",
                    )
                )
    if failures:
        print("Global Elo aggregate consistency check failed:")
        for row, reason in failures:
            print(f"  - {row['region_key']} / {row['player_id']}: {reason}")
        raise SystemExit(1)

    print(f"Validated {len(stat_rows)} regional Elo player stats rows against primary state activity.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run backend maintenance validations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("views", help="Validate backend views and RPC functions")
    subparsers.add_parser("data-integrity", help="Validate baseline data counts")
    subparsers.add_parser("regional-elo", help="Validate regional Elo consistency")
    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Benchmark analytics surfaces and optionally compare against a baseline file",
    )
    benchmark_parser.add_argument(
        "--compare-to",
        dest="compare_to",
        help="Optional JSON benchmark baseline to compare against",
    )
    benchmark_parser.add_argument(
        "--output",
        dest="output",
        help="Optional path to write the benchmark results JSON",
    )
    benchmark_parser.add_argument(
        "--runs",
        type=int,
        default=BENCHMARK_RUNS_DEFAULT,
        help=f"Number of timed runs per query (default: {BENCHMARK_RUNS_DEFAULT})",
    )
    benchmark_parser.add_argument(
        "--warmups",
        type=int,
        default=BENCHMARK_WARMUPS_DEFAULT,
        help=f"Number of warmup runs per query (default: {BENCHMARK_WARMUPS_DEFAULT})",
    )
    benchmark_parser.add_argument(
        "--max-regression-pct",
        type=float,
        default=BENCHMARK_FAILURE_REGRESSION_PCT_DEFAULT,
        help=(
            "Maximum allowed median regression percentage when comparing against a baseline "
            f"(default: {BENCHMARK_FAILURE_REGRESSION_PCT_DEFAULT})"
        ),
    )
    benchmark_parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Run only the named benchmark query. May be provided multiple times.",
    )
    benchmark_parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Run only the fast smoke-test benchmark queries. Skips known slow surfaces.",
    )
    subparsers.add_parser("all", help="Run all backend maintenance validations")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "views":
        validate_views()
    elif args.command == "data-integrity":
        validate_data_integrity()
    elif args.command == "regional-elo":
        validate_regional_elo_consistency()
    elif args.command == "benchmark":
        benchmark_queries(
            compare_to=args.compare_to,
            output=args.output,
            runs=args.runs,
            warmups=args.warmups,
            max_regression_pct=args.max_regression_pct,
            only=set(args.only) if args.only else None,
            smoke_only=args.smoke_only,
        )
    elif args.command == "all":
        validate_views()
        validate_data_integrity()
        validate_regional_elo_consistency()
    else:  # pragma: no cover - argparse enforces valid commands
        raise SystemExit(f"Unknown command: {args.command}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
