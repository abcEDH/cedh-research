-- Track historical backfill runs and chunk-level progress.

CREATE TABLE IF NOT EXISTS ingestion_backfill_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_key text NOT NULL UNIQUE,
  manifest_path text NOT NULL,
  manifest_sha256 text NOT NULL,
  requested_start_date date,
  requested_end_date date,
  batch_size integer NOT NULL CHECK (batch_size > 0),
  discovered_tournament_count integer NOT NULL DEFAULT 0 CHECK (discovered_tournament_count >= 0),
  processed_tournament_count integer NOT NULL DEFAULT 0 CHECK (processed_tournament_count >= 0),
  succeeded_tournament_count integer NOT NULL DEFAULT 0 CHECK (succeeded_tournament_count >= 0),
  failed_tournament_count integer NOT NULL DEFAULT 0 CHECK (failed_tournament_count >= 0),
  total_batches integer NOT NULL DEFAULT 0 CHECK (total_batches >= 0),
  status text NOT NULL DEFAULT 'pending' CHECK (
    status IN ('pending', 'running', 'completed', 'completed_with_errors', 'failed')
  ),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ingestion_backfill_runs_status_idx
  ON ingestion_backfill_runs (status, created_at DESC);

CREATE TABLE IF NOT EXISTS ingestion_backfill_batches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES ingestion_backfill_runs(id) ON DELETE CASCADE,
  batch_index integer NOT NULL CHECK (batch_index >= 0),
  batch_start integer NOT NULL CHECK (batch_start >= 0),
  batch_end integer NOT NULL CHECK (batch_end >= batch_start),
  tournament_count integer NOT NULL DEFAULT 0 CHECK (tournament_count >= 0),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
  error_text text,
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, batch_index)
);

CREATE INDEX IF NOT EXISTS ingestion_backfill_batches_run_status_idx
  ON ingestion_backfill_batches (run_id, status, batch_index);
