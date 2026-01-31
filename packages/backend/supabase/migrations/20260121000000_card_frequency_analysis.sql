-- Card Frequency Analysis Migration
-- Phase 1 of Analytics Implementation Plan
-- Implements: decklist parsing function, card frequencies materialized view

-- ============================================================================
-- FUNCTION: Parse Decklist Text
-- ============================================================================

-- Parses TopDeck decklist format into array of card names
-- Format: "~~Commanders~~\n1 Card Name\n~~Mainboard~~\n1 Card Name\n..."
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

    -- Split by literal \n (TopDeck format uses escaped newlines)
    lines := string_to_array(decklist, '\n');
    result := '{}';

    FOREACH line IN ARRAY lines LOOP
        line := trim(line);

        -- Skip section headers (~~Commanders~~, ~~Mainboard~~, etc.)
        IF line LIKE '~~%~~' THEN
            CONTINUE;
        END IF;

        -- Skip empty lines
        IF line = '' OR line IS NULL THEN
            CONTINUE;
        END IF;

        -- Parse "N Card Name" format (e.g., "1 Sol Ring", "4 Island")
        IF line ~ '^\d+\s+' THEN
            card_name := regexp_replace(line, '^\d+\s+', '');
            IF card_name IS NOT NULL AND card_name != '' THEN
                result := array_append(result, card_name);
            END IF;
        END IF;
    END LOOP;

    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION parse_decklist(TEXT) TO anon, authenticated, service_role;

COMMENT ON FUNCTION parse_decklist IS 'Parses TopDeck decklist text format into an array of card names';

-- ============================================================================
-- FUNCTION: Classify Card Tier
-- ============================================================================

-- Classifies a card into a tier based on inclusion rate
-- Thresholds: core (80%+), essential (60-79%), common (30-59%), flex (10-29%), spice (<10%)
CREATE OR REPLACE FUNCTION classify_card_tier(inclusion_rate NUMERIC)
RETURNS TEXT AS $$
BEGIN
    RETURN CASE
        WHEN inclusion_rate >= 0.80 THEN 'core'
        WHEN inclusion_rate >= 0.60 THEN 'essential'
        WHEN inclusion_rate >= 0.30 THEN 'common'
        WHEN inclusion_rate >= 0.10 THEN 'flex'
        ELSE 'spice'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

GRANT EXECUTE ON FUNCTION classify_card_tier(NUMERIC) TO anon, authenticated, service_role;

COMMENT ON FUNCTION classify_card_tier IS 'Classifies a card tier based on inclusion rate: core(80%+), essential(60-79%), common(30-59%), flex(10-29%), spice(<10%)';

-- ============================================================================
-- MATERIALIZED VIEW: Card Frequencies by Commander
-- ============================================================================

-- Drop if exists (for re-running migration)
DROP MATERIALIZED VIEW IF EXISTS card_frequencies_by_commander;

-- Create materialized view for card frequencies
-- Note: Only includes decks with parseable decklist_text (not URL-only)
CREATE MATERIALIZED VIEW card_frequencies_by_commander AS
WITH deck_cards AS (
    -- Extract cards from each deck
    SELECT
        te.id AS entry_id,
        te.tournament_id,
        te.commander_id,
        unnest(parse_decklist(te.decklist_text)) AS card_name
    FROM tournament_entries te
    WHERE te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(te.decklist_text), 1) > 0
),
commander_totals AS (
    -- Count total decks per commander (only those with parsed decklists)
    SELECT
        commander_id,
        COUNT(DISTINCT id) AS total_decks
    FROM tournament_entries
    WHERE decklist_text IS NOT NULL
      AND decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(decklist_text), 1) > 0
    GROUP BY commander_id
)
SELECT
    c.id AS commander_id,
    c.name AS commander,
    dc.card_name,
    COUNT(DISTINCT dc.entry_id) AS deck_count,
    ct.total_decks,
    ROUND(
        COUNT(DISTINCT dc.entry_id)::NUMERIC / NULLIF(ct.total_decks, 0),
        4
    ) AS inclusion_rate,
    classify_card_tier(
        COUNT(DISTINCT dc.entry_id)::NUMERIC / NULLIF(ct.total_decks, 0)
    ) AS tier
FROM deck_cards dc
JOIN commanders c ON dc.commander_id = c.id
JOIN commander_totals ct ON dc.commander_id = ct.commander_id
GROUP BY c.id, c.name, dc.card_name, ct.total_decks
HAVING COUNT(DISTINCT dc.entry_id) >= 2  -- Minimum 2 appearances
ORDER BY c.name, COUNT(DISTINCT dc.entry_id) DESC;

