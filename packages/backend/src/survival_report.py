#!/usr/bin/env python3
"""
cEDH Survival Analysis Reporter

Generates reports from survival analysis views in Supabase.
Run SQL migration first: supabase/migrations/20260111100000_survival_analysis_views.sql

Usage:
    python src/survival_report.py                    # Full report
    python src/survival_report.py --report pod      # Pod survival only
    python src/survival_report.py --report meta     # Meta trends only
    python src/survival_report.py --commander "Kraum" # Commander-specific
    python src/survival_report.py --direct          # Use direct Postgres
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Optional: psycopg2 for direct connection
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class SurvivalReporter:
    """Generate survival analysis reports from Supabase views."""

    def __init__(self, url: str = None, key: str = None, db_url: str = None, use_direct: bool = False):
        self.use_direct = use_direct and PSYCOPG2_AVAILABLE and db_url

        if self.use_direct:
            self.db_url = db_url
            self._conn = None
        else:
            self.url = url
            self.headers = {
                "apikey": key,
                "Authorization": f"Bearer {key}",
            }

    def _query_rest(self, view: str, filters: dict = None, order: str = None, limit: int = None) -> list:
        """Query via REST API."""
        endpoint = f"{self.url}/rest/v1/{view}"
        params = {"select": "*"}

        if filters:
            for k, v in filters.items():
                params[k] = v
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)

        response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _query_direct(self, view: str, filters: dict = None, order: str = None, limit: int = None) -> list:
        """Query via direct Postgres."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.db_url)

        where_clauses = []
        params = []

        if filters:
            for col, val in filters.items():
                if val.startswith("eq."):
                    where_clauses.append(f"{col} = %s")
                    params.append(val[3:])
                elif val.startswith("ilike."):
                    where_clauses.append(f"{col} ILIKE %s")
                    params.append(val[6:])

        sql = f"SELECT * FROM {view}"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        if order:
            # Parse order like "entries.desc" -> "entries DESC"
            col, direction = order.split(".")
            sql += f" ORDER BY {col} {direction.upper()}"
        if limit:
            sql += f" LIMIT {limit}"

        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
            if not results:
                return []
            col_names = [desc[0] for desc in cursor.description]
            return [dict(zip(col_names, row)) for row in results]

    def query(self, view: str, **kwargs) -> list:
        """Query a view (auto-selects connection type)."""
        if self.use_direct:
            return self._query_direct(view, **kwargs)
        return self._query_rest(view, **kwargs)

    def close(self):
        """Close direct connection if open."""
        if self.use_direct and self._conn and not self._conn.closed:
            self._conn.close()


def print_table(data: list, columns: list, title: str = None, max_rows: int = 20):
    """Print data as a formatted table."""
    if not data:
        print(f"\n{title}: No data available")
        return

    if title:
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")

    # Calculate column widths
    widths = {}
    for col in columns:
        header = col.replace("_", " ").title()
        widths[col] = max(len(header), max(len(str(row.get(col, "N/A"))[:20]) for row in data[:max_rows]))

    # Print header
    header_row = " | ".join(col.replace("_", " ").title()[:widths[col]].ljust(widths[col]) for col in columns)
    print(header_row)
    print("-" * len(header_row))

    # Print data rows
    for row in data[:max_rows]:
        values = []
        for col in columns:
            val = row.get(col, "N/A")
            if isinstance(val, float):
                val = f"{val:.4f}" if val < 1 else f"{val:.2f}"
            values.append(str(val)[:widths[col]].ljust(widths[col]))
        print(" | ".join(values))

    if len(data) > max_rows:
        print(f"... and {len(data) - max_rows} more rows")


def pod_survival_report(reporter: SurvivalReporter):
    """Generate pod survival (seat position) report."""
    print("\n" + "="*70)
    print(" POD SURVIVAL ANALYSIS: Turn Order Advantage")
    print("="*70)

    # Overall seat position stats (exists in base schema)
    data = reporter.query("seat_position_stats", order="seat_position.asc")
    print_table(
        data,
        ["seat_position", "total_games", "wins", "losses", "win_rate"],
        "Overall Seat Position Win Rates"
    )

    # Seat position by commander (requires new migration)
    try:
        for seat in range(4):
            data = reporter.query(
                "seat_survival_by_commander",
                filters={"seat_position": f"eq.{seat}"},
                order="win_rate.desc",
                limit=10
            )
            if data:
                print_table(
                    data,
                    ["commander_name", "games_played", "wins", "win_rate", "win_rate_vs_expected"],
                    f"Top Commanders at Seat {seat} (first to act = 0)"
                )
    except Exception as e:
        print(f"\n[Note: seat_survival_by_commander view not found. Apply migration: supabase/migrations/20260111100000_survival_analysis_views.sql]")


