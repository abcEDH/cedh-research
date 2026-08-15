-- Keep the canonical commander color identity in sync with Scryfall.
--
-- `commanders` stores both solo commanders and partner pairs. Scryfall card
-- metadata is cached per face in `scryfall_cards`, so resolve every face and
-- persist the ordered union only when Scryfall has metadata for all faces.

CREATE OR REPLACE FUNCTION public.sync_commander_scryfall_color_identities()
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    updated_count integer;
BEGIN
    WITH resolved AS (
        SELECT
            c.id,
            COUNT(DISTINCT face.name) = CARDINALITY(c.commander_names) AS all_faces_found,
            COALESCE(
                ARRAY_AGG(DISTINCT color.symbol ORDER BY ARRAY_POSITION(ARRAY['W', 'U', 'B', 'R', 'G'], color.symbol))
                    FILTER (WHERE color.symbol IS NOT NULL),
                ARRAY[]::text[]
            ) AS color_identity
        FROM public.commanders AS c
        CROSS JOIN LATERAL UNNEST(c.commander_names) AS face(name)
        LEFT JOIN public.scryfall_cards AS sc ON sc.name = face.name
        LEFT JOIN LATERAL UNNEST(sc.color_identity) AS color(symbol) ON TRUE
        GROUP BY c.id, c.commander_names
    )
    UPDATE public.commanders AS c
    SET
        color_identity = resolved.color_identity,
        updated_at = NOW()
    FROM resolved
    WHERE resolved.id = c.id
      AND resolved.all_faces_found
      AND c.color_identity IS DISTINCT FROM resolved.color_identity;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$;

-- Backfill current commanders immediately. Future Scryfall cache refreshes
-- call the same function after they upsert the latest metadata.
SELECT public.sync_commander_scryfall_color_identities();
