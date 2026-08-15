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
-- ============================================================

CREATE TABLE IF NOT EXISTS partner_commander_sweep_state (
  id            boolean PRIMARY KEY DEFAULT true CHECK (id),  -- singleton row
  pending       boolean NOT NULL DEFAULT false,
  merged_count  integer,
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
-- ============================================================
CREATE OR REPLACE FUNCTION mark_partner_commander_sweep_pending(
  p_merged_count integer DEFAULT 0
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
BEGIN
  UPDATE partner_commander_sweep_state
  SET pending = true,
      merged_count = p_merged_count,
      set_at = now()
  WHERE id = true;
END;
$$;

-- ============================================================
-- consume_partner_commander_sweep_pending: atomically read-and-clear
-- ============================================================
CREATE OR REPLACE FUNCTION consume_partner_commander_sweep_pending()
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_was_pending boolean;
BEGIN
  SELECT pending INTO v_was_pending
  FROM partner_commander_sweep_state
  WHERE id = true
  FOR UPDATE;

  IF v_was_pending THEN
    UPDATE partner_commander_sweep_state
    SET pending = false,
        cleared_at = now()
    WHERE id = true;
  END IF;

  RETURN COALESCE(v_was_pending, false);
END;
$$;
