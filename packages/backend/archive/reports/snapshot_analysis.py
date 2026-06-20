#!/usr/bin/env python3
"""
Analysis Snapshot Generator

Captures point-in-time analytical insights and stores them in Supabase
for historical comparison and trend tracking.

Usage:
    python src/snapshot_analysis.py                     # Generate all snapshots for current period
    python src/snapshot_analysis.py --period 2025-01   # Specific period
    python src/snapshot_analysis.py --commander Kinnan  # Single commander snapshot
    python src/snapshot_analysis.py --export-md        # Also generate markdown report
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests


class SnapshotGenerator:
    """Generate and store analysis snapshots."""

    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self.version = "1.0"

    def query(self, endpoint: str, params: dict = None) -> list:
        """Query Supabase REST API."""
        response = requests.get(
            f"{self.url}/rest/v1/{endpoint}",
            headers=self.headers,
            params=params or {},
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def save_snapshot(self, snapshot: dict) -> dict:
        """Save a snapshot to the database."""
        # Mark previous as not-latest
        requests.patch(
            f"{self.url}/rest/v1/analysis_snapshots",
            headers=self.headers,
            params={
                "report_type": f"eq.{snapshot['report_type']}",
                "entity_type": f"eq.{snapshot.get('entity_type', 'global')}",
                "entity_id": f"eq.{snapshot.get('entity_id', 'null')}",
                "is_latest": "eq.true"
            },
            json={"is_latest": False},
            timeout=30
        )

        # Insert new snapshot
        response = requests.post(
            f"{self.url}/rest/v1/analysis_snapshots",
            headers=self.headers,
            json=snapshot,
            timeout=30
        )
        if response.status_code >= 400:
            print(f"Error saving snapshot: {response.text}")
            return None
        return response.json()

    def generate_commander_snapshot(self, commander_name: str, meta_period: str) -> dict:
        """Generate survival analysis snapshot for a commander."""
        # Get commander data
        commanders = self.query("commanders", {"name": f"eq.{commander_name}"})
        if not commanders:
            print(f"Commander not found: {commander_name}")
            return None

        cmd = commanders[0]
        cmd_id = cmd["id"]

        # Get stats from views
        stats = self.query("commander_stats", {"commander_id": f"eq.{cmd_id}"})
        if not stats:
            return None

        stat = stats[0]

        # Get tournament entries for more details
        entries = self.query("tournament_entries", {
            "commander_id": f"eq.{cmd_id}",
            "select": "id,final_standing,win_rate,wins,losses,tournaments(start_date,player_count)"
        })

        # Calculate additional metrics
        win_rates = [e["win_rate"] for e in entries if e["win_rate"]]
        standings = [e["final_standing"] for e in entries if e["final_standing"]]

        high_wr = len([w for w in win_rates if w >= 0.25]) / len(win_rates) if win_rates else 0
        low_wr = len([w for w in win_rates if w < 0.15]) / len(win_rates) if win_rates else 0

        # Date range
        dates = [e["tournaments"]["start_date"] for e in entries if e.get("tournaments")]
        start_date = min(dates) if dates else None
        end_date = max(dates) if dates else None

        # Get seat position data
        entry_ids = [e["id"] for e in entries]
        seat_data = {}
        if entry_ids:
            # Batch query game participants
            all_participants = []
            for i in range(0, len(entry_ids), 50):
                batch = entry_ids[i:i+50]
                participants = self.query("game_participants", {
                    "entry_id": f"in.({','.join(batch)})",
                    "select": "seat_position,result"
                })
                all_participants.extend(participants)

            for seat in range(4):
                seat_games = [p for p in all_participants if p["seat_position"] == seat]
                wins = len([p for p in seat_games if p["result"] == "win"])
                losses = len([p for p in seat_games if p["result"] == "loss"])
                total = wins + losses
                seat_data[f"seat_{seat}_wr"] = wins / total if total > 0 else None
                seat_data[f"seat_{seat}_games"] = total

        snapshot = {
            "report_type": "commander_survival",
            "entity_type": "commander",
            "entity_id": cmd_id,
            "entity_name": commander_name,
            "meta_period": meta_period,
            "data_start_date": start_date,
            "data_end_date": end_date,
            "tournaments_included": stat.get("tournaments_played", 0),
            "games_analyzed": sum(seat_data.get(f"seat_{s}_games", 0) for s in range(4)),
            "metrics": {
                "total_entries": stat["total_entries"],
                "tournaments": stat["tournaments_played"],
                "win_rate": stat["avg_win_rate"],
                "top_16_count": stat["top_16_count"],
                "top_16_rate": stat["conversion_rate_top_16"],
                "top_cut_rate": stat["conversion_rate_top_cut"],
                "high_wr_pct": round(high_wr, 4),
                "low_wr_pct": round(low_wr, 4),
                **seat_data,
                "seat_spread": (seat_data.get("seat_0_wr") or 0) - (seat_data.get("seat_3_wr") or 0)
            },
            "insights": {
                "variance": "high" if low_wr > 0.4 else "medium" if low_wr > 0.25 else "low",
                "seat_dependent": (seat_data.get("seat_0_wr") or 0) - (seat_data.get("seat_3_wr") or 0) > 0.15,
            },
            "summary": f"{commander_name}: {stat['total_entries']} entries, "
                       f"{stat['avg_win_rate']*100:.1f}% WR, "
                       f"{stat['conversion_rate_top_16']*100:.1f}% T16 conversion",
            "generator_version": self.version,
            "is_latest": True,
        }

        return snapshot

    def generate_global_snapshot(self, meta_period: str) -> dict:
        """Generate global meta snapshot."""
        # Get top commanders
        stats = self.query("commander_stats", {
            "order": "total_entries.desc",
            "limit": "50"
        })

        # Filter out Unknown Commander
        stats = [s for s in stats if s["commander_name"] != "Unknown Commander"]

        # Calculate meta health metrics
        total_entries = sum(s["total_entries"] for s in stats)
        top_10_share = sum(s["total_entries"] for s in stats[:10]) / total_entries if total_entries else 0

        snapshot = {
            "report_type": "meta_snapshot",
            "entity_type": "global",
            "entity_id": None,
            "entity_name": "cEDH Meta",
            "meta_period": meta_period,
            "metrics": {
                "total_commanders": len(stats),
                "total_entries": total_entries,
                "top_10_meta_share": round(top_10_share, 4),
                "top_commanders": [
                    {"name": s["commander_name"], "entries": s["total_entries"], "win_rate": s["avg_win_rate"]}
                    for s in stats[:10]
                ],
            },
            "summary": f"Meta snapshot: {len(stats)} commanders, {total_entries} entries",
            "generator_version": self.version,
            "is_latest": True,
        }

        return snapshot


def generate_markdown_report(snapshots: list, output_dir: str, meta_period: str):
    """Generate a markdown report from snapshots."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    report_file = output_path / f"{meta_period}-meta-report.md"

    lines = [
        f"# cEDH Meta Report: {meta_period}",
        f"",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"",
    ]

    # Global snapshot
    global_snap = next((s for s in snapshots if s["report_type"] == "meta_snapshot"), None)
    if global_snap:
        metrics = global_snap["metrics"]
        lines.extend([
            "## Meta Overview",
            "",
            f"- **Total Commanders**: {metrics['total_commanders']}",
            f"- **Total Entries**: {metrics['total_entries']}",
            f"- **Top 10 Meta Share**: {metrics['top_10_meta_share']*100:.1f}%",
            "",
            "### Seat Position Win Rates",
            "",
            "| Seat | Win Rate |",
            "|------|----------|",
        ])
        for seat in range(4):
            wr = metrics["seat_win_rates"].get(f"seat_{seat}", 0)
            lines.append(f"| {seat} | {wr*100:.1f}% |")

        lines.extend([
            "",
            "### Top 10 Commanders",
            "",
            "| Commander | Entries | Win Rate |",
            "|-----------|---------|----------|",
        ])
        for cmd in metrics["top_commanders"]:
            lines.append(f"| {cmd['name'][:40]} | {cmd['entries']} | {cmd['win_rate']*100:.1f}% |")

    # Commander snapshots
    cmd_snaps = [s for s in snapshots if s["report_type"] == "commander_survival"]
    if cmd_snaps:
        lines.extend([
            "",
            "## Commander Deep Dives",
            "",
        ])
        for snap in sorted(cmd_snaps, key=lambda x: x["metrics"]["total_entries"], reverse=True)[:10]:
            m = snap["metrics"]
            lines.extend([
                f"### {snap['entity_name']}",
                "",
                f"- **Entries**: {m['total_entries']}",
                f"- **Win Rate**: {m['win_rate']*100:.1f}%",
                f"- **Top 16 Rate**: {m['top_16_rate']*100:.1f}%",
                f"- **Seat Spread**: {m['seat_spread']*100:+.1f}%",
                f"- **Variance**: {snap['insights']['variance']}",
                "",
            ])

    with open(report_file, "w") as f:
        f.write("\n".join(lines))

    print(f"Markdown report saved: {report_file}")
    return report_file


