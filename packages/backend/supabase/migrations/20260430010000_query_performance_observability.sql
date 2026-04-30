-- Query performance observability for admin-only Regional Elo analysis.
--
-- This exposes pg_stat_statements through a service_role-only RPC so we can
-- attach database-side query timing proof to performance PRs without granting
-- public access to raw statement text.

CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA extensions;

CREATE OR REPLACE FUNCTION public.get_regional_elo_query_stats(
  p_limit integer DEFAULT 50,
  p_search_terms text[] DEFAULT ARRAY[
    'global_elo_active_leaderboard',
    'global_elo_leaderboard',
    'regional_elo_leaderboard',
    'topdeck_player_elos',
    'tournament_entries',
    'player_commander_profiles'
  ]
)
RETURNS TABLE (
  query text,
  calls bigint,
  total_exec_time_ms double precision,
  mean_exec_time_ms double precision,
  min_exec_time_ms double precision,
  max_exec_time_ms double precision,
  stddev_exec_time_ms double precision,
  rows_returned bigint,
  shared_blks_hit bigint,
  shared_blks_read bigint,
  shared_blks_dirtied bigint,
  shared_blks_written bigint,
  temp_blks_read bigint,
  temp_blks_written bigint,
  blk_read_time_ms double precision,
  blk_write_time_ms double precision
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
  SELECT
    stats.query,
    stats.calls,
    stats.total_exec_time AS total_exec_time_ms,
    stats.mean_exec_time AS mean_exec_time_ms,
    stats.min_exec_time AS min_exec_time_ms,
    stats.max_exec_time AS max_exec_time_ms,
    stats.stddev_exec_time AS stddev_exec_time_ms,
    stats.rows AS rows_returned,
    stats.shared_blks_hit,
    stats.shared_blks_read,
    stats.shared_blks_dirtied,
    stats.shared_blks_written,
    stats.temp_blks_read,
    stats.temp_blks_written,
    stats.blk_read_time AS blk_read_time_ms,
    stats.blk_write_time AS blk_write_time_ms
  FROM extensions.pg_stat_statements AS stats
  WHERE EXISTS (
    SELECT 1
    FROM unnest(COALESCE(p_search_terms, ARRAY[]::text[])) AS search_term(term)
    WHERE search_term.term <> ''
      AND stats.query ILIKE '%' || search_term.term || '%'
  )
  ORDER BY stats.total_exec_time DESC
  LIMIT LEAST(GREATEST(COALESCE(p_limit, 50), 1), 200);
$$;

REVOKE ALL ON FUNCTION public.get_regional_elo_query_stats(integer, text[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_regional_elo_query_stats(integer, text[]) FROM anon;
REVOKE ALL ON FUNCTION public.get_regional_elo_query_stats(integer, text[]) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.get_regional_elo_query_stats(integer, text[]) TO service_role;
