#!/usr/bin/env python3
"""
Turn Order Fairness Analysis Module for cEDH Analytics.

Performs chi-square goodness-of-fit testing to determine if seat position
significantly affects win rate in 4-player Commander games.

Usage:
    python src/turn_order_analysis.py --analyze
    python src/turn_order_analysis.py --power-analysis
    python src/turn_order_analysis.py --by-tournament

References:
    - cEDH League Season 1: https://github.com/isleep2late/cEDHLeague-Season1
    - scipy.stats.chisquare: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chisquare.html
"""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import requests
from scipy import stats


@dataclass
class PositionStats:
    """Win statistics for a single seat position."""
    position: int
    wins: int
    losses: int
    draws: int
    total: int

    @property
    def decisive_games(self) -> int:
        """Games that ended with a winner (not draws)."""
        return self.wins + self.losses

    @property
    def win_rate(self) -> float:
        """Win rate among decisive games."""
        if self.decisive_games == 0:
            return 0.0
        return self.wins / self.decisive_games

    @property
    def raw_win_rate(self) -> float:
        """Win rate including draws as non-wins."""
        if self.total == 0:
            return 0.0
        return self.wins / self.total

    def confidence_interval(self, confidence: float = 0.95) -> tuple[float, float]:
        """
        Calculate Wilson score confidence interval for win rate.

        Wilson score is preferred for:
        - Small to medium samples
        - Extreme proportions (close to 0 or 1)
        - Produces asymmetric intervals
        """
        if self.decisive_games == 0:
            return (0.0, 1.0)

        n = self.decisive_games
        p = self.win_rate
        z = stats.norm.ppf(1 - (1 - confidence) / 2)

        denominator = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denominator
        spread = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator

        return (max(0, center - spread), min(1, center + spread))


@dataclass
class TurnOrderAnalysis:
    """Complete turn order fairness analysis results."""
    # Position statistics
    positions: list[PositionStats]

    # Chi-square test results
    chi_square: float
    p_value: float
    degrees_of_freedom: int

    # Effect size
    cohens_w: float

    # Test parameters
    alpha: float
    expected_rate: float  # Usually 0.25
    draw_rate: float

    @property
    def is_significant(self) -> bool:
        """True if result is statistically significant at alpha level."""
        return self.p_value < self.alpha

    @property
    def total_decisive_games(self) -> int:
        """Total games with a winner."""
        return sum(p.decisive_games for p in self.positions) // 4

    @property
    def total_wins(self) -> int:
        """Total wins across all positions."""
        return sum(p.wins for p in self.positions)

    def effect_interpretation(self) -> str:
        """
        Interpret Cohen's w effect size.

        Cohen (1988) conventions:
        - w = 0.10: small effect
        - w = 0.30: medium effect
        - w = 0.50: large effect
        """
        if self.cohens_w < 0.10:
            return "negligible"
        elif self.cohens_w < 0.30:
            return "small"
        elif self.cohens_w < 0.50:
            return "medium"
        else:
            return "large"


def analyze_turn_order(
    positions: list[PositionStats],
    alpha: float = 0.05,
) -> TurnOrderAnalysis:
    """
    Perform chi-square goodness-of-fit test for turn order fairness.

    The null hypothesis is that each seat position has equal win probability.

    Args:
        positions: List of PositionStats for seats 0-3
        alpha: Significance level (default 0.05 for 95% confidence)

    Returns:
        TurnOrderAnalysis with complete results
    """
    if len(positions) != 4:
        raise ValueError(f"Expected 4 positions, got {len(positions)}")

    # Calculate draw rate from the data
    total_games = sum(p.total for p in positions) // 4
    total_draws = sum(p.draws for p in positions) // 4
    draw_rate = total_draws / total_games if total_games > 0 else 0

    # Calculate expected win rate (adjusted for draws)
    # Under null hypothesis: each seat has 25% chance of winning
    expected_rate = 0.25

    # Get observed wins per position
    observed_wins = [p.wins for p in positions]
    total_wins = sum(observed_wins)

    # Calculate expected wins per position
    # Under null: each seat should have equal share of total wins
    expected_wins = [total_wins / 4 for _ in positions]

    # Chi-square goodness-of-fit test
    chi2, p_value = stats.chisquare(f_obs=observed_wins, f_exp=expected_wins)
    df = len(positions) - 1  # 3 degrees of freedom

    # Cohen's w effect size: w = sqrt(chi2 / n)
    cohens_w = np.sqrt(chi2 / total_wins) if total_wins > 0 else 0

    return TurnOrderAnalysis(
        positions=positions,
        chi_square=chi2,
        p_value=p_value,
        degrees_of_freedom=df,
        cohens_w=cohens_w,
        alpha=alpha,
        expected_rate=expected_rate,
        draw_rate=draw_rate,
    )


