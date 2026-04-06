# cEDH Analytics - Claude Instructions

## Quick Reference

| Item | Value |
|------|-------|
| **Supabase Project ID** | `msjjihqbxtgjdtapywrj` |
| **Supabase URL** | `https://msjjihqbxtgjdtapywrj.supabase.co` |
| **Python Version** | 3.14 (use `.venv`) |
| **TopDeck API** | V2 - requires API key in `.env` |

## Project Structure

```
src/
  ingest.py        # Main ingestion pipeline (TopDeckClient, SupabaseClient, DataIngester)
supabase/
  migrations/      # SQL migrations (apply via MCP or Supabase dashboard)
.github/
  workflows/       # GitHub Actions for weekly ingestion
```

## Running Ingestion

```bash
# Activate venv first
source .venv/bin/activate

# Ingest specific tournament by TID (from TopDeck URL slug)
python src/ingest.py --tournament-id steel-city-spectacular-20k-cedh-main-event

# Ingest recent tournaments
python src/ingest.py --days 7 --min-players 32

# Use direct Postgres for ~10x faster batch operations (requires psycopg2)
python src/ingest.py --tournament-id TID --direct

# Historical backfill from a stable TID manifest in restartable batches
python src/ingest.py --tids-file data/all_time_tids.txt --batch-size 50 --direct --record-backfill --run-key all-time-cedh

# Refresh the committed all-time TID manifest from Supabase
python src/export_all_time_tids.py --out data/all_time_tids.txt
```

### Performance Notes

- **REST API (default):** Batches of 500-1000 rows per call, ~100 rows/sec
- **Direct Postgres (`--direct`):** Uses `psycopg2.execute_values`, ~5000 rows/sec
- See `docs/supabase-batch-ingestion-patterns.md` for detailed benchmarks

## Known Issues & Workarounds

### 1. Connection Drops During Large Ingestions
**Problem:** Supabase connections reset during large tournament ingestion (500+ players)
**Solution:** Retry logic with exponential backoff is now implemented in `SupabaseClient.upsert()` and `select()`. The `--direct` flag provides even more reliable connections for very large batches.

### 2. API Timeouts for Large Date Ranges
**Problem:** TopDeck API times out when querying 6+ months of tournaments
**Workaround:** Use shorter date ranges or ingest specific tournament TIDs from a stable manifest. See `docs/HISTORICAL_BACKFILL_RUNBOOK.md`.

### 3. Moxfield Decklists
**Problem:** Some decklists are just Moxfield URLs, no card data
**Current:** Store URL in `decklist_url`, commander marked as "Unknown"
**TODO:** Add Moxfield API integration to fetch commander names

## Data Model Highlights

### Decklist Data
The API provides full decklists in this format:
```
~~Commanders~~
1 Commander Name
1 Partner Name (if applicable)

~~Mainboard~~
1 Card Name
1 Another Card
...
```
- Stored in `tournament_entries.decklist_text`
- Commanders extracted and normalized (sorted alphabetically for partners)
- Individual card parsing not yet implemented

### Seat Position
- Array index 0-3 = seats 1-4 (first to last to act)
- Validated against known tournament data
- Stored in `game_participants.seat_position`

## Large Tournaments to Ingest

Priority tournaments from EDHTop16 (100+ players):

| TID | Name | Players |
|-----|------|---------|
| `steel-city-spectacular-20k-cedh-main-event` | Steel City Spectacular $20k | 514 |
| `TheBoil2` | The Boil 2 | 324 |
| `roadtomunich` | Road to Munich | 314 |
| `the-fishbowl-san-diego-copy` | Fishbowl San Diego | 295 |

Get more TIDs from: https://edhtop16.com/tournaments (sort by size)

## Session Handoff Checklist

Before ending a session:
1. Update `progress.md` with completed work
2. Note any partial ingestion state (check `tournament_entries` count)
3. Document new TIDs discovered for future ingestion
4. Run `/handover` if significant work completed

## Useful Queries

```sql
-- Check ingestion progress for a tournament
SELECT t.name, t.player_count, COUNT(te.id) as entries_ingested
FROM tournaments t
LEFT JOIN tournament_entries te ON te.tournament_id = t.id
WHERE t.name LIKE '%Tournament Name%'
GROUP BY t.id;

-- Tournament size distribution
SELECT name, player_count, start_date
FROM tournaments
ORDER BY player_count DESC NULLS LAST
LIMIT 20;
```
