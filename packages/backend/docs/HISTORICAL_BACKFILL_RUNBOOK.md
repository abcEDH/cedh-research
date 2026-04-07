# Historical Backfill Runbook

## Goal

Run a comprehensive cEDH backfill in restartable batches without creating duplicate tournaments, entries, games, or game participants.

## Why This Is Safe

- `tournaments` upserts on `topdeck_tid`
- `players` upserts on `topdeck_id`
- `tournament_entries` upserts on `(tournament_id, player_id)`
- `games` upserts on deterministic `game_key`
- `game_participants` upserts on `(game_id, entry_id)`

This means a failed or repeated batch can be rerun without producing duplicate logical rows.

## Recommended Flow

1. Build a stable TID manifest ordered oldest-to-newest.
   Recommended source: export from Supabase `tournaments.topdeck_tid` into `data/all_time_tids.txt`, then merge any known-missing IDs from a supplemental file.
2. Apply the migration `20260406000000_ingestion_backfill_runs.sql`.
3. Run ingestion from the dedicated worktree with direct Postgres enabled.
4. Execute one batch at a time or let the full manifest run.
5. Rerun failed batches with the same manifest and `run_key`.

Export the committed manifest from Supabase and merge any supplemental TIDs:

```bash
uv run python src/export_all_time_tids.py \
  --out data/all_time_tids.txt \
  --supplemental data/all_time_tids.supplemental.txt
```

## Commands

Process the full manifest in batches of 50:

```bash
uv run python src/ingest.py \
  --tids-file data/all_time_tids.txt \
  --batch-size 50 \
  --direct \
  --record-backfill \
  --run-key all-time-cedh
```

Process only batch 7:

```bash
uv run python src/ingest.py \
  --tids-file data/all_time_tids.txt \
  --batch-size 50 \
  --batch-index 7 \
  --direct \
  --record-backfill \
  --run-key all-time-cedh
```

Fail fast on the first fetch or processing error:

```bash
uv run python src/ingest.py \
  --tids-file data/all_time_tids.txt \
  --batch-size 50 \
  --batch-index 7 \
  --direct \
  --record-backfill \
  --run-key all-time-cedh \
  --stop-on-error
```

Inspect a recorded run:

```bash
uv run python src/backfill_status.py --run-key all-time-cedh
```

## Notes

- Keep the manifest file stable for a given `run_key`. The run record stores the manifest SHA-256.
- Preserve TID order in the file so batch indexes stay deterministic across reruns.
- Prefer `--direct` for historical runs; REST is slower and more brittle for large backfills.
- If a batch partially succeeds, rerun the same batch. The database uniqueness constraints make that safe.
- `ingestion_backfill_runs` stores a heartbeat, current TID, last completed TID, and per-batch counters so progress updates during a batch instead of only after it finishes.
- `ingestion_backfill_events` stores an append-only event stream for batch boundaries and per-tournament fetch/process outcomes.
- The existing search endpoint is not reliable for true all-time discovery, and the Supabase export is only as complete as the tournaments already ingested. For comprehensive backfills, maintain a curated supplemental manifest for known-missing TIDs.
