"""
Golf-style "top-N tournaments" rating vs averaging Elo.

Question from podcast prep §4.1: does a peak-finding rating
materially reorder the leaderboard, or is it a cosmetic relabel?

Method:
  1. Pull every game event from global_elo_game_event_log (region=ALL).
  2. Aggregate to (player, tournament) -> sum of rating_delta = "tournament delta".
  3. For each player with >= MIN_TOURNEYS tournaments:
       - mean_td  = average tournament delta across all their tournaments
       - peakN_td = average of their top-N tournament deltas
  4. Rank players by current Elo, by mean_td, and by peakN_td and look at
     the disagreement.

Outputs:
  - distribution of tournament deltas
  - top-25 by current Elo, with mean_td / peak3_td shown next to it
  - biggest rank-shift candidates between the two metrics
"""

import os
import sys
from collections import defaultdict
from statistics import mean

import requests


URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

PAGE = 50_000
MIN_TOURNEYS = 5      # need at least this many tournaments to rank
PEAK_N = 3            # "golf" = average of best-N tournaments


def fetch_all(path: str, select: str) -> list[dict]:
    """Page through a PostgREST endpoint until exhausted."""
    out: list[dict] = []
    offset = 0
    while True:
        r = requests.get(
            f"{URL}/rest/v1/{path}",
            headers={**H, "Range-Unit": "items", "Range": f"{offset}-{offset + PAGE - 1}"},
            params={"select": select},
            timeout=120,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
        print(f"  fetched {len(out):>8} rows from {path}", file=sys.stderr)
    return out


def main() -> None:
    print("Loading game events (global, ALL region)...", file=sys.stderr)
    events = fetch_all(
        "global_elo_game_event_log?region_type=eq.global&region_key=eq.ALL",
        "player_id,player_name,tournament_id,tournament_name,rating_delta,rating_after,game_date",
    )
    print(f"  {len(events):,} game events loaded", file=sys.stderr)

    # current Elo (ALL region, global)
    print("Loading current ratings...", file=sys.stderr)
    ratings = fetch_all(
        "global_elo_ratings?region_type=eq.global&region_key=eq.ALL",
        "player_id,rating,games_played",
    )
    rating_by_pid = {r["player_id"]: r for r in ratings}

    # Aggregate: (player_id, tournament_id) -> tournament delta
    tourney_delta: dict[tuple[str, str], float] = defaultdict(float)
    last_game_after: dict[str, float] = {}      # rating_after at end of tourney
    player_name: dict[str, str] = {}
    for ev in events:
        pid = ev["player_id"]
        tid = ev["tournament_id"]
        if tid is None:
            continue
        tourney_delta[(pid, tid)] += ev["rating_delta"] or 0.0
        player_name[pid] = ev["player_name"]

    # Per-player list of tournament deltas
    per_player: dict[str, list[float]] = defaultdict(list)
    for (pid, _tid), td in tourney_delta.items():
        per_player[pid].append(td)

    print(f"  {len(per_player):,} distinct players, "
          f"{sum(len(v) for v in per_player.values()):,} player-tournament pairs",
          file=sys.stderr)

    # Distribution of tournament deltas (gives a sense of variance)
    all_tds = [td for tds in per_player.values() for td in tds]
    all_tds.sort()
    n = len(all_tds)
    pcts = [1, 10, 50, 90, 99]
    print("\n=== Tournament-delta distribution (all players) ===")
    print(f"{'Pctile':<8} {'Δ Elo':>10}")
    for p in pcts:
        idx = max(0, min(n - 1, int(n * p / 100)))
        print(f"P{p:<6} {all_tds[idx]:>+10.2f}")
    print(f"Mean = {mean(all_tds):+.2f}, N = {n:,}")

    # Build comparison rows: only players with current Elo + enough tournaments
    rows: list[dict] = []
    for pid, tds in per_player.items():
        if len(tds) < MIN_TOURNEYS:
            continue
        r = rating_by_pid.get(pid)
        if not r:
            continue
        top_n = sorted(tds, reverse=True)[:PEAK_N]
        rows.append({
            "pid": pid,
            "name": player_name.get(pid, "?"),
            "current_elo": r["rating"],
            "games": r["games_played"],
            "tourneys": len(tds),
            "mean_td": mean(tds),
            "peak_td": mean(top_n),
            "best_td": max(tds),
            "worst_td": min(tds),
        })

    print(f"\nEligible players (>= {MIN_TOURNEYS} tournaments, has current Elo): "
          f"{len(rows):,}")

    # Rank under each metric
    for key in ("current_elo", "mean_td", "peak_td"):
        rows_sorted = sorted(rows, key=lambda x: x[key], reverse=True)
        for i, r in enumerate(rows_sorted, 1):
            r[f"rank_{key}"] = i

    # Top-25 by current Elo, side-by-side with golf rank
    print(f"\n=== Top 25 by current Elo (peak = mean of best {PEAK_N} tournaments) ===")
    print(f"{'#':>3} {'Player':<32} {'Elo':>7} {'Trn':>4} "
          f"{'mean Δ':>7} {'peak Δ':>7} {'best Δ':>7} "
          f"{'r_mean':>6} {'r_peak':>6}")
    top_by_elo = sorted(rows, key=lambda x: x["current_elo"], reverse=True)[:25]
    for r in top_by_elo:
        print(f"{r['rank_current_elo']:>3} {r['name'][:32]:<32} "
              f"{r['current_elo']:>7.0f} {r['tourneys']:>4} "
              f"{r['mean_td']:>+7.2f} {r['peak_td']:>+7.2f} {r['best_td']:>+7.2f} "
              f"{r['rank_mean_td']:>6} {r['rank_peak_td']:>6}")

    # Biggest movers: players ranked much higher under golf than under current Elo
    print(f"\n=== Biggest 'golf risers' (peak rank << Elo rank, min {MIN_TOURNEYS} trn) ===")
    risers = sorted(rows, key=lambda x: x["rank_current_elo"] - x["rank_peak_td"], reverse=True)
    print(f"{'Player':<32} {'Elo':>7} {'Trn':>4} "
          f"{'mean Δ':>7} {'peak Δ':>7} {'r_elo':>6} {'r_peak':>6} {'shift':>6}")
    for r in risers[:15]:
        shift = r["rank_current_elo"] - r["rank_peak_td"]
        print(f"{r['name'][:32]:<32} {r['current_elo']:>7.0f} {r['tourneys']:>4} "
              f"{r['mean_td']:>+7.2f} {r['peak_td']:>+7.2f} "
              f"{r['rank_current_elo']:>6} {r['rank_peak_td']:>6} {shift:>+6}")

    # Symmetric: who drops under golf?
    print(f"\n=== Biggest 'golf droppers' (peak rank >> Elo rank) ===")
    droppers = sorted(rows, key=lambda x: x["rank_current_elo"] - x["rank_peak_td"])
    for r in droppers[:15]:
        shift = r["rank_current_elo"] - r["rank_peak_td"]
        print(f"{r['name'][:32]:<32} {r['current_elo']:>7.0f} {r['tourneys']:>4} "
              f"{r['mean_td']:>+7.2f} {r['peak_td']:>+7.2f} "
              f"{r['rank_current_elo']:>6} {r['rank_peak_td']:>6} {shift:>+6}")


if __name__ == "__main__":
    main()
