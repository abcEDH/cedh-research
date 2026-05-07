-- Persist commander-level Elo so prediction can blend commander strength with player strength.

CREATE TABLE IF NOT EXISTS public.global_commander_elo_ratings (
  commander_id uuid PRIMARY KEY REFERENCES public.commanders(id) ON DELETE CASCADE,
  rating numeric NOT NULL,
  games_played integer NOT NULL,
  wins integer NOT NULL,
  draws integer NOT NULL,
  losses integer NOT NULL,
  last_game_date date,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS global_commander_elo_ratings_rating_idx
  ON public.global_commander_elo_ratings (rating DESC, last_game_date DESC);

CREATE TABLE IF NOT EXISTS public.global_commander_elo_game_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id uuid NOT NULL REFERENCES public.games(id) ON DELETE CASCADE,
  tournament_id uuid NOT NULL REFERENCES public.tournaments(id) ON DELETE CASCADE,
  commander_id uuid NOT NULL REFERENCES public.commanders(id) ON DELETE CASCADE,
  player_id uuid NOT NULL REFERENCES public.players(id) ON DELETE CASCADE,
  entry_id uuid NOT NULL REFERENCES public.tournament_entries(id) ON DELETE CASCADE,
  game_date timestamptz,
  game_result text NOT NULL,
  is_draw boolean NOT NULL DEFAULT false,
  opponent_count integer NOT NULL DEFAULT 0,
  expected_score numeric NOT NULL,
  actual_score numeric NOT NULL,
  rating_before numeric NOT NULL,
  rating_delta numeric NOT NULL,
  rating_after numeric NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (game_id, entry_id)
);

CREATE INDEX IF NOT EXISTS global_commander_elo_game_events_commander_idx
  ON public.global_commander_elo_game_events (commander_id, game_date DESC);

CREATE INDEX IF NOT EXISTS global_commander_elo_game_events_tournament_idx
  ON public.global_commander_elo_game_events (tournament_id, game_date DESC);

ALTER TABLE public.global_commander_elo_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.global_commander_elo_game_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read access" ON public.global_commander_elo_ratings;
CREATE POLICY "Public read access"
ON public.global_commander_elo_ratings
FOR SELECT
USING (true);

DROP POLICY IF EXISTS "Public read access" ON public.global_commander_elo_game_events;
CREATE POLICY "Public read access"
ON public.global_commander_elo_game_events
FOR SELECT
USING (true);

GRANT SELECT ON public.global_commander_elo_ratings TO anon, authenticated;
GRANT SELECT ON public.global_commander_elo_game_events TO anon, authenticated;
