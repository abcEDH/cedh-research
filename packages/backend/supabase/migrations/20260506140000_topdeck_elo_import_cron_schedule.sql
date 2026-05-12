-- ============================================================
-- Weekly TopDeck Elo import cron trigger -> Edge Function dispatch
-- ============================================================

CREATE OR REPLACE FUNCTION trigger_topdeck_elo_import_via_edge()
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_project_url text;
  v_anon_key text;
BEGIN
  SELECT decrypted_secret INTO v_project_url
  FROM vault.decrypted_secrets
  WHERE name = 'project_url';

  SELECT decrypted_secret INTO v_anon_key
  FROM vault.decrypted_secrets
  WHERE name = 'anon_key';

  IF v_project_url IS NULL OR v_anon_key IS NULL THEN
    RAISE EXCEPTION 'Vault secrets project_url and anon_key must be configured before scheduling TopDeck Elo imports.';
  END IF;

  PERFORM net.http_post(
    url := v_project_url || '/functions/v1/trigger-topdeck-elo-import',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer ' || v_anon_key,
      'apikey', v_anon_key
    ),
    body := '{}'::jsonb
  );

  RETURN true;
END;
$$;

DO $$
BEGIN
  IF to_regclass('cron.job') IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'topdeck-elo-weekly-dispatch') THEN
      EXECUTE format('SELECT cron.unschedule(%L)', 'topdeck-elo-weekly-dispatch');
    END IF;

    EXECUTE format(
      'SELECT cron.schedule(%L, %L, %L)',
      'topdeck-elo-weekly-dispatch',
      '0 16 * * 2',
      'select public.trigger_topdeck_elo_import_via_edge();'
    );
  END IF;
END;
$$;
