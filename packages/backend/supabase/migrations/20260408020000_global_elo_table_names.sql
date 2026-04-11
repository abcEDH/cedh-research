-- Rename legacy regional_elo_* storage to global_elo_* and keep read aliases.

DO $$
BEGIN
  IF to_regclass('public.global_elo_ratings') IS NULL
     AND to_regclass('public.regional_elo_ratings') IS NOT NULL THEN
    ALTER TABLE public.regional_elo_ratings RENAME TO global_elo_ratings;
  END IF;

  IF to_regclass('public.global_elo_state_activity') IS NULL
     AND to_regclass('public.regional_elo_state_activity') IS NOT NULL THEN
    ALTER TABLE public.regional_elo_state_activity RENAME TO global_elo_state_activity;
  END IF;

  IF to_regclass('public.global_elo_game_events') IS NULL
     AND to_regclass('public.regional_elo_game_events') IS NOT NULL THEN
    ALTER TABLE public.regional_elo_game_events RENAME TO global_elo_game_events;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.global_elo_ratings_region_idx') IS NULL
     AND to_regclass('public.regional_elo_ratings_region_idx') IS NOT NULL THEN
    ALTER INDEX public.regional_elo_ratings_region_idx RENAME TO global_elo_ratings_region_idx;
  END IF;

  IF to_regclass('public.global_elo_state_activity_region_idx') IS NULL
     AND to_regclass('public.regional_elo_state_activity_region_idx') IS NOT NULL THEN
    ALTER INDEX public.regional_elo_state_activity_region_idx RENAME TO global_elo_state_activity_region_idx;
  END IF;

  IF to_regclass('public.global_elo_state_activity_player_idx') IS NULL
     AND to_regclass('public.regional_elo_state_activity_player_idx') IS NOT NULL THEN
    ALTER INDEX public.regional_elo_state_activity_player_idx RENAME TO global_elo_state_activity_player_idx;
  END IF;

  IF to_regclass('public.global_elo_state_activity_country_idx') IS NULL
     AND to_regclass('public.regional_elo_state_activity_country_idx') IS NOT NULL THEN
    ALTER INDEX public.regional_elo_state_activity_country_idx RENAME TO global_elo_state_activity_country_idx;
  END IF;

  IF to_regclass('public.global_elo_game_events_region_idx') IS NULL
     AND to_regclass('public.regional_elo_game_events_region_idx') IS NOT NULL THEN
    ALTER INDEX public.regional_elo_game_events_region_idx RENAME TO global_elo_game_events_region_idx;
  END IF;

  IF to_regclass('public.global_elo_game_events_player_idx') IS NULL
     AND to_regclass('public.regional_elo_game_events_player_idx') IS NOT NULL THEN
    ALTER INDEX public.regional_elo_game_events_player_idx RENAME TO global_elo_game_events_player_idx;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS global_elo_ratings_region_idx
  ON public.global_elo_ratings (region_type, region_key, rating DESC);

CREATE INDEX IF NOT EXISTS global_elo_state_activity_region_idx
  ON public.global_elo_state_activity (region_type, region_key, is_primary_state, activity_score DESC);

CREATE INDEX IF NOT EXISTS global_elo_state_activity_player_idx
  ON public.global_elo_state_activity (player_id, is_primary_state, activity_score DESC);

CREATE INDEX IF NOT EXISTS global_elo_state_activity_country_idx
  ON public.global_elo_state_activity (country_key, region_key, is_primary_state, activity_score DESC);

CREATE INDEX IF NOT EXISTS global_elo_game_events_region_idx
  ON public.global_elo_game_events (region_type, region_key, game_date DESC);

CREATE INDEX IF NOT EXISTS global_elo_game_events_player_idx
  ON public.global_elo_game_events (player_id, game_date DESC);

CREATE OR REPLACE VIEW regional_elo_ratings AS
SELECT * FROM global_elo_ratings;

CREATE OR REPLACE VIEW regional_elo_state_activity AS
SELECT * FROM global_elo_state_activity;

CREATE OR REPLACE VIEW regional_elo_game_events AS
SELECT * FROM global_elo_game_events;

CREATE OR REPLACE VIEW global_elo_game_results AS
SELECT * FROM regional_elo_game_results;

CREATE OR REPLACE VIEW global_elo_primary_state_assignments AS
SELECT * FROM regional_elo_primary_state_assignments;

CREATE OR REPLACE VIEW global_elo_player_stats AS
SELECT * FROM regional_elo_player_stats;

CREATE OR REPLACE VIEW global_elo_leaderboard AS
SELECT * FROM regional_elo_leaderboard;

CREATE OR REPLACE VIEW global_elo_regions AS
SELECT * FROM regional_elo_regions;

CREATE OR REPLACE VIEW global_elo_game_event_log AS
SELECT * FROM regional_elo_game_event_log;

CREATE OR REPLACE VIEW global_elo_data_validity AS
SELECT * FROM regional_elo_data_validity;

ALTER VIEW regional_elo_ratings SET (security_invoker = true);
ALTER VIEW regional_elo_state_activity SET (security_invoker = true);
ALTER VIEW regional_elo_game_events SET (security_invoker = true);
ALTER VIEW global_elo_game_results SET (security_invoker = true);
ALTER VIEW global_elo_primary_state_assignments SET (security_invoker = true);
ALTER VIEW global_elo_player_stats SET (security_invoker = true);
ALTER VIEW global_elo_leaderboard SET (security_invoker = true);
ALTER VIEW global_elo_regions SET (security_invoker = true);
ALTER VIEW global_elo_game_event_log SET (security_invoker = true);
ALTER VIEW global_elo_data_validity SET (security_invoker = true);

GRANT SELECT ON global_elo_ratings TO anon, authenticated;
GRANT SELECT ON global_elo_state_activity TO anon, authenticated;
GRANT SELECT ON global_elo_game_events TO anon, authenticated;
GRANT SELECT ON regional_elo_ratings TO anon, authenticated;
GRANT SELECT ON regional_elo_state_activity TO anon, authenticated;
GRANT SELECT ON regional_elo_game_events TO anon, authenticated;
GRANT SELECT ON global_elo_game_results TO anon, authenticated;
GRANT SELECT ON global_elo_primary_state_assignments TO anon, authenticated;
GRANT SELECT ON global_elo_player_stats TO anon, authenticated;
GRANT SELECT ON global_elo_leaderboard TO anon, authenticated;
GRANT SELECT ON global_elo_regions TO anon, authenticated;
GRANT SELECT ON global_elo_game_event_log TO anon, authenticated;
GRANT SELECT ON global_elo_data_validity TO anon, authenticated;
