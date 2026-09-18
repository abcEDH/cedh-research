-- Add last_active to global_elo_state_activity.
-- Column is set to today's date each run to mark when a player was last seen active.

ALTER TABLE public.global_elo_state_activity
  ADD COLUMN IF NOT EXISTS last_active date;