def required_sample_size(
    effect_size: float = 0.2,
    power: float = 0.80,
    alpha: float = 0.05,
) -> int:
    """
    Calculate required sample size to detect an effect with given power.

    Uses statsmodels GofChisquarePower approximation.

    Args:
        effect_size: Cohen's w (0.1=small, 0.2=medium-small, 0.3=medium, 0.5=large)
        power: Desired statistical power (default 0.80)
        alpha: Significance level (default 0.05)

    Returns:
        Required number of games with complete turn order data
    """
    try:
        from statsmodels.stats.power import GofChisquarePower
        analysis = GofChisquarePower()
        n = analysis.solve_power(
            effect_size=effect_size,
            n_bins=4,
            alpha=alpha,
            power=power,
            nobs=None
        )
        return int(np.ceil(n))
    except ImportError:
        # Approximation if statsmodels not available
        # Formula: n ≈ (chi2_crit / w^2) where chi2_crit ≈ 7.81 for df=3, alpha=0.05
        chi2_crit = stats.chi2.ppf(1 - alpha, df=3)
        # Adjust for power (rough approximation)
        power_factor = stats.norm.ppf(power) + stats.norm.ppf(1 - alpha)
        n = (power_factor**2) / (effect_size**2) * 4
        return int(np.ceil(n))


def generate_report(analysis: TurnOrderAnalysis) -> str:
    """Generate a human-readable analysis report."""
    lines = [
        "=" * 70,
        "TURN ORDER FAIRNESS ANALYSIS REPORT",
        "=" * 70,
        "",
        f"Total Games Analyzed: {analysis.total_decisive_games:,}",
        f"Total Wins: {analysis.total_wins:,}",
        f"Draw Rate: {analysis.draw_rate * 100:.1f}%",
        f"Expected Win Rate (adjusted): {analysis.expected_rate * 100:.2f}%",
        "",
        "--- Win Rates by Seat Position ---",
    ]

    for pos in analysis.positions:
        ci_low, ci_high = pos.confidence_interval()
        diff = (pos.win_rate - analysis.expected_rate) * 100
        diff_from_25 = (pos.win_rate - 0.25) * 100

        lines.append(
            f"  Seat {pos.position} ({'1st' if pos.position == 0 else '2nd' if pos.position == 1 else '3rd' if pos.position == 2 else '4th'}): "
            f"{pos.win_rate * 100:.1f}% ({diff_from_25:+.1f}pp from 25%)"
        )
        lines.append(
            f"         95% CI: [{ci_low * 100:.1f}%, {ci_high * 100:.1f}%] "
            f"| {pos.wins:,} wins / {pos.decisive_games:,} decisive games"
        )

    lines.extend([
        "",
        "--- Statistical Test Results ---",
        f"Chi-square statistic: {analysis.chi_square:.2f}",
        f"Degrees of freedom: {analysis.degrees_of_freedom}",
        f"P-value: {analysis.p_value:.2e}",
        f"Significance level (alpha): {analysis.alpha}",
        "",
        f"Effect size (Cohen's w): {analysis.cohens_w:.3f} ({analysis.effect_interpretation()})",
        "",
        "--- Interpretation ---",
    ])

    if analysis.is_significant:
        lines.append("CONCLUSION: Turn order has a STATISTICALLY SIGNIFICANT effect")
        lines.append("on win rate. The null hypothesis of equal probability is REJECTED.")
        lines.append("")
        lines.append(f"With p = {analysis.p_value:.2e}, there is strong evidence that seat")
        lines.append("position affects win probability in cEDH tournaments.")

        # Calculate the first-player advantage
        first_wr = analysis.positions[0].win_rate
        last_wr = analysis.positions[3].win_rate
        advantage = first_wr - last_wr
        lines.append("")
        lines.append(f"First-player advantage: {advantage * 100:.1f} percentage points")
        lines.append(f"(Seat 0: {first_wr * 100:.1f}% vs Seat 3: {last_wr * 100:.1f}%)")
    else:
        lines.append("CONCLUSION: No statistically significant turn order effect detected.")
        lines.append("Cannot reject the null hypothesis of equal win probability.")

        if analysis.p_value < 0.10:
            lines.append(f"\nNOTE: P-value ({analysis.p_value:.3f}) approaches significance.")
            lines.append("Consider collecting more data.")

    # Power analysis
    lines.extend([
        "",
        "--- Sample Size Reference ---",
    ])
    for effect, desc in [(0.10, "small"), (0.20, "medium-small"), (0.30, "medium")]:
        n = required_sample_size(effect_size=effect)
        status = "✓ SUFFICIENT" if analysis.total_decisive_games >= n else f"need {n:,}"
        lines.append(f"  To detect {desc} effect (w={effect}): {status}")

    lines.append("=" * 70)
    return "\n".join(lines)


