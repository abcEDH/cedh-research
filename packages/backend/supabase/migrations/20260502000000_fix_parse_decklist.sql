-- Migration: Fix parse_decklist to handle escaped newlines and literal \n
-- This fix ensures that decklists from TopDeck that use literal \n or \r\n are correctly parsed.

CREATE OR REPLACE FUNCTION parse_decklist(decklist TEXT)
RETURNS TEXT[] AS $$
DECLARE
    lines TEXT[];
    result TEXT[];
    line TEXT;
    card_name TEXT;
BEGIN
    IF decklist IS NULL OR trim(decklist) = '' THEN
        RETURN '{}';
    END IF;

    -- Handle Moxfield URLs - can't parse without API
    IF decklist LIKE '%moxfield.com%' THEN
        RETURN '{}';
    END IF;

    -- Normalize escaped newlines (\n, \r\n) and actual newlines to a single format
    -- We use regexp_split_to_array to handle multiple newline formats
    lines := regexp_split_to_array(
        replace(replace(decklist, E'\\r\\n', chr(10)), E'\\n', chr(10)),
        E'[\\n\\r]+'
    );
    
    result := '{}';

    FOREACH line IN ARRAY lines LOOP
        line := trim(line);

        -- Skip section headers (~~Commanders~~, ~~Mainboard~~, etc.)
        IF line LIKE '~~%~~' OR line LIKE '~~%~~%' THEN
            CONTINUE;
        END IF;

        -- Skip empty lines
        IF line = '' OR line IS NULL THEN
            CONTINUE;
        END IF;

        -- Parse "N Card Name" format (e.g., "1 Sol Ring", "4 Island")
        -- We use a more robust regex that handles potential trailing whitespace or notes
        IF line ~ '^\d+\s+' THEN
            card_name := regexp_replace(line, '^\d+\s+', '');
            -- Strip potential trailing info in parentheses or after asterisks
            card_name := regexp_replace(card_name, '\s*\(.*\).*$', '');
            card_name := regexp_replace(card_name, '\s*\*.*$', '');
            
            IF card_name IS NOT NULL AND card_name != '' THEN
                result := array_append(result, card_name);
            END IF;
        END IF;
    END LOOP;

    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger a refresh of the materialized views to pick up the changes
-- Note: This might take a while for large datasets.
-- SELECT refresh_card_frequencies();
