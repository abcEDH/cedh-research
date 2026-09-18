#!/usr/bin/env python3
"""
Commander EV Simulations

Runs reproducible Monte Carlo simulations using Supabase commander stats.
Supports:
- cohort simulation (working vs not-working decks by EV score)
- explicit shortlist simulation (e.g., Ral/Kraum/Kinnan/Tivit)
- matchup and seat diagnostics for selected commanders
- optional mixed-pod edge simulation

Usage examples:
  python src/commander_ev_simulations.py
  python src/commander_ev_simulations.py --commander "Ral, Monsoon Mage // Ral, Leyline Prodigy" --commander "Kraum, Ludevic's Opus / Tymna the Weaver"
  python src/commander_ev_simulations.py --min-entries 100 --top-n 8 --bottom-n 8 --sims 100000 --output-json reports/ev-simulations.json
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests


def normalize_name(name: str) -> str:
    return name.replace("\\'", "'")


class SupabaseClient:
    """Minimal REST/RPC wrapper for read-only analytics queries."""

    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def select(self, table: str, select: str = "*", params: Optional[Dict[str, str]] = None) -> List[Dict]:
        query = {"select": select}
        if params:
            query.update(params)
        resp = requests.get(
            f"{self.url}/rest/v1/{table}",
            headers=self.headers,
            params=query,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    def rpc(self, function_name: str, payload: Dict) -> List[Dict]:
        resp = requests.post(
            f"{self.url}/rest/v1/rpc/{function_name}",
            headers=self.headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()


def load_credentials() -> tuple[str, str]:
    """Load Supabase credentials from env or local .env files."""
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    if supabase_url and supabase_key:
        return supabase_url, supabase_key

    env_paths = [
        ".env",
        ".env.local",
        "apps/web/.env.local",
        "packages/backend/.env",
    ]
    for env_path in env_paths:
        if not os.path.exists(env_path):
            continue
        with open(env_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if not supabase_url and k in {"SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL"}:
                    supabase_url = v
                if not supabase_key and k in {"SUPABASE_SERVICE_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY"}:
                    supabase_key = v
        if supabase_url and supabase_key:
            break

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing Supabase credentials. Set SUPABASE_URL + SUPABASE_SERVICE_KEY (or NEXT_PUBLIC_SUPABASE_*).")
    return supabase_url, supabase_key


def commander_probabilities(row: Dict) -> tuple[float, float, float]:
    total = row["total_wins"] + row["total_losses"] + row["total_draws"]
    if total <= 0:
        return 0.0, 0.0, 1.0
    p_win = row["total_wins"] / total
    p_draw = row["total_draws"] / total
    p_loss = max(0.0, 1.0 - p_win - p_draw)
    return p_win, p_draw, p_loss


def simulate_swiss(row: Dict, rounds: int, sims: int, rng: random.Random) -> Dict:
    """Independent-round approximation with points: win=5, draw=1, loss=0."""
    p_win, p_draw, _ = commander_probabilities(row)
    total_points = 0
    ge_16 = ge_18 = ge_20 = undefeated = 0

    for _ in range(sims):
        points = 0
        losses = 0
        for _ in range(rounds):
            x = rng.random()
            if x < p_win:
                points += 5
            elif x < p_win + p_draw:
                points += 1
            else:
                losses += 1
        total_points += points
        if points >= 16:
            ge_16 += 1
        if points >= 18:
            ge_18 += 1
        if points >= 20:
            ge_20 += 1
        if losses == 0:
            undefeated += 1

    return {
        "commander_name": row["commander_name"],
        "entries": row["total_entries"],
        "p_win": round(p_win, 4),
        "p_draw": round(p_draw, 4),
        "ev_points": round(total_points / sims, 2),
        "p_ge_16": round(ge_16 / sims, 4),
        "p_ge_18": round(ge_18 / sims, 4),
        "p_ge_20": round(ge_20 / sims, 4),
        "p_undefeated": round(undefeated / sims, 4),
        "observed_top_cut": round(row["conversion_rate_top_cut"], 4),
        "observed_top16": round(row["conversion_rate_top_16"], 4),
    }


def weighted_pod_winner(ps: List[float], rng: random.Random) -> int:
    total = sum(ps)
    if total <= 0:
        return int(rng.random() * len(ps))
    x = rng.random() * total
    for i, p in enumerate(ps):
        x -= p
        if x <= 0:
            return i
    return len(ps) - 1


def simulate_mixed_pods(working_rows: List[Dict], struggling_rows: List[Dict], sims: int, seed: int) -> Dict:
    """
    Pod model approximation (no draws): winner probability proportional to p_win.
    Scenario A: 1 working + 3 struggling.
    Scenario B: 1 struggling + 3 working.
    """
    rng = random.Random(seed)
    working_p = [commander_probabilities(r)[0] for r in working_rows]
    struggling_p = [commander_probabilities(r)[0] for r in struggling_rows]
    working_wins = 0
    struggling_wins = 0

    for _ in range(sims):
        wp = [rng.choice(working_p)] + [rng.choice(struggling_p) for _ in range(3)]
        if weighted_pod_winner(wp, rng) == 0:
            working_wins += 1

        sp = [rng.choice(struggling_p)] + [rng.choice(working_p) for _ in range(3)]
        if weighted_pod_winner(sp, rng) == 0:
            struggling_wins += 1

    return {
        "sims": sims,
        "scenario_a": "1 working + 3 struggling decks",
        "p_working_wins": round(working_wins / sims, 4),
        "scenario_b": "1 struggling + 3 working decks",
        "p_struggling_wins": round(struggling_wins / sims, 4),
        "equal_pod_baseline": 0.25,
    }


def ev_score(row: Dict, w_wr: float, w_top16: float, w_topcut: float) -> float:
    return (w_wr * row["avg_win_rate"]) + (w_top16 * row["conversion_rate_top_16"]) + (w_topcut * row["conversion_rate_top_cut"])


def fetch_commander_stats(client: SupabaseClient, min_entries: int) -> List[Dict]:
    rows = client.select(
        "commander_stats",
        select=(
            "commander_id,commander_name,total_entries,total_wins,total_losses,total_draws,"
            "avg_win_rate,conversion_rate_top_16,conversion_rate_top_cut"
        ),
        params={
            "commander_name": "neq.Unknown Commander",
            "total_entries": f"gte.{min_entries}",
        },
    )
    cleaned = []
    for row in rows:
        if not row["total_entries"] or row["total_entries"] < min_entries:
            continue
        row["commander_name"] = normalize_name(row["commander_name"])
        cleaned.append(row)
    return cleaned


def fetch_diagnostics(client: SupabaseClient, commander_name: str, min_games: int) -> Optional[Dict]:
    commanders = client.select("commanders", select="id,name", params={"name": f"eq.{commander_name}"})
    if not commanders:
        return None
    commander = commanders[0]
    commander["name"] = normalize_name(commander["name"])
    cid = commander["id"]

    try:
        seat = client.select(
            "commander_seat_stats",
            select="seat_position,games,wins,losses,draws,win_rate,draw_rate,win_plus_draw_rate",
            params={
                "commander_id": f"eq.{cid}",
                "order": "seat_position.asc",
            },
        )
    except Exception:
        seat = []
    matchups = client.rpc("get_commander_matchups", {"p_commander_id": cid})
    valid = [
        m for m in matchups
        if normalize_name(m["opponent_commander_name"]) != "Unknown Commander"
        and normalize_name(m["opponent_commander_name"]) != commander_name
        and m.get("games_played", 0) >= min_games
    ]
    for row in valid:
        row["opponent_commander_name"] = normalize_name(row["opponent_commander_name"])
    best = sorted(valid, key=lambda x: x.get("win_rate_vs_expected", 0), reverse=True)[:5]
    worst = sorted(valid, key=lambda x: x.get("win_rate_vs_expected", 0))[:5]
    return {
        "commander_name": commander_name,
        "seat_performance": seat,
        "best_matchups": best,
        "worst_matchups": worst,
        "matchup_filter_min_games": min_games,
    }


def write_markdown(path: Path, payload: Dict) -> None:
    lines = [
        f"# Commander EV Simulations ({payload['as_of']})",
        "",
        f"- Cohort filter: `{payload['config']['cohort_filter']}`",
        f"- Simulation: `{payload['config']['sims']} sims`, `{payload['config']['rounds']} rounds`, points `{payload['config']['points_system']}`",
        "",
        "## Working Cohort",
    ]
    for row in payload["cohorts"]["working"]:
        lines.append(f"- {row['commander_name']} (entries={row['entries']}, ev_score={row['ev_score']})")
    lines.extend(["", "## Struggling Cohort"])
    for row in payload["cohorts"]["struggling"]:
        lines.append(f"- {row['commander_name']} (entries={row['entries']}, ev_score={row['ev_score']})")
    lines.extend(["", "## Swiss Simulation (Working)"])
    for row in payload["simulations"]["working"]:
        lines.append(f"- {row['commander_name']}: EV points {row['ev_points']}, P(>=16) {row['p_ge_16']}")
    lines.extend(["", "## Swiss Simulation (Struggling)"])
    for row in payload["simulations"]["struggling"]:
        lines.append(f"- {row['commander_name']}: EV points {row['ev_points']}, P(>=16) {row['p_ge_16']}")

    mixed = payload["simulations"].get("mixed_pod")
    if mixed:
        lines.extend([
            "",
            "## Mixed Pod Edge",
            f"- P(working wins in 1v3 scenario): {mixed['p_working_wins']}",
            f"- P(struggling wins in 1v3 scenario): {mixed['p_struggling_wins']}",
        ])

    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run commander EV simulations from Supabase stats.")
    parser.add_argument("--min-entries", type=int, default=200, help="Minimum entries for cohort inclusion.")
    parser.add_argument("--top-n", type=int, default=6, help="Working cohort size (highest EV).")
    parser.add_argument("--bottom-n", type=int, default=6, help="Struggling cohort size (lowest EV).")
    parser.add_argument("--rounds", type=int, default=6, help="Swiss rounds per simulation.")
    parser.add_argument("--sims", type=int, default=50000, help="Monte Carlo iterations per commander.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument("--commander", action="append", default=[], help="Commander name to include in explicit shortlist diagnostics.")
    parser.add_argument("--matchup-min-games", type=int, default=30, help="Minimum games for matchup best/worst tables.")
    parser.add_argument("--no-mixed-pod", action="store_true", help="Disable mixed-pod edge simulation.")
    parser.add_argument("--w-win-rate", type=float, default=0.5, help="EV weight for win rate.")
    parser.add_argument("--w-top16", type=float, default=0.35, help="EV weight for top16/top10/top4 conversion.")
    parser.add_argument("--w-topcut", type=float, default=0.15, help="EV weight for top-cut conversion.")
    parser.add_argument("--output-json", type=str, default="", help="Write full payload JSON to this path.")
    parser.add_argument("--output-md", type=str, default="", help="Write markdown summary to this path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    total_weight = args.w_win_rate + args.w_top16 + args.w_topcut
    if abs(total_weight - 1.0) > 1e-9:
        print("Error: EV weights must sum to 1.0", file=sys.stderr)
        return 1

    url, key = load_credentials()
    client = SupabaseClient(url, key)

    rows = fetch_commander_stats(client, args.min_entries)
    if len(rows) < (args.top_n + args.bottom_n):
        print("Error: not enough commanders for requested cohort sizes.", file=sys.stderr)
        return 1

    for row in rows:
        row["ev_score"] = ev_score(row, args.w_win_rate, args.w_top16, args.w_topcut)

    ranked = sorted(rows, key=lambda x: x["ev_score"], reverse=True)
    working = ranked[: args.top_n]
    struggling = list(reversed(ranked[-args.bottom_n:]))

    rng_working = random.Random(args.seed)
    rng_struggling = random.Random(args.seed + 1)
    working_sims = [simulate_swiss(r, args.rounds, args.sims, rng_working) for r in working]
    struggling_sims = [simulate_swiss(r, args.rounds, args.sims, rng_struggling) for r in struggling]

    mixed_pod = None
    if not args.no_mixed_pod:
        mixed_pod = simulate_mixed_pods(working, struggling, max(10000, args.sims), args.seed + 2)

    shortlist = []
    if args.commander:
        by_name = {r["commander_name"]: r for r in rows}
        for i, name in enumerate(args.commander):
            if name not in by_name:
                shortlist.append({"commander_name": name, "error": "Not found in filtered cohort. Lower --min-entries or check name."})
                continue
            shortlist_row = by_name[name]
            shortlist_sim = simulate_swiss(shortlist_row, args.rounds, args.sims, random.Random(args.seed + 100 + i))
            diagnostics = fetch_diagnostics(client, name, args.matchup_min_games)
            shortlist.append({
                "commander_name": name,
                "ev_score": round(shortlist_row["ev_score"], 4),
                "simulation": shortlist_sim,
                "diagnostics": diagnostics,
            })

    payload = {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d"),
        "config": {
            "cohort_filter": f"total_entries >= {args.min_entries}, excluding Unknown Commander",
            "rounds": args.rounds,
            "sims": args.sims,
            "seed": args.seed,
            "points_system": "win=5 draw=1 loss=0",
            "ev_weights": {
                "win_rate": args.w_win_rate,
                "top16_like_conversion": args.w_top16,
                "top_cut_conversion": args.w_topcut,
            },
        },
        "cohorts": {
            "working": [
                {"commander_name": r["commander_name"], "entries": r["total_entries"], "ev_score": round(r["ev_score"], 4)}
                for r in working
            ],
            "struggling": [
                {"commander_name": r["commander_name"], "entries": r["total_entries"], "ev_score": round(r["ev_score"], 4)}
                for r in struggling
            ],
        },
        "simulations": {
            "working": working_sims,
            "struggling": struggling_sims,
            "mixed_pod": mixed_pod,
        },
        "shortlist": shortlist,
    }

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.output_md:
        write_markdown(Path(args.output_md), payload)

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
