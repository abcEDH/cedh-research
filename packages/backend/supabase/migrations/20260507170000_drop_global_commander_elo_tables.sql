DROP POLICY IF EXISTS "Public read access" ON public.global_commander_elo_game_events;
DROP POLICY IF EXISTS "Public read access" ON public.global_commander_elo_ratings;

DROP TABLE IF EXISTS public.global_commander_elo_game_events;
DROP TABLE IF EXISTS public.global_commander_elo_ratings;
