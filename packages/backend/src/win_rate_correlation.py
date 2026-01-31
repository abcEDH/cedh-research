#!/usr/bin/env python3
"""
Win-Rate Correlation Analysis Module for cEDH Analytics.

Correlates card presence with tournament performance to identify:
- Overperforming cards (positive win rate delta)
- Underperforming cards (negative win rate delta)
- Trap cards (popular but underperform)
- Spice cards (rare but overperform)

Usage:
    python src/win_rate_correlation.py --commander "Kraum / Tymna"
    python src/win_rate_correlation.py --trap-cards
    python src/win_rate_correlation.py --spice-cards
    python src/win_rate_correlation.py --refresh
"""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests


@dataclass
class CardPerformance:
    """Performance metrics for a single card."""
    card_name: str
    deck_count: int
    total_decks: int
    inclusion_rate: float
    avg_win_rate: float
    baseline_win_rate: float
    win_rate_delta: float
    std_win_rate: Optional[float] = None
    top_16_count: Optional[int] = None
    top_16_rate: Optional[float] = None
    performance_tier: Optional[str] = None
    commander_count: Optional[int] = None
    is_potential_trap: Optional[bool] = None
    is_spice: Optional[bool] = None

    def __str__(self) -> str:
        delta_str = f"{self.win_rate_delta:+.1%}" if self.win_rate_delta else "0.0%"
        return f"{self.card_name}: {self.avg_win_rate:.1%} win rate ({delta_str} vs baseline)"


@dataclass
class CommanderPerformanceProfile:
    """Performance analysis for a specific commander."""
    commander: str
    commander_id: str
    total_decks: int
    baseline_win_rate: float
    cards: list[CardPerformance]

    def get_overperformers(self, min_delta: float = 0.03) -> list[CardPerformance]:
        """Get cards that overperform the baseline."""
        return sorted(
            [c for c in self.cards if c.win_rate_delta >= min_delta],
            key=lambda c: c.win_rate_delta,
            reverse=True
        )

    def get_underperformers(self, max_delta: float = -0.03) -> list[CardPerformance]:
        """Get cards that underperform the baseline."""
        return sorted(
            [c for c in self.cards if c.win_rate_delta <= max_delta],
            key=lambda c: c.win_rate_delta
        )

    def get_by_tier(self, tier: str) -> list[CardPerformance]:
        """Get cards by performance tier."""
        return [c for c in self.cards if c.performance_tier == tier]


