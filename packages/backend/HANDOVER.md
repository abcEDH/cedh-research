# cEDH Analytics Backend - Handover Document

## Project Overview
Python-based data ingestion and PostgreSQL analytics for competitive Magic: The Gathering (cEDH) tournament data.

**Frontend:** https://cedh-analytics-frontend.vercel.app
**Frontend Repo:** ~/Documents/Repositories/personal/cedh-analytics-frontend

## Current State

### Data Volume (Updated 2026-01-21)
- **69 tournaments** ingested
- **343 commanders** with stats
- **3,693 decks** analyzed (with decklists)
- **6,812 games** with detailed data
- **5,020 tournament entries**
- **3,667 unique players**

### Materialized Views & Functions
| Object | Type | Status | Frontend Usage |
|--------|------|--------|----------------|
| `commander_stats` | View | Working | /commanders, / |
| `seat_position_stats` | View | Working | /turn-order |
| `commander_seat_stats` | MView | Working | /turn-order (commander grouping) |
| `card_frequencies_global` | MView | Working | /cards |
| `card_frequencies_by_commander` | MView | Working | /commanders/[id] |
| `commander_card_report` | View | Working | /commanders/[id] |
| `card_performance_by_commander` | MView | Working | /commanders/[id] Card Performance tab |
| `card_performance_global` | MView | Working | Planned |
| `trap_cards_report` | View | Working | /trap-spice |
| `spice_cards_report` | View | Working | /trap-spice |
| `commander_head_to_head` | View | Empty | Needs investigation |
| `get_notable_players_for_commander` | Func | Working | /commanders/[id] Players tab |
| `get_commander_matchups` | Func | Working | /commanders/[id] Matchups tab |
| `get_commanders_for_card` | Func | Working | /cards commander column |
| `round_win_rates` | View | Working | Planned |

## Pending Backend Work

### 1. Survival Analysis Views (Priority: High)
Comprehensive research complete in `docs/SURVIVAL_ANALYSIS_PLAN.md` (on `feat/survival-analysis` branch).
Includes 5 materialized views for Kaplan-Meier style survival curves.
Ready for review and merge.

### 2. ~~Fix commander_head_to_head~~ Resolved (2026-01-21)
**Root cause:** The `commander_matchups` table (0 rows) was never populated by ingestion.
**Solution:** The `get_commander_matchups(UUID)` function computes the same data on-the-fly from `game_participants`. Frontend should use the function instead of the view.
**Future option:** Could add ingestion logic to populate `commander_matchups` for better query performance, but the function is sufficient for now.

### 3. ~~Frontend-Required Functions~~ ✅ DONE (2026-01-21)
All 4 functions/views created and verified:
- `get_notable_players_for_commander(UUID, limit, offset)` - Players tab (with pagination)
- `get_commander_matchups(UUID, limit, offset, min_games)` - Matchups tab (with pagination + stats)
- `commander_seat_stats` - Turn order commander grouping
- `get_commanders_for_card(TEXT)` - Cards page commander column

### 4. Matchup Enhancements ✅ DONE (2026-01-21)
Enhanced `get_commander_matchups` now returns:
- `is_statistically_significant` - boolean based on sample size
- `confidence_level` - 'high' (50+), 'medium' (30+), 'low' (15+), 'very_low'
- `win_rate_vs_expected` - difference from 25% expected win rate
- Pagination support with `p_limit`, `p_offset`, `p_min_games`

### 5. Player Profile Links
**Discovery:** TopDeck profile URLs work with existing `topdeck_id`:
```
https://topdeck.gg/profile/{topdeck_id}
```
No separate handle needed - frontend can construct links directly from player data.

## Known Issues

### "Unknown Commander" (1,209 entries)
This is real data where commander wasn't identified from source. Options:
1. Leave as-is (current)
2. Try to backfill from decklist parsing
3. Filter from frontend queries

### Draw Rate in Seat Stats
Draws are tracked but win_rate calculation doesn't include them. Added win_plus_draw_rate to proposed views.

## Environment

### Database
- **Project ID:** msjjihqbxtgjdtapywrj
- **Region:** us-west-1
- **URL:** https://msjjihqbxtgjdtapywrj.supabase.co

### Secrets (1Password)
- `cEDH Analytics Secrets` vault item contains:
  - SUPABASE_URL
  - SUPABASE_ANON_KEY
  - SUPABASE_SERVICE_ROLE_KEY
  - DATABASE_URL

## Migration Files
```
supabase/migrations/
├── 20260110000001_initial_schema.sql
├── 20260111100000_survival_analysis_views.sql (empty placeholder)
├── 20260111110000_analysis_snapshots.sql
└── ... (additional migrations)
```

## CLI Commands
```bash
# Refresh all materialized views
python src/ingest.py --refresh-views

# Ingest new tournament data
python src/ingest.py --tournament <tid>

# Generate card frequency report
python src/ingest.py --card-report <commander>
```

## Next Steps
1. ~~Review survival analysis research output~~ ✅ Done (PR #2)
2. ~~Create commander_seat_stats view~~ ✅ Done
3. ~~Create commander_notable_players view~~ ✅ Done
4. ~~Add card_name index to card_frequencies_by_commander~~ ✅ Done
5. ~~Investigate commander_head_to_head empty results~~ ✅ Resolved
6. Merge PR #2 (survival analysis) and PR #3 (matchup enhancements)
7. Frontend: Update matchups page to use pagination and show statistical significance
8. Frontend: Add player profile links using topdeck_id
