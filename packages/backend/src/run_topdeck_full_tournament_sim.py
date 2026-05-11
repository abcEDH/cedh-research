#!/usr/bin/env python3
"""Fast full-tournament TopDeck simulation using the parallel shared engine."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ingest import SupabaseClient, TopDeckClient, load_local_env
from run_historical_tournament_sim import (
    build_feature_context,
    fetch_historical_point_requirement_baseline,
)
from run_topdeck_ongoing_tournament_sim import (
    DEFAULT_DRAW_MODEL_PATH,
    build_base_state,
    collect_players,
    fetch_event_page_html,
    fetch_existing_players,
    infer_structure,
    parse_start_date,
)
from sim_models import load_draw_model_artifact
from sim_types import FeatureContext
from tournament_sim_runner import DEFAULT_ADVANCEMENT_SIZES, build_common_output, run_simulation_from_state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--draw-model-path", default=str(DEFAULT_DRAW_MODEL_PATH))
    parser.add_argument("--simulations", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--swiss-rounds", type=int, default=None)
    parser.add_argument("--top-cut", type=int, default=None)
    parser.add_argument("--repeat-avoidance-max-pods", type=int, default=32)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    load_local_env()
    topdeck = TopDeckClient(os.environ["TOPDECK_API_KEY"])
    tournament = topdeck.get_tournament(args.event_id)
    swiss_rounds, top_cut = infer_structure(
        tournament,
        fetch_event_page_html(args.event_id),
        swiss_rounds_override=args.swiss_rounds,
        top_cut_override=args.top_cut,
    )

    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])
    player_names = collect_players(tournament)
    topdeck_ids = sorted(player_names)
    existing_players = fetch_existing_players(client, topdeck_ids)
    player_records = {
        topdeck_id: existing_players.get(topdeck_id)
        or {"id": f"topdeck:{topdeck_id}", "name": player_names[topdeck_id]}
        for topdeck_id in topdeck_ids
    }
    known_player_ids = [
        record["id"]
        for record in player_records.values()
        if not record["id"].startswith("topdeck:")
    ]
    start_date = parse_start_date(tournament.get("startDate"))
    feature_context = (
        build_feature_context(client, known_player_ids, start_date.isoformat())
        if known_player_ids
        else FeatureContext()
    )

    state, active_round_index, active_round_pods, metadata = build_base_state(
        client,
        tournament,
        swiss_rounds=swiss_rounds,
        top_cut=top_cut,
        feature_context=feature_context,
        player_records=player_records,
        repeat_avoidance_max_pods=args.repeat_avoidance_max_pods,
    )
    state.fast_live_mode = True
    state.track_round_stats = True

    draw_model = load_draw_model_artifact(args.draw_model_path)
    summary = run_simulation_from_state(
        state,
        draw_model,
        simulations=args.simulations,
        seed=args.seed,
        workers=args.workers,
        start_round_index=active_round_index,
        locked_round_pods=active_round_pods,
        requested_advancement_sizes=DEFAULT_ADVANCEMENT_SIZES,
        collect_detailed_metrics=True,
    )
    historical_point_requirements = fetch_historical_point_requirement_baseline(
        client,
        active_player_count=len(state.eligible_player_ids or state.players),
        top_cut=state.spec.top_cut,
        swiss_rounds=state.spec.swiss_rounds,
        exclude_tournament_id=state.spec.tournament_id,
    )

    player_name_by_id = {player_id: player.name for player_id, player in state.players.items()}
    output = build_common_output(
        summary=summary,
        state=state,
        player_name_by_id=player_name_by_id,
        active_player_count=len(state.eligible_player_ids or state.players),
        historical_point_requirements=historical_point_requirements,
        current_state=metadata,
        top_limit=20,
    )

    if args.output:
        args.output.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
