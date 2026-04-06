-- Speed up state-based regional queries by indexing the normalized state expression.

CREATE INDEX IF NOT EXISTS idx_tournaments_state_normalized
  ON public.tournaments ((upper(trim(state))))
  WHERE state IS NOT NULL
    AND trim(state) <> '';
