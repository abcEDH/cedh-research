-- Add primary commander columns to global_elo_player_profile_summaries.
-- primary_commander_name: most-played known commander (NULL if known_pct < 0.5)
-- primary_commander_known_pct: fraction of entries with non-unknown commander
ALTER TABLE global_elo_player_profile_summaries
  ADD COLUMN IF NOT EXISTS primary_commander_name text,
  ADD COLUMN IF NOT EXISTS primary_commander_known_pct numeric;
