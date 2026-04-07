-- Add finer-grained backfill progress telemetry and an append-only event log.

ALTER TABLE ingestion_backfill_runs
  ADD COLUMN IF NOT EXISTS current_batch_index integer,
  ADD COLUMN IF NOT EXISTS current_tid text,
  ADD COLUMN IF NOT EXISTS last_completed_tid text,
  ADD COLUMN IF NOT EXISTS last_success_at timestamptz,
  ADD COLUMN IF NOT EXISTS heartbeat_at timestamptz,
  ADD COLUMN IF NOT EXISTS current_batch_processed_count integer NOT NULL DEFAULT 0 CHECK (current_batch_processed_count >= 0),
  ADD COLUMN IF NOT EXISTS current_batch_succeeded_count integer NOT NULL DEFAULT 0 CHECK (current_batch_succeeded_count >= 0),
  ADD COLUMN IF NOT EXISTS current_batch_failed_count integer NOT NULL DEFAULT 0 CHECK (current_batch_failed_count >= 0);

CREATE TABLE IF NOT EXISTS ingestion_backfill_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES ingestion_backfill_runs(id) ON DELETE CASCADE,
  batch_index integer NOT NULL CHECK (batch_index >= 0),
  tid text,
  event_type text NOT NULL CHECK (
    event_type IN (
      'batch_started',
      'batch_completed',
      'batch_failed',
      'fetch_started',
      'fetch_failed',
      'process_started',
      'process_succeeded',
      'process_failed',
      'tournament_skipped'
    )
  ),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ingestion_backfill_events_run_created_idx
  ON ingestion_backfill_events (run_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ingestion_backfill_events_run_batch_created_idx
  ON ingestion_backfill_events (run_id, batch_index, created_at DESC);

CREATE INDEX IF NOT EXISTS ingestion_backfill_events_run_tid_idx
  ON ingestion_backfill_events (run_id, tid)
  WHERE tid IS NOT NULL;
