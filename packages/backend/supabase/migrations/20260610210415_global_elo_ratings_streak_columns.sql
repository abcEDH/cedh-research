-- Add win_streak and loss_streak to global_elo_ratings.
-- These columns were added to regional_elo.py's create_empty_ratings_row()
-- but were never added to the schema, causing PGRST204 errors at upsert time.

ALTER TABLE public.global_elo_ratings
  ADD COLUMN IF NOT EXISTS win_streak  integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS loss_streak integer NOT NULL DEFAULT 0;
