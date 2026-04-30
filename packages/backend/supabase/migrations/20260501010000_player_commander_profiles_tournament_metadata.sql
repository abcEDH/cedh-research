-- Persist latest tournament metadata on player_commander_profiles so the regional Elo
-- profile summary surfaces can render without re-deriving names/dates/slugs at request time.

ALTER TABLE public.player_commander_profiles
  ADD COLUMN IF NOT EXISTS latest_tournament_id uuid;

ALTER TABLE public.player_commander_profiles
  ADD COLUMN IF NOT EXISTS latest_tournament_name text;

ALTER TABLE public.player_commander_profiles
  ADD COLUMN IF NOT EXISTS latest_tournament_date date;

ALTER TABLE public.player_commander_profiles
  ADD COLUMN IF NOT EXISTS latest_tournament_topdeck_tid text;

-- Note: deliberately no FK on latest_tournament_id -> tournaments(id). The recompute flow
-- repopulates these columns wholesale; an FK would risk breaking rebuilds if a tournament
-- row is removed between profile rebuilds. Application-level integrity is sufficient here.