-- Create indexes for efficient querying
CREATE UNIQUE INDEX idx_card_freq_pk ON card_frequencies_by_commander(commander_id, card_name);
CREATE INDEX idx_card_freq_commander ON card_frequencies_by_commander(commander_id);
CREATE INDEX idx_card_freq_commander_name ON card_frequencies_by_commander(commander);
CREATE INDEX idx_card_freq_card ON card_frequencies_by_commander(card_name);
CREATE INDEX idx_card_freq_tier ON card_frequencies_by_commander(tier);
CREATE INDEX idx_card_freq_rate ON card_frequencies_by_commander(inclusion_rate DESC);

COMMENT ON MATERIALIZED VIEW card_frequencies_by_commander IS 'Card inclusion frequencies per commander, refreshed manually';

-- ============================================================================
-- MATERIALIZED VIEW: Global Card Frequencies
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS card_frequencies_global;

-- Global card frequency across all commanders
CREATE MATERIALIZED VIEW card_frequencies_global AS
WITH deck_cards AS (
    SELECT
        te.id AS entry_id,
        unnest(parse_decklist(te.decklist_text)) AS card_name
    FROM tournament_entries te
    WHERE te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(te.decklist_text), 1) > 0
),
total_decks AS (
    SELECT COUNT(DISTINCT id) AS total
    FROM tournament_entries
    WHERE decklist_text IS NOT NULL
      AND decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(decklist_text), 1) > 0
)
SELECT
    dc.card_name,
    COUNT(DISTINCT dc.entry_id) AS deck_count,
    (SELECT total FROM total_decks) AS total_decks,
    ROUND(
        COUNT(DISTINCT dc.entry_id)::NUMERIC / NULLIF((SELECT total FROM total_decks), 0),
        4
    ) AS inclusion_rate,
    COUNT(DISTINCT te.commander_id) AS commander_count,
    classify_card_tier(
        COUNT(DISTINCT dc.entry_id)::NUMERIC / NULLIF((SELECT total FROM total_decks), 0)
    ) AS tier
FROM deck_cards dc
JOIN tournament_entries te ON dc.entry_id = te.id
GROUP BY dc.card_name
HAVING COUNT(DISTINCT dc.entry_id) >= 3  -- Minimum 3 appearances globally
ORDER BY COUNT(DISTINCT dc.entry_id) DESC;

CREATE UNIQUE INDEX idx_card_freq_global_pk ON card_frequencies_global(card_name);
CREATE INDEX idx_card_freq_global_tier ON card_frequencies_global(tier);
CREATE INDEX idx_card_freq_global_rate ON card_frequencies_global(inclusion_rate DESC);
CREATE INDEX idx_card_freq_global_cmd_count ON card_frequencies_global(commander_count DESC);

COMMENT ON MATERIALIZED VIEW card_frequencies_global IS 'Global card inclusion frequencies across all commanders';

-- ============================================================================
-- FUNCTION: Refresh Card Frequencies
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_card_frequencies()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY card_frequencies_by_commander;
    REFRESH MATERIALIZED VIEW CONCURRENTLY card_frequencies_global;
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION refresh_card_frequencies() TO service_role;

COMMENT ON FUNCTION refresh_card_frequencies IS 'Refreshes both card frequency materialized views';

-- ============================================================================
-- VIEW: Commander Card Report (convenient wrapper)
-- ============================================================================

CREATE OR REPLACE VIEW commander_card_report AS
SELECT
    cf.commander,
    cf.commander_id,
    cf.card_name,
    cf.deck_count,
    cf.total_decks,
    cf.inclusion_rate,
    cf.tier,
    gf.inclusion_rate AS global_rate,
    ROUND(cf.inclusion_rate - COALESCE(gf.inclusion_rate, 0), 4) AS synergy_score
FROM card_frequencies_by_commander cf
LEFT JOIN card_frequencies_global gf ON cf.card_name = gf.card_name
ORDER BY cf.commander, cf.inclusion_rate DESC;

COMMENT ON VIEW commander_card_report IS 'Card frequencies with synergy scores (commander rate - global rate)';

-- Grant read access
GRANT SELECT ON card_frequencies_by_commander TO anon, authenticated, service_role;
GRANT SELECT ON card_frequencies_global TO anon, authenticated, service_role;
GRANT SELECT ON commander_card_report TO anon, authenticated, service_role;
