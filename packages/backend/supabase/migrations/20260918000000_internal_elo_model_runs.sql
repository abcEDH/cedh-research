-- Model metadata commits atomically with its ratings and game-event replay.
CREATE TABLE IF NOT EXISTS public.internal_elo_model_runs (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  model_version text NOT NULL,
  source_cutoff timestamptz NOT NULL CHECK (source_cutoff <= CURRENT_TIMESTAMP),
  parameters jsonb NOT NULL,
  counts jsonb NOT NULL,
  published_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.internal_elo_model_runs ENABLE ROW LEVEL SECURITY;
GRANT ALL ON public.internal_elo_model_runs TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.internal_elo_model_runs_id_seq TO service_role;