class WinRateCorrelationClient:
    """Client for querying win-rate correlation data from Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.url = supabase_url.rstrip("/")
        self.headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }

    def _query(self, table: str, params: dict = None) -> list[dict]:
        """Execute a query against the Supabase REST API."""
        endpoint = f"{self.url}/rest/v1/{table}"
        response = requests.get(endpoint, headers=self.headers, params=params or {}, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_commander_performance(self, commander_name: str, limit: int = 100) -> Optional[CommanderPerformanceProfile]:
        """Get card performance data for a specific commander."""
        params = {
            "commander": f"ilike.%{commander_name}%",
            "order": "deck_count.desc",
            "limit": str(limit),
        }
        results = self._query("card_performance_by_commander", params)

        if not results:
            return None

        first = results[0]
        profile = CommanderPerformanceProfile(
            commander=first["commander"],
            commander_id=first["commander_id"],
            total_decks=first["total_decks"],
            baseline_win_rate=float(first["baseline_win_rate"]),
            cards=[],
        )

        for row in results:
            profile.cards.append(CardPerformance(
                card_name=row["card_name"],
                deck_count=row["deck_count"],
                total_decks=row["total_decks"],
                inclusion_rate=float(row["inclusion_rate"]),
                avg_win_rate=float(row["avg_win_rate"]),
                baseline_win_rate=float(row["baseline_win_rate"]),
                win_rate_delta=float(row["win_rate_delta"]),
                std_win_rate=float(row["std_win_rate"]) if row.get("std_win_rate") else None,
                top_16_count=row.get("top_16_count"),
                top_16_rate=float(row["top_16_rate"]) if row.get("top_16_rate") else None,
                performance_tier=row.get("performance_tier"),
            ))

        return profile

    def get_global_performance(self, limit: int = 100) -> list[CardPerformance]:
        """Get global card performance data."""
        params = {
            "order": "deck_count.desc",
            "limit": str(limit),
        }
        results = self._query("card_performance_global", params)

        return [
            CardPerformance(
                card_name=row["card_name"],
                deck_count=row["deck_count"],
                total_decks=row["total_decks"],
                inclusion_rate=float(row["inclusion_rate"]),
                avg_win_rate=float(row["avg_win_rate"]),
                baseline_win_rate=float(row["baseline_win_rate"]),
                win_rate_delta=float(row["win_rate_delta"]),
                std_win_rate=float(row["std_win_rate"]) if row.get("std_win_rate") else None,
                top_16_rate=float(row["top_16_rate"]) if row.get("top_16_rate") else None,
                commander_count=row.get("commander_count"),
                is_potential_trap=row.get("is_potential_trap"),
                is_spice=row.get("is_spice"),
            )
            for row in results
        ]

    def get_trap_cards(self, limit: int = 50) -> list[CardPerformance]:
        """Get potential trap cards (popular but underperform)."""
        params = {
            "order": "trap_score.desc",
            "limit": str(limit),
        }
        results = self._query("trap_cards_report", params)

        return [
            CardPerformance(
                card_name=row["card_name"],
                deck_count=row["deck_count"],
                total_decks=0,  # Not in view
                inclusion_rate=float(row["inclusion_rate"]),
                avg_win_rate=float(row["avg_win_rate"]),
                baseline_win_rate=float(row["baseline_win_rate"]),
                win_rate_delta=float(row["win_rate_delta"]),
                top_16_rate=float(row["top_16_rate"]) if row.get("top_16_rate") else None,
                commander_count=row.get("commander_count"),
            )
            for row in results
        ]

    def get_spice_cards(self, limit: int = 50) -> list[CardPerformance]:
        """Get spice cards (rare but overperform)."""
        params = {
            "order": "win_rate_delta.desc",
            "limit": str(limit),
        }
        results = self._query("spice_cards_report", params)

        return [
            CardPerformance(
                card_name=row["card_name"],
                deck_count=row["deck_count"],
                total_decks=0,  # Not in view
                inclusion_rate=float(row["inclusion_rate"]),
                avg_win_rate=float(row["avg_win_rate"]),
                baseline_win_rate=float(row["baseline_win_rate"]),
                win_rate_delta=float(row["win_rate_delta"]),
                top_16_rate=float(row["top_16_rate"]) if row.get("top_16_rate") else None,
                commander_count=row.get("commander_count"),
            )
            for row in results
        ]

    def refresh_views(self) -> bool:
        """Refresh the performance materialized views (requires service_role)."""
        endpoint = f"{self.url}/rest/v1/rpc/refresh_card_performance"
        response = requests.post(endpoint, headers=self.headers, timeout=120)
        return response.status_code == 200


def print_commander_report(profile: CommanderPerformanceProfile):
    """Print a formatted performance report for a commander."""
    print(f"\n{'=' * 70}")
    print(f"WIN-RATE CORRELATION: {profile.commander}")
    print(f"{'=' * 70}")
    print(f"Total Decks Analyzed: {profile.total_decks}")
    print(f"Baseline Win Rate: {profile.baseline_win_rate:.1%}")
    print(f"Cards Analyzed: {len(profile.cards)}")

    # Tier distribution
    tiers = {}
    for card in profile.cards:
        tier = card.performance_tier or "unknown"
        tiers[tier] = tiers.get(tier, 0) + 1

    print(f"\nPerformance Tier Distribution:")
    for tier in ["overperformer", "neutral", "underperformer"]:
        count = tiers.get(tier, 0)
        print(f"  {tier.capitalize():15} {count:4} cards")

    print(f"\n--- Top Overperforming Cards ---")
    overperformers = profile.get_overperformers(min_delta=0.02)[:15]
    if overperformers:
        print(f"{'Card':<40} {'Win%':>8} {'Delta':>8} {'Decks':>6} {'Top16%':>8}")
        print("-" * 70)
        for card in overperformers:
            top16_str = f"{card.top_16_rate:.1%}" if card.top_16_rate else "-"
            print(f"{card.card_name:<40} {card.avg_win_rate:>7.1%} {card.win_rate_delta:>+7.1%} {card.deck_count:>6} {top16_str:>8}")
    else:
        print("  No significant overperformers found")

    print(f"\n--- Top Underperforming Cards ---")
    underperformers = profile.get_underperformers(max_delta=-0.02)[:15]
    if underperformers:
        print(f"{'Card':<40} {'Win%':>8} {'Delta':>8} {'Decks':>6} {'Top16%':>8}")
        print("-" * 70)
        for card in underperformers:
            top16_str = f"{card.top_16_rate:.1%}" if card.top_16_rate else "-"
            print(f"{card.card_name:<40} {card.avg_win_rate:>7.1%} {card.win_rate_delta:>+7.1%} {card.deck_count:>6} {top16_str:>8}")
    else:
        print("  No significant underperformers found")

    print(f"{'=' * 70}\n")


def print_trap_report(cards: list[CardPerformance]):
    """Print a formatted trap cards report."""
    print(f"\n{'=' * 70}")
    print("TRAP CARDS REPORT")
    print("Cards that are popular but consistently underperform")
    print(f"{'=' * 70}")

    if not cards:
        print("No trap cards identified.")
        return

    print(f"{'Card':<40} {'Incl%':>8} {'Win%':>8} {'Delta':>8} {'Cmdrs':>6}")
    print("-" * 70)

    for card in cards:
        cmdr_str = str(card.commander_count) if card.commander_count else "-"
        print(f"{card.card_name:<40} {card.inclusion_rate:>7.1%} {card.avg_win_rate:>7.1%} {card.win_rate_delta:>+7.1%} {cmdr_str:>6}")

    print(f"\nInterpretation: These cards appear in many decks but correlate with")
    print(f"below-average win rates. Consider whether they're worth the slot.")
    print(f"{'=' * 70}\n")


def print_spice_report(cards: list[CardPerformance]):
    """Print a formatted spice cards report."""
    print(f"\n{'=' * 70}")
    print("SPICE CARDS REPORT")
    print("Hidden gems: low-popularity cards that overperform")
    print(f"{'=' * 70}")

    if not cards:
        print("No spice cards identified.")
        return

    print(f"{'Card':<40} {'Incl%':>8} {'Win%':>8} {'Delta':>8} {'Cmdrs':>6}")
    print("-" * 70)

    for card in cards:
        cmdr_str = str(card.commander_count) if card.commander_count else "-"
        print(f"{card.card_name:<40} {card.inclusion_rate:>7.1%} {card.avg_win_rate:>7.1%} {card.win_rate_delta:>+7.1%} {cmdr_str:>6}")

    print(f"\nInterpretation: These underplayed cards correlate with above-average")
    print(f"win rates. They may be undervalued or fit specific strategies well.")
    print(f"{'=' * 70}\n")


def print_global_report(cards: list[CardPerformance], limit: int = 50):
    """Print global card performance report."""
    print(f"\n{'=' * 70}")
    print("GLOBAL CARD PERFORMANCE")
    print(f"{'=' * 70}")

    if not cards:
        print("No performance data available.")
        return

    print(f"{'Card':<40} {'Win%':>8} {'Delta':>8} {'Decks':>6} {'Cmdrs':>6}")
    print("-" * 70)

    for card in cards[:limit]:
        cmdr_str = str(card.commander_count) if card.commander_count else "-"
        print(f"{card.card_name:<40} {card.avg_win_rate:>7.1%} {card.win_rate_delta:>+7.1%} {card.deck_count:>6} {cmdr_str:>6}")

    print(f"{'=' * 70}\n")


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
        description="Win-Rate Correlation Analysis for cEDH Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Get performance data for a commander
    python src/win_rate_correlation.py --commander "Kraum / Tymna"
    python src/win_rate_correlation.py --commander "Kinnan"

    # View trap cards (popular but underperform)
    python src/win_rate_correlation.py --trap-cards

    # View spice cards (rare but overperform)
    python src/win_rate_correlation.py --spice-cards

    # Global card performance
    python src/win_rate_correlation.py --global-report

    # Refresh materialized views (requires service_role key)
    python src/win_rate_correlation.py --refresh
        """
    )

    parser.add_argument("--commander", "-c", type=str, help="Commander name to analyze")
    parser.add_argument("--trap-cards", "-t", action="store_true", help="Show trap cards report")
    parser.add_argument("--spice-cards", "-s", action="store_true", help="Show spice cards report")
    parser.add_argument("--global-report", "-g", action="store_true", help="Show global card performance")
    parser.add_argument("--limit", type=int, default=50, help="Number of cards to show (default: 50)")
    parser.add_argument("--refresh", "-r", action="store_true", help="Refresh materialized views")

    args = parser.parse_args()

    # Load credentials
    supabase_url, supabase_key = load_credentials()
    client = WinRateCorrelationClient(supabase_url, supabase_key)

    # Handle commands
    if args.refresh:
        print("Refreshing win-rate correlation materialized views...")
        if client.refresh_views():
            print("Views refreshed successfully.")
        else:
            print("Failed to refresh views. Ensure you're using the service_role key.")
        return

    if args.trap_cards:
        cards = client.get_trap_cards(limit=args.limit)
        print_trap_report(cards)
        return

    if args.spice_cards:
        cards = client.get_spice_cards(limit=args.limit)
        print_spice_report(cards)
        return

    if args.global_report:
        cards = client.get_global_performance(limit=args.limit)
        print_global_report(cards, limit=args.limit)
        return

    if args.commander:
        profile = client.get_commander_performance(args.commander, limit=args.limit)
        if profile:
            print_commander_report(profile)
        else:
            print(f"No data found for commander: {args.commander}")
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
