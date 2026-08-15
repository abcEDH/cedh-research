-- ============================================================
-- Partner-commander sweep "pending" flag (#314)
--
-- ci-backend-ingestion.yml's chain-elo job exits 0 without dispatching a
-- maintenance refresh when enqueue_elo_refresh() returns null because an
-- Elo job is already in flight. If that in-flight job has already passed
-- its commander-view rebuild step, a live sweep_partner_commander_order.py
-- merge landing after it leaves commander_weekly_trends,
-- commander_monthly_trends, and player_commander_profiles referencing
-- merged-away commander IDs until some later, unrelated refresh.
--
-- This is a singleton flag: the sweep marks it pending whenever it performs
-- a live merge (regardless of whether chain-elo goes on to skip or
-- dispatch), and ci-backend-maintenance.yml consumes-and-clears it at the
-- start of every run. A run that finds it pending forces a commander-view /
-- player_commander_profiles rebuild even when it would otherwise be a
-- lightweight smoke check, guaranteeing the merge's follow-up refresh isn't
-- silently dropped. Consuming it redundantly on a run that was already
-- going to do a full rebuild anyway is a harmless no-op extra pass.
--
-- Token-based ack (post-review hardening): the naive "read pending, then
-- clear it" shape has two failure modes once the consumer's rebuild isn't
-- instantaneous:
--   1. A run reads pending=true, the forced rebuild then fails/raises, but
--      the flag was already cleared -- the refresh request is silently lost.
--   2. A newer live merge marks the flag again while an older, still
--      in-flight maintenance run is mid-rebuild; the older run's ack would
--      clear the *newer* merge's pending state instead of its own.
--
-- Fix: mark_partner_commander_sweep_pending() stamps a fresh `token` (uuid)
-- on every call and returns it. Consumers read the current `pending`/`token`
-- via a plain SELECT (RLS lets service_role read regardless; the existing
-- "Public read access" policy covers anon/authenticated too), run the
-- rebuild, and only then call consume_partner_commander_sweep_pending(p_token)
-- -- a compare-and-clear that clears the row only `WHERE pending AND
-- token = p_token`. A failed rebuild never calls consume, so the flag stays
-- pending for the next run to retry. A stale token (a newer mark_pending
-- happened mid-flight) makes consume a no-op that returns false -- that
-- pending state belongs to the newer request, not this run's to clear.
-- ============================================================

CREATE TABLE IF NOT EXISTS partner_commander_sweep_state (
  id            boolean PRIMARY KEY DEFAULT true CHECK (id),  -- singleton row
  pending       boolean NOT NULL DEFAULT false,
  merged_count  integer,
  token         uuid,
  set_at        timestamptz,
  cleared_at    timestamptz
);

INSERT INTO partner_commander_sweep_state (id, pending)
VALUES (true, false)
ON CONFLICT (id) DO NOTHING;

ALTER TABLE partner_commander_sweep_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access"
  ON partner_commander_sweep_state FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Public read access"
  ON partner_commander_sweep_state FOR SELECT
  USING (true);

GRANT SELECT ON partner_commander_sweep_state TO anon, authenticated;

-- ============================================================
-- mark_partner_commander_sweep_pending: set the flag after a live merge
--
-- Stamps and returns a fresh token on every call. Callers that only care
-- about "fire the flag" (sweep_partner_commander_order.py's best-effort
-- mark_sweep_pending) can ignore the return value; consumers that need to
-- ack their own rebuild read the *current* token back off the table (a
-- plain SELECT) rather than trusting a value handed to them earlier, so a
-- newer mark_pending mid-flight is always what wins.
-- ============================================================
CREATE OR REPLACE FUNCTION mark_partner_commander_sweep_pending(
  p_merged_count integer DEFAULT 0
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_token uuid := gen_random_uuid();
BEGIN
  UPDATE partner_commander_sweep_state
  SET pending = true,
      merged_count = p_merged_count,
      token = v_token,
      set_at = now()
  WHERE id = true;

  RETURN v_token;
END;
$$;

-- ============================================================
-- consume_partner_commander_sweep_pending: compare-and-clear ack.
--
-- Takes the token the caller read (and acted on) before running its
-- rebuild, and clears the flag only if that token is still the one on
-- file -- i.e. no newer mark_pending has happened since. Returns whether
-- it actually cleared the row:
--   * false with nothing pending: nothing to do (never called after a
--     failed rebuild, since callers only ack after success).
--   * false with a *different* token on file: a newer live merge marked
--     the flag again while this run was mid-rebuild -- that pending state
--     belongs to the newer request, not this run's to consume.
--   * true: this run's ack matched and the flag is now clear.
-- ============================================================
CREATE OR REPLACE FUNCTION consume_partner_commander_sweep_pending(
  p_token uuid
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_row_count integer;
BEGIN
  UPDATE partner_commander_sweep_state
  SET pending = false,
      cleared_at = now()
  WHERE id = true
    AND pending = true
    AND token = p_token;

  GET DIAGNOSTICS v_row_count = ROW_COUNT;

  RETURN v_row_count > 0;
END;
$$;

-- ============================================================
-- Grants: internal maintenance RPCs, service_role only.
--
-- Both functions are SECURITY DEFINER and mutate internal pipeline state;
-- neither is meant to be callable by end-user (anon/authenticated)
-- PostgREST clients. Postgres grants EXECUTE on newly created functions to
-- PUBLIC by default, so without an explicit revoke here anon/authenticated
-- would inherit the ability to mark or forge-clear the flag. Follow the
-- house pattern used for other internal-only RPCs (see
-- 20260511235955_global_elo_incremental_snapshot_rpcs.sql and
-- 20260618183116_active_global_elo_player_ids_rpc.sql).
-- ============================================================
REVOKE ALL ON FUNCTION mark_partner_commander_sweep_pending(integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION consume_partner_commander_sweep_pending(uuid) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION mark_partner_commander_sweep_pending(integer) TO service_role;
GRANT EXECUTE ON FUNCTION consume_partner_commander_sweep_pending(uuid) TO service_role;
