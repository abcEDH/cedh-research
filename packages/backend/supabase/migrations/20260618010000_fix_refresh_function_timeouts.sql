-- Fix the materialized-view refresh RPCs that the global Elo maintenance job
-- logged as (non-fatal) failures.
--
-- Root cause: PostgREST connects as the `authenticator` role, which has
-- statement_timeout=8s. `SET ROLE service_role` per request does NOT reset that
-- session GUC, so any refresh function that does not raise its own
-- statement_timeout is cancelled at 8s (error 57014). The working
-- refresh_card_frequencies() already sets '30min'; these did not.

-- 1. refresh_card_performance() was missing from the database (schema drift from
--    migration 20260121000001 — the two MVs still exist). Recreate it, this time
--    with the 30min timeout so the CONCURRENTLY refresh isn't cancelled at 8s.
CREATE OR REPLACE FUNCTION public.refresh_card_performance()
RETURNS void
LANGUAGE plpgsql
SET statement_timeout TO '30min'
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY card_performance_by_commander;
    REFRESH MATERIALIZED VIEW CONCURRENTLY card_performance_global;
END;
$$;

GRANT EXECUTE ON FUNCTION public.refresh_card_performance() TO service_role;

-- 2. refresh_regional_elo_data_validity() lacked a statement_timeout and was
--    cancelled at the 8s role default. Add the same 30min override.
CREATE OR REPLACE FUNCTION public.refresh_regional_elo_data_validity()
RETURNS void
LANGUAGE plpgsql
SET statement_timeout TO '30min'
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY regional_elo_data_validity;
END;
$$;

-- 3. Harden get_active_global_elo_player_ids (migration 20260618000000). Its
--    DISTINCT-over-a-view scan runs ~3.4s today and grows with the dataset —
--    raise its timeout so it does not creep into the 8s wall later.
ALTER FUNCTION public.get_active_global_elo_player_ids(date, integer, integer)
    SET statement_timeout TO '5min';
