#!/usr/bin/env python3
"""
Card Frequency Analysis Module for cEDH Analytics.

Calculates card inclusion rates and tier classifications for commanders
using data from the card_frequencies_by_commander materialized view.

Usage:
    python src/card_frequency.py --commander "Kraum / Tymna"
    python src/card_frequency.py --global-report
    python src/card_frequency.py --refresh
"""

import argparse
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests


@dataclass
class CardFrequencyResult:
    """Result of card frequency analysis for a single card."""
    card_name: str
    deck_count: int
    total_decks: int
    inclusion_rate: float
    tier: str
    synergy_score: Optional[float] = None
    commander_count: Optional[int] = None  # For global stats

    def __str__(self) -> str:
        rate_pct = f"{self.inclusion_rate * 100:.1f}%"
        synergy_str = f" (synergy: {self.synergy_score:+.1%})" if self.synergy_score else ""
        return f"{self.card_name}: {rate_pct} [{self.tier}]{synergy_str}"


@dataclass
class CommanderCardPool:
    """Card frequency analysis for a specific commander."""
    commander: str
    commander_id: str
    total_decks: int
    cards: dict[str, CardFrequencyResult] = field(default_factory=dict)

    def get_core_cards(self, threshold: float = 0.80) -> list[CardFrequencyResult]:
        """Get cards at or above the core threshold."""
        return sorted(
            [c for c in self.cards.values() if c.inclusion_rate >= threshold],
            key=lambda c: c.inclusion_rate,
            reverse=True
        )

    def get_flex_slots(self, min_rate: float = 0.10, max_rate: float = 0.50) -> list[CardFrequencyResult]:
        """Get cards in the flex range (good options but not universal)."""
        return sorted(
            [c for c in self.cards.values() if min_rate <= c.inclusion_rate < max_rate],
            key=lambda c: c.inclusion_rate,
            reverse=True
        )

    def get_spice_cards(self, max_rate: float = 0.10) -> list[CardFrequencyResult]:
        """Get low-inclusion "spice" cards."""
        return sorted(
            [c for c in self.cards.values() if c.inclusion_rate < max_rate],
            key=lambda c: c.inclusion_rate,
            reverse=True
        )

    def get_synergy_cards(self, min_synergy: float = 0.10) -> list[CardFrequencyResult]:
        """Get cards with high synergy scores (commander-specific)."""
        return sorted(
            [c for c in self.cards.values() if c.synergy_score and c.synergy_score >= min_synergy],
            key=lambda c: c.synergy_score or 0,
            reverse=True
        )

    def tier_summary(self) -> dict[str, int]:
        """Count cards in each tier."""
        tiers = Counter(c.tier for c in self.cards.values())
        return dict(tiers)


def classify_tier(inclusion_rate: float) -> str:
    """Classify a card tier based on inclusion rate."""
    if inclusion_rate >= 0.80:
        return "core"
    elif inclusion_rate >= 0.60:
        return "essential"
    elif inclusion_rate >= 0.30:
        return "common"
    elif inclusion_rate >= 0.10:
        return "flex"
    return "spice"


class CardFrequencyClient:
    """Client for querying card frequency data from Supabase."""

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

    def get_commander_card_pool(self, commander_name: str) -> Optional[CommanderCardPool]:
        """Get card frequency data for a specific commander."""
        # Query the commander_card_report view for synergy scores
        params = {
            "commander": f"ilike.%{commander_name}%",
            "order": "inclusion_rate.desc",
        }
        results = self._query("commander_card_report", params)

        if not results:
            return None

        # Build the card pool
        first = results[0]
        pool = CommanderCardPool(
            commander=first["commander"],
            commander_id=first["commander_id"],
            total_decks=first["total_decks"],
        )

        for row in results:
            pool.cards[row["card_name"]] = CardFrequencyResult(
                card_name=row["card_name"],
                deck_count=row["deck_count"],
                total_decks=row["total_decks"],
                inclusion_rate=float(row["inclusion_rate"]),
                tier=row["tier"],
                synergy_score=float(row["synergy_score"]) if row.get("synergy_score") else None,
            )

        return pool

    def get_global_frequencies(self, limit: int = 100, tier: str = None) -> list[CardFrequencyResult]:
        """Get global card frequencies across all commanders."""
        params = {
            "order": "inclusion_rate.desc",
            "limit": str(limit),
        }
        if tier:
            params["tier"] = f"eq.{tier}"

        results = self._query("card_frequencies_global", params)

        return [
            CardFrequencyResult(
                card_name=row["card_name"],
                deck_count=row["deck_count"],
                total_decks=row["total_decks"],
                inclusion_rate=float(row["inclusion_rate"]),
                tier=row["tier"],
                commander_count=row["commander_count"],
            )
            for row in results
        ]

    def list_commanders(self, min_decks: int = 10) -> list[dict]:
        """List commanders with card frequency data available."""
        # Get distinct commanders from the materialized view
        params = {
            "select": "commander,commander_id,total_decks",
            "total_decks": f"gte.{min_decks}",
            "order": "total_decks.desc",
        }
        results = self._query("card_frequencies_by_commander", params)

        # Deduplicate
        seen = set()
        commanders = []
        for row in results:
            if row["commander_id"] not in seen:
                seen.add(row["commander_id"])
                commanders.append({
                    "name": row["commander"],
                    "id": row["commander_id"],
                    "deck_count": row["total_decks"],
                })
        return commanders

    def refresh_views(self) -> bool:
        """Refresh the card frequency materialized views (requires service_role)."""
        endpoint = f"{self.url}/rest/v1/rpc/refresh_card_frequencies"
        response = requests.post(endpoint, headers=self.headers, timeout=120)
        return response.status_code == 200


