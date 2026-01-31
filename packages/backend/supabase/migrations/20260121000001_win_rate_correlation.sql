-- Win-Rate Correlation Analysis Migration
-- Phase 3 of Analytics Implementation Plan
-- Correlates card presence with tournament performance

-- ============================================================================
-- MATERIALIZED VIEW: Card Performance by Commander
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS card_performance_by_commander;

-- Card performance: correlates card presence with win rate
CREATE MATERIALIZED VIEW card_performance_by_commander AS
WITH deck_cards AS (
    -- Extract cards from each deck with performance data
    SELECT
        te.id AS entry_id,
        te.commander_id,
        te.win_rate,
        te.made_top_16,
        te.made_top_cut,
        te.final_standing,
        unnest(parse_decklist(te.decklist_text)) AS card_name
    FROM tournament_entries te
    WHERE te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(te.decklist_text), 1) > 0
      AND te.win_rate IS NOT NULL
),
card_stats AS (
    SELECT
        dc.commander_id,
        dc.card_name,
        COUNT(DISTINCT dc.entry_id) AS deck_count,
        AVG(dc.win_rate) AS avg_win_rate,
        STDDEV(dc.win_rate) AS std_win_rate,
        COUNT(*) FILTER (WHERE dc.made_top_16) AS top_16_count,
        COUNT(*) FILTER (WHERE dc.made_top_cut) AS top_cut_count,
        AVG(dc.final_standing) AS avg_standing
    FROM deck_cards dc
    GROUP BY dc.commander_id, dc.card_name
    HAVING COUNT(DISTINCT dc.entry_id) >= 5  -- Minimum sample size
),
commander_baseline AS (
    -- Get baseline win rate per commander (all decks)
    SELECT
        commander_id,
        AVG(win_rate) AS baseline_win_rate,
        COUNT(*) AS total_decks,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY win_rate) AS median_win_rate
    FROM tournament_entries
    WHERE win_rate IS NOT NULL
      AND decklist_text IS NOT NULL
      AND decklist_text NOT LIKE '%moxfield.com%'
    GROUP BY commander_id
)
SELECT
    c.id AS commander_id,
    c.name AS commander,
    cs.card_name,
    cs.deck_count,
    cb.total_decks,
    ROUND(cs.deck_count::NUMERIC / cb.total_decks, 4) AS inclusion_rate,
    ROUND(cs.avg_win_rate::NUMERIC, 4) AS avg_win_rate,
    ROUND(cb.baseline_win_rate::NUMERIC, 4) AS baseline_win_rate,
    ROUND((cs.avg_win_rate - cb.baseline_win_rate)::NUMERIC, 4) AS win_rate_delta,
    ROUND(cs.std_win_rate::NUMERIC, 4) AS std_win_rate,
    cs.top_16_count,
    cs.top_cut_count,
    ROUND(cs.top_16_count::NUMERIC / cs.deck_count, 4) AS top_16_rate,
    ROUND(cs.avg_standing::NUMERIC, 1) AS avg_standing,
    -- Performance tier based on delta from baseline
    CASE
        WHEN cs.avg_win_rate - cb.baseline_win_rate >= 0.05 THEN 'overperformer'
        WHEN cs.avg_win_rate - cb.baseline_win_rate <= -0.05 THEN 'underperformer'
        ELSE 'neutral'
    END AS performance_tier
FROM card_stats cs
JOIN commanders c ON cs.commander_id = c.id
JOIN commander_baseline cb ON cs.commander_id = cb.commander_id
ORDER BY c.name, cs.deck_count DESC;

CREATE UNIQUE INDEX idx_card_perf_pk ON card_performance_by_commander(commander_id, card_name);
CREATE INDEX idx_card_perf_commander ON card_performance_by_commander(commander_id);
CREATE INDEX idx_card_perf_card ON card_performance_by_commander(card_name);
CREATE INDEX idx_card_perf_delta ON card_performance_by_commander(win_rate_delta DESC);
CREATE INDEX idx_card_perf_tier ON card_performance_by_commander(performance_tier);

COMMENT ON MATERIALIZED VIEW card_performance_by_commander IS 'Card win rate correlation per commander with performance tiers';

-- ============================================================================
-- MATERIALIZED VIEW: Global Card Performance
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS card_performance_global;