class TurnOrderClient:
    """Client for querying turn order data from Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.url = supabase_url.rstrip("/")
        self.headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }

    def _query_sql(self, sql: str) -> list[dict]:
        """Execute raw SQL via RPC (requires a SQL function or direct REST)."""
        # Use PostgREST for simple queries
        endpoint = f"{self.url}/rest/v1/rpc/execute_sql"
        response = requests.post(
            endpoint,
            headers=self.headers,
            json={"query": sql},
            timeout=30
        )
        if response.status_code == 404:
            # Fallback: query the view directly
            return self._query_view()
        response.raise_for_status()
        return response.json()

    def _query_view(self) -> list[dict]:
        """Query seat_position_stats view via REST."""
        endpoint = f"{self.url}/rest/v1/seat_position_stats"
        response = requests.get(endpoint, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_position_stats(self) -> list[PositionStats]:
        """Get seat position statistics from the database."""
        # Use RPC to run aggregation on server side (avoids pagination issues)
        # First try the seat_position_stats view
        endpoint = f"{self.url}/rest/v1/seat_position_stats"
        headers = self.headers.copy()
        headers["Range"] = "0-9"  # Only 4 rows expected

        response = requests.get(endpoint, headers=headers, timeout=60)

        if response.status_code == 200:
            data = response.json()
            positions = []
            for row in data:
                pos = row.get("seat_position")
                if pos is None:
                    continue
                positions.append(PositionStats(
                    position=pos,
                    wins=row.get("wins", 0),
                    losses=row.get("losses", 0),
                    draws=row.get("draws", 0),
                    total=row.get("total_games", 0),
                ))
            if positions:
                return sorted(positions, key=lambda p: p.position)

        # Fallback: paginated query
        return self._get_position_stats_paginated()

    def _get_position_stats_paginated(self) -> list[PositionStats]:
        """Fallback: fetch all records with pagination."""
        position_data = {i: {"wins": 0, "losses": 0, "draws": 0, "total": 0} for i in range(4)}
        offset = 0
        batch_size = 10000

        while True:
            endpoint = f"{self.url}/rest/v1/game_participants"
            headers = self.headers.copy()
            headers["Range"] = f"{offset}-{offset + batch_size - 1}"
            headers["Prefer"] = "count=exact"

            params = {
                "select": "seat_position,result",
                "seat_position": "not.is.null",
                "order": "id",
            }
            response = requests.get(endpoint, headers=headers, params=params, timeout=120)
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            for row in data:
                pos = row["seat_position"]
                if pos not in position_data:
                    continue
                position_data[pos]["total"] += 1
                if row["result"] == "win":
                    position_data[pos]["wins"] += 1
                elif row["result"] == "loss":
                    position_data[pos]["losses"] += 1
                elif row["result"] == "draw":
                    position_data[pos]["draws"] += 1

            if len(data) < batch_size:
                break
            offset += batch_size

        return [
            PositionStats(
                position=i,
                wins=position_data[i]["wins"],
                losses=position_data[i]["losses"],
                draws=position_data[i]["draws"],
                total=position_data[i]["total"],
            )
            for i in range(4)
        ]

    def get_position_stats_by_tournament_size(self, min_players: int = 32) -> list[PositionStats]:
        """Get position stats filtered by tournament size."""
        # This requires a join, so we'll use a simpler approach
        # Query tournaments first, then filter
        endpoint = f"{self.url}/rest/v1/game_participants"
        params = {
            "select": "seat_position,result,game_id,games!inner(tournament_id,tournaments!inner(player_count))",
            "seat_position": "not.is.null",
            "games.tournaments.player_count": f"gte.{min_players}",
        }
        response = requests.get(endpoint, headers=self.headers, params=params, timeout=120)

        if response.status_code != 200:
            # Fallback to unfiltered
            return self.get_position_stats()

        data = response.json()

        # Aggregate
        position_data = {i: {"wins": 0, "losses": 0, "draws": 0, "total": 0} for i in range(4)}
        for row in data:
            pos = row["seat_position"]
            if pos not in position_data:
                continue
            position_data[pos]["total"] += 1
            if row["result"] == "win":
                position_data[pos]["wins"] += 1
            elif row["result"] == "loss":
                position_data[pos]["losses"] += 1
            elif row["result"] == "draw":
                position_data[pos]["draws"] += 1

        return [
            PositionStats(
                position=i,
                wins=position_data[i]["wins"],
                losses=position_data[i]["losses"],
                draws=position_data[i]["draws"],
                total=position_data[i]["total"],
            )
            for i in range(4)
        ]


def load_credentials() -> tuple[str, str]:
    """Load Supabase credentials from environment or .env file."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        if key == "SUPABASE_URL":
                            supabase_url = value
                        elif key in ("SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"):
                            supabase_key = value

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY/SUPABASE_ANON_KEY must be set")
        sys.exit(1)

    return supabase_url, supabase_key