def tournament_survival_report(reporter: SurvivalReporter):
    """Generate tournament survival (elimination depth) report."""
    print("\n" + "="*70)
    print(" TOURNAMENT SURVIVAL ANALYSIS: Elimination & Progression")
    print("="*70)

    # Commander stats (exists in base schema)
    try:
        data = reporter.query("commander_stats", order="total_entries.desc", limit=25)
        print_table(
            data,
            ["commander_name", "total_entries", "avg_win_rate", "top_16_count", "conversion_rate_top_16"],
            "Commander Performance (Base Schema)"
        )
    except Exception:
        pass

    # Commander tournament depth (requires new migration)
    try:
        data = reporter.query("commander_tournament_depth", order="avg_percentile.asc", limit=25)
        print_table(
            data,
            ["commander_name", "total_entries", "avg_standing", "avg_percentile", "top_cut_rate", "win_rate"],
            "Commander Tournament Depth (Lower Percentile = Better)"
        )
    except Exception:
        print("\n[Note: commander_tournament_depth view not found. Apply migration.]")

    # Player survival stats (requires new migration)
    try:
        data = reporter.query("player_survival_stats", order="top_cut_rate.desc", limit=20)
        print_table(
            data,
            ["player_name", "tournaments_played", "avg_standing", "top_cuts", "top_cut_rate", "main_commander"],
            "Top Players by Consistency"
        )
    except Exception:
        print("\n[Note: player_survival_stats view not found. Apply migration.]")


def meta_survival_report(reporter: SurvivalReporter):
    """Generate meta survival (temporal trends) report."""
    print("\n" + "="*70)
    print(" META SURVIVAL ANALYSIS: Temporal Trends & Momentum")
    print("="*70)

    # Commander momentum (rising/falling) - requires new migration
    try:
        data = reporter.query("commander_momentum", order="momentum_score.desc", limit=15)
        print_table(
            data,
            ["commander_name", "entries", "meta_share", "meta_share_delta", "win_rate_delta", "momentum_score"],
            "Rising Commanders (Positive Momentum)"
        )

        data = reporter.query("commander_momentum", order="momentum_score.asc", limit=15)
        print_table(
            data,
            ["commander_name", "entries", "meta_share", "meta_share_delta", "win_rate_delta", "momentum_score"],
            "Falling Commanders (Negative Momentum)"
        )
    except Exception:
        print("\n[Note: commander_momentum view not found. Apply migration.]")

    # New commanders - requires new migration
    try:
        data = reporter.query("commander_first_appearances", order="first_seen.desc", limit=15)
        print_table(
            data,
            ["commander_name", "first_seen", "total_entries", "tournaments", "avg_win_rate"],
            "Recently Emerged Commanders"
        )
    except Exception:
        print("\n[Note: commander_first_appearances view not found. Apply migration.]")


