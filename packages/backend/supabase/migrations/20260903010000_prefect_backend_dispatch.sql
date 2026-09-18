-- Prepare the database for Prefect before any legacy dispatcher is disabled.
-- The idempotent enqueue RPC changes land in the following migration. Keep the
-- legacy dispatchers active until Prefect has been manually verified; disabling
-- them is an operational cutover, not an automatic part of schema migration.

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