def main():
    parser = argparse.ArgumentParser(
        description="Turn Order Fairness Analysis for cEDH Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run full turn order analysis
    python src/turn_order_analysis.py --analyze

    # Show power analysis / sample size requirements
    python src/turn_order_analysis.py --power-analysis

    # Analyze with custom significance level
    python src/turn_order_analysis.py --analyze --alpha 0.01

    # Use local data (for testing without database)
    python src/turn_order_analysis.py --local-test
        """
    )

    parser.add_argument("--analyze", "-a", action="store_true", help="Run turn order analysis")
    parser.add_argument("--power-analysis", "-p", action="store_true", help="Show sample size requirements")
    parser.add_argument("--alpha", type=float, default=0.05, help="Significance level (default: 0.05)")
    parser.add_argument("--min-players", type=int, default=32, help="Minimum tournament size")
    parser.add_argument("--local-test", action="store_true", help="Test with sample data (no database)")

    args = parser.parse_args()

    if args.power_analysis:
        print("\n" + "=" * 50)
        print("SAMPLE SIZE REQUIREMENTS FOR TURN ORDER ANALYSIS")
        print("=" * 50)
        print("\nPower = 0.80 (80% chance of detecting true effect)")
        print("Alpha = 0.05 (5% false positive rate)")
        print("\n" + "-" * 50)
        for effect, desc in [
            (0.05, "very small"),
            (0.10, "small"),
            (0.15, "small-medium"),
            (0.20, "medium-small"),
            (0.30, "medium"),
            (0.50, "large"),
        ]:
            n = required_sample_size(effect_size=effect)
            print(f"  Cohen's w = {effect:.2f} ({desc:14}): {n:,} games")
        print("-" * 50)
        print("\nNote: cEDH League Season 1 had ~90 games (insufficient for small effects)")
        print("=" * 50 + "\n")
        return

    if args.local_test:
        # Use sample data for testing
        print("Using local test data...")
        positions = [
            PositionStats(position=0, wins=1335, losses=2807, draws=1508, total=5650),
            PositionStats(position=1, wins=1107, losses=3035, draws=1508, total=5650),
            PositionStats(position=2, wins=886, losses=3255, draws=1507, total=5648),
            PositionStats(position=3, wins=723, losses=3270, draws=1486, total=5479),
        ]
    elif args.analyze:
        # Load from database
        supabase_url, supabase_key = load_credentials()
        client = TurnOrderClient(supabase_url, supabase_key)

        print("Fetching turn order data from database...")
        positions = client.get_position_stats()
    else:
        parser.print_help()
        return

    # Run analysis
    analysis = analyze_turn_order(positions, alpha=args.alpha)
    report = generate_report(analysis)
    print(report)


if __name__ == "__main__":
    main()
