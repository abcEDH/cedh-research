-- Track TopDeck league tournaments in the normal tournament table.
ALTER TABLE public.tournaments
ADD COLUMN IF NOT EXISTS is_league boolean NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_tournaments_is_league
ON public.tournaments(is_league)
WHERE is_league;

NOTIFY pgrst, 'reload schema';
