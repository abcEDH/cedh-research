-- Add tier column to tournaments table
ALTER TABLE public.tournaments
ADD COLUMN IF NOT EXISTS tier text;

-- Create index for tier filtering
CREATE INDEX IF NOT EXISTS idx_tournaments_tier ON public.tournaments(tier);
