-- Keep the regional selector metadata on the same refreshed snapshot as the
-- leaderboard it controls. This separate view deliberately leaves the legacy
-- regional_elo_regions/global_elo_regions views intact: their historical
-- column order differs between existing production and clean local schemas.

CREATE OR REPLACE VIEW public.global_elo_active_regions AS
SELECT
  region_type,
  region_key,
  country_key,
  COUNT(*)::bigint AS player_count,
  MAX(updated_at) AS updated_at
FROM public.global_elo_active_leaderboard
GROUP BY region_type, region_key, country_key;

ALTER VIEW public.global_elo_active_regions SET (security_invoker = true);

GRANT SELECT ON public.global_elo_active_regions TO anon, authenticated;