def commander_report(reporter: SurvivalReporter, commander_search: str):
    """Generate report for a specific commander."""
    print("\n" + "="*70)
    print(f" COMMANDER REPORT: {commander_search}")
    print("="*70)

    # Try new survival_summary view first, fall back to commander_stats
    try:
        data = reporter.query(
            "survival_summary",
            filters={"commander_name": f"ilike.*{commander_search}*"},
            limit=5
        )
        if data:
            print_table(
                data,
                ["commander_name", "total_entries", "tournaments", "overall_win_rate",
                 "avg_percentile", "top_cut_rate", "recent_entries", "recent_win_rate"],
                "Summary Statistics"
            )
            commander_name = data[0]["commander_name"]
        else:
            commander_name = None
    except Exception:
        # Fall back to commander_stats
        data = reporter.query(
            "commander_stats",
            filters={"commander_name": f"ilike.*{commander_search}*"},
            limit=5
        )
        if data:
            print_table(
                data,
                ["commander_name", "total_entries", "tournaments_played", "avg_win_rate",
                 "top_16_count", "conversion_rate_top_16"],
                "Summary Statistics (Base Schema)"
            )
            commander_name = data[0]["commander_name"]
        else:
            print(f"No data found for commander matching '{commander_search}'")
            return

    if not commander_name:
        print(f"No data found for commander matching '{commander_search}'")
        return

    # Survival curve by round (requires new migration)
    try:
        curve_data = reporter.query(
            "commander_survival_curve",
            filters={"commander_name": f"eq.{commander_name}"},
            order="round_number.asc"
        )
        print_table(
            curve_data,
            ["round_number", "games_played", "wins", "losses", "win_rate", "cumulative_wins"],
            f"Survival Curve: {commander_name}"
        )
    except Exception:
        print("\n[Note: commander_survival_curve view not found. Apply migration.]")

    # Seat position performance (requires new migration)
    try:
        seat_data = reporter.query(
            "seat_survival_by_commander",
            filters={"commander_name": f"eq.{commander_name}"},
            order="seat_position.asc"
        )
        print_table(
            seat_data,
            ["seat_position", "games_played", "wins", "win_rate", "win_rate_vs_expected"],
            f"Seat Position Performance: {commander_name}"
        )
    except Exception:
        print("\n[Note: seat_survival_by_commander view not found. Apply migration.]")


def full_report(reporter: SurvivalReporter):
    """Generate comprehensive survival analysis report."""
    print("\n" + "#"*70)
    print(" cEDH SURVIVAL ANALYSIS REPORT")
    print(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*70)

    # Summary overview - try new view first, fall back to commander_stats
    try:
        data = reporter.query("survival_summary", order="total_entries.desc", limit=20)
        print_table(
            data,
            ["commander_name", "total_entries", "overall_win_rate", "top_cut_rate", "recent_win_rate"],
            "Top 20 Commanders by Volume"
        )
    except Exception:
        data = reporter.query("commander_stats", order="total_entries.desc", limit=20)
        print_table(
            data,
            ["commander_name", "total_entries", "avg_win_rate", "top_16_count", "conversion_rate_top_16"],
            "Top 20 Commanders by Volume (Base Schema)"
        )

    pod_survival_report(reporter)
    tournament_survival_report(reporter)
    meta_survival_report(reporter)


def load_env():
    """Load credentials from environment or .env file."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    db_url = os.getenv("SUPABASE_DB_URL")

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
                    elif k == "SUPABASE_DB_URL":
                        db_url = v

    return url, key, db_url


def main():
    parser = argparse.ArgumentParser(description="cEDH Survival Analysis Reporter")
    parser.add_argument(
        "--report",
        choices=["full", "pod", "tournament", "meta"],
        default="full",
        help="Report type to generate"
    )
    parser.add_argument(
        "--commander",
        type=str,
        help="Generate report for specific commander (partial name match)"
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct Postgres connection"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file (default: stdout)"
    )
    args = parser.parse_args()

    url, key, db_url = load_env()

    if args.direct and not PSYCOPG2_AVAILABLE:
        print("Warning: psycopg2 not installed, falling back to REST API")
        args.direct = False

    if args.direct and not db_url:
        print("Error: SUPABASE_DB_URL required for --direct mode")
        sys.exit(1)

    if not args.direct and (not url or not key):
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    reporter = SurvivalReporter(url=url, key=key, db_url=db_url, use_direct=args.direct)

    # Redirect output if file specified
    original_stdout = sys.stdout
    if args.output:
        sys.stdout = open(args.output, "w")

    try:
        if args.commander:
            commander_report(reporter, args.commander)
        elif args.report == "pod":
            pod_survival_report(reporter)
        elif args.report == "tournament":
            tournament_survival_report(reporter)
        elif args.report == "meta":
            meta_survival_report(reporter)
        else:
            full_report(reporter)
    finally:
        reporter.close()
        if args.output:
            sys.stdout.close()
            sys.stdout = original_stdout
            print(f"Report saved to: {args.output}")


if __name__ == "__main__":
    main()