def load_env():
    """Load credentials from environment or .env file."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    env_path = Path(".env")
    if env_path.exists() and not url:
        with open(env_path) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    if k == "SUPABASE_URL":
                        url = v
                    elif k == "SUPABASE_SERVICE_KEY":
                        key = v

    return url, key


def main():
    parser = argparse.ArgumentParser(description="Generate Analysis Snapshots")
    parser.add_argument(
        "--period",
        type=str,
        default=datetime.now().strftime("%Y-%m"),
        help="Meta period (e.g., 2025-01)"
    )
    parser.add_argument(
        "--commander",
        type=str,
        help="Generate snapshot for specific commander"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top commanders to snapshot"
    )
    parser.add_argument(
        "--export-md",
        action="store_true",
        help="Export markdown report"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate but don't save"
    )
    args = parser.parse_args()

    url, key = load_env()
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    generator = SnapshotGenerator(url, key)
    snapshots = []

    if args.commander:
        # Single commander snapshot
        print(f"Generating snapshot for: {args.commander}")
        snapshot = generator.generate_commander_snapshot(args.commander, args.period)
        if snapshot:
            snapshots.append(snapshot)
            print(f"  {snapshot['summary']}")
    else:
        # Global + top commanders
        print(f"Generating meta snapshot for period: {args.period}")

        # Global snapshot
        global_snap = generator.generate_global_snapshot(args.period)
        snapshots.append(global_snap)
        print(f"  Global: {global_snap['summary']}")

        # Top commanders
        stats = generator.query("commander_stats", {
            "order": "total_entries.desc",
            "limit": str(args.top)
        })
        stats = [s for s in stats if s["commander_name"] != "Unknown Commander"]

        for stat in stats:
            print(f"  Generating: {stat['commander_name'][:40]}...")
            snapshot = generator.generate_commander_snapshot(stat["commander_name"], args.period)
            if snapshot:
                snapshots.append(snapshot)

    # Save snapshots
    if not args.dry_run:
        print(f"\nSaving {len(snapshots)} snapshots...")
        for snap in snapshots:
            result = generator.save_snapshot(snap)
            if result:
                print(f"  Saved: {snap.get('entity_name', snap['report_type'])}")
            else:
                print(f"  Failed: {snap.get('entity_name', snap['report_type'])}")
    else:
        print(f"\nDry run - would save {len(snapshots)} snapshots")
        for snap in snapshots:
            print(f"  {json.dumps(snap['metrics'], indent=2)[:200]}...")

    # Export markdown
    if args.export_md:
        generate_markdown_report(snapshots, "reports", args.period)

    print("\nDone!")


if __name__ == "__main__":
    main()
