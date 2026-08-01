# Data Model (Supabase Schema)

This document summarizes the Supabase schema used to power cEDH Analytics, including core tables and curated analytical views.

## Source of Truth

- Primary schema definitions live in Supabase migrations under `packages/backend/supabase/migrations`.
- A summarized data dictionary is maintained in `packages/backend/docs/data_dictionary.md`.

## ETL Flow

```mermaid
flowchart LR
  A["TopDeck.gg API"] --> B["Ingest: packages/backend/src/ingest.py"]
  B --> C["Base tables: tournaments · players · tournament_entries · games · game_participants"]
  C --> D["Transform jobs: card_frequency.py · regional_elo.py · win_rate_correlation.py · turn_order_analysis.py"]
  D --> E["Analytics views + materialized views"]
  E --> F["Next.js frontend: apps/web"]

  classDef source fill:#111827,stroke:#111827,color:#f9fafb;
  classDef process fill:#0f766e,stroke:#0f766e,color:#f8fafc;
  classDef store fill:#1d4ed8,stroke:#1d4ed8,color:#eff6ff;
  classDef view fill:#7c2d12,stroke:#7c2d12,color:#fff7ed;
  classDef client fill:#0b4a6f,stroke:#0b4a6f,color:#e0f2fe;

  class A source;
  class B,D process;
  class C store;
  class E view;
  class F client;
```

## Data Model (ERD)

```mermaid
erDiagram
  COMMANDERS ||--o{ TOURNAMENT_ENTRIES : has
  PLAYERS ||--o{ TOURNAMENT_ENTRIES : has
  TOURNAMENTS ||--o{ TOURNAMENT_ENTRIES : has

  TOURNAMENTS ||--o{ GAMES : has
  GAMES ||--o{ GAME_PARTICIPANTS : has
  TOURNAMENT_ENTRIES ||--o{ GAME_PARTICIPANTS : has

  GAMES ||--o{ COMMANDER_MATCHUPS : has
  COMMANDERS ||--o{ COMMANDER_MATCHUPS : has

  COMMANDERS {
    uuid id PK
    text name
    text[] commander_names
  }

  PLAYERS {
    uuid id PK
    text topdeck_id
    text name
  }

  TOURNAMENTS {
    uuid id PK
    text topdeck_tid
    timestamptz start_date
    int player_count
  }

  TOURNAMENT_ENTRIES {
    uuid id PK
    uuid tournament_id FK
    uuid player_id FK
    uuid commander_id FK
  }

  GAMES {
    uuid id PK
    uuid tournament_id FK
    text game_key UK
    int round_number
    text round_name
    int table_number
  }

  GAME_PARTICIPANTS {
    uuid id PK
    uuid game_id FK
    uuid entry_id FK
    int seat_position
    text result
  }

  COMMANDER_MATCHUPS {
    uuid id PK
    uuid game_id FK
    uuid commander_id FK
    uuid opponent_commander_id FK
  }
```

## Core Entities

## Identity And Idempotency

- Every major base row has its own UUID primary key: `players.id`, `tournaments.id`, `tournament_entries.id`, `games.id`, and `game_participants.id`.
- UUIDs identify stored rows, not logical dedupe boundaries.
- Logical game idempotency is enforced by `games.game_key`, a deterministic key built from `tournament_id`, round identity, table number, and bracket flag.
- `game_participants` hangs off `games.id`, so duplicate logical games will fan out directly into duplicated participant rows and downstream analytics unless `game_key` is canonical and unique.

### Tournaments

- `tournaments`: TopDeck.gg events (location, dates, player_count, rounds, top_cut, `is_league`).

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

### Global Elo

- `global_elo_ratings`: Global per-player rating state.
- `global_elo_leaderboard`: Global leaderboard view with country/state filter rows derived from global ratings.
- `global_elo_regions`: Region availability and update metadata.
- `global_elo_game_results`: Base view for global Elo calculations.

### Meta Preparation

- `player_commander_entries`: Player’s commander history per tournament for fast meta scans.

## Conventions

- Analytics generally filter to tournaments with `player_count >= 32`.
- Partner commanders are stored as a single combined commander entity.
- “Unknown Commander” entries can appear when deck data is missing and are typically filtered from analytics.
- Some TopDeck league-style events only expose standings-level rates (`successRate`, `opponentSuccessRate`) and no pod rounds. Those events should be treated as standings-only, not pod-level analytics inputs.

## Frontend Consumption

The Next.js app reads from Supabase views for most pages to keep the anon role safe:

- Rankings: `commander_stats`, `commander_weekly_trends`, `commander_monthly_trends`
- Card analytics: `card_frequencies_*`, `card_performance_*`
- Global Elo: `global_elo_leaderboard`, `global_elo_regions`
- Meta prep: `player_commander_entries`

If a view is missing, the corresponding page will show empty state messaging.
