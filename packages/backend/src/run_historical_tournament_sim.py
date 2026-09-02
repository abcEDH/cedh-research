#!/usr/bin/env python3
"""Run Monte Carlo simulation for a historical tournament from Supabase."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any

from ingest import SupabaseClient, load_local_env
from sim_engine import initialize_state
from sim_models import DEFAULT_DRAW_MODEL_PATH, load_draw_model_artifact
from sim_pairings import topdeck_bye_rank
from sim_types import FeatureContext, PlayerHistory, SimPlayer, TournamentSpec
from tournament_sim_runner import build_common_output, run_simulation_from_state


def parse_database_datetime(value: Any) -> datetime:
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        match = re.match(r"^(.*T\d{2}:\d{2}:\d{2})\.(\d{1,6})([+-]\d{2}:\d{2})$", text)
        if match:
            prefix, fraction, offset = match.groups()
            return datetime.fromisoformat(f"{prefix}.{fraction.ljust(6, '0')}{offset}")
        raise


def parse_database_date(value: Any) -> date | None:
    if value is None:
        return None
    return parse_database_datetime(value).date()


def fetch_all(
    client: SupabaseClient,
    table: str,
    params: dict[str, str],
    *,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = client.select(table, {**params, "limit": str(limit), "offset": str(offset)}, max_retries=8)
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
    return rows


def batched(values: list[str], batch_size: int) -> list[list[str]]:
    return [values[index : index + batch_size] for index in range(0, len(values), batch_size)]


def in_filter(values: list[str]) -> str:
    escaped = [value.replace('"', '\\"') for value in values]
    return "(" + ",".join(f'"{value}"' for value in escaped) + ")"


def fetch_tournament(client: SupabaseClient, tournament_id: str) -> dict[str, Any]:
    rows = client.select(
        "tournaments",
        {
            "select": "id,name,start_date,player_count,top_cut,state,country",
            "id": f"eq.{tournament_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise RuntimeError(f"Tournament not found: {tournament_id}")
    return rows[0]


def fetch_entries(client: SupabaseClient, tournament_id: str) -> list[dict[str, Any]]:
    return fetch_all(
        client,
        "tournament_entries",
        {
            "select": "player_id,commander_id,final_standing,points,wins,losses,draws,made_top_cut,players(name,topdeck_id),commanders(name,color_identity)",
            "tournament_id": f"eq.{tournament_id}",
        },
    )


def fetch_topdeck_elos_for_topdeck_ids(client: SupabaseClient, topdeck_ids: list[str]) -> dict[str, float]:
    if not topdeck_ids:
        return {}
    try:
        rows = fetch_all(
            client,
            "topdeck_player_elos",
            {
                "select": "topdeck_id,elo",
                "topdeck_id": f"in.({','.join(topdeck_ids)})",
            },
        )
    except Exception:
        return {}
    return {
        str(row["topdeck_id"]): float(row["elo"])
        for row in rows
        if row.get("topdeck_id") and row.get("elo") is not None
    }


def derive_top_cut_player_ids(entries: list[dict[str, Any]], top_cut: int) -> set[str]:
    if top_cut <= 0:
        return set()
    top_cut_players: set[str] = set()
    for row in entries:
        player_id = row.get("player_id")
        final_standing = row.get("final_standing")
        if not player_id or final_standing is None:
            continue
        try:
            if int(final_standing) <= top_cut:
                top_cut_players.add(str(player_id))
        except (TypeError, ValueError):
            continue
    return top_cut_players


def entry_games_played(entry: dict[str, Any]) -> int:
    total = 0
    for key in ("wins", "losses", "draws"):
        try:
            total += int(entry.get(key) or 0)
        except (TypeError, ValueError):
            continue
    return total


def active_player_count_from_entries(entries: list[dict[str, Any]]) -> int:
    return sum(1 for entry in entries if entry.get("player_id") and entry_games_played(entry) > 0)


def fetch_active_player_count_from_games(client: SupabaseClient, tournament_id: str) -> int:
    rows = fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": "player_id",
            "tournament_id": f"eq.{tournament_id}",
        },
    )
    return len({str(row["player_id"]) for row in rows if row.get("player_id")})


def fetch_active_player_ids_from_games(client: SupabaseClient, tournament_id: str) -> set[str]:
    rows = fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": "player_id",
            "tournament_id": f"eq.{tournament_id}",
        },
    )
    return {str(row["player_id"]) for row in rows if row.get("player_id")}


def point_count_distribution(counts: Counter[int], total: int) -> list[dict[str, float | int]]:
    if total <= 0:
        return []
    return [
        {"points": points, "probability": count / total, "count": count}
        for points, count in sorted(counts.items())
    ]


def fetch_historical_point_requirement_baseline(
    client: SupabaseClient,
    *,
    active_player_count: int,
    top_cut: int,
    swiss_rounds: int | None = None,
    exclude_tournament_id: str | None = None,
    window_fraction: float = 0.15,
    min_window: int = 8,
) -> dict[str, Any]:
    if active_player_count <= 0 or top_cut <= 0:
        return {
            "active_player_count": active_player_count,
            "cut_size": top_cut,
            "swiss_rounds": swiss_rounds,
            "events": 0,
            "active_player_count_window": None,
            "top_cut": [],
            "bye": [],
        }

    window = max(min_window, int(round(active_player_count * window_fraction)))
    min_players = max(1, active_player_count - window)
    max_players = active_player_count + window
    tournaments = fetch_all(
        client,
        "tournaments",
        {
            "select": "id,top_cut,swiss_rounds",
            "top_cut": f"eq.{top_cut}",
        },
    )
    tournament_meta = {
        str(row["id"]): row
        for row in tournaments
        if row.get("id") and str(row.get("id")) != str(exclude_tournament_id)
    }
    if swiss_rounds is not None:
        tournament_meta = {
            tournament_id: row
            for tournament_id, row in tournament_meta.items()
            if str(row.get("swiss_rounds")) == str(swiss_rounds)
        }
    tournament_ids = list(tournament_meta)

    top_cut_counts: Counter[int] = Counter()
    bye_counts: Counter[int] = Counter()
    events = 0
    bye_rank = topdeck_bye_rank(top_cut)

    for batch in batched(tournament_ids, 80):
        game_rows = fetch_all(
            client,
            "global_elo_game_results",
            {
                "select": "tournament_id,player_id",
                "tournament_id": f"in.{in_filter(batch)}",
            },
        )
        active_players_by_tournament: dict[str, set[str]] = defaultdict(set)
        for row in game_rows:
            tournament_id = row.get("tournament_id")
            player_id = row.get("player_id")
            if tournament_id and player_id:
                active_players_by_tournament[str(tournament_id)].add(str(player_id))
        rows = fetch_all(
            client,
            "tournament_entries",
            {
                "select": "tournament_id,player_id,final_standing,points,wins,losses,draws",
                "tournament_id": f"in.{in_filter(batch)}",
            },
        )
        by_tournament: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            tournament_id = row.get("tournament_id")
            if tournament_id:
                by_tournament[str(tournament_id)].append(row)

        for tournament_id, entries in by_tournament.items():
            event_active_count = len(active_players_by_tournament.get(tournament_id, set()))
            if event_active_count < min_players or event_active_count > max_players:
                continue
            swiss_rounds = tournament_meta.get(tournament_id, {}).get("swiss_rounds")
            try:
                max_possible_points = int(swiss_rounds) * 5 if swiss_rounds is not None else None
            except (TypeError, ValueError):
                max_possible_points = None
            standings_rows: list[tuple[int, int]] = []
            for entry in entries:
                final_standing = entry.get("final_standing")
                points = entry.get("points")
                if final_standing is None or points is None:
                    continue
                try:
                    standings_rows.append((int(final_standing), int(points)))
                except (TypeError, ValueError):
                    continue
            if len(standings_rows) < top_cut:
                continue
            points_by_rank = {rank: points for rank, points in standings_rows}
            if top_cut not in points_by_rank:
                continue
            top_cut_points = points_by_rank[top_cut]
            if top_cut_points <= 0 or (
                max_possible_points is not None and top_cut_points > max_possible_points
            ):
                continue
            bye_points = points_by_rank.get(bye_rank) if bye_rank is not None else None
            if bye_points is not None and (
                bye_points <= 0 or (max_possible_points is not None and bye_points > max_possible_points)
            ):
                bye_points = None
            events += 1
            top_cut_counts[top_cut_points] += 1
            if bye_points is not None:
                bye_counts[bye_points] += 1

    return {
        "active_player_count": active_player_count,
        "cut_size": top_cut,
        "swiss_rounds": swiss_rounds,
        "events": events,
        "active_player_count_window": {"min": min_players, "max": max_players},
        "top_cut": point_count_distribution(top_cut_counts, events),
        "bye": point_count_distribution(bye_counts, events),
    }


def infer_swiss_rounds(client: SupabaseClient, tournament_id: str) -> int:
    rows = fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": "round_number",
            "tournament_id": f"eq.{tournament_id}",
        },
    )
    round_numbers = [int(row["round_number"]) for row in rows if row.get("round_number") is not None]
    if not round_numbers:
        raise RuntimeError(f"No swiss rounds found for tournament {tournament_id}")
    return max(round_numbers)


def fetch_pre_tournament_elos(
    client: SupabaseClient,
    player_ids: list[str],
    start_date: str,
) -> dict[str, float]:
    start_day = parse_database_datetime(start_date).date()
    ratings: dict[str, float] = {}
    unresolved_player_ids = set(player_ids)

    for batch in batched(player_ids, 40):
        rating_rows = fetch_all(
            client,
            "global_elo_ratings",
            {
                "select": "player_id,rating,last_game_date",
                "region_type": "eq.global",
                "region_key": "eq.ALL",
                "player_id": f"in.{in_filter(batch)}",
            },
        )
        for row in rating_rows:
            player_id = row.get("player_id")
            rating = row.get("rating")
            last_game_date = parse_database_date(row.get("last_game_date"))
            if not player_id or rating is None or last_game_date is None:
                continue
            if last_game_date < start_day:
                ratings[str(player_id)] = float(rating)
                unresolved_player_ids.discard(str(player_id))

    for batch in batched([player_id for player_id in player_ids if player_id in unresolved_player_ids], 40):
        rows = fetch_all(
            client,
            "global_elo_game_events",
            {
                "select": "player_id,game_date,rating_after",
                "region_type": "eq.global",
                "region_key": "eq.ALL",
                "game_date": f"lt.{start_date}",
                "player_id": f"in.{in_filter(batch)}",
                "order": "game_date.desc",
            },
        )
        for row in rows:
            player_id = row.get("player_id")
            game_date = row.get("game_date")
            rating_after = row.get("rating_after")
            if not player_id or game_date is None or rating_after is None:
                continue
            if player_id not in ratings:
                ratings[str(player_id)] = float(rating_after)
    return ratings


def build_feature_context(
    client: SupabaseClient,
    player_ids: list[str],
    start_date: str,
) -> FeatureContext:
    player_stats: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    prior_games: dict[str, list[str]] = defaultdict(list)
    for batch in batched(player_ids, 40):
        rows = fetch_all(
            client,
            "global_elo_game_results",
            {
                "select": "game_id,player_id,result",
                "player_id": f"in.{in_filter(batch)}",
                "start_date": f"lt.{start_date}",
            },
        )
        for row in rows:
            player_id = row.get("player_id")
            result = str(row.get("result") or "")
            game_id = row.get("game_id")
            if not player_id or not game_id:
                continue
            stats = player_stats[player_id]
            stats[1] += 1
            if result == "draw":
                stats[0] += 1
            if result == "win":
                stats[2] += 1
            if result != "draw":
                stats[3] += 1
            prior_games[str(game_id)].append(player_id)

    tournament_pair_meetings: dict[tuple[str, str], int] = {}
    global_pair_meetings: dict[tuple[str, str], int] = defaultdict(int)
    for players in prior_games.values():
        unique_players = sorted(set(players))
        for index, player_id in enumerate(unique_players):
            for opponent_id in unique_players[index + 1 :]:
                pair = (player_id, opponent_id)
                global_pair_meetings[pair] += 1

    history = {}
    for player_id in player_ids:
        draws, total, wins, decisive = player_stats[player_id]
        history[player_id] = PlayerHistory(
            draw_rate=(draws / total) if total else 0.0,
            win_rate=(wins / total) if total else 0.0,
            decisive_rate=(decisive / total) if total else 0.0,
            games_played=total,
        )

    return FeatureContext(
        player_history=history,
        tournament_pair_meetings=tournament_pair_meetings,
        global_pair_meetings=dict(global_pair_meetings),
        series_prior_draw_rate=0.0,
        series_events_seen=0,
        state_prior_draw_rate=0.0,
        country_prior_draw_rate=0.0,
        global_recent_draw_rate_90d=0.0,
    )


def build_spec_and_players(
    client: SupabaseClient,
    tournament_id: str,
    *,
    repeat_avoidance_max_pods: int | None = None,
    active_players_only: bool = True,
) -> tuple[TournamentSpec, list[SimPlayer], list[dict[str, Any]], FeatureContext]:
    tournament = fetch_tournament(client, tournament_id)
    entries = fetch_entries(client, tournament_id)
    if active_players_only:
        active_player_ids = fetch_active_player_ids_from_games(client, tournament_id)
        if active_player_ids:
            entries = [
                entry
                for entry in entries
                if entry.get("player_id") and str(entry["player_id"]) in active_player_ids
            ]
    swiss_rounds = infer_swiss_rounds(client, tournament_id)
    player_ids = [str(row["player_id"]) for row in entries if row.get("player_id")]
    start_date = parse_database_datetime(tournament["start_date"])
    pre_elos = fetch_pre_tournament_elos(client, player_ids, start_date.isoformat())
    feature_context = build_feature_context(client, player_ids, start_date.isoformat())

    sortable_entries = []
    topdeck_ids_for_elo = [
        str((row.get("players") or {}).get("topdeck_id"))
        for row in entries
        if (row.get("players") or {}).get("topdeck_id")
    ]
    topdeck_elos = fetch_topdeck_elos_for_topdeck_ids(client, topdeck_ids_for_elo)
    for row in entries:
        player_id = row.get("player_id")
        player = row.get("players") or {}
        commander = row.get("commanders") or {}
        topdeck_id = player.get("topdeck_id")
        if not player_id:
            continue
        sortable_entries.append(
            (
                str(player_id),
                str(player.get("name") or player_id),
                topdeck_id,
                float(pre_elos.get(str(player_id), 1500.0)),
                topdeck_elos.get(str(topdeck_id)) if topdeck_id else None,
                tuple(sorted({str(color).upper() for color in (commander.get("color_identity") or ()) if color})),
            )
        )

    seed_source = f"historical:{tournament_id}"
    seeded_rng = random.Random(seed_source)
    seeded_rng.shuffle(sortable_entries)
    players = []
    for tiebreak_seed, (player_id, name, topdeck_id, elo, topdeck_elo, commander_colors) in enumerate(sortable_entries, start=1):
        players.append(
            SimPlayer(
                player_id=player_id,
                name=name,
                elo=elo,
                topdeck_id=topdeck_id,
                topdeck_elo=topdeck_elo,
                commander_colors=commander_colors,
                tiebreak_seed=tiebreak_seed,
            )
        )

    spec = TournamentSpec(
        tournament_id=str(tournament["id"]),
        name=str(tournament["name"]),
        start_date=start_date,
        swiss_rounds=swiss_rounds,
        top_cut=int(tournament.get("top_cut") or 0),
        player_count=len(players) if active_players_only else int(tournament.get("player_count") or len(players)),
        repeat_avoidance_max_pods=repeat_avoidance_max_pods,
        state=tournament.get("state"),
        country=tournament.get("country"),
    )
    return spec, players, entries, feature_context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournament-id", required=True)
    parser.add_argument("--draw-model-path", default=str(DEFAULT_DRAW_MODEL_PATH))
    parser.add_argument("--simulations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--repeat-avoidance-max-pods", type=int, default=32)
    parser.add_argument(
        "--include-inactive-entries",
        action="store_true",
        help="Include registered players with no recorded games. By default historical sims use active players only.",
    )
    args = parser.parse_args()

    load_local_env()
    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])
    spec, players, entries, feature_context = build_spec_and_players(
        client,
        args.tournament_id,
        repeat_avoidance_max_pods=args.repeat_avoidance_max_pods,
        active_players_only=not args.include_inactive_entries,
    )
    draw_model = load_draw_model_artifact(args.draw_model_path)
    state = initialize_state(spec, players, feature_context=feature_context)
    summary_dict = run_simulation_from_state(
        state,
        draw_model,
        simulations=args.simulations,
        seed=args.seed,
        workers=args.workers,
    )

    actual_top_cut = derive_top_cut_player_ids(entries, spec.top_cut)
    actual_winner = next((str(row["player_id"]) for row in entries if row.get("final_standing") == 1), None)
    player_name_by_id = {player.player_id: player.name for player in players}
    active_player_count = fetch_active_player_count_from_games(client, spec.tournament_id)
    historical_point_requirements = fetch_historical_point_requirement_baseline(
        client,
        active_player_count=active_player_count,
        top_cut=spec.top_cut,
        swiss_rounds=spec.swiss_rounds,
        exclude_tournament_id=spec.tournament_id,
    )

    output = build_common_output(
        summary=summary_dict,
        state=state,
        player_name_by_id=player_name_by_id,
        active_player_count=active_player_count,
        historical_point_requirements=historical_point_requirements,
        actual_winner_id=actual_winner,
        actual_top_cut_count=len(actual_top_cut),
        top_limit=20,
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
