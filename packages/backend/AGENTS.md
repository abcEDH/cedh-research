# cEDH Analytics - Agent Instructions

> Canonical backend instructions for every coding agent. `CLAUDE.md` and `GEMINI.md` in this
> directory are symlinks to this file. Repo-wide rules live in the root [`AGENTS.md`](../../AGENTS.md).

## Quick Reference

| Item | Value |
|------|-------|
| **Supabase Project ID** | `msjjihqbxtgjdtapywrj` |
| **Supabase URL** | `https://msjjihqbxtgjdtapywrj.supabase.co` |
| **Python Version** | 3.14 (use `uv`) |
| **TopDeck API** | V2 - requires API key in `.env` |

## Project Structure

```
src/
  ingest.py           # Orchestration: arg parsing, pipeline flow, re-exports for backward compat
  supabase_client.py  # SupabaseClient, DirectPostgresClient, all Supabase/Postgres I/O
  topdeck_client.py   # TopDeckClient, Firestore helpers, all TopDeck API I/O
supabase/
  migrations/         # SQL migrations (apply via MCP or Supabase dashboard)
.github/
  workflows/          # GitHub Actions for weekly ingestion
```

## Running Ingestion

```bash
# Ingest specific tournament by TID (from TopDeck URL slug)
uv run python src/ingest.py --tournament-id steel-city-spectacular-20k-cedh-main-event

# Ingest recent tournaments
uv run python src/ingest.py --days 7

# Use direct Postgres for ~10x faster batch operations (requires psycopg2)
uv run python src/ingest.py --tournament-id TID --direct

# Historical backfill from a stable TID manifest in restartable batches
uv run python src/ingest.py --tids-file data/all_time_tids.txt --batch-size 50 --direct --record-backfill --run-key all-time-cedh

# Refresh the committed all-time TID manifest from Supabase
uv run python src/export_all_time_tids.py --out data/all_time_tids.txt
```

### Performance Notes

- **REST API (default):** Batches of 500-1000 rows per call, ~100 rows/sec
- **Direct Postgres (`--direct`):** Uses `psycopg2.execute_values`, ~5000 rows/sec
- See `docs/supabase-batch-ingestion-patterns.md` for detailed benchmarks

## TopDeck Webhooks

Push-based path for staffed tournaments (ADR 0015); the daily cron sweep
remains the primary pipeline. See `docs/TOPDECK_WEBHOOK_RUNBOOK.md` for
registration, secret rotation, and troubleshooting.

- **Edge function:** `supabase/functions/topdeck-webhook/` — verifies the
  HMAC signature (`verify.ts` is the only file encoding the scheme) and
  persists every delivery to `webhook_events`. Deploy with
  `supabase functions deploy topdeck-webhook --no-verify-jwt`.
- **Consumer:** the `process_webhook_event` DB trigger; on
  `tournament.finished` it calls `enqueue_targeted_ingestion(tid)` and the
  job flows through `trigger-ingestion-refresh` →
  `ci-backend-ingestion.yml` (`tournament_id` input) →
  `ingest.py --tournament-id`.
- **Secrets:** `TOPDECK_WEBHOOK_SECRET` (Supabase function secret,
  backend-only like `TOPDECK_API_KEY`); optional
  `TOPDECK_WEBHOOK_SIGNATURE_MODE=log` during scheme discovery.
- **`webhook_events` is service-role-only** — payloads may carry player
  PII. Do not add public read policies.

## Known Issues & Workarounds

### 1. Connection Drops During Large Ingestions
**Problem:** Supabase connections reset during large tournament ingestion (500+ players)
**Solution:** Retry logic with exponential backoff is now implemented in `SupabaseClient.upsert()` and `select()`. The `--direct` flag provides even more reliable connections for very large batches.

### 2. API Timeouts for Large Date Ranges
**Problem:** TopDeck API times out when querying 6+ months of tournaments
**Workaround:** Use shorter date ranges or ingest specific tournament TIDs from a stable manifest. See `docs/HISTORICAL_BACKFILL_RUNBOOK.md`.

### 3. Moxfield Decklists
**Problem:** Some decklists are just Moxfield URLs, no card data
**Current:** Imported Moxfield deck text with `~~Commanders~~` can be backfilled with `src/backfill_moxfield_commanders.py --embedded-only`. Pure Moxfield URLs require `--resolve-moxfield-api` or `--resolve-moxfield-page` from an environment that can reach Moxfield without Cloudflare blocking. When Moxfield blocks the runtime, export unresolved rows with `--export-unresolved-csv`, fill `commander_names` with `|`-delimited commanders, then import with `--import-resolved-csv`.

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

### 4. Data Derivation Pitfalls
**Problem:** Deriving `losses` from `points` when `wins`, `losses`, and `draws` are missing from a standings row.
**Solution:** Do NOT derive `losses` from `points` alone. While `wins` and `draws` can be mathematically deduced (since a win is 5 points and a draw is 1), `losses` grant 0 points and cannot be inferred without the total number of rounds. Setting `losses = 0` as a fallback overwrites existing loss counts in `tournament_entries` during re-ingestion and incorrectly inflates win rates in downstream trend views.
