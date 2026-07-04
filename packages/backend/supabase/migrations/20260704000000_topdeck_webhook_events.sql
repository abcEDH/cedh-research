-- ============================================================
-- TopDeck developer webhooks: raw event log + targeted ingestion
-- consumer for tournament.finished (ADR 0015)
-- ============================================================

-- Raw event log. Every delivery is persisted verbatim so future
-- consumers (match.result_reported, roster events, live coverage)
-- can be designed against real payloads.
CREATE TABLE IF NOT EXISTS webhook_events (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  delivery_id       text NOT NULL,
  event_type        text NOT NULL DEFAULT 'unknown',
  tid               text,
  payload           jsonb NOT NULL,
  headers           jsonb,
  signature_valid   boolean NOT NULL DEFAULT true,
  is_test           boolean NOT NULL DEFAULT false,
  received_at       timestamptz NOT NULL DEFAULT now(),
  processing_status text NOT NULL DEFAULT 'received'
                      CHECK (processing_status IN ('received','enqueued','deferred','skipped','error')),
  processing_note   text,
  ingestion_job_id  uuid REFERENCES ingestion_jobs(id)
);

-- Idempotency: TopDeck retries with backoff and the portal supports
-- replay. Duplicate deliveries hit this index and are dropped by the
-- receiver's ON CONFLICT DO NOTHING insert, so the processing trigger
-- never fires twice for the same delivery.
CREATE UNIQUE INDEX IF NOT EXISTS webhook_events_delivery_id_key
  ON webhook_events (delivery_id);

CREATE INDEX IF NOT EXISTS webhook_events_type_received_idx
  ON webhook_events (event_type, received_at DESC);

CREATE INDEX IF NOT EXISTS webhook_events_tid_idx
  ON webhook_events (tid);

-- RLS: service_role only. Unlike ingestion_jobs there is deliberately
-- no public read policy — payloads can carry player registration PII.
ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access"
  ON webhook_events FOR ALL
  USING (auth.role() = 'service_role');

-- ============================================================
-- ingestion_jobs: allow webhook-triggered targeted jobs
-- ============================================================

ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS target_tid text;

ALTER TABLE ingestion_jobs DROP CONSTRAINT IF EXISTS ingestion_jobs_trigger_source_check;
ALTER TABLE ingestion_jobs ADD CONSTRAINT ingestion_jobs_trigger_source_check
  CHECK (trigger_source IN ('cron','manual','edge_function','webhook'));

-- ============================================================
-- enqueue_targeted_ingestion: insert a pending single-TID job if
-- no job is active. Mirrors enqueue_ingestion_refresh and shares
-- advisory lock 8675310 so targeted and daily enqueues serialize.
-- ============================================================
CREATE OR REPLACE FUNCTION enqueue_targeted_ingestion(
  p_tid text,
  p_trigger_source text DEFAULT 'webhook'
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
  IF p_tid IS NULL OR length(trim(p_tid)) = 0 THEN
    RAISE EXCEPTION 'enqueue_targeted_ingestion requires a non-empty TID';
  END IF;

  -- Same lock as enqueue_ingestion_refresh: check-then-insert must be
  -- atomic across both entry points.
  PERFORM pg_advisory_xact_lock(8675310);

  SELECT id INTO v_existing_id
  FROM ingestion_jobs
  WHERE status IN ('pending', 'dispatched', 'running')
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_existing_id IS NOT NULL THEN
    RAISE NOTICE 'Ingestion job already in progress: %', v_existing_id;
    RETURN NULL;
  END IF;

  INSERT INTO ingestion_jobs (trigger_source, target_tid)
  VALUES (p_trigger_source, trim(p_tid))
  RETURNING id INTO v_new_id;

  RETURN v_new_id;
END;
$$;

-- ============================================================
-- process_webhook_event: AFTER INSERT consumer. Only
-- tournament.finished enqueues work; everything else is logged and
-- marked skipped. Exception-safe on purpose — a consumer failure must
-- never bubble into the receiver's insert and cause a webhook 5xx.
-- ============================================================
CREATE OR REPLACE FUNCTION process_webhook_event()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_job_id uuid;
  v_project_url text;
  v_anon_key text;
BEGIN
  IF NEW.event_type <> 'tournament.finished' OR NEW.tid IS NULL OR NEW.is_test THEN
    UPDATE webhook_events
    SET processing_status = 'skipped'
    WHERE id = NEW.id;
    RETURN NEW;
  END IF;

  v_job_id := enqueue_targeted_ingestion(NEW.tid, 'webhook');

  IF v_job_id IS NULL THEN
    UPDATE webhook_events
    SET processing_status = 'deferred',
        processing_note = 'Another ingestion job is active; the daily cron will cover this tournament.'
    WHERE id = NEW.id;
    RETURN NEW;
  END IF;

  SELECT decrypted_secret INTO v_project_url
  FROM vault.decrypted_secrets
  WHERE name = 'project_url';

  SELECT decrypted_secret INTO v_anon_key
  FROM vault.decrypted_secrets
  WHERE name = 'anon_key';

  IF v_project_url IS NULL OR v_anon_key IS NULL THEN
    RAISE EXCEPTION 'Vault secrets project_url and anon_key must be configured before webhook-triggered ingestion.';
  END IF;

  -- Async fire-and-forget: pg_net queues the request, the insert
  -- transaction never blocks on the edge function or GitHub.
  PERFORM net.http_post(
    url := v_project_url || '/functions/v1/trigger-ingestion-refresh',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer ' || v_anon_key,
      'apikey', v_anon_key
    ),
    body := jsonb_build_object('job_id', v_job_id)
  );

  UPDATE webhook_events
  SET processing_status = 'enqueued',
      ingestion_job_id = v_job_id
  WHERE id = NEW.id;

  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  UPDATE webhook_events
  SET processing_status = 'error',
      processing_note = left(SQLERRM, 2000)
  WHERE id = NEW.id;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS webhook_events_process ON webhook_events;
CREATE TRIGGER webhook_events_process
  AFTER INSERT ON webhook_events
  FOR EACH ROW
  EXECUTE FUNCTION process_webhook_event();
