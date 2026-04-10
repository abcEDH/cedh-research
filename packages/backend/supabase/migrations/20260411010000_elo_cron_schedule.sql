-- ============================================================
-- Elo maintenance cron trigger: enqueue -> Edge Function dispatch
-- ============================================================

CREATE OR REPLACE FUNCTION trigger_elo_refresh_via_edge()
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

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'elo-refresh-daily-dispatch') THEN
    PERFORM cron.unschedule('elo-refresh-daily-dispatch');
  END IF;

  IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'elo-refresh-stale-cleanup') THEN
    PERFORM cron.unschedule('elo-refresh-stale-cleanup');
  END IF;
END;
$$;

SELECT cron.schedule(
  'elo-refresh-daily-dispatch',
  '0 6 * * *',
  $$select public.trigger_elo_refresh_via_edge();$$
);

SELECT cron.schedule(
  'elo-refresh-stale-cleanup',
  '*/15 * * * *',
  $$select public.cleanup_stale_elo_jobs(30);$$
);
