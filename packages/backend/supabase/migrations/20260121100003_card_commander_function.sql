-- Migration: Card-Commander Cross Reference Function
-- Required by: Frontend /cards commander usage column

-- Index for efficient card->commander lookups on cards page
CREATE INDEX IF NOT EXISTS idx_card_freq_by_commander_cardname
ON card_frequencies_by_commander(card_name);

-- Function to get commanders using a specific card
CREATE OR REPLACE FUNCTION get_commanders_for_card(p_card_name TEXT)
RETURNS TABLE (
    commander_id UUID,
    commander_name TEXT,
    deck_count BIGINT,
    inclusion_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cf.commander_id,
        cf.commander,
        cf.deck_count::BIGINT,
        cf.inclusion_rate::NUMERIC
    FROM card_frequencies_by_commander cf
    WHERE cf.card_name = p_card_name
    ORDER BY cf.deck_count DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql STABLE;

GRANT EXECUTE ON FUNCTION get_commanders_for_card(TEXT) TO anon;
GRANT EXECUTE ON FUNCTION get_commanders_for_card(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_commanders_for_card(TEXT) TO service_role;
