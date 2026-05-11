DO $$
BEGIN
  IF to_regclass('public.global_commander_elo_game_events') IS NOT NULL THEN
    DROP POLICY IF EXISTS "Public read access" ON public.global_commander_elo_game_events;
  END IF;
  IF to_regclass('public.global_commander_elo_ratings') IS NOT NULL THEN
    DROP POLICY IF EXISTS "Public read access" ON public.global_commander_elo_ratings;
  END IF;
END;
$$;

DROP TABLE IF EXISTS public.global_commander_elo_game_events;
DROP TABLE IF EXISTS public.global_commander_elo_ratings;
