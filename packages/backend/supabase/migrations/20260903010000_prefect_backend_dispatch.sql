-- Prefect owns production execution of the backend refresh. Keep Supabase
-- pg_cron for stale-job cleanup, but stop the old GitHub Actions dispatchers.

DO $$
DECLARE
  v_job_name text;
BEGIN
  IF to_regclass('cron.job') IS NOT NULL THEN
    FOREACH v_job_name IN ARRAY ARRAY[
      'ingestion-refresh-daily-dispatch',
      'elo-refresh-daily-dispatch'
    ]
    LOOP
      IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = v_job_name) THEN
        PERFORM cron.unschedule(v_job_name);
      END IF;
    END LOOP;
  END IF;
END;
$$;

ALTER TABLE public.ingestion_jobs
  DROP CONSTRAINT IF EXISTS ingestion_jobs_trigger_source_check;
ALTER TABLE public.ingestion_jobs
  ADD CONSTRAINT ingestion_jobs_trigger_source_check
  CHECK (trigger_source IN ('cron', 'manual', 'edge_function', 'prefect'));

ALTER TABLE public.elo_maintenance_jobs
  DROP CONSTRAINT IF EXISTS elo_maintenance_jobs_trigger_source_check;
ALTER TABLE public.elo_maintenance_jobs
  ADD CONSTRAINT elo_maintenance_jobs_trigger_source_check
  CHECK (trigger_source IN ('cron', 'manual', 'edge_function', 'prefect'));