CREATE MATERIALIZED VIEW card_performance_global AS
WITH deck_cards AS (
    SELECT
        te.id AS entry_id,
        te.commander_id,
        te.win_rate,
        te.made_top_16,
        unnest(parse_decklist(te.decklist_text)) AS card_name
    FROM tournament_entries te
    WHERE te.decklist_text IS NOT NULL
      AND te.decklist_text NOT LIKE '%moxfield.com%'
      AND array_length(parse_decklist(te.decklist_text), 1) > 0
      AND te.win_rate IS NOT NULL
),
global_baseline AS (
    SELECT
        AVG(win_rate) AS baseline_win_rate,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY win_rate) AS median_win_rate,
        COUNT(*) AS total_decks
    FROM tournament_entries
    WHERE win_rate IS NOT NULL
      AND decklist_text IS NOT NULL
),
card_stats AS (
    SELECT
        dc.card_name,
        COUNT(DISTINCT dc.entry_id) AS deck_count,
        COUNT(DISTINCT dc.commander_id) AS commander_count,
        AVG(dc.win_rate) AS avg_win_rate,
        STDDEV(dc.win_rate) AS std_win_rate,
        COUNT(*) FILTER (WHERE dc.made_top_16) AS top_16_count,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dc.win_rate) AS median_win_rate
    FROM deck_cards dc
    GROUP BY dc.card_name
    HAVING COUNT(DISTINCT dc.entry_id) >= 10  -- Higher threshold for global
)
SELECT
    cs.card_name,
    cs.deck_count,
    (SELECT total_decks FROM global_baseline) AS total_decks,
    ROUND(cs.deck_count::NUMERIC / (SELECT total_decks FROM global_baseline), 4) AS inclusion_rate,
    cs.commander_count,
    ROUND(cs.avg_win_rate::NUMERIC, 4) AS avg_win_rate,
    ROUND((SELECT baseline_win_rate FROM global_baseline)::NUMERIC, 4) AS baseline_win_rate,
    ROUND((cs.avg_win_rate - (SELECT baseline_win_rate FROM global_baseline))::NUMERIC, 4) AS win_rate_delta,
    ROUND(cs.std_win_rate::NUMERIC, 4) AS std_win_rate,
    ROUND(cs.median_win_rate::NUMERIC, 4) AS median_win_rate,
    cs.top_16_count,
    ROUND(cs.top_16_count::NUMERIC / cs.deck_count, 4) AS top_16_rate,
    -- Trap card identification: high popularity + below median performance
    CASE
        WHEN cs.deck_count::NUMERIC / (SELECT total_decks FROM global_baseline) >= 0.20
             AND cs.avg_win_rate < (SELECT median_win_rate FROM global_baseline)
        THEN TRUE
        ELSE FALSE
    END AS is_potential_trap,
    -- Spice card identification: low popularity + above median performance
    CASE
        WHEN cs.deck_count::NUMERIC / (SELECT total_decks FROM global_baseline) < 0.10
             AND cs.avg_win_rate > (SELECT baseline_win_rate FROM global_baseline) + 0.03
        THEN TRUE
        ELSE FALSE
    END AS is_spice
FROM card_stats cs
ORDER BY cs.deck_count DESC;

CREATE UNIQUE INDEX idx_card_perf_global_pk ON card_performance_global(card_name);
CREATE INDEX idx_card_perf_global_delta ON card_performance_global(win_rate_delta DESC);
CREATE INDEX idx_card_perf_global_trap ON card_performance_global(is_potential_trap) WHERE is_potential_trap = TRUE;
CREATE INDEX idx_card_perf_global_spice ON card_performance_global(is_spice) WHERE is_spice = TRUE;

COMMENT ON MATERIALIZED VIEW card_performance_global IS 'Global card performance with trap and spice identification';

-- ============================================================================
-- VIEW: Trap Cards Report
-- ============================================================================

CREATE OR REPLACE VIEW trap_cards_report AS
SELECT
    card_name,
    deck_count,
    inclusion_rate,
    avg_win_rate,
    baseline_win_rate,
    win_rate_delta,
    top_16_rate,
    commander_count,
    ROUND(inclusion_rate * ABS(win_rate_delta), 4) AS trap_score
FROM card_performance_global
WHERE is_potential_trap = TRUE
ORDER BY inclusion_rate * ABS(win_rate_delta) DESC;

COMMENT ON VIEW trap_cards_report IS 'Cards that are popular but underperform - potential traps';

-- ============================================================================
-- VIEW: Spice Cards Report
-- ============================================================================

CREATE OR REPLACE VIEW spice_cards_report AS
SELECT
    card_name,
    deck_count,
    inclusion_rate,
    avg_win_rate,
    baseline_win_rate,
    win_rate_delta,
    top_16_rate,
    commander_count
FROM card_performance_global
WHERE is_spice = TRUE
ORDER BY win_rate_delta DESC;

COMMENT ON VIEW spice_cards_report IS 'Low-popularity cards that overperform - hidden gems';

-- ============================================================================
-- FUNCTION: Refresh Performance Views
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_card_performance()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY card_performance_by_commander;
    REFRESH MATERIALIZED VIEW CONCURRENTLY card_performance_global;
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION refresh_card_performance() TO service_role;

-- Grant read access
GRANT SELECT ON card_performance_by_commander TO anon, authenticated, service_role;
GRANT SELECT ON card_performance_global TO anon, authenticated, service_role;
GRANT SELECT ON trap_cards_report TO anon, authenticated, service_role;
GRANT SELECT ON spice_cards_report TO anon, authenticated, service_role;
