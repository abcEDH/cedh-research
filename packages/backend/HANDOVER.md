# cEDH Analytics Backend - Handover Document

## Project Overview
Python-based data ingestion and PostgreSQL analytics for competitive Magic: The Gathering (cEDH) tournament data.

## Supported Surfaces

- `Cards`, `Turn Order`, and `Survival` are retired surfaces.
- New backend work should assume those surfaces are no longer active product areas.

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
| `card_frequencies_by_commander` | MView | Working | /commanders/[id] |
| `commander_card_report` | View | Working | /commanders/[id] |
| `card_performance_by_commander` | MView | Working | /commanders/[id] Card Performance tab |
| `card_performance_global` | MView | Working | Planned |
| `trap_cards_report` | View | Working | /trap-spice |
| `spice_cards_report` | View | Working | /trap-spice |
| `commander_head_to_head` | View | Empty | Needs investigation |
| `get_notable_players_for_commander` | Func | Working | /commanders/[id] Players tab |
| `get_commander_matchups` | Func | Working | /commanders/[id] Matchups tab |

## Pending Backend Work

### 1. Surface retirement cleanup
Cards, Turn Order, and Survival have been deleted in the frontend. Backend follow-up is to keep migrations, validation, and docs from silently re-introducing their retired SQL surfaces.

### 2. ~~Fix commander_head_to_head~~ Resolved (2026-01-21)
**Root cause:** The `commander_matchups` table (0 rows) was never populated by ingestion.
**Solution:** The `get_commander_matchups(UUID)` function computes the same data on-the-fly from `game_participants`. Frontend should use the function instead of the view.
**Future option:** Could add ingestion logic to populate `commander_matchups` for better query performance, but the function is sufficient for now.

### 3. ~~Frontend-Required Functions~~ ✅ DONE (2026-01-21)
Supported functions/views created and verified:
- `get_notable_players_for_commander(UUID, limit, offset)` - Players tab (with pagination)
- `get_commander_matchups(UUID, limit, offset, min_games)` - Matchups tab (with pagination + stats)

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

### Retired Surface Artifacts
If you see `seat_position_stats`, `commander_seat_stats`, `get_commanders_for_card`, or the survival-analysis views referenced in CI or docs, treat that as cleanup debt rather than active product support.

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
1. Remove retired surface references from backend views, CI checks, and docs.
2. Keep TopDeck attribution visible in the frontend.
3. Document and enforce the supported-surface policy for future migrations.
