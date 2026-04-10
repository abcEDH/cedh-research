-- ============================================================
-- Elo maintenance job queue: table, enqueue guard, stale cleanup
-- ============================================================

-- Job queue table
CREATE TABLE IF NOT EXISTS elo_maintenance_jobs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  status          text NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','dispatched','running','completed','failed','stale')),
  trigger_source  text NOT NULL DEFAULT 'cron'
                    CHECK (trigger_source IN ('cron','manual','edge_function')),

  -- GitHub Actions linkage
  github_run_id   bigint,

  -- Timing
  created_at      timestamptz NOT NULL DEFAULT now(),
  dispatched_at   timestamptz,
  started_at      timestamptz,
  completed_at    timestamptz,
  heartbeat_at    timestamptz,

  -- Output metrics (written by worker on completion)
  ratings_count             integer,
  state_activity_count      integer,
  game_events_count         integer,
  leaderboard_count         integer,
  profile_count             integer,
  commander_profile_count   integer,
  duration_seconds          numeric,
  error_text                text
);

CREATE INDEX IF NOT EXISTS elo_maintenance_jobs_status_created_idx
  ON elo_maintenance_jobs (status, created_at DESC);

CREATE INDEX IF NOT EXISTS elo_maintenance_jobs_created_idx
  ON elo_maintenance_jobs (created_at DESC);

-- RLS: service_role full access, public read-only
ALTER TABLE elo_maintenance_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access"
  ON elo_maintenance_jobs FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Public read access"
  ON elo_maintenance_jobs FOR SELECT
  USING (true);

-- ============================================================
-- enqueue_elo_refresh: insert a pending job if none are active
-- ============================================================
CREATE OR REPLACE FUNCTION enqueue_elo_refresh(
  p_trigger_source text DEFAULT 'cron'
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_existing_id uuid;
  v_new_id uuid;
BEGIN
  -- Block if any job is already pending, dispatched, or running
  SELECT id INTO v_existing_id
  FROM elo_maintenance_jobs
  WHERE status IN ('pending', 'dispatched', 'running')
  ORDER BY created_at DESC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF v_existing_id IS NOT NULL THEN
    RAISE NOTICE 'Elo refresh already in progress: %', v_existing_id;
    RETURN NULL;
  END IF;

  INSERT INTO elo_maintenance_jobs (trigger_source)
  VALUES (p_trigger_source)
  RETURNING id INTO v_new_id;

  RETURN v_new_id;
END;
$$;

-- ============================================================
-- cleanup_stale_elo_jobs: mark stuck jobs as stale
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_stale_elo_jobs(
  p_stale_minutes integer DEFAULT 30
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_count integer;
BEGIN
  UPDATE elo_maintenance_jobs
  SET status = 'stale',
      error_text = 'Marked stale: no heartbeat for ' || p_stale_minutes || ' minutes',
      completed_at = now()
  WHERE status IN ('pending', 'dispatched', 'running')
    AND (
      (heartbeat_at IS NOT NULL AND heartbeat_at < now() - (p_stale_minutes || ' minutes')::interval)
      OR
      (heartbeat_at IS NULL AND created_at < now() - (p_stale_minutes || ' minutes')::interval)
    );

  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$;
