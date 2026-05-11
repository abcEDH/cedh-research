-- ============================================================
-- Ingestion cron trigger: enqueue -> Edge Function dispatch
-- ============================================================

CREATE OR REPLACE FUNCTION trigger_ingestion_refresh_via_edge()
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_job_id uuid;
  v_project_url text;
  v_anon_key text;
BEGIN
  v_job_id := enqueue_ingestion_refresh('cron');

  IF v_job_id IS NULL THEN
    RETURN NULL;
  END IF;

  SELECT decrypted_secret INTO v_project_url
  FROM vault.decrypted_secrets
  WHERE name = 'project_url';

  SELECT decrypted_secret INTO v_anon_key
  FROM vault.decrypted_secrets
  WHERE name = 'anon_key';

  IF v_project_url IS NULL OR v_anon_key IS NULL THEN
    RAISE EXCEPTION 'Vault secrets project_url and anon_key must be configured before scheduling ingestion refreshes.';
  END IF;

  PERFORM net.http_post(
    url := v_project_url || '/functions/v1/trigger-ingestion-refresh',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer ' || v_anon_key,
      'apikey', v_anon_key
    ),
    body := jsonb_build_object('job_id', v_job_id)
  );

  RETURN v_job_id;
END;
$$;

CREATE OR REPLACE FUNCTION trigger_elo_refresh_via_edge()
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_job_id uuid;
  v_active_ingestion_job_id uuid;
  v_project_url text;
  v_anon_key text;
BEGIN
  SELECT id INTO v_active_ingestion_job_id
  FROM ingestion_jobs
  WHERE status IN ('pending', 'dispatched', 'running')
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_active_ingestion_job_id IS NOT NULL THEN
    RAISE NOTICE 'Skipping fallback Elo refresh because ingestion job % is still active.', v_active_ingestion_job_id;
    RETURN NULL;
  END IF;

  v_job_id := enqueue_elo_refresh('cron');

  IF v_job_id IS NULL THEN
    RETURN NULL;
  END IF;

  SELECT decrypted_secret INTO v_project_url
  FROM vault.decrypted_secrets
  WHERE name = 'project_url';

  SELECT decrypted_secret INTO v_anon_key
  FROM vault.decrypted_secrets
  WHERE name = 'anon_key';

  IF v_project_url IS NULL OR v_anon_key IS NULL THEN
    RAISE EXCEPTION 'Vault secrets project_url and anon_key must be configured before scheduling Elo refreshes.';
  END IF;

  PERFORM net.http_post(
    url := v_project_url || '/functions/v1/trigger-elo-refresh',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer ' || v_anon_key,
      'apikey', v_anon_key
    ),
    body := jsonb_build_object('job_id', v_job_id)
  );

  RETURN v_job_id;
END;
$$;

-- Unschedule existing jobs if they exist, then reschedule.
DO $$
DECLARE
  v_job_name text;
BEGIN
  IF to_regclass('cron.job') IS NOT NULL THEN
    FOREACH v_job_name IN ARRAY ARRAY[
      'elo-refresh-daily-dispatch',
      'ingestion-refresh-daily-dispatch',
      'ingestion-refresh-stale-cleanup'
    ]
    LOOP
      IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = v_job_name) THEN
        EXECUTE format('SELECT cron.unschedule(%L)', v_job_name);
      END IF;
    END LOOP;

    -- Ingestion at 6:00 AM UTC daily
    EXECUTE format(
      'SELECT cron.schedule(%L, %L, %L)',
      'ingestion-refresh-daily-dispatch',
      '0 6 * * *',
      'select public.trigger_ingestion_refresh_via_edge();'
    );

    -- Move Elo to 6:30 AM UTC (30-min offset as safety net; primary chain is workflow-driven)
    EXECUTE format(
      'SELECT cron.schedule(%L, %L, %L)',
      'elo-refresh-daily-dispatch',
      '30 6 * * *',
      'select public.trigger_elo_refresh_via_edge();'
    );

    -- Ingestion stale cleanup every 15 min
    EXECUTE format(
      'SELECT cron.schedule(%L, %L, %L)',
      'ingestion-refresh-stale-cleanup',
      '*/15 * * * *',
      'select public.cleanup_stale_ingestion_jobs(45);'
    );
  END IF;
END;
$$;