def print_commander_report(pool: CommanderCardPool, show_all: bool = False):
    """Print a formatted report for a commander's card frequencies."""
    print(f"\n{'=' * 70}")
    print(f"CARD FREQUENCY REPORT: {pool.commander}")
    print(f"{'=' * 70}")
    print(f"Total Decks Analyzed: {pool.total_decks}")
    print(f"Unique Cards: {len(pool.cards)}")

    tiers = pool.tier_summary()
    print(f"\nTier Distribution:")
    for tier in ["core", "essential", "common", "flex", "spice"]:
        count = tiers.get(tier, 0)
        print(f"  {tier.capitalize():12} {count:4} cards")

    print(f"\n--- Core Cards (80%+ inclusion) ---")
    for card in pool.get_core_cards()[:20]:
        print(f"  {card}")

    print(f"\n--- High Synergy Cards (10%+ above global) ---")
    synergy_cards = pool.get_synergy_cards(min_synergy=0.10)[:15]
    if synergy_cards:
        for card in synergy_cards:
            print(f"  {card}")
    else:
        print("  No high-synergy cards found")

    if show_all:
        print(f"\n--- Essential Cards (60-79%) ---")
        essential = [c for c in pool.cards.values() if 0.60 <= c.inclusion_rate < 0.80]
        for card in sorted(essential, key=lambda c: c.inclusion_rate, reverse=True):
            print(f"  {card}")

        print(f"\n--- Common Cards (30-59%) ---")
        common = [c for c in pool.cards.values() if 0.30 <= c.inclusion_rate < 0.60]
        for card in sorted(common, key=lambda c: c.inclusion_rate, reverse=True):
            print(f"  {card}")

    print(f"{'=' * 70}\n")


def print_global_report(cards: list[CardFrequencyResult], title: str = "GLOBAL CARD FREQUENCIES"):
    """Print a formatted global card frequency report."""
    print(f"\n{'=' * 70}")
    print(title)
    print(f"{'=' * 70}")

    if not cards:
        print("No cards found.")
        return

    print(f"{'Card Name':<40} {'Rate':>8} {'Decks':>8} {'Cmdrs':>6} {'Tier':>10}")
    print("-" * 70)

    for card in cards:
        rate_str = f"{card.inclusion_rate * 100:.1f}%"
        cmdr_str = str(card.commander_count) if card.commander_count else "-"
        print(f"{card.card_name:<40} {rate_str:>8} {card.deck_count:>8} {cmdr_str:>6} {card.tier:>10}")

    print(f"{'=' * 70}\n")


def load_credentials() -> tuple[str, str]:
    """Load Supabase credentials from environment or .env file."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        if key == "SUPABASE_URL":
                            supabase_url = value
                        elif key == "SUPABASE_SERVICE_KEY":
                            supabase_key = value

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    return supabase_url, supabase_key


def main():
    parser = argparse.ArgumentParser(
        description="Card Frequency Analysis for cEDH Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Get card frequencies for a commander
    python src/card_frequency.py --commander "Kraum / Tymna"
    python src/card_frequency.py --commander "Kinnan"

    # List commanders with frequency data
    python src/card_frequency.py --list-commanders

    # Global card frequency report
    python src/card_frequency.py --global-report
    python src/card_frequency.py --global-report --tier core

    # Refresh materialized views (requires service_role key)
    python src/card_frequency.py --refresh
        """
    )

    parser.add_argument("--commander", "-c", type=str, help="Commander name to analyze")
    parser.add_argument("--list-commanders", "-l", action="store_true", help="List available commanders")
    parser.add_argument("--global-report", "-g", action="store_true", help="Show global card frequencies")
    parser.add_argument("--tier", "-t", type=str, choices=["core", "essential", "common", "flex", "spice"],
                        help="Filter by tier (for global report)")
    parser.add_argument("--limit", type=int, default=50, help="Number of cards to show (default: 50)")
    parser.add_argument("--show-all", "-a", action="store_true", help="Show all tiers in commander report")
    parser.add_argument("--refresh", "-r", action="store_true", help="Refresh materialized views")
    parser.add_argument("--min-decks", type=int, default=10, help="Minimum decks for commander listing")

    args = parser.parse_args()

    # Load credentials
    supabase_url, supabase_key = load_credentials()
    client = CardFrequencyClient(supabase_url, supabase_key)

    # Handle commands
    if args.refresh:
        print("Refreshing card frequency materialized views...")
        if client.refresh_views():
            print("Views refreshed successfully.")
        else:
            print("Failed to refresh views. Ensure you're using the service_role key.")
        return

    if args.list_commanders:
        print(f"\nCommanders with Card Frequency Data (min {args.min_decks} decks):\n")
        commanders = client.list_commanders(min_decks=args.min_decks)
        for cmd in commanders[:50]:
            print(f"  {cmd['name']:<50} ({cmd['deck_count']} decks)")
        if len(commanders) > 50:
            print(f"\n  ... and {len(commanders) - 50} more")
        return

    if args.global_report:
        cards = client.get_global_frequencies(limit=args.limit, tier=args.tier)
        title = f"GLOBAL CARD FREQUENCIES"
        if args.tier:
            title += f" - {args.tier.upper()} TIER"
        print_global_report(cards, title)
        return

    if args.commander:
        pool = client.get_commander_card_pool(args.commander)
        if pool:
            print_commander_report(pool, show_all=args.show_all)
        else:
            print(f"No data found for commander: {args.commander}")
            print("Use --list-commanders to see available commanders.")
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
