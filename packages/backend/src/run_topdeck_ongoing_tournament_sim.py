"""CLI for ongoing TopDeck simulations; helpers re-exported for compatibility."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ingest import TopDeckClient, load_local_env
from ongoing_tournament_execution import (
    STREAM_EMIT_SIMULATION_INTERVAL,
    STREAM_INITIAL_EMIT_SIMULATIONS,
    run_live_monte_carlo,
    run_live_monte_carlo_stream,
)
from ongoing_tournament_inputs import (
    DEFAULT_PREPARED_STATE_CACHE_DIR,
    PREPARED_STATE_CACHE_VERSION,
    collect_players,
    eligible_player_count,
    extract_numeric_value,
    fetch_event_page_html,
    fetch_existing_players,
    infer_structure,
    load_prepared_state_cache,
    parse_start_date,
    parse_table_number,
    prepared_state_cache_path,
    relevant_advancement_sizes,
    save_prepared_state_cache,
    standings_tiebreak_seed_map,
    tournament_state_fingerprint,
)
from ongoing_tournament_state import (
    build_base_state,
    build_pods_for_round,
    build_result_for_table,
    split_rounds,
    table_active,
    table_completed,
    table_is_bye,
    update_elos_for_result,
)
from run_historical_tournament_sim import (
    build_feature_context,
    fetch_historical_point_requirement_baseline,
)
from sim_engine import (
    apply_points_drop_if_due,
)
from sim_models import (
    DEFAULT_DRAW_MODEL_PATH,
    load_candidate_winner_model_artifact,
    load_draw_model_artifact,
)
from sim_types import FeatureContext
from tournament_sim_runner import (
    build_common_output,
    run_simulation_from_state,
)

__all__ = [
    "DEFAULT_PREPARED_STATE_CACHE_DIR",
    "PREPARED_STATE_CACHE_VERSION",
    "STREAM_INITIAL_EMIT_SIMULATIONS",
    "STREAM_EMIT_SIMULATION_INTERVAL",
    "DEFAULT_DRAW_MODEL_PATH",
    "relevant_advancement_sizes",
    "eligible_player_count",
    "fetch_event_page_html",
    "extract_numeric_value",
    "infer_structure",
    "collect_players",
    "tournament_state_fingerprint",
    "prepared_state_cache_path",
    "load_prepared_state_cache",
    "save_prepared_state_cache",
    "standings_tiebreak_seed_map",
    "fetch_existing_players",
    "parse_start_date",
    "parse_table_number",
    "build_pods_for_round",
    "table_is_bye",
    "table_completed",
    "table_active",
    "build_result_for_table",
    "update_elos_for_result",
    "split_rounds",
    "build_base_state",
    "run_live_monte_carlo",
    "run_live_monte_carlo_stream",
    "build_arg_parser",
    "main",
]


def build_arg_parser() -> argparse.ArgumentParser:
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
        help=(
            "Run repeat-opponent swap optimization only when generated Swiss pod count is at "
            "or below this value. Use 0 to disable."
        ),
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
    return parser


def main() -> None:
    parser = build_arg_parser()
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
    event_html = (
        "" if args.swiss_rounds is not None and args.top_cut is not None else fetch_event_page_html(args.event_id)
    )
    swiss_rounds, top_cut = infer_structure(
        tournament,
        event_html,
        swiss_rounds_override=args.swiss_rounds,
        top_cut_override=args.top_cut,
    )

    player_names = collect_players(tournament)
    topdeck_ids = sorted(player_names)
    from supabase_client import get_supabase_client  # local import to keep script entry focused

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
        client = get_supabase_client(url=os.environ["SUPABASE_URL"], key=os.environ["SUPABASE_SERVICE_KEY"])
        existing_players = fetch_existing_players(client, topdeck_ids)
        player_records = {
            topdeck_id: existing_players.get(topdeck_id)
            or {"id": f"topdeck:{topdeck_id}", "name": player_names[topdeck_id]}
            for topdeck_id in topdeck_ids
        }
        known_player_ids = [
            record["id"] for record in player_records.values() if not record["id"].startswith("topdeck:")
        ]
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
        client or get_supabase_client(url=os.environ["SUPABASE_URL"], key=os.environ["SUPABASE_SERVICE_KEY"]),
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
