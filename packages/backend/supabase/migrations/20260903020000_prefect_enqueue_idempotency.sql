-- Make Prefect enqueue retries safe and preserve the ingestion-to-Elo chain.

ALTER TABLE public.ingestion_jobs
  ADD COLUMN IF NOT EXISTS idempotency_key text;

ALTER TABLE public.elo_maintenance_jobs
  ADD COLUMN IF NOT EXISTS idempotency_key text;

CREATE UNIQUE INDEX IF NOT EXISTS ingestion_jobs_idempotency_key_idx
  ON public.ingestion_jobs (idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS elo_maintenance_jobs_idempotency_key_idx
  ON public.elo_maintenance_jobs (idempotency_key)
  WHERE idempotency_key IS NOT NULL;

DROP FUNCTION IF EXISTS public.enqueue_ingestion_refresh(text);

CREATE OR REPLACE FUNCTION public.enqueue_ingestion_refresh(
  p_trigger_source text DEFAULT 'cron',
  p_idempotency_key text DEFAULT NULL
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
  PERFORM pg_advisory_xact_lock(8675310);

  IF p_idempotency_key IS NOT NULL THEN
    SELECT id INTO v_existing_id
    FROM ingestion_jobs
    WHERE idempotency_key = p_idempotency_key;
    IF v_existing_id IS NOT NULL THEN
      RETURN v_existing_id;
    END IF;
  END IF;

  SELECT id INTO v_existing_id
  FROM ingestion_jobs
  WHERE status IN ('pending', 'dispatched', 'running')
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_existing_id IS NOT NULL THEN
    RETURN NULL;
  END IF;

  INSERT INTO ingestion_jobs (trigger_source, idempotency_key)
  VALUES (p_trigger_source, p_idempotency_key)
  ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
  RETURNING id INTO v_new_id;

  IF v_new_id IS NULL AND p_idempotency_key IS NOT NULL THEN
    SELECT id INTO v_new_id
    FROM ingestion_jobs
    WHERE idempotency_key = p_idempotency_key;
  END IF;
  RETURN v_new_id;
END;
$$;

DROP FUNCTION IF EXISTS public.enqueue_elo_refresh(text);

CREATE OR REPLACE FUNCTION public.enqueue_elo_refresh(
  p_trigger_source text DEFAULT 'cron',
  p_idempotency_key text DEFAULT NULL
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
  IF p_idempotency_key IS NOT NULL THEN
    SELECT id INTO v_existing_id
    FROM elo_maintenance_jobs
    WHERE idempotency_key = p_idempotency_key;
    IF v_existing_id IS NOT NULL THEN
      RETURN v_existing_id;
    END IF;
  END IF;

  SELECT id INTO v_existing_id
  FROM elo_maintenance_jobs
  WHERE status IN ('pending', 'dispatched', 'running')
  ORDER BY created_at DESC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF v_existing_id IS NOT NULL THEN
    RETURN NULL;
  END IF;

  INSERT INTO elo_maintenance_jobs (trigger_source, idempotency_key)
  VALUES (p_trigger_source, p_idempotency_key)
  ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
  RETURNING id INTO v_new_id;

  IF v_new_id IS NULL AND p_idempotency_key IS NOT NULL THEN
    SELECT id INTO v_new_id
    FROM elo_maintenance_jobs
    WHERE idempotency_key = p_idempotency_key;
  END IF;
  RETURN v_new_id;
END;
$$;
