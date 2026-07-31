-- Keep the regional selector metadata on the same refreshed snapshot as the
-- leaderboard it controls. The legacy regional_elo_ratings source is no
-- longer rebuilt, which left its `updated_at` value stale on the public page.

CREATE OR REPLACE VIEW public.regional_elo_regions AS
SELECT
  region_type,
  region_key,
  COUNT(*)::bigint AS player_count,
  MAX(updated_at) AS updated_at,
  country_key
FROM public.global_elo_active_leaderboard
GROUP BY region_type, region_key, country_key;

ALTER VIEW public.regional_elo_regions SET (security_invoker = true);

GRANT SELECT ON public.regional_elo_regions TO anon, authenticated;
