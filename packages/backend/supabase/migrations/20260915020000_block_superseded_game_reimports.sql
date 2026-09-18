-- Preserve confirmed game identity corrections across later reimports.
-- Entries are populated only after source verification; this is not a
-- uniqueness rule on player sets, which would incorrectly remove league rematches.
CREATE TABLE IF NOT EXISTS public.superseded_game_keys (
    game_key text PRIMARY KEY,
    canonical_game_id uuid NOT NULL REFERENCES public.games(id) ON DELETE RESTRICT,
    reason text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE public.superseded_game_keys ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.superseded_game_keys FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.superseded_game_keys TO service_role;

CREATE OR REPLACE FUNCTION public.skip_superseded_game_reimport()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM public.superseded_game_keys AS s
        WHERE s.game_key = NEW.game_key
    ) THEN
        RETURN NULL;
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.skip_superseded_game_reimport() FROM PUBLIC, anon, authenticated;

-- PostgreSQL runs same-event triggers alphabetically. This must run after
-- trg_set_canonical_game_key so the key is derived from the incoming fields.
CREATE TRIGGER trg_skip_superseded_game_reimport
BEFORE INSERT OR UPDATE ON public.games
FOR EACH ROW EXECUTE FUNCTION public.skip_superseded_game_reimport();

COMMENT ON TABLE public.superseded_game_keys IS
'Administrator-verified obsolete game keys. Reimports are skipped; canonical games and legitimate league rematches remain eligible.';
