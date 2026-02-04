# Data Model (Supabase Schema)

This document summarizes the Supabase schema used to power cEDH Analytics, including core tables and curated analytical views.

## Source of Truth

- Primary schema definitions live in Supabase migrations under `packages/backend/supabase/migrations`.
- A summarized data dictionary is maintained in `packages/backend/docs/data_dictionary.md`.

## Core Entities

### Tournaments

- `tournaments`: TopDeck.gg events (location, dates, player_count, rounds, top_cut).

### Players

- `players`: TopDeck.gg player identities (name, topdeck_id).

### Commanders

- `commanders`: Commander or partner combinations (name, color_identity, scryfall_ids).

### Participation

- `tournament_entries`: One player’s entry in one tournament (wins/losses/draws, standings, points, decklist).

### Games

- `games`: Individual pod games within a tournament round.
- `game_participants`: One player’s seat and result in a game.

### Matchups

- `commander_matchups`: Commander-vs-commander outcomes per game.

## Curated Views (Analytics)

### Commander Performance

- `commander_stats`: Aggregate entries, win rate, and top cut conversion. Filtered to 32+ player events.
- `commander_seat_stats`: Commander performance split by seat position.

### Trends

- `commander_weekly_trends`: Weekly commander aggregates.
- `commander_monthly_trends`: Monthly commander aggregates.
- `commander_wow_mom`: Latest week-over-week and month-over-month deltas.

### Card Analytics

- `card_frequencies_by_commander`: Card inclusion rates per commander.
- `card_frequencies_global`: Global card inclusion rates.
- `card_performance_by_commander`: Card performance by commander.
- `card_performance_global`: Global card performance.

### Tournament Journeys

- `player_tournament_journey`: Round-by-round progression for each player.
- `pod_composition`: Full pod lineups with seat and result.
- `player_seat_distribution`: Seat distribution and win rate by player.

### Survival Analysis

- `get_survival_curve` (RPC): Cumulative survival curve by round.
- `survival_curves_by_seat` (view): Survival by seat position and round.

### Regional Elo

- `regional_elo_ratings`: Per-player rating state at a region granularity.
- `regional_elo_leaderboard`: Regional leaderboard view.
- `regional_elo_regions`: Region availability and update metadata.
- `regional_elo_game_results`: Base view for regional Elo calculations.

### Meta Preparation

- `player_commander_entries`: Player’s commander history per tournament for fast meta scans.

## Conventions

- Analytics generally filter to tournaments with `player_count >= 32`.
- Partner commanders are stored as a single combined commander entity.
- “Unknown Commander” entries can appear when deck data is missing and are typically filtered from analytics.

## Frontend Consumption

The Next.js app reads from Supabase views for most pages to keep the anon role safe:

- Rankings: `commander_stats`, `commander_weekly_trends`, `commander_monthly_trends`
- Card analytics: `card_frequencies_*`, `card_performance_*`
- Turn order: `seat_position_stats`, `survival_curves_by_seat`
- Regional Elo: `regional_elo_leaderboard`, `regional_elo_regions`
- Meta prep: `player_commander_entries`

If a view is missing, the corresponding page will show empty state messaging.
