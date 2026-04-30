-- Persist TopDeck Elo + per-region rank on the leaderboard table so /regional-elo
-- can sort and display TopDeck Elo without a second query against topdeck_player_elos.

ALTER TABLE public.global_elo_active_leaderboard
  ADD COLUMN IF NOT EXISTS topdeck_elo numeric;

ALTER TABLE public.global_elo_active_leaderboard
  ADD COLUMN IF NOT EXISTS topdeck_elo_rank integer;

-- Sorted reads of "top N by TopDeck Elo within (region_type, region_key)" should
-- hit an index, and only ranked rows matter (NULL TopDeck Elo => no rank).
CREATE INDEX IF NOT EXISTS global_elo_active_leaderboard_region_topdeck_rank_idx
  ON public.global_elo_active_leaderboard (region_type, region_key, topdeck_elo_rank)
  WHERE topdeck_elo_rank IS NOT NULL;

-- Recreate the alias view so the new columns are surfaced to PostgREST consumers.
CREATE OR REPLACE VIEW public.regional_elo_active_leaderboard AS
SELECT * FROM public.global_elo_active_leaderboard;

ALTER VIEW public.regional_elo_active_leaderboard SET (security_invoker = true);

GRANT SELECT ON public.regional_elo_active_leaderboard TO anon, authenticated;
